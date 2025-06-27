#!/usr/bin/env python
#
# Mar 6 2024 RK
#  +  minor refactor in main to accept optional --heatmaps_subdir argument that
#     is useful for side-by-side testing of scone codes or options. This code
#     should still be compatible with both original and refactored scone codes
#
import tensorflow as tf

# =====================================================
# =====================================================


tf.compat.v1.saved_model

def SconeClassifier(image, external_trained_model):
    # images is a tf tensor containg float32's with dimentions (32, 180, 2) (wavelength bin, MJD bin, flux_error/flux)
    # external_trained_model is a path to a trained model
    trained_model = tf.saved_model.load(external_trained_model) # SavedModel format

    # model takes list of images as a tf tensor containg float32's with dimentions (32, 180, 2) (wavelength bin, MJD bin, flux_error/flux)
    tf_dataset = tf.constant([image], dtype=tf.float32, name='image')
    prediction = float(trained_model(tf_dataset)[0][0])

    return prediction