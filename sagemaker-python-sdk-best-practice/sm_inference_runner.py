# -*- coding: utf-8 -*-
"""
Runs the preprocessing and processing steps of the NRE model with AQ features
as well as the upload and mlflow run tracking.

$ python -m models.negative_engine.sagemaker_runner

Usage:
    models.negative_engine.sagemaker_runner [--horizon=<days>] [--decile=<decile>] [--upload]
                                            [--local-code] [--alias=<alias>]

Options:
    -h --help                               Show this help dialogue
    --horizon=<days>                        Prediction horizon in days [default: 360]
    --decile=<decile>                       Fraction of universe to flag (e.g., 0.10 = bottom decile) [default: 0.1]
    --upload                                Boolean of whether to upload to RDS after run
    --local-code                            Package and upload current local repo code to S3 instead
                                            of using the code bundle from the registered model
    --alias=<alias>                         Alias of the registered model to use for inference [default: production]
"""
import uuid

import boto3
import docopt
import mlflow
import pandas as pd
from sagemaker.core.local.local_session import LocalSession
from sagemaker.core.processing import FrameworkProcessor
from sagemaker.core.shapes import (
    ProcessingInput,
    ProcessingOutput,
    ProcessingS3Input,
    ProcessingS3Output,
)

from database.models.model.model import Prediction, PredictionFeatureImportance
from ifp_common import core
from ifp_common.database import DBEngine, DBTable
from ifp_common.io.s3 import S3Connection
from models.modelling_utils import mlflow_utils
from models.modelling_utils.sagemaker_sdk import (
    DATA_FOLDER,
    IMPORTANCES_FILENAME,
    MODEL_ARTIFACTS_FOLDER,
    MODEL_FOLDER,
    OUTPUT_FOLDER,
    PREDICTIONS_FILENAME,
    PROCESSING_INPUT_PATH,
    SAGEMAKER_TMP_DIR,
    build_local_code_bundle,
    cleanup_sagemaker_tmp,
    get_env_vars,
)

log = core.configure_logger(__name__)

SAGEMAKER_IMAGE_URI = (
    "578285294703.dkr.ecr.eu-west-2.amazonaws.com/invtools-sklearn:0.2-cpu-py3.13"
)
MLFLOW_EXPERIMENT = "nre_aq_ranker_v2_"


