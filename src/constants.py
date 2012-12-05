"""constants.py - Miscellaneous constants."""

import os

from gi.repository import GLib

VERSION = '4.0.5'
HOME_DIR = GLib.get_home_dir()
CONFIG_DIR = os.path.join(GLib.get_user_config_dir(), 'comix')
DATA_DIR = os.path.join(GLib.get_user_data_dir(), 'comix')
