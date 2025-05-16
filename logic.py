# This file contains application logic functions

from database import fetch_all

def get_ceos_for_service_provider(service_provider_id):
    """
    Returns a list of CEO names for a given service provider.
    """
    query = """
        SELECT CEO_NAME
        FROM REF_LABOR_COST AS rlc
        JOIN CEO AS ceo ON rlc.FK_ST_NR = ceo.ST_NR
        WHERE rlc.FK_UST_IDNR = ?
    """
    data, _ = fetch_all(query, (service_provider_id,))
    return [row[0] for row in data]

def get_service_provider_ceos_and_bank(service_provider_id):
    """
    Returns CEO names for a given service provider.
    """
    query = """
        SELECT CEO.CEO_NAME
        FROM CEO
        INNER JOIN REF_LABOR_COST ON CEO.ST_NR = REF_LABOR_COST.FK_ST_NR
        INNER JOIN SERVICE_PROVIDER ON REF_LABOR_COST.FK_UST_IDNR = SERVICE_PROVIDER.UST_IDNR
        WHERE SERVICE_PROVIDER.UST_IDNR = ?
    """
    data, _ = fetch_all(query, (service_provider_id,))
    return [row[0] for row in data]

def get_invoice_positions(invoice_id):
    """
    Returns position details for a given invoice.
    """
    query = """
        SELECT p.POS_ID, p.NAME, p.DESCRIPTION, p.AREA, p.UNIT_PRICE
        FROM POSITIONS AS p
        JOIN INVOICES AS i ON p.FK_INVOICE_NR = i.INVOICE_NR
        WHERE i.INVOICE_NR = ?
    """
    data, _ = fetch_all(query, (invoice_id,))
    return data