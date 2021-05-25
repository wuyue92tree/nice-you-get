# -*- coding: UTF-8 -*-
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if sys.platform == 'win32':
    HOME_DIR = os.path.join(os.path.expanduser('~'), '.nice_you_get')
else:
    HOME_DIR = os.path.join(os.environ['HOME'], '.nice_you_get')

LOG_DIR = os.path.join(HOME_DIR, 'log')

if os.path.exists(HOME_DIR) is False:
    os.makedirs(HOME_DIR)

if os.path.exists(LOG_DIR) is False:
    os.makedirs(LOG_DIR)

CONFIG_PATH = os.path.join(HOME_DIR, 'config.json')

VERSION = '1.1.0b1'