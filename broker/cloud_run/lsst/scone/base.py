# base program for create_heatmaps

import numpy as np
import os
import pandas as pd
import abc
from helpers import (
    build_gp,
    get_extinction,
    get_band_to_wave,
    image_example,
)


SIMTAG_Ia = "Ia"  # from GENTYPE_TO_CLASS dict in sim readme
SIMTAG_nonIa = "nonIa"


class CreateHeatmapsBase(abc.ABC):
    def __init__(self, config):

        self.survey = config.get("survey", None)

        # file paths
        self.mode = config["mode"]
        self.output_path = config["heatmaps_path"]
        self.finished_filenames_path = os.path.join(self.output_path, "finished_filenames.csv")

        # heatmap parameters / metadata
        self.wavelength_bins = config["num_wavelength_bins"]
        self.mjd_bins = config["num_mjd_bins"]
        self.has_peakmjd = config.get("has_peakmjd", True)

        # load info from sim-readme that has been appended to config (4.3.2024, RK)
        self.SIM_GENTYPE_TO_CLASS = config.setdefault("SIM_GENTYPE_TO_CLASS", {})
        self.band_to_wave = get_band_to_wave(self.survey)

        self.REFAC = len(self.SIM_GENTYPE_TO_CLASS) > 0 or config.setdefault(
            "prob_column_name", None
        )
        self.LEGACY = not self.REFAC

        self.IS_DATA_REAL = len(self.SIM_GENTYPE_TO_CLASS) == 0
        self.IS_DATA_SIM = len(self.SIM_GENTYPE_TO_CLASS) > 0

        # - - - - - - -
        # RK 4.2.2024: if type_to_name map is not already read from sim-data readme,
        #              then use legacy feature to read it from user config file.

        if self.REFAC:
            self.categorical = False  # disable for now; maybe restore later
            self.types = [SIMTAG_nonIa, SIMTAG_Ia]
            self.type_to_int_label = {SIMTAG_nonIa: 0, SIMTAG_Ia: 1}
            self.sn_type_id_to_name = self.SIM_GENTYPE_TO_CLASS

        else:
            # legacy feature reading hard-wired map from scone-input config
            self.categorical = config["categorical"]
            self.types = config["types"]
            self.sn_type_id_to_name = config["sn_type_id_to_name"]
            self.type_to_int_label = (
                {
                    type_str: 1 if type_str == "SNIa" or type_str == "Ia" else 0
                    for type_str in self.types
                }
                if not self.categorical
                else {v: i for i, v in enumerate(sorted(self.types))}
            )  # int label for classification

        # - - - - - - - -
        # restricting number of heatmaps that are made
        if self.LEGACY:
            self.ids_path = config.get("ids_path", None)
        else:
            # refactored, RK
            self.hdf5_select_file = config.get("hdf5_select_file", None)

        return

    @abc.abstractmethod
    def run(self):
        pass

    @staticmethod
    @abc.abstractmethod
    def _calculate_mjd_range(sn_data):
        pass

    def create_heatmaps(self, input_data, mjd_minmaxes, fit_on_full_lc=True):
        # TODO: infer this from config file rather than making the subclasses pass it in
        self.fit_on_full_lc = fit_on_full_lc

        for mjd_minmax in mjd_minmaxes:
            sn_data = self._get_sn_data(input_data)
            sn_lcdata, mjd_range = sn_data
            wave = [self.band_to_wave[elem] for elem in sn_lcdata["passband"]]
            gp = build_gp(20, sn_lcdata, wave)
            milkyway_ebv = 0.0019738385  # TODO: Update parameter; I, Chris, asserted this value (obtained from an ELAsTiCC2 FITS file)
            predictions, prediction_errs = self._get_predictions_heatmap(
                gp, mjd_range, milkyway_ebv
            )
            heatmap = np.dstack((predictions, prediction_errs))

            image_bytes = image_example(heatmap.flatten().tobytes())

            return image_bytes

    # ================================================
    # HELPER FUNCTIONS
    # ================================================

    def _get_sn_data(self, input_data):
        # TODO: find a better thing to early return

        sn_lcdata = input_data
        if len(sn_lcdata) == 0 or np.all(sn_lcdata["mjd"] < 0):
            print("sn lcdata empty")
            return None

        expected_filters = list(self.band_to_wave.keys())
        sn_lcdata = sn_lcdata[np.isin(sn_lcdata["passband"], expected_filters)]
        if len(sn_lcdata) == 0:
            print("expected filters filtering not working")
            return None

        # mjd_range = self._calculate_mjd_range(sn_lcdata, mjd_minmax, self.has_peakmjd)
        mjd_range = self._calculate_mjd_range(sn_lcdata)
        if not mjd_range:
            print("mjd range is none")
            return None

        # extend light curve to include very early & late epoch with zero flux.
        # Beware to pass flux_err > 0 to avoid divide-by-zero in build_gp.
        mjd_early = min(sn_lcdata["mjd"]) - 100
        mjd_late = max(sn_lcdata["mjd"]) + 100
        flux = 0.0
        flux_err = 0.1
        band = expected_filters[2]
        additional_rows = pd.DataFrame(
            {
                "object_id": [input_data["object_id"]]
                * 2,  # TODO: this line needs to be validated
                "mjd": [mjd_early, mjd_late],
                "flux": [flux, flux],
                "flux_err": [flux_err, flux_err],
                "passband": [band, band],
            }
        )
        lcdata = pd.concat([sn_lcdata, additional_rows], ignore_index=True)

        return lcdata, mjd_range

    def _get_predictions_heatmap(self, gp, mjd_range, milkyway_ebv):
        times = np.linspace(mjd_range[0], mjd_range[1], self.mjd_bins)

        wavelengths = np.linspace(3000.0, 10100.0, self.wavelength_bins)
        ext = get_extinction(milkyway_ebv, wavelengths)
        ext = np.tile(np.expand_dims(ext, axis=1), len(times))
        time_wavelength_grid = np.transpose(
            [np.tile(times, len(wavelengths)), np.repeat(wavelengths, len(times))]
        )

        predictions, prediction_vars = gp(time_wavelength_grid, return_var=True)
        ext_corrected_predictions = np.array(predictions).reshape(32, 180) + ext
        prediction_uncertainties = np.sqrt(prediction_vars).reshape(32, 180)

        return ext_corrected_predictions, prediction_uncertainties
