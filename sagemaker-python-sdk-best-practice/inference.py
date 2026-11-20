# -*- coding: utf-8 -*-
"""
It is expected that this script will be run from the inference script via the sagemaker SDK.
It can be run independently but the data inputs need to be stored locally. This can be done
by running the preprocessing script.

$ python -m models.negative_engine.processing

Usage:
    models.negative_engine.processing [--horizon=<days>] [--decile=<decile>]

Options:
    -h --help                       Show this help dialogue
    --horizon=<days>                Prediction horizon in days [default: 360]
    --decile=<decile>               Bottom-decile fraction (e.g. 0.10 = bottom 10%) [default: 0.1]
"""

import os
import pickle
from pathlib import Path

import docopt
import mlflow
import pandas as pd

from ifp_common import core, ml_data_storage
from models.modelling_utils.sagemaker_sdk import (
    DATA_FOLDER,
    DATASET_FILENAME,
    IMPORTANCES_FILENAME,
    MODEL_ARTIFACTS_FOLDER,
    MODEL_PKL_PATH,
    OUTPUT_FOLDER,
    PREDICTIONS_FILENAME,
    PROCESSING_INPUT_PATH,
)
from models.negative_engine.nre import get_processing_data

log = core.configure_logger(__name__)


def main(
    horizon: int,
    decile: float,
) -> None:
    """
    Run inference inside a SageMaker container: load the preprocessed dataset,
    run the AQ model, and write predictions and feature importances to the output folder.

    Parameters
    ----------
    horizon : int
        Prediction horizon in days (e.g. 360).
    decile : float
        Fraction of universe to flag as bottom decile (e.g. 0.10).
    """
    mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
    mlflow.start_run(run_id=os.environ["MLFLOW_RUN_ID"])

    data_path = PROCESSING_INPUT_PATH + DATA_FOLDER
    model_path = PROCESSING_INPUT_PATH + MODEL_ARTIFACTS_FOLDER

    log.info("Data Files: %s", sorted(p.name for p in Path(data_path).iterdir()))
    log.info("Model Files: %s", sorted(p.name for p in Path(model_path).iterdir()))

    with open(model_path + MODEL_PKL_PATH, "rb") as f:
        aq_model = pickle.load(f)

    input_file_path = data_path + DATASET_FILENAME
    if not Path(input_file_path).exists():
        log.warning(
            "NRE inference: Input dataset not found: %s. "
            "This is probably due to an error in the preprocessing script.",
            input_file_path,
        )
        return
    df_all = pd.read_parquet(input_file_path)
    ml_data_storage.store_or_reuse_dataset_in_s3_and_log(
        df_all, "processing", context="inference"
    )

    df_pred, df_importances = get_processing_data(df_all, aq_model, decile, horizon)

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    df_pred.to_parquet(OUTPUT_FOLDER + PREDICTIONS_FILENAME)
    importances_out = df_importances if df_importances is not None else pd.DataFrame()
    importances_out.to_parquet(OUTPUT_FOLDER + IMPORTANCES_FILENAME)


if __name__ == "__main__":
    cmd_args = core.handle_docopt_arguments(docopt.docopt(__doc__))
    if "horizon" in cmd_args:
        cmd_args["horizon"] = int(cmd_args["horizon"])
    if "decile" in cmd_args:
        cmd_args["decile"] = float(cmd_args["decile"])
    main(**cmd_args)
