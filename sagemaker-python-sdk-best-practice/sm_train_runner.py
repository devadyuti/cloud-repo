# -*- coding: utf-8 -*-
"""
Training runner for the NRE + AQ Bottom Decile Ranker.

Orchestrates the training pipeline using the SageMaker SDK:

1. Starts a parent MLflow run.
2. Runs ``preprocessing.py`` inside a SageMaker processing job — loads the full
   NRE+AQ panel and logs it to S3 as ``raw_data`` and ``preprocessing_output``.
3. Runs ``train.py`` inside a SageMaker processing job — attaches returns, builds
   the modeling frame, and trains one LightGBM model per horizon.

$ python -m models.negative_engine.train_runner

Usage:
    models.negative_engine.train_runner [--horizon=<days>] [--decile=<decile>]
                                        [--register]

Options:
    -h --help                       Show this help dialogue
    --horizon=<days>                Comma-separated horizons in days [default: 360,720,1080]
    --decile=<decile>               Bottom-decile fraction [default: 0.1]
    --register                      Register trained models in the MLflow model registry
"""
import tempfile
from typing import Optional

import boto3
import docopt
import mlflow
import pandas as pd
from sagemaker.core.local.local_session import Session
from sagemaker.core.network import NetworkConfig
from sagemaker.core.processing import FrameworkProcessor
from sagemaker.core.shapes import (
    ProcessingInput,
    ProcessingOutput,
    ProcessingS3Input,
    ProcessingS3Output,
)

from ifp_common import core
from models.modelling_utils import mlflow_utils
from models.modelling_utils.sagemaker_sdk import (
    DATA_FOLDER,
    MODEL_FOLDER,
    OUTPUT_FOLDER,
    PROCESSING_INPUT_PATH,
    build_local_code_bundle,
    get_env_vars,
)

log = core.configure_logger(__name__)

SAGEMAKER_IMAGE_URI = (
    "578285294703.dkr.ecr.eu-west-2.amazonaws.com/invtools-sklearn:0.2-cpu-py3.13"
)
MLFLOW_EXPERIMENT = "nre_aq_ranker_v2_"
DEFAULT_HORIZONS = "360,720,1080"
DEFAULT_INSTANCE_TYPE = "ml.m5.4xlarge"


def main(
    horizon: Optional[str] = None,
    decile: float = 0.1,
    register: bool = False,
) -> None:
    """
    Orchestrate the NRE AQ training pipeline via SageMaker processing jobs.

    Parameters
    ----------
    horizon : str, optional
        Comma-separated horizon days (e.g. ``"360,720,1080"``).
    decile : float, optional
        Bottom-decile fraction. Default is 0.10.
    register : bool, optional
        Register trained models in the MLflow model registry.
    """
    horizon_list = [int(h.strip()) for h in (horizon or DEFAULT_HORIZONS).split(",")]
    now = pd.Timestamp.now().strftime("%Y-%m-%d:%H-%M")

    mlflow_utils.init_experiment(MLFLOW_EXPERIMENT, staging=False)
    run_name = f"nre_aq_train_{now}"
    mlflow_utils.start_run(
        run_name=run_name,
        model_name="nre_aq",
        model_type="lightgbm",
        stage="development",
        run_type="train",
        description=(
            f"NRE AQ ranker training. {now}. "
            f"Horizons: {horizon_list}. Bottom decile: {decile:.0%}."
        ),
        store_code=False,
        force=True,
    )
    mlflow.log_params(
        {
            "horizons": str(horizon_list),
            "decile": decile,
            "instance_type": DEFAULT_INSTANCE_TYPE,
        }
    )
    run_id = mlflow.active_run().info.run_id
    experiment_id = mlflow.active_run().info.experiment_id

    env_vars = get_env_vars(include_credentials=False)
    env_vars["MLFLOW_RUN_ID"] = run_id
    env_vars["MLFLOW_TRACKING_URI"] = mlflow_utils.MLFLOW_SERVER_URI
    env_vars["MLFLOW_EXPERIMENT_ID"] = experiment_id

    vpc_conf = core.config["aws"]["sagemaker"]["vpc"]
    network_config = NetworkConfig(
        subnets=vpc_conf["subnets"],
        security_group_ids=vpc_conf["security_group_ids"],
    )
    session = Session(boto_session=boto3.Session())
    processor = FrameworkProcessor(
        image_uri=SAGEMAKER_IMAGE_URI,
        role=core.config["aws"]["sagemaker"]["role_arn"],
        instance_type=DEFAULT_INSTANCE_TYPE,
        instance_count=1,
        env=env_vars,
        command=["bash"],
        sagemaker_session=session,
        network_config=network_config,
    )

    code_path = build_local_code_bundle(
        s3_key_prefix=f"local_code_bundles/{MLFLOW_EXPERIMENT}/{run_id}"
    )
    log.info("Using local code bundle: %s", code_path)

    code_input = ProcessingInput(
        input_name="code",
        s3_input=ProcessingS3Input(
            s3_uri=code_path,
            local_path=PROCESSING_INPUT_PATH + MODEL_FOLDER,
            s3_data_type="S3Prefix",
            s3_input_mode="File",
        ),
    )

    s3_processing_path = f"ml_processing/{MLFLOW_EXPERIMENT}/{now}_{run_id}/"
    s3_processing_path_full = (
        f"s3://{core.config['aws']['bucket']['read_bucket']}/{s3_processing_path}"
    )
    mlflow.log_param("s3_processing_path", s3_processing_path_full)

    preprocessing_output = ProcessingOutput(
        output_name="output",
        s3_output=ProcessingS3Output(
            s3_uri=s3_processing_path_full,
            local_path=OUTPUT_FOLDER,
            s3_upload_mode="EndOfJob",
        ),
    )

    data_input = ProcessingInput(
        input_name="data",
        s3_input=ProcessingS3Input(
            s3_uri=s3_processing_path_full,
            local_path=PROCESSING_INPUT_PATH + DATA_FOLDER,
            s3_data_type="S3Prefix",
            s3_input_mode="File",
        ),
    )

    try:
        with tempfile.TemporaryDirectory() as entrypoint_dir:
            processor.run(
                code=code_path + "/code/run_model.sh",
                source_dir=entrypoint_dir,
                arguments=["models.negative_engine.preprocessing"],
                wait=True,
                inputs=[code_input],
                outputs=[preprocessing_output],
            )

            train_arguments = [
                "models.negative_engine.train",
                "--horizons",
                horizon or DEFAULT_HORIZONS,
                "--decile",
                str(decile),
            ]
            if register:
                train_arguments.append("--register")

            processor.run(
                code=code_path + "/code/run_model.sh",
                source_dir=entrypoint_dir,
                arguments=train_arguments,
                wait=True,
                inputs=[code_input, data_input],
            )
        mlflow.end_run()
    except Exception:
        log.error("Training pipeline failed", exc_info=True)
        mlflow.end_run(status="FAILED")
        raise
    finally:
        core.docker_prune()


if __name__ == "__main__":
    cmd_args = core.handle_docopt_arguments(docopt.docopt(__doc__))
    if cmd_args.get("decile") is not None:
        cmd_args["decile"] = float(cmd_args["decile"])
    main(**cmd_args)
