# base program for create_heatmaps

import numpy as np
from helpers import (
    build_gp,
    get_extinction,
    get_band_to_wave
)


SIMTAG_Ia = "Ia"  # from GENTYPE_TO_CLASS dict in sim readme
SIMTAG_nonIa = "nonIa"


class CreateHeatmaps():
    def __init__(self, metadata, lcdata):
        self.lcdata = lcdata

        # heatmap parameters
        self.wavelength_bins = metadata['wavelength_bins']
        self.mjd_bins        = metadata['mjd_bins']

        self.mwebv           = metadata['mwebv']
        self.band_to_wave    = get_band_to_wave(metadata['survey'])
        return

    def create_heatmaps(self):
        mjd_range = self._get_sn_data()
        # gets mean wavelentgth of each observation
        wave = [self.band_to_wave[elem] for elem in self.lcdata['passband']]
        # creates grid from data
        gp = build_gp(20, self.lcdata, wave)

        predictions, prediction_errs = self._get_predictions_heatmap(gp, mjd_range)
            
        return np.dstack((prediction_errs, predictions))

    # ================================================
    # HELPER FUNCTIONS
    # ================================================

    def _get_sn_data(self):
        if len(self.lcdata) == 0 or np.all(self.lcdata['mjd'] < 0):
            print("sn lcdata empty")
            return None

        expected_filters = list(self.band_to_wave.keys())
        lclen = len(self.lcdata)
        self.lcdata = self.lcdata[np.isin(self.lcdata['passband'], expected_filters)]      
        if lclen != len(self.lcdata):
            print("missing filters")
        if len(self.lcdata) == 0:
            print("expected filters filtering not working")
            return None

        mjd_range = [np.min(self.lcdata['mjd']), np.max(self.lcdata['mjd'])]
        if not mjd_range:
            print("mjd range is none")
            return None

        # extend light curve to include very early & late epoch with zero flux.
        # Beware to pass flux_err > 0 to avoid divide-by-zero in build_gp.
        mjd_early = min(self.lcdata['mjd']) - 100
        mjd_late  = max(self.lcdata['mjd']) + 100
        flux = 0.0;  flux_err = 0.1;  band = expected_filters[2]
        self.lcdata.add_row( [mjd_early, flux, flux_err, band] )
        self.lcdata.add_row( [mjd_late,  flux, flux_err, band] )

        return mjd_range

    def _get_predictions_heatmap(self, gp, mjd_range):
        times = np.linspace(mjd_range[0], mjd_range[1], self.mjd_bins)

        wavelengths = np.linspace(3000.0, 10100.0, self.wavelength_bins)
        ext = get_extinction(self.mwebv, wavelengths)
        ext = np.tile(np.expand_dims(ext, axis=1), len(times))
        time_wavelength_grid = np.transpose([np.tile(times, len(wavelengths)), np.repeat(wavelengths, len(times))])

        predictions, prediction_vars = gp(time_wavelength_grid, return_var=True)
        ext_corrected_predictions = np.array(predictions).reshape(self.wavelength_bins, self.mjd_bins) + ext
        prediction_uncertainties = np.sqrt(prediction_vars).reshape(self.wavelength_bins, self.mjd_bins)

        return ext_corrected_predictions, prediction_uncertainties