def main(
    horizon: int = 360,
    decile: float = 0.1,
    upload: bool = False,
    local_code: bool = False,
    alias: str = "production",
) -> None:
    """
    Orchestrate the NRE AQ inference pipeline via SageMaker local processing jobs.

    Parameters
    ----------
    horizon : int, optional
        Prediction horizon in days. Default is 360.
    decile : float, optional
        Fraction of universe to flag as bottom decile. Default is 0.10.
    upload : bool, optional
        Upload predictions and feature importances to the database after the run.
    local_code : bool, optional
        If True, package and upload current local repo code to S3 rather than
        using the code bundle from the registered model.
    alias : str, optional
        Alias of the registered model to use for inference. Default is ``"production"``.
    """
    now = pd.Timestamp.now().strftime("%Y-%m-%d:%H-%M")

    model_name = f"nre_aq_{horizon}d"
    model_uri = f"models:/{model_name}@{alias}"
    run_name = f"{model_name}_{now}"

    mlflow_utils.init_experiment(MLFLOW_EXPERIMENT)
    mlflow_utils.start_run(
        run_name=run_name,
        model_name=model_name,
        model_type="lightgbm",
        stage=alias,
        run_type="inference",
        description=f"NRE AQ v3 inference run via SageMaker local processing jobs. {now}",
        store_code=False,
        force=True,
    )
    run_id = mlflow.active_run().info.run_id

    s3_processing_path = f"ml_processing/{MLFLOW_EXPERIMENT}/{now}_{run_id}/"
    s3_processing_path_full = (
        f"s3://{core.config['aws']['bucket']['read_bucket']}/{s3_processing_path}"
    )

    log.info(
        f"NRE inference: attempting to pull from model registry: {model_name}@{alias}"
    )
    client = mlflow.MlflowClient()
    model_version = client.get_model_version_by_alias(model_name, alias)
    model_path = client.get_model_version_download_uri(
        model_name, model_version.version
    )
    log.info(f"NRE inference: model artifact URI: {model_path}")

    if local_code:
        code_path = build_local_code_bundle(
            s3_key_prefix=f"local_code_bundles/{MLFLOW_EXPERIMENT}/{run_name}"
        )
        log.info("Using local code bundle: %s", code_path)
    else:
        code_path = model_path

    mlflow.log_params(
        {
            "model_uri": model_uri,
            "model_id": model_version.model_id,
            "model_training_run_id": model_version.run_id,
            "s3_processing_path": s3_processing_path_full,
            "horizon": horizon,
            "decile": decile,
            "local_code": local_code,
        }
    )

    # sets tmp file location on docker to SAGEMAKER_TMP_DIR so that it can be cleaned up later
    core.docker_prune()
    run_tmp_dir = SAGEMAKER_TMP_DIR / str(uuid.uuid1())[:8]
    run_tmp_dir.mkdir(parents=True, exist_ok=True)
    local_session = LocalSession(boto_session=boto3.Session())
    local_session.config = {"local": {"container_root": str(run_tmp_dir)}}

    env_vars = get_env_vars()
    env_vars["MLFLOW_RUN_ID"] = run_id
    env_vars["MLFLOW_TRACKING_URI"] = mlflow_utils.MLFLOW_SERVER_URI

    processor = FrameworkProcessor(
        image_uri=SAGEMAKER_IMAGE_URI,
        role=core.config["aws"]["sagemaker"]["role_arn"],
        instance_type="local",
        instance_count=1,
        env=env_vars,
        command=["bash"],
        sagemaker_session=local_session,
    )

    # Build a minimal source directory containing nothing so that
    # the SDK doesn't package the entire repo root into sourcedir.tar.gz.
    entrypoint_dir = run_tmp_dir / "tmp_empty"
    entrypoint_dir.mkdir()

    code_input = ProcessingInput(
        input_name="code",
        s3_input=ProcessingS3Input(
            s3_uri=code_path,
            local_path=PROCESSING_INPUT_PATH + MODEL_FOLDER,
            s3_data_type="S3Prefix",
            s3_input_mode="File",
        ),
    )
    model_artifacts_input = ProcessingInput(
        input_name="model_artifacts",
        s3_input=ProcessingS3Input(
            s3_uri=model_path,
            local_path=PROCESSING_INPUT_PATH + MODEL_ARTIFACTS_FOLDER,
            s3_data_type="S3Prefix",
            s3_input_mode="File",
        ),
    )

    try:
        processor.run(
            code=code_path + "/code/run_model.sh",
            source_dir=str(entrypoint_dir),
            arguments=["models.negative_engine.preprocessing"],
            wait=False,
            inputs=[code_input],
            outputs=[
                ProcessingOutput(
                    output_name="output",
                    s3_output=ProcessingS3Output(
                        s3_uri=s3_processing_path_full,
                        local_path=OUTPUT_FOLDER,
                        s3_upload_mode="EndOfJob",
                    ),
                )
            ],
        )

        processor.run(
            code=code_path + "/code/run_model.sh",
            source_dir=str(entrypoint_dir),
            arguments=[
                "models.negative_engine.processing",
                "--horizon",
                str(horizon),
                "--decile",
                str(decile),
            ],
            wait=False,
            inputs=[
                code_input,
                ProcessingInput(
                    input_name="data",
                    s3_input=ProcessingS3Input(
                        s3_uri=s3_processing_path_full,
                        local_path=PROCESSING_INPUT_PATH + DATA_FOLDER,
                        s3_data_type="S3Prefix",
                        s3_input_mode="File",
                    ),
                ),
                model_artifacts_input,
            ],
            outputs=[
                ProcessingOutput(
                    output_name="output",
                    s3_output=ProcessingS3Output(
                        s3_uri=s3_processing_path_full,
                        local_path=OUTPUT_FOLDER,
                        s3_upload_mode="EndOfJob",
                    ),
                )
            ],
        )

        mlflow_utils.log_run_manifest(
            model_uri=model_uri,
            docker_image=SAGEMAKER_IMAGE_URI,
        )
        mlflow.end_run()
    except Exception:
        log.error("NRE inference failed", exc_info=True)
        mlflow.end_run(status="FAILED")
        raise
    finally:
        cleanup_sagemaker_tmp(run_tmp_dir)
        core.docker_prune()

    if upload:
        s3 = S3Connection(core.config)
        df_pred = s3.retrieve_s3_object(
            PREDICTIONS_FILENAME,
            s3_processing_path,
            action="dataframe",
            filetype="parquet",
        )
        df_importances = s3.retrieve_s3_object(
            IMPORTANCES_FILENAME,
            s3_processing_path,
            action="dataframe",
            filetype="parquet",
        )

        engine = DBEngine(core.config)
        pred_table = DBTable(Prediction, engine)
        model_name = f"nre_aq_{horizon}d_sagemaker"

        if pred_table.table_exists():
            for dt in df_pred.date_asof.unique():
                pred_table.delete_where(
                    f"date_asof = '{dt}'"
                    f" AND model_name = '{model_name}'"
                    f" AND horizon = {horizon}"
                    f" AND model_alias = '{alias}'"
                )
        df_pred["model_name"] = model_name
        df_pred["mlflow_run_id"] = run_id
        df_pred["model_alias"] = alias
        df_pred["model_version"] = model_version.version
        pred_table.upload(df_pred[pred_table.columns], "upsert")

        if df_importances is not None and not df_importances.empty:
            importances_table = DBTable(PredictionFeatureImportance, engine)
            importances_table.upload(
                df_importances[importances_table.columns], "upsert"
            )


if __name__ == "__main__":
    cmd_args = core.handle_docopt_arguments(docopt.docopt(__doc__))
    # Convert types
    if "horizon" in cmd_args:
        cmd_args["horizon"] = int(cmd_args["horizon"])
    if "decile" in cmd_args:
        cmd_args["decile"] = float(cmd_args["decile"])
    main(**cmd_args)
