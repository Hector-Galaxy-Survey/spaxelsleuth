"""
File:       metallicity.py
Author:     Henry Zovaro
Email:      henry.zovaro@anu.edu.au

DESCRIPTION
------------------------------------------------------------------------------
A collection of functions used to compute metallicities and ionisation 
parameters using strong-line diagnostics.

The following functions are included:

    _get_metallicity()
        This is the bottom-leven function which actually implementes the 
        metallicity calculation using strong-line diagnostics (plus the 
        ionisation parameter if required).

    _get_metallicity_no_errs()
        This function simly computes the metallicity (plus ionisation 
        parameter) in all rows of a DataFrame classified as SF.

        This function calls _get_metallicity() to compute the actual
        metallicity (and ionisation parameter).

    _get_metallicity_errs()
        This function computes the metallicity (plus ionisation parameter)
        and associated errors in all rows of a DataFrame. 

        Errors are computed using a Monte Carlo approach based on the 
        uncertainties on the emission line fluxes contained in the 
        DataFrame: in each MC iterations, random noise is added to the flux of 
        each emission line used in the metallicity/ionisation parameter
        calculation, where the noise is drawn from a Gaussian distribution 
        with standard deviation equal to the 1sigma uncertainties on the 
        emission line fluxes. The final value returned is the mean of the 
        resulting distribution of metallcity (plus ionisation parameter)
        values, and upper and lower error bars are computed from the 16% and 
        84% quantiles of the distribution.
        
        This function MULTITHREADS the function _met_err_helper_fn() to compute 
        the metallicity + errors (plus ionisation parameter + errors) in 
        individual rows simultaneously.

    _met_err_helper_fn()
        This function computes the metallicity + errors (plus ionisation 
        parameter + errors) using the MC approach described above for a 
        SINGLE row in a DataFrame. It is designed to be multithreaded.

        This function calls _get_metallicity() to compute the actual
        metallicity (and ionisation parameter) in each MC iteration.

    calculate_metallicity()


------------------------------------------------------------------------------
Copyright (C) 2022 Henry Zovaro 
"""
###############################################################################
import multiprocessing
import numpy as np
import pandas as pd
from scipy import constants
import sys
from time import time
from tqdm import tqdm

from IPython.core.debugger import Tracer

import matplotlib.pyplot as plt
plt.ion()
plt.close("all")

#//////////////////////////////////////////////////////////////////////////////
# Dict containing the line lists for each metallicity/ionisation parameter diagnostic
line_list_dict = {
    # Kewley (2019) - log(O/H) + 12
    "N2Ha_K19": ["NII6583", "HALPHA"],
    "S2Ha_K19": ["SII6716+SII6731", "HALPHA"],
    "N2S2_K19": ["NII6583", "SII6716+SII6731"],
    "S23_K19": ["SII6716+SII6731", "SIII9069", "SIII9531", "HALPHA"],
    "O3N2_K19": ["OIII5007", "HBETA", "NII6583", "HALPHA"],
    "O2S2_K19": ["OII3726+OII3729", "SII6716+SII6731"],
    "O2Hb_K19": ["OII3726+OII3729", "HBETA"],
    "N2O2_K19": ["NII6583", "OII3726+OII3729"],
    "R23_K19": ["OIII4959+OIII5007", "OII3726+OII3729", "HBETA"],

    # Kewley (2019) - log(U)
    "O3O2_K19": ["OIII5007", "OII3726+OII3729"],
    "S32_K19": ["SIII9069", "SIII9531", "SII6716+SII6731"],

    # Others 
    "N2Ha_PP04": ["NII6583", "HALPHA"],
    "N2Ha_M13": ["NII6583", "HALPHA"],
    "O3N2_PP04": ["OIII5007", "HBETA", "HALPHA", "NII6583"],
    "O3N2_M13": ["OIII5007", "HBETA", "HALPHA", "NII6583"],
    "R23_KK04": ["NII6583", "OII3726+OII3729", "HBETA", "OIII4959+OIII5007", "OII3726+OII3729"],
    "O3O2_KK04": ["OIII4959+OIII5007", "OII3726+OII3729"], # KK04 - log(U) diagnostic. NOTE different O3O2 defn. to K19
    "R23_C17": ["OII3726", "OIII4959+OIII5007", "HBETA"],
    "N2S2Ha_D16": ["NII6583", "SII6716+SII6731", "HALPHA"],
    "N2O2_KD02": ["NII6583", "OII3726+OII3729"],
    "Rcal_PG16": ["OII3726+OII3729", "HBETA", "NII6548+NII6583", "OIII4959+OIII5007"],
    "Scal_PG16": ["HBETA", "NII6548+NII6583", "OIII4959+OIII5007", "SII6716+SII6731"],
    "ONS_P10": ["OII3726+OII3729", "OIII4959+OIII5007", "NII6548+NII6583", "SII6716+SII6731", "HBETA"],
    "ON_P10": ["OII3726+OII3729", "OIII4959+OIII5007", "NII6548+NII6583", "SII6716+SII6731", "HBETA"],
}

