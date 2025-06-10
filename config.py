# This file contains configuration values and constants
import os

DB_PATH = "data/rechnungsverwaltung.db"
UI_PATH = "Qt/main.ui"
POSITION_DIALOG_PATH = "./Qt/position_dialog.ui"
DEBOUNCE_TIME=300
CACHE_OUTPUT_PATH=os.getenv("PROGRAMDATA") + r"\Rechnungsverwaltung\export"
MIN_LENGTH_EXPORT=8

IS_VALIDATION_ACTIVE = True
IS_AUTHENTICATION_ACTIVE = True
IS_AUTHORIZATION_ACTIVE = True