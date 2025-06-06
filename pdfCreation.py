from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from io import BytesIO
import xml.etree.ElementTree as ET


class InvoicePDFBuilder:
    def __init__(self, xml_string: str, logo_bytes: bytes):
        self.root = ET.fromstring(xml_string)
        self.logo_bytes = logo_bytes
        self.canvas = None
        self.width, self.height = A4
        self.margin = 20 * mm
        self.line_height = 5 * mm
        self.y = self.height - self.margin
        self.page_num = 1
        self.min_y = 40 * mm  # Minimaler Y-Wert vor Seitenumbruch

        # Parse XML
        self.invoice = self.root.find("invoice")
        self.customer = self.root.find("customer")
        self.provider = self.root.find("service_provider")
        self.ceo = self.root.find("ceos/ceo")
        positions_elem = self.root.find("positions")
        self.positions = positions_elem.findall("position") if positions_elem is not None else []
        self.bank = self.root.find("bank")

    def _extract(self, element, tag):
        child = element.find(tag)
        return child.text.strip() if child is not None and child.text else ""

    # Prüft, ob ausreichend Platz vorhanden ist und erstellt ggf. neue Seite.
    def _check_page_break(self, required_height):
        if self.y - required_height < self.min_y:
            self._new_page()

    # Erstellt eine neue Seite und zeichnet Kopf- und Fußzeilen-
    def _new_page(self):
        self._draw_footer_bar()  # Fußzeile für aktuelle Seite
        self.canvas.showPage()  # Beendet aktuelle Seite
        self.page_num += 1
        self.y = self.height - self.margin  # Setzt Y-Position zurück
        self._draw_header()  # Kopfzeile für neue Seite
        self._draw_footer_bar()  # Fußzeile für neue Seite

    def _draw_text(self, x, y, text, size=10, bold=False):
        font = "Helvetica-Bold" if bold else "Helvetica"
        self.canvas.setFont(font, size)
        self.canvas.drawString(x, y, text)

    def _draw_right(self, x, y, text, size=10, bold=False):
        font = "Helvetica-Bold" if bold else "Helvetica"
        self.canvas.setFont(font, size)
        self.canvas.drawRightString(x, y, text)

    def _draw_logo(self):
        if self.logo_bytes:
            try:
                logo = ImageReader(BytesIO(self.logo_bytes))
                self.canvas.drawImage(logo, self.width - self.margin - 40 * mm, self.y - 10 * mm,
                                      width=40 * mm, preserveAspectRatio=True)
            except Exception:
                pass

    def _draw_header(self):
        self._draw_logo()
        self._draw_text(
            self.margin,
            self.y,
            f"{self._extract(self.provider, 'PROVIDER_NAME')}   •   "
            f"{self._extract(self.provider, 'STREET')} {self._extract(self.provider, 'NUMBER')}   •   "
            f"{self._extract(self.provider, 'ZIP')} {self._extract(self.provider, 'CITY')}"
        )
        self.y -= 15 * mm

    def _draw_recipient(self):
        self._check_page_break(25 * mm)  # 3 Zeilen + Abstand
        
        self._draw_text(self.margin, self.y, f"{self._extract(self.customer, 'FIRST_NAME')} {self._extract(self.customer, 'LAST_NAME')}")
        self.y -= self.line_height
        self._draw_text(self.margin, self.y, f"{self._extract(self.customer, 'STREET')} {self._extract(self.customer, 'NUMBER')}")
        self.y -= self.line_height
        self._draw_text(self.margin, self.y, f"{self._extract(self.customer, 'ZIP')} {self._extract(self.customer, 'CITY')}")
        self.y -= 10 * mm

    def _draw_sender(self):
        self._check_page_break(45 * mm)  # 7 Zeilen + Abstände
        
        self._draw_text(self.margin, self.y, self._extract(self.provider, "PROVIDER_NAME"))
        self.y -= self.line_height
        self._draw_text(self.margin, self.y, self._extract(self.ceo, "CEO_NAME"))
        self.y -= self.line_height
        self._draw_text(self.margin, self.y, f"{self._extract(self.provider, 'STREET')} {self._extract(self.provider, 'NUMBER')}")
        self.y -= self.line_height
        self._draw_text(self.margin, self.y, f"{self._extract(self.provider, 'ZIP')} {self._extract(self.provider, 'CITY')}")
        self.y -= 8 * mm

        for label, tag in [("Mobil", "MOBILTELNR"), ("Tel.", "TELNR"), ("Fax", "FAXNR"),
                           ("E-Mail", "EMAIL"), ("Web", "WEBSITE")]:
            self._draw_text(self.margin, self.y, f"{label}: {self._extract(self.provider, tag)}")
            self.y -= self.line_height

    def _draw_invoice_metadata(self):
        self._check_page_break(20 * mm)  # 3 Zeilen + Abstand
        
        self.y -= 5 * mm
        self._draw_text(self.margin, self.y, "Rechnung", size=14, bold=True)
        self.y -= 8 * mm

        metadata = [
            ("Rechnungsnummer:", self._extract(self.invoice, "INVOICE_NR")),
            ("Kundennummer:", self._extract(self.invoice, "FK_CUSTID")),
            ("Datum:", self._extract(self.invoice, "CREATION_DATE")),
        ]
        for label, value in metadata:
            self._draw_text(self.margin, self.y, label)
            self._draw_text(self.margin + 40 * mm, self.y, value)
            self.y -= self.line_height

    def _draw_greeting(self):
        self._check_page_break(10 * mm)  # 2 Zeilen
        
        self._draw_text(self.margin, self.y, f"Sehr geehrter Herr {self._extract(self.customer, 'LAST_NAME')},")
        self.y -= self.line_height
        self._draw_text(self.margin, self.y, "vielen Dank für Ihren Auftrag, den wir wie folgt in Rechnung stellen.")
        self.y -= 10 * mm

    def _draw_positions(self):
        self._check_page_break(10 * mm)  # Mindestplatz für Überschrift
        
        self._draw_text(self.margin, self.y, "Pos. Bezeichnung Preis", bold=True)
        self.y -= self.line_height

        self.netto_summe = 0
        for idx, pos in enumerate(self.positions, 1):
            # Schätze benötigten Platz für diese Position
            name = self._extract(pos, "NAME")
            desc = self._extract(pos, "DESCRIPTION")
            area = float(self._extract(pos, "AREA") or 0)
            unit_price = float(self._extract(pos, "UNIT_PRICE") or 0)
            total = area * unit_price
            self.netto_summe += total

            # Berechne benötigte Höhe
            lines_needed = 2  # Grund: Positionszeile + Flächenzeile
            if desc:
                lines_needed += len(desc.splitlines())
            required_space = lines_needed * self.line_height + 10 * mm
            
            # Prüfe Seitenumbruch
            if self.y - required_space < self.min_y:
                self._new_page()
                self._draw_text(self.margin, self.y, "Pos. Bezeichnung Preis", bold=True)
                self.y -= self.line_height

            # Zeichne Position
            self._draw_text(self.margin, self.y, f"Pos. {idx} {name}")
            self.y -= self.line_height

            if desc:
                for line in desc.splitlines():
                    self._draw_text(self.margin + 5 * mm, self.y, line)
                    self.y -= self.line_height

            self._draw_text(self.margin + 5 * mm, self.y, f"{area:.2f} m² EP: {unit_price:.2f} €")
            self._draw_right(self.width - self.margin, self.y, f"{total:.2f} €")
            self.y -= 2 * self.line_height

    def _draw_totals(self):
        self._check_page_break(30 * mm)  # Platz für Summenblock
        
        self.y -= 2 * self.line_height
        vat_rate = float(self._extract(self.invoice, "VAT_RATE_POSITIONS") or 19)
        vat = self.netto_summe * vat_rate / 100
        brutto = self.netto_summe + vat

        self._draw_text(self.margin, self.y, "Nettobetrag:")
        self._draw_right(self.width - self.margin, self.y, f"{self.netto_summe:.2f} €")
        self.y -= self.line_height

        self._draw_text(self.margin, self.y, f"zzgl. {vat_rate:.0f} % MwSt.:")
        self._draw_right(self.width - self.margin, self.y, f"{vat:.2f} €")
        self.y -= self.line_height

        self._draw_text(self.margin, self.y, "Bruttobetrag:")
        self._draw_right(self.width - self.margin, self.y, f"{brutto:.2f} €")
        self.y -= 10 * mm

        labor_cost = float(self._extract(self.invoice, "LABOR_COST") or 0)
        vat_labor_rate = float(self._extract(self.invoice, "VAT_RATE_LABOR") or 19)

        if labor_cost > 0:
            self._check_page_break(15 * mm)  # Zusätzliche 2 Zeilen
            lohnsteueranteil = labor_cost * vat_labor_rate / (100 + vat_labor_rate)
            self._draw_text(self.margin, self.y, f"Überweisen Sie bitte den offenen Betrag in Höhe von {brutto:.2f} € auf das unten aufgeführte Geschäftskonto.")
            self.y -= self.line_height
            self._draw_text(self.margin, self.y, f"Im Bruttobetrag sind {labor_cost:.2f} € Lohnkosten enthalten. Die darin enthaltene Mehrwertsteuer beträgt {lohnsteueranteil:.2f} €.")
            self.y -= 10 * mm

    def _draw_closing(self):
        self._check_page_break(30 * mm)  # Platz für Grußformel
        
        self._draw_text(self.margin, self.y, "Mit freundlichen Grüßen")
        self.y -= self.line_height
        self._draw_text(self.margin, self.y, self._extract(self.ceo, "CEO_NAME"))
        self.y -= 15 * mm

        self._draw_text(self.margin, self.y, "Sie sind verpflichtet, die Rechnung zu Steuerzwecken zwei Jahre lang aufzubewahren.")
        self.y -= self.line_height
        self._draw_text(self.margin, self.y, "Die aufgeführten Arbeiten wurden ausgeführt im Januar 2020.")
        self.y -= 10 * mm

    def _draw_footer(self):
        self._check_page_break(70 * mm)  # Geschätzter Platz für Footer
        
        self._draw_text(self.margin, self.y, "Sitz des Unternehmens:")
        self.y -= self.line_height
        self._draw_text(self.margin, self.y, self._extract(self.provider, "PROVIDER_NAME"))
        self.y -= self.line_height
        self._draw_text(self.margin, self.y, f"{self._extract(self.provider, 'STREET')} {self._extract(self.provider, 'NUMBER')}")
        self.y -= self.line_height
        self._draw_text(self.margin, self.y, f"{self._extract(self.provider, 'ZIP')} {self._extract(self.provider, 'CITY')}")
        self.y -= 10 * mm

        self._draw_text(self.margin, self.y, "Bankverbindung:")
        self.y -= self.line_height
        if self.bank is not None:
            self._draw_text(self.margin, self.y, self._extract(self.bank, "BANK_NAME"))
            self.y -= self.line_height
            self._draw_text(self.margin, self.y, f"IBAN: {self._extract(self.bank, 'IBAN')}")
            self.y -= self.line_height
            self._draw_text(self.margin, self.y, f"BIC: {self._extract(self.bank, 'BIC')}")
        else:
            self._draw_text(self.margin, self.y, "(nicht angegeben)")
            self.y -= 2 * self.line_height

        self.y -= 5 * mm
        self._draw_text(self.margin, self.y, "Geschäftsführung:")
        self.y -= self.line_height
        self._draw_text(self.margin, self.y, self._extract(self.ceo, "CEO_NAME"))
        self.y -= self.line_height
        self._draw_text(self.margin, self.y, f"St.-Nr.: {self._extract(self.ceo, 'ST_NR')}")
        self.y -= self.line_height
        self._draw_text(self.margin, self.y, f"USt-IdNr.: {self._extract(self.invoice, 'FK_UST_IDNR')}")

    def _draw_footer_bar(self):
        self.canvas.setFont("Helvetica", 8)
        self.canvas.drawString(self.margin, 10 * mm, "BackOffice 2020 – Das ideale Rechnungsprogramm für Handwerksbetriebe")
        self.canvas.drawRightString(self.width - self.margin, 10 * mm, f"Seite {self.page_num}")

    def build(self, output_path: str):
        self.canvas = canvas.Canvas(output_path, pagesize=A4)
        self._draw_header()
        self._draw_recipient()
        self._draw_sender()
        self._draw_invoice_metadata()
        self._draw_greeting()
        self._draw_positions()
        self._draw_totals()
        self._draw_closing()
        self._draw_footer()
        self._draw_footer_bar()  # Für erste Seite
        self.canvas.save()
        return output_path