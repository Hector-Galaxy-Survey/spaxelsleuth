import json
import multiprocessing
from pathlib import Path

import logging
logging.captureWarnings(True)
logger = logging.getLogger(__name__)

def configure_multiprocessing():
    """Configure multiprocessing to use 'fork' rather than 'spawn' to prevent reinitialising the 'settings' global variable when running on OSX."""
    multiprocessing.set_start_method("fork")
    return

# Load the default config file
def configure_logger(logfile_name=None, level="INFO"):
    """Configure the logger for spaxelsleuth."""
    if level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        raise ValueError(f"level must be one of the following: 'DEBUG', 'INFO', 'WARNING', 'ERROR', or 'CRITICAL'")
    if logfile_name is None:
        logging.basicConfig(
            format='%(filename)s (%(lineno)s) %(funcName)s(): %(levelname)s: %(message)s', 
            level=logging.getLevelName(level),
            force=True)
    else:
        logging.basicConfig(
            filename=logfile_name, filemode="w",
            format='%(filename)s (%(lineno)s) %(funcName)s(): %(levelname)s: %(message)s', 
            level=logging.getLevelName(level),
            force=True)
    

# Load the default config file
def load_default_config():
    """Load the default config file."""
    print("Loading default config file")
    with open(Path(__file__).parent / "config.json", "r") as f:
        global settings
        settings = json.load(f)

# Allow user to upload custom settings - e.g. colourmaps, vmin/vmax limits, paths
def load_user_config(p, verbose=False):
    """Load a custom config file. Overwrites default configuration files."""
    print("Loading user config file")
    with open(Path(p)) as f:
        user_settings = json.load(f)
    # Merge with existing settings
    if verbose:
        logger.info(f"updating settings from {p}:")
    for key in user_settings:
        if key in settings:
            if verbose:
                logger.info(f"{key}:")
            if type(settings[key]) == dict:
                for subkey in user_settings[key]:
                    if verbose:
                        logger.info(f"\t{subkey}:")
                    new_setting = user_settings[key][subkey]
                    if subkey in settings[key]:
                        old_setting = settings[key][subkey]
                        if verbose:
                            logger.info(f"\t\t{old_setting} --> {new_setting}")
                    else:
                        if verbose:
                            logger.info(f"\t\tadding new setting {new_setting}")
                    settings[key][subkey] = new_setting
            else:
                settings[key] = user_settings[key]
        else:
            if verbose:
                logger.info(f"adding new key {key}: {user_settings[key]}")
            settings[key] = user_settings[key]