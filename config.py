# This file contains configuration values and constants
import os

DB_PATH = "data/rechnungsverwaltung.db"
UI_PATH = "Qt/main.ui"
POSITION_DIALOG_PATH = "./Qt/position_dialog.ui"
DEBOUNCE_TIME=300
EXPORT_OUTPUT_PATH=os.getenv("PROGRAMDATA") + r"\Rechnungsverwaltung\export"
APPLICATION_WORKING_PATH=os.getenv("PROGRAMDATA") + r"\Rechnungsverwaltung"

IS_VALIDATION_ACTIVE = False
IS_AUTHENTICATION_ACTIVE = False
IS_AUTHORIZATION_ACTIVE = False