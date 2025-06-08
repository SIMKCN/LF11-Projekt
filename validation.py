import re

def validate_kundennummer(val):
    return re.fullmatch(r"\d{5}", val) is not None and "00001" <= val <= "99999"

def validate_hausnummer(val):
    return 1 <= len(val) <= 4

def validate_plz(val):
    return 1 <= len(val) <= 7

def validate_ustidnr(val):
    return len(val) <= 11

def validate_telefonnummer(val):
    # +49 351 35266472 oder 0351 3488354
    return re.fullmatch(r"(\+?\d{2,3}\s?)?\d{2,4}\s?\d{5,}", val) is not None

def validate_email(val):
    return re.fullmatch(r"[^@]+@[^@]+\.[^@]+", val) is not None

def validate_mobilnummer(val):
    # +49 17335266472 oder 01733488624
    return re.fullmatch(r"(\+?\d{2,3}\s?)?\d{7,}", val) is not None

def validate_iban(val):
    return 1 <= len(val) <= 22

def validate_bic(val):
    return 1 <= len(val) <= 12

def validate_beschreibung(val):
    return len(val) <= 1000

def validate_positionsnummer(val):
    return val.isdigit() and int(val) >= 0

def validate_mwst(val):
    try:
        f = float(val)
        return 0 <= f <= 100
    except:
        return False