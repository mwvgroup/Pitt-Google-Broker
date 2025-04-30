#
import tensorflow as tf
import numpy as np
from scipy.optimize import minimize
from functools import partial
import george
from george import kernels


def get_band_to_wave(survey):

    # Apr 2024 RK - this method is for legacy scone only;
    #   refactored scone reads badn_to_wave from FILTERS dictionary in sim-readme.

    band_to_wave = None

    if survey == "LSST" or survey == "DES":
        # Jun 2024 RK-comment: these <lam> are for 2017-era LSST bands without atmos-trans.
        #    They are quite off for DES (4828, 6435, 7828, 9181). I am NOT fixing it now
        #    to ensure that LEGACY scone behaves the same as before, and it is fine if
        #    both training and predict mode use the same <lam>.
        #    The refactored SCONE reads <lam> from sim-readme, but not for real data ...
        #    so need a more robust fix for real data.
        band_to_wave = {
            "u": 3670.69,  # 2017 era, LSST-approx without atmos-trans
            "g": 4826.85,
            "r": 6223.24,
            "i": 7545.98,
            "z": 8590.90,
            "Y": 9710.28,
        }

    if band_to_wave is None:
        raise ValueError(
            f"survey {survey} not registered for LEGACY scone! " f"contact helenqu@sas.upenn.edu"
        )

    return band_to_wave


def build_gp(guess_length_scale, sn_data, bands):
    """This is  all  taken from Avacado -
    see https://github.com/kboone/avocado/blob/master/avocado/astronomical_object.py
    In this a 2D matern kernal is used  to  model the transient. The kernel
    width in the wavelength direction is fixed. We fit for the kernel width
    in the time direction"""

    mjdall = sn_data["mjd"]
    fluxall = sn_data["flux"]
    flux_errall = sn_data["flux_err"]

    # Want to compute the scale factor that we will use...
    signal_to_noises = np.abs(fluxall) / np.sqrt(flux_errall**2 + (0.01 * np.max(fluxall)) ** 2)
    scale = np.abs(fluxall[np.argmax(signal_to_noises)])

    kernel = (0.5 * scale) ** 2 * kernels.Matern32Kernel([guess_length_scale**2, 6000**2], ndim=2)

    gp = george.GP(kernel)
    guess_parameters = gp.get_parameter_vector()

    x_data = np.vstack([mjdall, bands]).T
    gp.compute(x_data, flux_errall)

    def neg_ln_like(p):
        gp.set_parameter_vector(p)
        return -gp.log_likelihood(fluxall)

    def grad_neg_ln_like(p):
        gp.set_parameter_vector(p)
        return -gp.grad_log_likelihood(fluxall)

    bounds = [(0, np.log(1000**2))]
    bounds = [(guess_parameters[0] - 10, guess_parameters[0] + 10)] + bounds + [(None, None)]
    # check if result with/without bounds are the same

    try:
        fit_result = minimize(
            neg_ln_like, gp.get_parameter_vector(), jac=grad_neg_ln_like, bounds=bounds
        )
        gp.set_parameter_vector(fit_result.x)
        gaussian_process = partial(gp.predict, fluxall)
    except ValueError:
        return None

    return gaussian_process


def image_example(image_string):
    def _bytes_feature(value):
        """Returns a bytes_list from a string / byte."""
        if isinstance(value, type(tf.constant(0))):
            value = value.numpy()  # BytesList won't unpack a string from an EagerTensor.
        return tf.train.Feature(bytes_list=tf.train.BytesList(value=[value]))

    feature = {
        "image_raw": _bytes_feature(image_string),
    }

    example_proto = tf.train.Example(features=tf.train.Features(feature=feature))
    return example_proto.SerializeToString()


def get_extinction(ebv, wave):
    avu = 3.1 * ebv

    x = 10000.0 / wave  # inverse wavelength in microns   - creates a numpy array
    xv = 1.82
    y = x - 1.82  # another numpy array

    # Creating empty arrays in which to store the final data
    aval = []
    bval = []

    # Now need to loop through each indavidual wavlength value
    for i in range(len(x)):

        if x[i] >= 0.3 and x[i] < 1.1:  # For IR data
            a = 0.574 * pow(x[i], 1.61)
            b = -0.527 * pow(x[i], 1.61)
            aval.append(a)
            bval.append(b)

        elif x[i] >= 1.1 and x[i] < 3.3:  # For Optical/NIR data
            a = (
                1.0
                + 0.17699 * y[i]
                - 0.50447 * np.power(y[i], 2)
                - 0.02427 * np.power(y[i], 3)
                + 0.72085 * np.power(y[i], 4)
                + 0.01979 * np.power(y[i], 5)
                - 0.77530 * np.power(y[i], 6)
                + 0.32999 * np.power(y[i], 7)
            )
            b = (
                1.41338 * y[i]
                + 2.28305 * np.power(y[i], 2)
                + 1.07233 * np.power(y[i], 3)
                - 5.38434 * np.power(y[i], 4)
                - 0.62251 * np.power(y[i], 5)
                + 5.30260 * np.power(y[i], 6)
                - 2.09002 * np.power(y[i], 7)
            )
            aval.append(a)
            bval.append(b)

        elif x[i] >= 3.3 and x[i] < 8.0:  # For UV data
            if x[i] >= 5.9:
                fa = -0.04473 * np.power(x[i] - 5.9, 2) - 0.009779 * np.power(x[i] - 5.9, 3)
                fb = 0.21300 * np.power(x[i] - 5.9, 2) + 0.120700 * np.power(x[i] - 5.9, 3)
            else:
                fa = fb = 0.0

            a = 1.752 - 0.316 * x[i] - 0.104 / (np.power(x[i] - 4.67, 2) + 0.341) + fa
            b = -3.090 + 1.825 * x[i] + 1.206 / (np.power(x[i] - 4.62, 2) + 0.263) + fb

            aval.append(a)
            bval.append(b)

        elif x[i] >= 8.0 and x[i] <= 10.0:  # For Far-UV data
            a = (
                -1.073
                - 0.628 * (x[i] - 8.0)
                + 0.137 * np.power(x[i] - 8.0, 2)
                - 0.070 * np.power(x[i] - 8.0, 3)
            )
            b = (
                13.670
                + 4.257 * (x[i] - 8.0)
                - 0.420 * np.power(x[i] - 8.0, 2)
                + 0.374 * np.power(x[i] - 8.0, 3)
            )

            aval.append(a)
            bval.append(b)
        else:
            a = b = 0.0

            aval.append(a)
            bval.append(b)

    aval = np.array(aval)
    bval = np.array(bval)

    RV = 3.1
    extinct = avu * (aval + bval / RV)

    return extinct
