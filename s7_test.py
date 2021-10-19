# Test all functions.

import numpy as np

from loaddata.s7 import load_s7_galaxies
from plotting.sdssimg import plot_sdss_image
from plotting.plotgalaxies import plot2dscatter, plot2dhist, plot2dcontours, plot2dhistcontours
from plotting.plottools import label_fn, bpt_labels, vmin_fn, vmax_fn, label_fn, component_labels
from plotting.plot2dmap import plot2dmap

import seaborn as sns

import matplotlib.pyplot as plt
plt.close("all")
plt.ion()

from IPython.core.debugger import Tracer

##############################################################################
# Load a dataset
##############################################################################
ncomponents = "recom"
bin_type = "default"
eline_SNR_min = 5

df = load_s7_galaxies(eline_SNR_min=eline_SNR_min,
                       sigma_gas_SNR_cut=True,
                       vgrad_cut=False)

gal = "NGC5253"
df_gal = df[df.catid == gal]

##############################################################################
# Test: 2D map plots
##############################################################################
plot2dmap(df_gal, survey="s7", bin_type=bin_type, col_z="HALPHA (total)")
Tracer()()

##############################################################################
# Test: 2D scatter
##############################################################################
fig, ax = plt.subplots(nrows=1, ncols=1)
bbox = ax.get_position()
cax = fig.add_axes([bbox.x0 + bbox.width, bbox.y0, 0.05, bbox.height])
plot2dscatter(df, col_x="log N2 (total)", col_y="log O3 (total)",
              col_z="log sigma_gas (component 0)", ax=ax, cax=cax)

# Test without providing axes
fig, ax = plt.subplots(nrows=1, ncols=1)
plot2dscatter(df_gal, col_x="log N2 (total)", col_y="log O3 (total)",
              col_z="log sigma_gas (component 0)", ax=ax)

##############################################################################
# Test: 2D histogram & 2D contours
##############################################################################
fig, ax = plt.subplots(nrows=1, ncols=1)
plot2dhist(df, col_x="log N2 (total)", col_y="log O3 (total)",
           col_z="BPT (numeric) (total)", ax=ax, nbins=30)

plot2dcontours(df, col_x="log N2 (total)", col_y="log O3 (total)",
              ax=ax, nbins=30)

##############################################################################
# Test: 2D contours
##############################################################################
fig, ax = plt.subplots(nrows=1, ncols=1)
plot2dhist(df, col_x="log N2 (total)", col_y="log O3 (total)",
           col_z="log sigma_gas (component 0)", ax=ax, nbins=30)

##############################################################################
# Test: 2D histogram + contours
##############################################################################
plot2dhistcontours(df, col_x="log sigma_gas (component 0)", col_y="log HALPHA EW (component 0)",
                   col_z="count", log_z=True)