#//////////////////////////////////////////////////////////////////////////////
# Coefficients from Kewley (2019)
# Valid for log(P/k) = 5.0 and -3.98 < log(U) < -1.98
met_coeffs_K19 = {
    "N2Ha_K19"     : {
        "A" : 10.526,
        "B" : 1.9958,
        "C" : -0.6741,
        "D" : 0.2892,
        "E" : 0.5712,
        "F" : -0.6597,
        "G" : 0.0101,
        "H" : 0.0800,
        "I" : 0.0782,
        "J" : -0.0982,
        "RMS ERR" : 0.67,   # PERCENT
        "Zmin" : 7.63,
        "Zmax" : 8.53,
        },
    "S2Ha_K19"     : {
    # Notes: strong dependence on U. Can be avoided by using S23. 
    # Shouldn"t be used unless ionisation parameter can be determined to an 
    # accuracy of better than 0.05 dex in log(U).
        "A" : 23.370,
        "B" : 11.700,
        "C" : 7.2562,
        "D" : 4.3320,
        "E" : 3.1564,
        "F" : 1.0361,
        "G" : 0.4315,
        "H" : 0.6576,
        "I" : 0.3319,
        "J" : 0.0336,
        "RMS ERR" : 0.92,   # PERCENT
        "Zmin" : 7.63,
        "Zmax" : 8.53,
        },
    "N2S2_K19"  : {
        "A" : 5.8892,
        "B" : 3.1688,
        "C" : -3.5991,
        "D" : 1.6394,
        "E" : -2.3939,
        "F" : -1.6764,
        "G" : 0.4455,
        "H" : -0.9302,
        "I" : -0.0966,
        "J" : -0.2490,
        "RMS ERR" : 1.19,   # PERCENT
        "Zmin" : 7.63,
        "Zmax" : 8.53,
        },
    "S23_K19"   : {
        "A" : 11.033,
        "B" : 0.9907,
        "C" : 1.5789,
        "D" : 0.4233,
        "E" : -3.1663,
        "F" : 0.3666,
        "G" : 0.0654,
        "H" : -0.2146,
        "I" : -1.7045,
        "J" : 0.0316,
        "RMS ERR" : 0.55,   # PERCENT
        "Zmin" : 7.63,
        "Zmax" : 8.53,
        },
    "O3N2_K19"  : { 
    # Notes: strong dependence on U. Not recommended to use. 
    # [NII]/Ha is a better alternative when few lines are available.
        "A" : 10.312,
        "B" : -1.6575,
        "C" : 2.2525,
        "D" : -1.3594,
        "E" : 0.4764,
        "F" : 1.1730,
        "G" : -0.2968,
        "H" : 0.1974,
        "I" : -0.0544,
        "J" : 0.1891,
        "RMS ERR" : 2.97,   # PERCENT
        "Zmin" : 8.23,
        "Zmax" : 8.93,
        },
    "O2S2_K19"  : {
    # Notes: less sensitive to U than [SII]/Halpha, but N2O2 is better if available
        "A" : 12.489,
        "B" : -3.2646,
        "C" : 3.2581,
        "D" : -2.0544,
        "E" : 0.5282,
        "F" : 1.0730,
        "G" : -0.3445,
        "H" : 0.2130,
        "I" : -0.3047,
        "J" : 0.1209,
        "RMS ERR" : 2.52,   # PERCENT
        "Zmin" : 8.23,
        "Zmax" : 9.23,
    },
    "O2Hb_K19"     : {
        "A" : 6.2084,
        "B" : -4.0513,
        "C" : -1.4847,
        "D" : -1.9125,
        "E" : -1.0071,
        "F" : -0.1275,
        "G" : -0.2471,
        "H" : -0.1872,
        "I" : -0.1052,
        "J" : 0.0173,
        "RMS ERR" : 0.02,   # PERCENT
        "Zmin" : 8.53,
        "Zmax" : 9.23,
    },
    "N2O2_K19"  : {
    # Notes: "By far the most reliable" diagnostic in the optical. 
    # No dependence on U and only marginally sensitive to pressure.
    # Also relatively insensitive to DIG and AGN radiation.
        "A" :   9.4772,
        "B" :   1.1797,
        "C" :   0.5085,
        "D" :   0.6879,
        "E" :   0.2807,
        "F" :   0.1612,
        "G" :   0.1187,
        "H" :   0.1200,
        "I" :   0.2293,
        "J" :   0.0164,
        "RMS ERR" : 2.65,   # PERCENT
        "Zmin" : 7.63,
        "Zmax" : 9.23,
    },
    "R23_K19"   : {
    # Notes: two-valued and sensitive to ISM pressure at metallicities 
    # exceeding ~8.5. A pressure diagnostic should be used in conjunction!
        "A" : 9.7757,
        "B" : -0.5059,
        "C" : 0.9707,
        "D" : -0.1744,
        "E" : -0.0255,
        "F" : 0.3838,
        "G" : -0.0378,
        "H" : 0.0806,
        "I" : -0.0852,
        "J" : 0.0462,
        "RMS ERR" : 2.11,   # PERCENT
        "Zmin" : 8.23,
        "Zmax" : 8.93,
    },
}

# Valid for log(P/k) = 5.0
ion_coeffs_K19 = {
    "O3O2_K19" : {
        "A" : 13.768,
        "B" : 9.4940,
        "C" : -4.3223,
        "D" : -2.3531,
        "E" : -0.5769,
        "F" : 0.2794,
        "G" : 0.1574,
        "H" : 0.0890,
        "I" : 0.0311,
        "J" : 0.0000,
        "RMS ERR" : 1.35,   # PERCENT
        "Zmin" : 7.63,
        "Zmax" : 8.93,
        "Umin" : -3.98,
        "Umax" : -2.98,
    },
    "S32_K19" : {
        "A" : 90.017,
        "B" : 21.934,
        "C" : -34.095,
        "D" : -5.0818,
        "E" : -1.4762,
        "F" : 4.1343,
        "G" : 0.3096,
        "H" : 0.1786,
        "I" : 0.1959,
        "J" : -0.1668,
        "RMS ERR" : 1.96,   # PERCENT
        "Zmin" : 7.63,
        "Zmax" : 9.23,
        "Umin" : -3.98,
        "Umax" : -2.48,
    },
}

