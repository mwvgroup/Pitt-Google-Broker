#!/usr/bin/env python
#
# Mar 6 2024 RK
#  +  minor refactor in main to accept optional --heatmaps_subdir argument that
#     is useful for side-by-side testing of scone codes or options. This code
#     should still be compatible with both original and refactored scone codes
#
import os
import numpy as np
import pandas as pd
import yaml
import tensorflow as tf
from tensorflow.keras import layers, models
import time
import json

from data_utils import *
from scone_utils import *  # RK - should merge with data_utils ?
import scone_utils as util

# =====================================================
# =====================================================


class SconeClassifier:
    # define my own reshape layer
    class Reshape(layers.Layer):
        def call(self, inputs):
            return tf.transpose(inputs, perm=[0, 3, 2, 1])

        def get_config(self):  # for model saving/loading
            return {}

    def __init__(self, config):
        self.scone_config = config
        self.seed = config.get("seed", 42)

        self.output_path = config["output_path"]
        self.heatmaps_paths = (
            config["heatmaps_paths"] if "heatmaps_paths" in config else config["heatmaps_path"]
        )  # #TODO(6/21/23): eventually remove, for backwards compatibility
        self.mode = config["mode"]

        self.strategy = tf.distribute.MirroredStrategy()
        self.batch_size_per_replica = config.get("batch_size", 32)
        self.batch_size = self.batch_size_per_replica * self.strategy.num_replicas_in_sync
        print(
            f"batch size in config: {self.batch_size_per_replica}, num replicas: {self.strategy.num_replicas_in_sync}, true batch size: {self.batch_size}"
        )

        self.num_epochs = config["num_epochs"]
        self.input_shape = (config["num_wavelength_bins"], config["num_mjd_bins"], 2)
        self.categorical = config.setdefault("categorical", False)
        self.types = config.get("types", None)
        if self.categorical and self.types is None:
            raise KeyError(
                "cannot perform categorical classification without knowing the number of source types! please specify the `types` key in your config file to reflect this information"
            )
            # TODO: should i write num types info into a file after create heatmaps? maybe ids file will be large
            # ids_file = h5py.File(config['ids_path'], "r")
            # types = [x.decode('utf-8').split("_")[0] for x in ids_file["names"]]
            # ids_file.close()
            # self.num_types = len(np.unique(types))
        self.num_types = len(self.types) if self.categorical else 2
        self.train_proportion = config.get("train_proportion", 0.8)
        self.with_z = config.get("with_z", False)
        self.abundances = None
        self.train_set = self.val_set = self.test_set = None
        self.class_balanced = config.get("class_balanced", True)
        self.external_trained_model = config.get("trained_model")
        self.prob_column_name = config.setdefault("prob_column_name", "PROB_SCONE")  # RK

        self.LEGACY = "sim_fraction" in config
        self.REFAC = not self.LEGACY
        print(f"LEGACY code: {self.LEGACY}")

        return

    def run(self, raw_dataset):
        tf.random.set_seed(self.seed)
        self.trained_model = None

        if self.external_trained_model:
            print(f"loading trained model found at {self.external_trained_model}")
            self.trained_model = models.load_model(
                self.external_trained_model, custom_objects={"Reshape": self.Reshape}
            )

        dataset = self._retrieve_data(raw_dataset)
        predict_dict = self.predict(dataset)
        return predict_dict

    def predict(self, dataset):
        if self.external_trained_model and not self.trained_model:
            self.trained_model = models.load_model(
                self.external_trained_model, custom_objects={"Reshape": self.Reshape}
            )

        if not self.trained_model:
            raise RuntimeError(
                "model has not been trained! call `train` on the SconeClassifier instance before predict!"
            )

        dataset = (
            dataset.cache()
        )  # otherwise the rest of the dataset operations won't return entries in the same order
        dataset_no_ids = dataset.map(lambda image, *_: (image)).batch(self.batch_size)

        predictions = self.trained_model.predict(dataset_no_ids, verbose=0)

        if self.categorical:
            predictions = np.argmax(
                predictions, axis=1
            )  # TODO: is this the best way to return categorical results? doesnt preserve confidence info
        predictions = predictions.flatten()

        df_dict = {
            "pred_labels": predictions,
        }

        return df_dict

    def _retrieve_data(self, raw_dataset):
        _dataset = tf.data.Dataset.from_tensor_slices([raw_dataset])
        dataset = _dataset.map(
            lambda x: get_images(x, self.input_shape, self.with_z),
            num_parallel_calls=tf.data.experimental.AUTOTUNE,
        )

        return dataset.apply(tf.data.experimental.ignore_errors())
