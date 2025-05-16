-- View für die vollständigen Kundendaten
DROP VIEW IF EXISTS view_customers_full;
CREATE VIEW view_customers_full AS
SELECT
    c.CUSTID,  -- Kundennummer
    c.CREATION_DATE,  -- Erstellungsdatum
    c.FIRST_NAME,  -- Vorname
    c.LAST_NAME,  -- Nachname
    c.GENDER,  -- Geschlecht
    a.STREET,  -- Straße
    a.NUMBER,  -- Hausnummer
    a.PLZ,  -- PLZ
    a.CITY,  -- Stadt
    a.COUNTRY  -- Land
FROM CUSTOMERS c
JOIN ADDRESSES a ON c.FK_ADDRESS_ID = a.ID;

-- View für die vollständigen Dienstleisterdaten
DROP VIEW IF EXISTS view_service_provider_full;
CREATE VIEW view_service_provider_full AS
SELECT
    sp.UST_IDNR,  -- USt-IDNr.
    sp.CREATION_DATE,  -- Erstellungsdatum
    sp.PROVIDER_NAME,  -- Firmenname
    sp.TELNR,  -- Telefonnummer
    sp.MOBILTELNR,  -- Mobiltelefonnummer
    sp.FAXNR,  -- Faxnummer
    sp.EMAIL,  -- E-Mail
    sp.WEBSITE,  -- Website
    a.STREET,  -- Straße
    a.NUMBER,  -- Hausnummer
    a.PLZ,  -- PLZ
    a.CITY,  -- Stadt
    a.COUNTRY,  -- Land
    l.FILE_NAME,  -- Logo-Dateiname
    acc.IBAN,  -- IBAN
    b.BANK_NAME  -- Bankname
FROM SERVICE_PROVIDER sp
JOIN ADDRESSES a ON sp.FK_ADDRESS_ID = a.ID
JOIN LOGOS l ON sp.FK_LOGO_ID = l.ID
LEFT JOIN ACCOUNT acc ON sp.UST_IDNR = acc.FK_UST_IDNR
LEFT JOIN BANK b ON acc.FK_BANK_ID = b.BIC;

-- View für die vollständigen Rechnungsdaten
DROP VIEW IF EXISTS view_invoices_full;
CREATE VIEW view_invoices_full AS
SELECT
    i.INVOICE_NR,
    i.CREATION_DATE,
    i.LABOR_COST,
    i.VAT_RATE_LABOR,
    i.VAT_RATE_POSITIONS,
    sp.PROVIDER_NAME,
    c.FIRST_NAME || ' ' || c.LAST_NAME AS Kunde
FROM
    INVOICES i
JOIN
    SERVICE_PROVIDER sp ON sp.UST_IDNR = i.FK_UST_IDNR
JOIN
    CUSTOMERS c ON c.CUSTID = i.FK_CUSTID;

-- View für Positionen einer Rechnung
DROP VIEW IF EXISTS view_positions_full;
CREATE VIEW view_positions_full AS
SELECT
    p.POS_ID,  -- Positions-ID
    p.CREATION_DATE,  -- Erstellungsdatum
    p.NAME,  -- Positionsname
    p.DESCRIPTION,  -- Beschreibung
    p.AREA,  -- Fläche/Menge
    p.UNIT_PRICE,  -- Preis pro Einheit
    i.INVOICE_NR  -- Rechnungsnummer
FROM POSITIONS p
JOIN INVOICES i ON p.FK_INVOICE_NR = i.INVOICE_NR;