###############################################################################
def _get_metallicity(met_diagnostic, df, 
                     logU=None, 
                     compute_logU=False, ion_diagnostic=None, 
                     max_niters=10):
    """

    This function implements strong-line metallicity diagnostics to compute the 
    metallicity given a DataFrame containing emission line fluxes. 

    Note that this function ONLY calculates the metallicity (and ionisation
    parameter if required) - NO errors are calculated in this function.

    INPUTS
    ---------------------------------------------------------------------------
        met_diagnostic:      str
            Metallicity diagnostic.

        df:                  pandas DataFrame
            DataFrame containing emission line fluxes. NOTE: it's assumed that 
            the input will have had column suffixes removed prior to being 
            passed to this function.

        logU:                float
            Constant log ionisation parameter to assume for diagnostics 
            requiring one - this includes R23_KK04 and all Kewley (2019)
            diagnostics.

        compute_logU:        bool
            If True, compute self-consistent metallicity and ionisation 
            parameters using an iterative approach. Only valid for metallicity
            diagnostics that use the ionisation parameter - this includes 
            R23_KK04 and all Kewley (2019) diagnostics.

        ion_diagnostic:      str 
            The ionisation parameter diagnostic to use if compute_logU is True.
            For the Kewley (2019) diagnostics, the only valid options are 
            O3O2_K19 or S32_K19. For R23_KK04 the only valid option is 
            O3O2_KK04.

        max_niters:          int
            Maximum number of iterations used to compute self-consistent 
            metallicity and ionisation parameters. 
            
    OUTPUTS
    ---------------------------------------------------------------------------
        If logU is not specified -AND- compute_logU == False, this function 
        returns

            logOH12:       float OR numpy.array 
                log(O/H) + 12. If the input DataFrame is a single row, then a 
                float is returned. Otherwise, an array of log(O/H) + 12 values 
                is returned (corresponding to each row).

        Otherwise, this function returns 
            
            logOH12, logU:  tuple of (float OR numpy.array) 
                log(O/H) + 12 and log(U). If the input DataFrame is a single 
                row, then a float is returned for each value. Otherwise, 
                arrays of log(O/H) + 12 and log(U) values are returned 
                (corresponding to each row).

            
    """
    #//////////////////////////////////////////////////////////////////////////
    # Assume that linefns.ratio_fn() has already been run on the DataFrame, so
    # that doublets etc. are already there.
    for line in line_list_dict[met_diagnostic]:
        assert line in df,\
            f"Metallicity diagnostic {met_diagnostic} requires {line} which was not found in the DataFrame!"
    if compute_logU:
        for line in line_list_dict[ion_diagnostic]:
            assert line in df,\
                f"ionisation parameter diagnostic {ion_diagnostic} requires {line} which was not found in the DataFrame!"

    #//////////////////////////////////////////////////////////////////////////
    # K19 diagnostics
    if met_diagnostic.endswith("K19"):
        assert compute_logU or (logU is not None),\
            f"Metallicity diagnostic {met_diagnostic} requires log(U) to be specified!"
        
        # Compute the line ratio
        if met_diagnostic == "N2Ha_K19":
            logR = np.log10(df["NII6583"] / df["HALPHA"])
        if met_diagnostic == "S2Ha_K19":
            logR = np.log10((df["SII6716+SII6731"]) / df["HALPHA"])
        if met_diagnostic == "N2S2_K19":
            logR = np.log10(df["NII6583"] / (df["SII6716+SII6731"]))
        if met_diagnostic == "S23_K19": 
            logR = np.log10((df["SII6716+SII6731"] + df["SIII9069"] + df["SIII9531"]) / df["HALPHA"])
        if met_diagnostic == "O3N2_K19":
            logR = np.log10((df["OIII5007"] / df["HBETA"]) / (df["NII6583"] / df["HALPHA"]))
        if met_diagnostic == "O2S2_K19":
            logR = np.log10((df["OII3726+OII3729"]) / (df["SII6716+SII6731"]))
        if met_diagnostic == "O2Hb_K19":
            logR = np.log10((df["OII3726+OII3729"]) / df["HBETA"])
        if met_diagnostic == "N2O2_K19":
            logR = np.log10(df["NII6583"] / (df["OII3726+OII3729"]))
        if met_diagnostic == "R23_K19": 
            logR = np.log10((df["OIII4959+OIII5007"] + df["OII3726+OII3729"]) / df["HBETA"])

        # Compute metallicity
        logOH12_func = lambda x, y : \
              met_coeffs_K19[met_diagnostic]["A"] \
            + met_coeffs_K19[met_diagnostic]["B"] * x \
            + met_coeffs_K19[met_diagnostic]["C"] * y \
            + met_coeffs_K19[met_diagnostic]["D"] * x * y \
            + met_coeffs_K19[met_diagnostic]["E"] * x**2 \
            + met_coeffs_K19[met_diagnostic]["F"] * y**2 \
            + met_coeffs_K19[met_diagnostic]["G"] * x * y**2 \
            + met_coeffs_K19[met_diagnostic]["H"] * y * x**2 \
            + met_coeffs_K19[met_diagnostic]["I"] * x**3 \
            + met_coeffs_K19[met_diagnostic]["J"] * y**3
        
        if compute_logU:
            # Compute a self-consistent ionisation parameter using the O3O2
            # diagnostic
            logR_met = np.array(logR)
            if ion_diagnostic == "O3O2_K19":
                logR_ion = np.array(np.log10(df["OIII5007"] / df["OII3726+OII3729"]))
            if ion_diagnostic == "S23_K19":
                logR_ion = np.array(np.log10((df["SIII9069"] + df["SIII9531"]) / df["SII6716+SII6731"]))

            # Ionisation parameter
            # x = log(R)
            # y = log(O/H) + 12
            logU_func = lambda x, y : \
                  ion_coeffs_K19[ion_diagnostic]["A"]   \
                + ion_coeffs_K19[ion_diagnostic]["B"] * x     \
                + ion_coeffs_K19[ion_diagnostic]["C"] * y     \
                + ion_coeffs_K19[ion_diagnostic]["D"] * x * y   \
                + ion_coeffs_K19[ion_diagnostic]["E"] * x**2  \
                + ion_coeffs_K19[ion_diagnostic]["F"] * y**2  \
                + ion_coeffs_K19[ion_diagnostic]["G"] * x * y**2    \
                + ion_coeffs_K19[ion_diagnostic]["H"] * y * x**2    \
                + ion_coeffs_K19[ion_diagnostic]["I"] * x**3  \
                + ion_coeffs_K19[ion_diagnostic]["J"] * y**3

            logOH12 = np.full(df.shape[0], np.nan)
            logU = np.full(df.shape[0], np.nan)
            nrows = df.shape[0]
            for rr in range(nrows):
                if np.isnan(logR_met[rr]) or np.isnan(logR_ion[rr]):
                    logOH12[rr] = np.nan
                    logU[rr] = np.nan
                    continue

                # Starting guesses
                logOH12_old = 8.0
                logU_old = -3.0

                # Iteratively compute ionisation parameter & metallicity
                for n in range(max_niters):
                    logU_new = logU_func(x=logR_ion[rr], y=logOH12_old)
                    logOH12_new = logOH12_func(x=logR_met[rr], y=logU_new)

                    if np.abs(logOH12_new - logOH12_old) < 0.001 and np.abs(logU_new - logU_old) < 0.001:
                        break
                    else:
                        logOH12_old = logOH12_new
                        logU_old = logU_new
                logOH12[rr] = logOH12_new
                logU[rr] = logU_new

            # What about limits?
            good_pts = logOH12 > met_coeffs_K19[met_diagnostic]["Zmin"]     # log(O/H) + 12 - metallicity limits
            good_pts &= logOH12 < met_coeffs_K19[met_diagnostic]["Zmax"]    # log(O/H) + 12 - metallicity limits
            good_pts &= logOH12 < ion_coeffs_K19[ion_diagnostic]["Zmax"]    # log(U) - metallicity limits
            good_pts &= logOH12 > ion_coeffs_K19[ion_diagnostic]["Zmin"]    # log(U) - metallicity limits
            good_pts &= logU < ion_coeffs_K19[ion_diagnostic]["Umax"]       # log(U) - ionisation parameter limits
            good_pts &= logU > ion_coeffs_K19[ion_diagnostic]["Umin"]       # log(U) - ionisation parameter limits
            logOH12[~good_pts] = np.nan
            logU[~good_pts] = np.nan

            return np.squeeze(logOH12), np.squeeze(logU)

        else:
            # Assume a fixed ionisation parameter
            logOH12 = logOH12_func(x=logR, y=logU)

            # What about limits?
            good_pts = logOH12 > met_coeffs_K19[met_diagnostic]["Zmin"]     # log(O/H) + 12 - metallicity limits
            good_pts &= logOH12 < met_coeffs_K19[met_diagnostic]["Zmax"]    # log(O/H) + 12 - metallicity limits
            logOH12[~good_pts] = np.nan
            logU = np.full(df.shape[0], logU)
            logU[~good_pts] = np.nan

            return np.squeeze(logOH12), np.squeeze(logU)

    #//////////////////////////////////////////////////////////////////////////
    elif met_diagnostic == "R23_KK04":
        # R23 - Kobulnicky & Kewley (2004)
        logN2O2 = np.log10(df["NII6583"] / df["OII3726+OII3729"]).values
        logO3O2 = np.log10(df["OIII4959+OIII5007"] / df["OII3726+OII3729"]).values
        logR23 = np.log10((df["OII3726+OII3729"] + df["OIII4959+OIII5007"]) / df["HBETA"]).values
        logOH12 = np.full(df.shape[0], np.nan)

        if compute_logU:
            logU = np.full(df.shape[0], np.nan)
            nrows = df.shape[0]
            for rr in range(nrows):
                if np.isnan(logN2O2[rr]) or np.isnan(logO3O2[rr]) or np.isnan(logR23[rr]):
                    logOH12[rr] = np.nan
                    logU[rr] = np.nan
                    continue

                if logN2O2[rr] < -1.2:
                    logOH12_old = 8.2
                else:
                    logOH12_old = 8.7
                for n in range(max_niters):
                    # Compute ionisation parameter
                    # NOTE: there is a serious transcription error in the version of this eqn. that appears in the appendix of Poeotrodjojo+2021: refer to the eqn. in the original paper
                    logq = (32.81 - 1.153 * logO3O2[rr]**2\
                            + logOH12_old * (-3.396 - 0.025 * logO3O2[rr] + 0.1444 * logO3O2[rr]**2))\
                           * (4.603 - 0.3119 * logO3O2[rr] - 0.163 * logO3O2[rr]**2 + logOH12_old * (-0.48 + 0.0271 * logO3O2[rr] + 0.02037 * logO3O2[rr]**2))**(-1)

                    # Compute metallicity
                    if logN2O2[rr] < -1.2:
                        logOH12_new = 9.40 + 4.65 * logR23[rr] - 3.17 * logR23[rr]**2 - logq * (0.272 + 0.547 * logR23[rr] - 0.513 * logR23[rr]**2)
                    else:
                        logOH12_new = 9.72 - 0.777 * logR23[rr] - 0.951 * logR23[rr]**2 - 0.072 * logR23[rr]**3 - 0.811 * logR23[rr]**4 - logq * (0.0737 - 0.0713 * logR23[rr] - 0.141 * logR23[rr]**2 + 0.0373 * logR23[rr]**3 - 0.058 * logR23[rr]**4)

                    if np.abs(logOH12_new - logOH12_old) < 0.001:
                        break
                    else:
                        logOH12_old = logOH12_new
                logOH12[rr] = logOH12_new
                logU[rr] = logq - np.log10(constants.c * 1e2)

            # The diagnostic isn't defined for logR23 > 1.0, so remove these.
            good_pts = logR23 < 1.0
            logOH12[~good_pts] = np.nan
            logU[~good_pts] = np.nan

            return np.squeeze(logOH12), np.squeeze(logU)

        else:
            logq = logU + np.log10(constants.c * 1e2)
            pts_lower = logN2O2 < -1.2
            pts_upper = logN2O2 >= -1.2
            logOH12[pts_lower] = 9.40 + 4.65 * logR23[pts_lower] - 3.17 * logR23[pts_lower]**2 - logq * (0.272 + 0.547 * logR23[pts_lower] - 0.513 * logR23[pts_lower]**2)
            logOH12[pts_upper] = 9.72 - 0.777 * logR23[pts_upper] - 0.951 * logR23[pts_upper]**2 - 0.072 * logR23[pts_upper]**3 - 0.811 * logR23[pts_upper]**4 - logq * (0.0737 - 0.0713 * logR23[pts_upper] - 0.141 * logR23[pts_upper]**2 + 0.0373 * logR23[pts_upper]**3 - 0.058 * logR23[pts_upper]**4)

            # The diagnostic isn't defined for logR23 > 1.0, so remove these.
            good_pts = logR23 < 1.0
            logOH12[~good_pts] = np.nan
            logU = np.full(df.shape[0], logU)
            logU[~good_pts] = np.nan

            return np.squeeze(logOH12), np.squeeze(logU)

    elif met_diagnostic == "N2O2_KD02":
        # N2O2 - Kewley & Dopita (2002)
        # Only reliable above Z > 0.5Zsun (log(O/H) + 12 > 8.6)
        logR = np.log10(df["NII6583"] / (df["OII3726+OII3729"]))
        logOH12 = np.log10(1.54020 + 1.26602 * logR + 0.167977 * logR**2 ) + 8.93
        good_pts = (logOH12 > 8.6) & (logOH12 < 9.4)  # upper limit eyeballed from their fig. 3
        logOH12[~good_pts] = np.nan
        return np.squeeze(logOH12)

    elif met_diagnostic == "N2Ha_PP04":
        # N2Ha - Pettini & Pagel (2004)
        logR = np.log10(df["NII6583"] / df["HALPHA"])
        logOH12 = 9.37 + 2.03 * logR + 1.26 * logR**2 + 0.32 * logR**3
        good_pts = (-2.5 < logR) & (logR < -0.3)
        logOH12[~good_pts] = np.nan
        return np.squeeze(logOH12)

    elif met_diagnostic == "N2Ha_M13":
        # N2Ha - Marino (2013)
        logR = np.log10(df["NII6583"] / df["HALPHA"])
        logOH12 = 8.743 + 0.462 * logR
        good_pts = (-1.6 < logR) & (logR < -0.2)
        logOH12[~good_pts] = np.nan
        return np.squeeze(logOH12)
    
    if met_diagnostic == "O3N2_PP04":
        # O3N2 - Pettini & Pagel (2004)
        logR = np.log10((df["OIII5007"] / df["HBETA"]) / (df["NII6583"] / df["HALPHA"]))
        logOH12 = 8.73 - 0.32 * logR
        good_pts = (-1 < logR) & (logR < 1.9)
        logOH12[~good_pts] = np.nan
        return np.squeeze(logOH12)

    elif met_diagnostic == "O3N2_M13":
        # O3N2 - Marino (2013)
        logR = np.log10((df["OIII5007"] / df["HBETA"]) / (df["NII6583"] / df["HALPHA"]))
        logOH12 = 8.533 - 0.214 * logR
        good_pts = (-1.1 < logR) & (logR < 1.7)
        logOH12[~good_pts] = np.nan
        return np.squeeze(logOH12)
    
    if met_diagnostic == "N2S2Ha_D16":
        # N2S2Ha - Dopita et al. (2016)
        logR = np.log10(df["NII6583"] / df["SII6716+SII6731"]) + 0.264 * np.log10(df["NII6583"] / df["HALPHA"])
        logOH12 = 8.77 + logR + 0.45 * (logR + 0.3)**5
        good_pts = (-1.1 < logR) & (logR < 0.5)
        logOH12[~good_pts] = np.nan
        return np.squeeze(logOH12)

    elif met_diagnostic == "ONS_P10":
        # ONS - Pilyugin et al. (2016)
        logN2 = np.log10(df["NII6548+NII6583"] / df["HBETA"])
        logS2 = np.log10(df["SII6716+SII6731"] / df["HBETA"])
        logR3 = np.log10(df["OIII4959+OIII5007"] / df["HBETA"])
        logR2 = np.log10(df["OII3726+OII3729"] / df["HBETA"])
        R3 = df["OIII4959+OIII5007"] / df["HBETA"]
        R2 = df["OII3726+OII3729"] / df["HBETA"]
        P = R3 / (R3 + R2)  # should this be a log?

        logOH12 = np.full(df.shape[0], np.nan)
        pts_cool = logN2 >= -0.1
        pts_warm = (logN2 < -0.1) & ((logN2 - logS2) >= -0.25)
        pts_hot = (logN2 < -0.1) & ((logN2 - logS2) < -0.25)

        # Eqn. (17) from P10
        # Note that the below "warm" equation has a transcription error in Poetrodjojo+2021
        logOH12[pts_cool] = 8.277 + 0.657 * P[pts_cool] - 0.399 * logR3[pts_cool] - 0.061 * (logN2[pts_cool] - logR2[pts_cool]) + 0.005 * (logS2[pts_cool] - logR2[pts_cool])
        logOH12[pts_warm] = 8.816 - 0.733 * P[pts_warm] + 0.454 * logR3[pts_warm] + 0.710 * (logN2[pts_warm] - logR2[pts_warm]) - 0.337 * (logS2[pts_warm] - logR2[pts_warm])
        logOH12[pts_hot]  = 8.774 - 1.855 * P[pts_hot] + 1.517 * logR3[pts_hot] + 0.304 * (logN2[pts_hot] - logR2[pts_hot]) + 0.328 * (logS2[pts_hot] - logR2[pts_hot])

        return np.squeeze(logOH12)

    elif met_diagnostic == "ON_P10":
        # ON - Pilyugin et al. (2016)
        logN2 = np.log10(df["NII6548+NII6583"] / df["HBETA"])
        logS2 = np.log10(df["SII6716+SII6731"] / df["HBETA"])
        logR3 = np.log10(df["OIII4959+OIII5007"] / df["HBETA"])
        logR2 = np.log10(df["OII3726+OII3729"] / df["HBETA"])

        logOH12 = np.full(df.shape[0], np.nan)
        pts_cool = logN2 >= -0.1
        pts_warm = (logN2 < -0.1) & ((logN2 - logS2) >= -0.25)
        pts_hot = (logN2 < -0.1) & ((logN2 - logS2) < -0.25)

        # Eqn. (19) from P10
        logOH12[pts_cool] = 8.606 - 0.105 * logR3[pts_cool] - 0.410 * logR2[pts_cool] - 0.150 * (logN2[pts_cool] - logR2[pts_cool])
        logOH12[pts_warm] = 8.642 + 0.077 * logR3[pts_warm] + 0.411 * logR2[pts_warm] + 0.601 * (logN2[pts_warm] - logR2[pts_warm])
        logOH12[pts_hot]  = 8.013 + 0.905 * logR3[pts_hot] + 0.602 * logR2[pts_hot] + 0.751 * (logN2[pts_hot] - logR2[pts_hot])

        return np.squeeze(logOH12)

    elif met_diagnostic == "Rcal_PG16":
        # Rcal - Pilyugin & Grebel (2016)
        logO32 = np.log10((df["OIII4959+OIII5007"]) / (df["OII3726+OII3729"]))
        logN2Hb = np.log10((df["NII6548+NII6583"]) / df["HBETA"])
        logO2Hb = np.log10((df["OII3726+OII3729"]) / df["HBETA"])

        # Decide which branch we're on
        logOH12 = np.full(df.shape[0], np.nan)
        pts_lower = logN2Hb < -0.6
        pts_upper = logN2Hb >= 0.6

        logOH12[pts_lower] = 7.932 + 0.944 * logO32[pts_lower] + 0.695 * logN2Hb[pts_lower] + ( 0.970 - 0.291 * logO32[pts_lower] - 0.019 * logN2Hb[pts_lower]) * logO2Hb[pts_lower]
        logOH12[pts_upper] = 8.589 + 0.022 * logO32[pts_upper] + 0.399 * logN2Hb[pts_upper] + (-0.137 + 0.164 * logO32[pts_upper] + 0.589 * logN2Hb[pts_upper]) * logO2Hb[pts_upper]

        # Does this calibration have limits?
        return np.squeeze(logOH12)

    elif met_diagnostic == "Scal_PG16":
        # Scal - Pilyugin & Grebel (2016)
        logO3S2 = np.log10((df["OIII4959+OIII5007"]) / (df["SII6716+SII6731"]))
        logN2Hb = np.log10((df["NII6548+NII6583"]) / df["HBETA"])
        logS2Hb = np.log10((df["SII6716+SII6731"]) / df["HBETA"])

        # Decide which branch we're on
        logOH12 = np.full_like(logO3S2, np.nan)
        pts_lower = logN2Hb < -0.6
        pts_upper = logN2Hb >= 0.6

        logOH12[pts_lower] = 8.072 + 0.789 * logO3S2[pts_lower] + 0.726 * logN2Hb[pts_lower] + ( 1.069 - 0.170 * logO3S2[pts_lower] + 0.022 * logN2Hb[pts_lower]) * logS2Hb[pts_lower]
        logOH12[pts_upper] = 8.424 + 0.030 * logO3S2[pts_upper] + 0.751 * logN2Hb[pts_upper] + (-0.349 + 0.182 * logO3S2[pts_upper] + 0.508 * logN2Hb[pts_upper]) * logS2Hb[pts_upper]

        # Does this calibration have limits?
        return np.squeeze(logOH12)

