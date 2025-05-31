-- View für die vollständigen Kundendaten
DROP VIEW IF EXISTS view_customers_full;
CREATE VIEW view_customers_full AS
SELECT
    c.CUSTID AS Kundennummer,  -- Kundennummer
    c.CREATION_DATE AS Erstellungsdatum,  -- Erstellungsdatum
    c.FIRST_NAME AS Vorname,  -- Vorname
    c.LAST_NAME AS Nachname,  -- Nachname
    c.GENDER AS Geschlecht,  -- Geschlecht
    a.STREET AS Strasse,  -- Straße
    a.NUMBER AS Hausnummer,  -- Hausnummer
    a.ZIP AS PLZ,  -- PLZ
    a.CITY AS Stadt,  -- Stadt
    a.COUNTRY AS Land  -- Land
FROM CUSTOMERS c
JOIN ADDRESSES a ON c.FK_ADDRESS_ID = a.ID;

-- View für die vollständigen Dienstleisterdaten
DROP VIEW IF EXISTS view_service_provider_full;
CREATE VIEW view_service_provider_full AS
SELECT
    sp.UST_IDNR AS UStIdNr,  -- USt-IDNr.
    sp.CREATION_DATE AS Erstellungsdatum,  -- Erstellungsdatum
    sp.PROVIDER_NAME AS Unternehmensname,  -- Firmenname
    sp.EMAIL AS Email,  -- E-Mail
    sp.WEBSITE AS Webseite,  -- Website
    a.STREET AS Strasse,  -- Straße
    a.NUMBER AS Hausnummer,  -- Hausnummer
    a.ZIP AS PLZ,  -- PLZ
    a.CITY AS Stadt,  -- Stadt
    a.COUNTRY AS Land,  -- Land
    sp.TELNR AS Telefonnummer,  -- Telefonnummer
    sp.MOBILTELNR AS Mobiltelefonnummer,  -- Mobiltelefonnummer
    sp.FAXNR AS Faxnummer,  -- Faxnummer
    acc.IBAN AS IBAN,  -- IBAN
    b.BIC AS BIC, --BIC
    b.BANK_NAME AS Kreditinstitut  -- Bankname
FROM SERVICE_PROVIDER sp
JOIN ADDRESSES a ON sp.FK_ADDRESS_ID = a.ID
JOIN LOGOS l ON sp.FK_LOGO_ID = l.ID
LEFT JOIN ACCOUNT acc ON sp.UST_IDNR = acc.FK_UST_IDNR
LEFT JOIN BANK b ON acc.FK_BANK_ID = b.BIC;

-- View für die vollständigen Rechnungsdaten
DROP VIEW IF EXISTS view_invoices_full;
CREATE VIEW view_invoices_full AS
SELECT
    i.INVOICE_NR AS Rechnungsnummer,
    i.CREATION_DATE AS Erstellungsdatum,
    c.FIRST_NAME || ' ' || c.LAST_NAME AS Kunde,
    sp.PROVIDER_NAME AS Unternehmensname,
    i.LABOR_COST AS Lohnkosten,
    i.VAT_RATE_LABOR AS MwSt_Lohn,
    i.VAT_RATE_POSITIONS AS MwSt_Positionen
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
    p.POS_ID AS PositionsID,
    p.CREATION_DATE AS "Erstellungsdatum Position",
    p.NAME AS Bezeichnung,
    p.DESCRIPTION AS Beschreibung,
    p.UNIT_PRICE AS Einzelpreis,
    p.AREA AS Flaeche
FROM
    POSITIONS p;
