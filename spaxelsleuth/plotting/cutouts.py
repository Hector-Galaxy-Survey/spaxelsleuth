# Imports
import os
import numpy as np
from pathlib import Path
from urllib.request import urlretrieve

from astropy.visualization.wcsaxes import SphericalCircle
from astropy.wcs import WCS
from astropy import units

from spaxelsleuth.config import settings
from spaxelsleuth.plotting.plottools import plot_scale_bar

import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.patches import Circle

import logging
logger = logging.getLogger(__name__)

###############################################################################
# Paths
cutout_path = Path(settings["cutout_path"])


###############################################################################
def download_image(source, gal, ra_deg, dec_deg, as_per_px=0.1, sz_px=500):
    """
    Download a DECaLS or SDSS cutout image. 
    Images are saved to 
        settings["cutout_path"] / cutout_path / f"<source>_<gal>_<sz_px>px_<as_per_px>asperpx.jpg"
    
    INPUTS
    --------------------------------------------------------------------------
    source:         str
        Source of cutout. Must be "decals" or "sdss".
        
        gal:            str
            Name of galaxy. Note that this is not used in actually retrieving 
            the image, and is only used in the filename of the image - hence the 
            name can be arbitrary.

        ra_deg:         float 
            Right ascension of the galaxy in degrees.

        dec_deg:        float 
            Declination of the galaxy in degrees.

    as_per_px:      float 
        Plate scale of the decals image in arcseconds per pixel.

    sz_px:       int
        Size in pixels of image to download.

    OUTPUTS
    --------------------------------------------------------------------------
    Returns True if the image was successfully received; False otherwise.
    """
    # Input checking
    if source not in ["sdss", "decals"]:
        raise ValueError(f"'{source} is not a valid source for cutouts! source must be 'sdss' or 'decals'!")
    if not cutout_path.exists():
        raise FileNotFoundError(f"cutout image output path `{str(cutout_path)}` does not exist!")

    # Determine the URL
    if source == "sdss":
        url = f"https://skyserver.sdss.org/dr16/SkyServerWS/ImgCutout/getjpeg?TaskName=Skyserver.Explore.Image&ra={ra_deg}&dec={dec_deg}&scale={as_per_px}&width={sz_px}&height={sz_px}&opt=G"
    elif source == "decals":
        url = f"https://www.legacysurvey.org/viewer/jpeg-cutout?ra={ra_deg}&dec={dec_deg}&size={sz_px}&layer=ls-dr10&pixscale={as_per_px}"

    # Download the image
    imname = cutout_path / f"{source}_{gal}_{sz_px}px_{as_per_px}asperpx.jpg"
    try:
        urlretrieve(url, imname)
    except Exception as e:
        logger.warning(f"{gal} not in {source} footprint!")
        return False

    return True