###############################################################################
def _met_err_helper_fn(args):
    """
    This function SERIALLY computes the metallicity WITH ERRORS on a SINGLE
    row in a DataFrame. 

    This is passed to _get_metallicity_errs() in which it is MULTITHREADED.

    INPUTS
    ---------------------------------------------------------------------------


    OUTPUTS
    ---------------------------------------------------------------------------

    """
    rr, df, met_diagnostic, logU, compute_logU, ion_diagnostic, niters = args
    df_row = df.loc[[rr]]

    logOH12_vals = np.full(niters, np.nan)
    if (logU is not None) or compute_logU:
        logU_vals = np.full(niters, np.nan)
    
    # Evaluate log(O/H) + 12 (and log(U) if compute_logU is True) niters times 
    # with random noise added to the emission line fluxes each time
    for nn in range(niters):
        # Make a copy of the row
        df_tmp = df_row.copy()
        
        # Add random error 
        for eline in line_list_dict[met_diagnostic]:
            df_tmp[eline] += np.random.normal(scale=df_tmp[f"{eline} error"])
        if compute_logU:
            for eline in line_list_dict[ion_diagnostic]:
                df_tmp[eline] += np.random.normal(scale=df_tmp[f"{eline} error"])

        # Compute corresponding metallicity
        if compute_logU:
            res = _get_metallicity(met_diagnostic=met_diagnostic, df=df_tmp, 
                                   compute_logU=compute_logU, ion_diagnostic=ion_diagnostic)
            logOH12_vals[nn] = res[0]
            logU_vals[nn] = res[1]

        elif logU is not None:
            res = _get_metallicity(met_diagnostic=met_diagnostic, df=df_tmp, 
                                   logU=logU)
            logOH12_vals[nn] = res[0]
            logU_vals[nn] = res[1]

        else:
            logOH12_vals[nn] = _get_metallicity(met_diagnostic=met_diagnostic, df=df_tmp, 
                                                logU=None, compute_logU=False)

    # Add to DataFrame
    if compute_logU:
        df_row[f"log(O/H) + 12 ({met_diagnostic}/{ion_diagnostic})"] = np.nanmean(logOH12_vals)
        df_row[f"log(O/H) + 12 ({met_diagnostic}/{ion_diagnostic}) error (lower)"] = np.nanmean(logOH12_vals) - np.quantile(logOH12_vals, q=0.16)
        df_row[f"log(O/H) + 12 ({met_diagnostic}/{ion_diagnostic}) error (upper)"] = np.quantile(logOH12_vals, q=0.84) - np.nanmean(logOH12_vals)
        df_row[f"log(U) ({met_diagnostic}/{ion_diagnostic})"] = np.nanmean(logU_vals)
        df_row[f"log(U) ({met_diagnostic}/{ion_diagnostic}) error (lower)"] = np.nanmean(logU_vals) - np.quantile(logU_vals, q=0.16)
        df_row[f"log(U) ({met_diagnostic}/{ion_diagnostic}) error (upper)"] = np.quantile(logU_vals, q=0.84) - np.nanmean(logU_vals)
    
    else:
        df_row[f"log(O/H) + 12 ({met_diagnostic})"] = np.nanmean(logOH12_vals)
        df_row[f"log(O/H) + 12 ({met_diagnostic}) error (lower)"] = np.nanmean(logOH12_vals) - np.quantile(logOH12_vals, q=0.16)
        df_row[f"log(O/H) + 12 ({met_diagnostic}) error (upper)"] = np.quantile(logOH12_vals, q=0.84) - np.nanmean(logOH12_vals)
        if logU is not None:
            if not np.isnan(np.nanmean(logOH12_vals)):
                df_row.loc[f"log(U) ({met_diagnostic})"] = logU
            else:
                df_row.loc[f"log(U) ({met_diagnostic})"] = logU

    # Note that we need to return df_row.iloc[0], not just df_row, because we
    # extract the row using df.loc[[rr]] instead of df.loc[rr].
    return df_row.iloc[0]

