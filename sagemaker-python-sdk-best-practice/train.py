# -*- coding: utf-8 -*-
"""
Training script for the NRE + AQ Bottom Decile Ranker.

Runs inside a SageMaker container via ``sagemaker_train.py``. Connects to the
parent MLflow run started by the orchestrator, loads the raw NRE+AQ panel from
S3 (logged by ``preprocessing.py``), attaches index-relative returns, builds
the labeled and cross-sectionally standardised modeling frame, and trains a
LightGBM ranker per horizon.

$ python -m models.negative_engine.train

Usage:
    models.negative_engine.train [--horizons=<days>] [--decile=<decile>] [--register]

Options:
    -h --help               Show this help dialogue
    --horizons=<days>       Comma-separated horizons in days [default: 360,720,1080]
    --decile=<decile>       Bottom-decile fraction [default: 0.1]
    --register              Register trained models in the MLflow model registry
"""
import os

import docopt
import mlflow
import numpy as np
import pandas as pd

from ifp_common import core, ml_data_storage
from ifp_common.database import DBEngine
from models.modelling_utils import mlflow_utils
from models.modelling_utils import modeling as nre_modeling
from models.modelling_utils.model_prep import get_index_relative_returns
from models.modelling_utils.sagemaker_sdk import (
    DATA_FOLDER,
    DATASET_FILENAME,
    PROCESSING_INPUT_PATH,
)
from models.negative_engine.model_utils import nre_util, train_utils

log = core.configure_logger(__name__)

# Training constants
RANDOM_STATE = 42
DATE_COL = "date"
ID_COL = "ciq_id"
DEFAULT_RET_HORIZONS: tuple[int, ...] = (360, 720, 1080)
DECILE_FRAC = 0.10
USE_RET_THRESHOLD = False
RET_THRESHOLD = -0.05
MIN_TRAIN_MONTHS = 24
MAX_CV_SPLITS = None


def main(
    horizons: str | None = None,
    decile: float = DECILE_FRAC,
    register: bool = False,
) -> None:
    """
    Load the raw NRE+AQ panel from S3, attach returns, and train per horizon.

    Parameters
    ----------
    horizons : str, optional
        Comma-separated horizon days (e.g. ``"360,720,1080"``).
    decile : float, optional
        Bottom-decile fraction. Default is 0.10.
    register : bool, optional
        Register trained models in the MLflow model registry.
    """
    horizon_list = (
        [int(h.strip()) for h in horizons.split(",")]
        if horizons
        else list(DEFAULT_RET_HORIZONS)
    )
    ret_cols = [f"rel_ret_{h}d" for h in horizon_list]

    mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
    mlflow.set_experiment(experiment_id=os.environ["MLFLOW_EXPERIMENT_ID"])
    run_id = os.environ["MLFLOW_RUN_ID"]

    with mlflow.start_run(run_id=run_id):
        preprocessing_output = PROCESSING_INPUT_PATH + DATA_FOLDER + DATASET_FILENAME
        log.info("Reading preprocessed data from %s", preprocessing_output)
        df_raw = pd.read_parquet(preprocessing_output)
        ml_data_storage.store_or_reuse_dataset_in_s3_and_log(
            df_raw,
            "train",
            s3_bucket_path=f"nre_aq_training/{run_id}",
            context="training",
        )

        log.info("Attaching index-relative returns")
        engine = DBEngine(core.config)
        df_panel = get_index_relative_returns(
            df_raw, date_col="date_asof", engine=engine
        )

        if DATE_COL not in df_panel.columns:
            df_panel[DATE_COL] = nre_util.snap_to_month_end(df_panel["date_asof"])

        df_panel = df_panel.sort_values([ID_COL, DATE_COL]).drop_duplicates(
            [ID_COL, DATE_COL], keep="last"
        )
        log.info("Training panel after returns: %d rows x %d cols", *df_panel.shape)

        df_model, model_feature_cols, _ = train_utils.build_model_frame(
            df_panel, ret_cols, decile_frac=decile
        )
        for horizon in horizon_list:
            train_utils.train_horizon(
                df_model,
                model_feature_cols,
                horizon,
                register,
                run_id,
                decile_frac=decile,
            )


if __name__ == "__main__":
    cmd_args = core.handle_docopt_arguments(docopt.docopt(__doc__))
    if cmd_args.get("decile") is not None:
        cmd_args["decile"] = float(cmd_args["decile"])
    main(**cmd_args)
