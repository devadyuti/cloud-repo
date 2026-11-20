# -*- coding: utf-8 -*-
"""
Loads the NRE+AQ panel from the feature store and writes it to the SageMaker
output folder. Expected to be run from the sagemaker SDK (via either
``sagemaker_runner.py`` for inference or ``train_runner.py`` for training)
but can be run independently, in which case output is saved locally.

$ python -m models.negative_engine.preprocessing

Usage:
    models.negative_engine.preprocessing

Options:
    -h --help    Show this help dialogue
"""
import os

from ifp_common import core
from ifp_common.database import DBEngine
from models.modelling_utils.sagemaker_sdk import DATASET_FILENAME, OUTPUT_FOLDER
from models.negative_engine import nre

log = core.configure_logger(__name__)


def main():
    log.info(f"Running NRE preprocessing with output filename: {DATASET_FILENAME}")
    engine = DBEngine(core.config)

    df_preprocessed = nre.get_preprocessing_data(engine)
    if df_preprocessed is None:
        log.warning(
            "NRE preprocessing: no data returned from feature store after merge, skipping"
        )
        return

    log.info("Writing preprocessed dataset to output folder")
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    df_preprocessed.to_parquet(OUTPUT_FOLDER + DATASET_FILENAME)
    log.info("Dataset written to %s", OUTPUT_FOLDER + DATASET_FILENAME)


if __name__ == "__main__":
    main()