###############################################################################
def _get_metallicity_errs(met_diagnostic, df,
                         logU=None, 
                         compute_logU=False, ion_diagnostic=None,
                         niters=1000, nthreads=10,
                         debug=False):
    """

    
    INPUTS 
    ---------------------------------------------------------------------------

    OUTPUTS 
    ---------------------------------------------------------------------------

    """
    status_str = "In _get_metallicity_errs()"

    #//////////////////////////////////////////////////////////////////////////
    # Split into SF and non-SF rows 
    cond_met = df["BPT"] == "SF"

    # Split into 2 DataFrames
    df_met = df[cond_met]
    df_nomet = df[~cond_met]

    #//////////////////////////////////////////////////////////////////////////
    # Compute metallicity WITH ERRORS using an MC approach with multithreading
    pd.options.mode.chained_assignment = None
    args_list = [[rr, df, met_diagnostic, logU, compute_logU, ion_diagnostic, niters] for rr in df_met.index.values]
    if not debug:
        # Multithreading 
        print(f"{status_str}: Multithreading metallicity computation across {nthreads} threads...")
        pool = multiprocessing.Pool(nthreads)
        res_list = pool.map(_met_err_helper_fn, args_list)
        pool.close()
        pool.join()
    else:
        print(f"{status_str}: Executing metallicity computation sequentially...")
        res_list = []
        for args in tqdm(args_list):
            res = _met_err_helper_fn(args)
            res_list.append(res)

    # Concatenate results
    df_results_met = pd.concat(res_list, axis=1).T

    # Cast back to previous data types
    for col in df.columns:
        # Try statement for weird situation where there are duplicate columns...
        try:
            df_results_met[col] = df_results_met[col].astype(df[col].dtype)
        except:
            print(col)
            Tracer()()
            continue
    df_met = df_results_met

    #//////////////////////////////////////////////////////////////////////////
    # Merge back with original DataFrame
    print(f"{status_str}: Concatenating DataFrames...")
    df = pd.concat([df_nomet, df_met], sort=True)

    print(f"{status_str}: Done!")
    return df