###############################################################################
def plot_cutout_image(
    source,
    gal,
    df=None,
    ra_deg=None,
    dec_deg=None,
    kpc_per_as=None,
    axis_labels=True,
    as_per_px=0.1,
    sz_px=500,
    reload_image=False,
    show_scale_bar=True,
    ax=None,
    figsize=(5, 5),
):

    """Download and plot the DECaLS or SDSS cutout image of a galaxy.
    Cutout images are automatically downloaded using download_image() unless 
    they already exist in settings["cutout_path"].  
    If the galaxy lies outside the footprint of the specified survey, then
    no image is plotted.
    
    INPUTS
    --------------------------------------------------------------------------
    source:             str
        Source of cutout. Must be "decals" or "sdss".
        
    gal:                int or str
        Name of galaxy. Note that this is not used in actually retrieving 
        the image, and is only used in the filename of the image - hence the 
        name can be arbitrary. However, if ra_deg and dec_degare unspecified 
        then gal must be present in the index of df.

    df:             pandas DataFrame (optional)
        DataFrame containing spaxel-by-spaxel data.
        Must have index 
            ID - the catalogue ID of the galaxy
        and columns 
            RA (J2000) - the RA of the galaxy in degrees
            Dec (J2000) - the declination of the galaxy in degrees
        If df is unspecified, then ra_deg and dec_deg must be used to provide 
        the coordinates of the object. 

    ra_deg:         float (optional)
        Right ascension of the galaxy in degrees. Only used if df is unspecified.

    dec_deg:        float (optional)
        Declination of the galaxy in degrees. Only used if df is unspecified.

    axis_labels:    bool
        If True, plot RA and Dec axis labels.

    as_per_px:      float 
        Plate scale of the decals image in arcseconds per pixel.

    sz_px:          int
        Size in pixels of image to download.

    reload_image:   bool
        If True, force re-download of the image.

    ax:             matplotlib.axis
        axis on which to plot the image. Note that because axis projections 
        cannot be changed after an axis is created, the original axis is 
        removed and replaced with one of the same size with the correct WCS 
        projection. As a result, the order of the axis in fig.get_axes() 
        may change! 

    figsize:        tuple (width, height)
        Only used if axis is not specified, in which case a new figure is 
        created with figure size figsize.

    OUTPUTS
    --------------------------------------------------------------------------
    The axis containing the plotted image.

    """
    # Input checking
    if source not in ["sdss", "decals"]:
        raise ValueError(f"'{source} is not a valid source for cutouts! source must be 'sdss' or 'decals'!")
    if df is not None:
        df_gal = df[df["ID"] == gal]
        # Get the central coordinates from the DF
        if ("RA (IFU) (J2000)" in df_gal and "Dec (IFU) (J2000)" in df_gal) and (~np.isnan(df_gal["RA (IFU) (J2000)"].unique()[0])) and (~np.isnan(df_gal["Dec (IFU) (J2000)"].unique()[0])):
            ra_deg = df_gal["RA (IFU) (J2000)"].unique()[0]
            dec_deg = df_gal["Dec (IFU) (J2000)"].unique()[0]
        elif ("RA (J2000)" in df_gal and "Dec (J2000)" in df_gal) and (~np.isnan(df_gal["RA (J2000)"].unique()[0])) and (~np.isnan(df_gal["Dec (J2000)"].unique()[0])):
            ra_deg = df_gal["RA (J2000)"].unique()[0]
            dec_deg = df_gal["Dec (J2000)"].unique()[0]
        else:
            raise ValueError("No valid RA and Dec values found in DataFrame!")
        gal = df_gal["ID"].unique()[0]
        if show_scale_bar:
            kpc_per_as = df_gal["kpc per arcsec"].unique()[0]
    else:
        if gal is None:
            raise ValueError("gal must be specified!")
        if ra_deg is None:
            raise ValueError("ra_deg must be specified!")
        if dec_deg is None:
            raise ValueError("dec_deg must be specified!")
        if show_scale_bar and kpc_per_as is None:
            raise ValueError("kpc_per_as must be specified!")

    # Load image
    if reload_image or (not os.path.exists(cutout_path / f"{source}_{gal}_{sz_px}px_{as_per_px}asperpx.jpg")):
        # Download the image
        logger.warn(f"file {cutout_path / f'{source}_{gal}_{sz_px}px_{as_per_px}asperpx.jpg'} not found. Retrieving image from decals...")
        if not download_image(source=source, gal=gal, ra_deg=ra_deg, dec_deg=dec_deg,
                       as_per_px=as_per_px, sz_px=sz_px):
            return None

    im = mpimg.imread(cutout_path / f"{source}_{gal}_{sz_px}px_{as_per_px}asperpx.jpg")

    # Make a WCS for the image
    wcs = WCS(naxis=2)
    wcs.wcs.crpix = [im.shape[0] // 2, im.shape[1] // 2]
    wcs.wcs.cdelt = np.array([0.1 / 3600, 0.1 / 3600])
    wcs.wcs.crval = [ra_deg, dec_deg]
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]

    # If no axis is specified then create a new one with a vertical colorbar.
    if ax is None:
        fig, ax = plt.subplots(nrows=1, ncols=1, figsize=figsize, subplot_kw={"projection": wcs})
    else:
        # Sneaky... replace the provided axis with one that has the correct projection
        fig = ax.get_figure()
        bbox = ax.get_position()
        ax.remove()
        ax = fig.add_axes(bbox, projection=wcs)

    # Display the image
    ax.imshow(np.flipud(im))
    """
    WEIRD PROBLEM: only occurs for SOME galaxies. Exception occurs at 
        ax.imshow(np.flipud(im))
    also occurs when plotting a different image, e.g.
        ax.imshow(np.random.normal(loc=0, scale=10, size=(500, 500)))
    appears to be a latex error. Doesn't occur if the axis is not a WCS
    """

    # Include scale bar
    if show_scale_bar:
        plot_scale_bar(as_per_px=0.1, loffset=0.25, kpc_per_as=kpc_per_as, ax=ax, l=10, units="arcsec", fontsize=10, long_dist_str=False)

    # Axis labels
    if axis_labels:
        ax.set_ylabel("Dec (J2000)")
        ax.set_xlabel("RA (J2000)")

    return ax