###############################################################################
def _get_metallicity_no_errs(met_diagnostic, df, 
                             logU=None, 
                             compute_logU=False, ion_diagnostic=None):
    """

    
    INPUTS 
    ---------------------------------------------------------------------------

    OUTPUTS 
    ---------------------------------------------------------------------------

    """
    status_str = "In _get_metallicity_errs()"

    #//////////////////////////////////////////////////////////////////////////
    # Split into SF and non-SF rows 
    cond_met = df["BPT"] == "SF"

    # Split into 2 DataFrames
    df_met = df[cond_met]
    df_nomet = df[~cond_met]

    #//////////////////////////////////////////////////////////////////////////
    # Compute metallicity WITHOUT ERRORS
    pd.options.mode.chained_assignment = None
    print(f"{status_str}: computing metallicity without errors...")
    if compute_logU:
        res = _get_metallicity(met_diagnostic, df_met, compute_logU=True, ion_diagnostic=ion_diagnostic)
        df_met[f"log(O/H) + 12 ({met_diagnostic}/{ion_diagnostic})"] = res[0]
        df_met[f"log(U) ({met_diagnostic}/{ion_diagnostic})"] = res[1]
   
    elif logU is not None:
        res = _get_metallicity(met_diagnostic, df_met, compute_logU=False, logU=logU)
        df_met[f"log(O/H) + 12 ({met_diagnostic})"] = res[0]
        df_met[f"log(U) ({met_diagnostic})"] = res[1]

    else:
        df_met[f"log(O/H) + 12 ({met_diagnostic})"] = _get_metallicity(met_diagnostic, df_met, compute_logU=False, logU=logU) 
    pd.options.mode.chained_assignment = "warn"

    #//////////////////////////////////////////////////////////////////////////
    # Merge back with original DataFrame
    print(f"{status_str}: Concatenating DataFrames...")
    df = pd.concat([df_nomet, df_met], sort=True)

    print(f"{status_str}: Done!")
    return df

###############################################################################
def calculate_metallicity(df, met_diagnostic, 
                          logU=None, 
                          compute_logU=False, ion_diagnostic=None,
                          compute_errors=True, niters=1000, nthreads=10,
                          s=None):
    """
    Compute metallicities 



    INPUTS 
    ---------------------------------------------------------------------------

    df:                  pandas DataFrame
        Pandas DataFrame containing emission line fluxes.

    met_diagnostic:      str
        Strong-line metallicity diagnostic to use. Options:
            N2Ha_K19    N2Ha diagnostic from Kewley (2019).
            S2Ha_K19    S2Ha diagnostic from Kewley (2019).
            N2S2_K19    N2S2 diagnostic from Kewley (2019).
            S23_K19     S23 diagnostic from Kewley (2019).
            O3N2_K19    O3N2 diagnostic from Kewley (2019).
            O2S2_K19    O2S2 diagnostic from Kewley (2019).
            O2Hb_K19    O2Hb diagnostic from Kewley (2019).
            N2O2_K19    N2O2 diagnostic from Kewley (2019).
            R23_K19     R23 diagnostic from Kewley (2019).
            N2Ha_PP04   N2Ha diagnostic from Pilyugin & Peimbert (2004).
            N2Ha_M13    N2Ha diagnostic from Marino et al. (2013).
            O3N2_PP04   O3N2 diagnostic from Pilyugin & Peimbert (2004).
            O3N2_M13    O3N2 diagnostic from Marino et al. (2013).
            R23_KK04    R23 diagnostic from Kobulnicky & Kewley (2004).
            N2S2Ha_D16  N2S2Ha diagnostic from Dopita et al. (2016).
            N2O2_KD02   N2O2 diagnostic from Kewley & Dopita (2002).
            Rcal_PG16   Rcal diagnostic from Pilyugin & Grebel (2016).
            Scal_PG16   Scal diagnostic from Pilyugin & Grebel (2016).
            ONS_P10     ONS diagnostic from Pilyugin et al. (2010).
            ON_P10      ON diagnostic from Pilyugin et al. (2010).

    logU:                float
        Constant dimensionless ionisation parameter (where U = q / c) to 
        assume in diagnostics that require log(U) to be specified. These 
        include all Kewley (2019) diagnostics and the R23 calibration of 
        Kobulnicky & Kewley (2004).
    
    compute_logU:        bool
        If True, iteratively compute self-consistent metallicities and 
        ionisation parameters using a strong-line ionisation parameter 
        diagnostic. This parameter ignores the logU input parameter.

    ion_diagnostic:      str 
        If compute_logU is set, ion_diagnostic specifies the strong-line 
        ionisation parameter diagnostic to use. If the metallicity diagnostic
        is from Kewley (2019) then ion_diagnostic may be "O3O2_K19" or 
        "S32_K19". If the metallicity diagnostic is "R23_KD04" then 
        ion_diagnostic must be "O3O2_KD04".

    compute_errors:      bool
        If True, estimate 1-sigma errors on log(O/H) + 12 and log(U) using a 
        Monte Carlo approach, in which the 1-sigma uncertainties on the 
        emission line fluxes are used generate a distribution in log(O/H) + 12 
        values, the mean and standard deviation of which are used to 
        evaluate the metallicity and corresponding uncertainty.

    niters:              int
        Number of MC iterations. 1000 is recommended.

    nthreads:            int 
        Number of threads to use when computing errors.

    s:                   str 
        Column suffix to trim before carrying out computation - e.g. if 
        you want to compute metallicities using the "total" fluxes, and the 
        columns of the DataFrame look like 

            "HALPHA (total)", "HALPHA error (total)", etc.,

        then setting s=" (total)" will mean that this function "sees"

            "HALPHA", "HALPHA error".

        Useful for running this function on different emission line 
        components. The suffix is added back to the columns (and appended
        to any new columns that are added) before being returned. For 
        example, using the above example, the new added columns will be 

            "log(O/H) + 12 (N2O2_K19) (total)", 
            "log(O/H) + 12 (N2O2_K19) error (total)"


    OUTPUTS 
    ---------------------------------------------------------------------------

    The input DataFrame with additional columns added containing the computed 
    metallicity (plus ionisation parameter) and associated errors if 
    compute_errors is set to True.

    """
    t = time()
    status_str = f"In calculate_metallicity({met_diagnostic}, logU={logU}, compute_logU={compute_logU}, ion_diagnostic={ion_diagnostic}, compute_errors={compute_errors}, niters={niters}, nthreads={nthreads})"

    #//////////////////////////////////////////////////////////////////////////
    # Input checks
    #//////////////////////////////////////////////////////////////////////////
    assert met_diagnostic in line_list_dict,\
        f"Metallicity diagnostic {met_diagnostic} is not valid!"
    for line in line_list_dict[met_diagnostic]:
        assert f"{line}{s}" in df,\
            f"Metallicity diagnostic {met_diagnostic} requires {line} which was not found in the DataFrame!"

    # Check that logU is specified if the diagnostic requires it 
    if met_diagnostic.endswith("K19") or met_diagnostic == "R23_KK04":
        assert (logU is not None) or compute_logU,\
            f"Metallicity diagnostic {met_diagnostic} requires either logU to specified OR compute_logU = True!"

    # Check that the ionisation parameter diagnostic is specified & that all 
    # required lines are present 
    if compute_logU:
        if met_diagnostic == "R23_KK04":
            assert ion_diagnostic == "O3O2_KK04", "If R23_KK04 is the chosen metallicity diagnostic, then the ionisation parameter diagnostic must be O3O2_KK04!"
        elif met_diagnostic.endswith("K19"):
            assert ion_diagnostic.endswith("K19"), "If the the chosen metallicity diagnostic is from Kewley (2019), then the ionisation parameter diagnostic must also be from Kewley (2019)!"
        for line in line_list_dict[ion_diagnostic]:
            assert f"{line}{s}" in df,\
                f"ionisation parameter diagnostic {ion_diagnostic} requires {line} which was not found in the DataFrame!"


    #//////////////////////////////////////////////////////////////////////////
    # Remove suffixes on columns
    #//////////////////////////////////////////////////////////////////////////
    print(f"{status_str}: Removing column suffixes...")
    if s is not None:
        df_old = df
        suffix_cols = [c for c in df.columns if c.endswith(s)]
        suffix_removed_cols = [c.split(s)[0] for c in suffix_cols]
        df = df_old.rename(columns=dict(zip(suffix_cols, suffix_removed_cols)))
    old_cols = df.columns

    #//////////////////////////////////////////////////////////////////////////
    # Calculate the metallicity
    #//////////////////////////////////////////////////////////////////////////
    if compute_errors:
        print(f"{status_str}: Computing metallicities with errors...")
        df = _get_metallicity_errs(met_diagnostic=met_diagnostic, df=df, logU=logU, compute_logU=compute_logU, ion_diagnostic=ion_diagnostic, niters=niters, nthreads=nthreads)
    else:
        print(f"{status_str}: Computing metallicities without errors...")
        df = _get_metallicity_no_errs(met_diagnostic=met_diagnostic, df=df, logU=logU, compute_logU=compute_logU, ion_diagnostic=ion_diagnostic,)

    #//////////////////////////////////////////////////////////////////////////
    # Rename columns
    #//////////////////////////////////////////////////////////////////////////
    print(f"{status_str}: Adding column suffixes...")
    if s is not None:
        # Get list of new columns that have been added
        added_cols = [c for c in df.columns if c not in old_cols]
        suffix_added_cols = [f"{c}{s}" for c in added_cols]
        # Rename the new columns
        df = df.rename(columns=dict(zip(added_cols, suffix_added_cols)))
        # Replace the suffix in the column names
        df = df.rename(columns=dict(zip(suffix_removed_cols, suffix_cols)))

    print(f"{status_str}: Done! Total time = {int(np.floor((time() - t) / 3600)):d}:{int(np.floor((time() - t) / 60)):d}:{np.mod(time() - t, 60):02.5f}")
    return df 
