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

        self.invoice = self.root.find("invoice")
        self.customer = self.root.find("customer")
        self.provider = self.root.find("service_provider")
        self.ceo = self.root.find("ceos/ceo")
        self.positions = self.root.find("positions").findall("position")
        self.bank = self.root.find("bank")

    def _extract(self, element, tag):
        child = element.find(tag)
        return child.text.strip() if child is not None and child.text else ""

    def build(self, output_path: str):
        c = canvas.Canvas(output_path, pagesize=A4)
        width, height = A4
        margin = 20 * mm
        line_height = 5 * mm
        y = height - margin

        def draw_text(x, y, text, size=10, bold=False):
            font = "Helvetica-Bold" if bold else "Helvetica"
            c.setFont(font, size)
            c.drawString(x, y, text)

        def draw_right(x, y, text, size=10, bold=False):
            font = "Helvetica-Bold" if bold else "Helvetica"
            c.setFont(font, size)
            c.drawRightString(x, y, text)

        def draw_logo():
            if self.logo_bytes:
                try:
                    logo = ImageReader(BytesIO(self.logo_bytes))
                    c.drawImage(logo, width - margin - 40 * mm, y - 10 * mm, width=40 * mm, preserveAspectRatio=True)
                except Exception:
                    pass

        # Header
        draw_logo()
        draw_text(margin, y, f"{self._extract(self.provider, 'PROVIDER_NAME')}   •   "
                             f"{self._extract(self.provider, 'STREET')} {self._extract(self.provider, 'NUMBER')}   •   "
                             f"{self._extract(self.provider, 'ZIP')} {self._extract(self.provider, 'CITY')}")
        y -= 15 * mm

        # Customer
        draw_text(margin, y, f"{self._extract(self.customer, 'FIRST_NAME')} {self._extract(self.customer, 'LAST_NAME')}")
        y -= line_height
        draw_text(margin, y, f"{self._extract(self.customer, 'STREET')} {self._extract(self.customer, 'NUMBER')}")
        y -= line_height
        draw_text(margin, y, f"{self._extract(self.customer, 'ZIP')} {self._extract(self.customer, 'CITY')}")
        y -= 10 * mm

        # Provider
        draw_text(margin, y, self._extract(self.provider, 'PROVIDER_NAME'))
        y -= line_height
        draw_text(margin, y, self._extract(self.ceo, 'CEO_NAME'))
        y -= line_height
        draw_text(margin, y, f"{self._extract(self.provider, 'STREET')} {self._extract(self.provider, 'NUMBER')}")
        y -= line_height
        draw_text(margin, y, f"{self._extract(self.provider, 'ZIP')} {self._extract(self.provider, 'CITY')}")
        y -= 8 * mm

        # Contact
        for label, tag in [("Mobil", "MOBILTELNR"), ("Tel.", "TELNR"), ("Fax", "FAXNR"),
                           ("E-Mail", "EMAIL"), ("Web", "WEBSITE")]:
            draw_text(margin, y, f"{label}: {self._extract(self.provider, tag)}")
            y -= line_height

        # Invoice Meta
        y -= 5 * mm
        draw_text(margin, y, "Rechnung", size=14, bold=True)
        y -= 8 * mm
        draw_text(margin, y, "Rechnungsnummer:")
        draw_text(margin + 40 * mm, y, self._extract(self.invoice, "INVOICE_NR"))
        y -= line_height
        draw_text(margin, y, "Kundennummer:")
        draw_text(margin + 40 * mm, y, self._extract(self.invoice, "FK_CUSTID"))
        y -= line_height
        draw_text(margin, y, "Datum:")
        draw_text(margin + 40 * mm, y, self._extract(self.invoice, "CREATION_DATE"))
        y -= 10 * mm

        # Greeting
        draw_text(margin, y, f"Sehr geehrter Herr {self._extract(self.customer, 'LAST_NAME')},")
        y -= line_height
        draw_text(margin, y, "vielen Dank für Ihren Auftrag, den wir wie folgt in Rechnung stellen.")
        y -= 10 * mm

        # Positions
        draw_text(margin, y, "Pos. Bezeichnung Preis", bold=True)
        y -= line_height
        netto_summe = 0
        for idx, pos in enumerate(self.positions, 1):
            name = self._extract(pos, "NAME")
            desc = self._extract(pos, "DESCRIPTION")
            area = float(self._extract(pos, "AREA") or 0)
            unit_price = float(self._extract(pos, "UNIT_PRICE") or 0)
            total = area * unit_price
            netto_summe += total

            draw_text(margin, y, f"Pos. {idx} {name}")
            y -= line_height
            if desc:
                for line in desc.splitlines():
                    draw_text(margin + 5 * mm, y, line)
                    y -= line_height
            draw_text(margin + 5 * mm, y, f"{area:.2f} m² EP: {unit_price:.2f} €")
            draw_right(width - margin, y, f"{total:.2f} €")
            y -= 2 * line_height

        # Totals
        y -= 2 * line_height
        vat_rate_positions = float(self._extract(self.invoice, "VAT_RATE_POSITIONS") or 19)
        vat = netto_summe * vat_rate_positions / 100
        brutto = netto_summe + vat

        draw_text(margin, y, "Nettobetrag:")
        draw_right(width - margin, y, f"{netto_summe:.2f} €")
        y -= line_height
        draw_text(margin, y, f"zzgl. {vat_rate_positions:.0f} % MwSt.:")
        draw_right(width - margin, y, f"{vat:.2f} €")
        y -= line_height
        draw_text(margin, y, "Bruttobetrag:")
        draw_right(width - margin, y, f"{brutto:.2f} €")
        y -= 10 * mm

        # Notes
        labor_cost = float(self._extract(self.invoice, "LABOR_COST") or 0)
        vat_rate_labor = float(self._extract(self.invoice, "VAT_RATE_LABOR") or 19)
        lohnsteueranteil = labor_cost * vat_rate_labor / (100 + vat_rate_labor)

        draw_text(margin, y, f"Überweisen Sie bitte den offenen Betrag in Höhe von {brutto:.2f} € auf das unten "
                             f"aufgeführte Geschäftskonto.")
        y -= line_height
        draw_text(margin, y, f"Im Bruttobetrag sind {labor_cost:.2f} € Lohnkosten enthalten. Die darin enthaltene "
                             f"Mehrwertsteuer beträgt {lohnsteueranteil:.2f} €.")
        y -= 10 * mm
        draw_text(margin, y, "Mit freundlichen Grüßen")
        y -= line_height
        draw_text(margin, y, self._extract(self.ceo, "CEO_NAME"))
        y -= 15 * mm

        # Footer
        draw_text(margin, y, "Sie sind verpflichtet, die Rechnung zu Steuerzwecken zwei Jahre lang aufzubewahren.")
        y -= line_height
        draw_text(margin, y, "Die aufgeführten Arbeiten wurden ausgeführt im Januar 2020.")
        y -= 10 * mm

        draw_text(margin, y, "Sitz des Unternehmens:")
        y -= line_height
        draw_text(margin, y, self._extract(self.provider, "PROVIDER_NAME"))
        y -= line_height
        draw_text(margin, y, f"{self._extract(self.provider, 'STREET')} {self._extract(self.provider, 'NUMBER')}")
        y -= line_height
        draw_text(margin, y, f"{self._extract(self.provider, 'ZIP')} {self._extract(self.provider, 'CITY')}")
        y -= 10 * mm

        draw_text(margin, y, "Bankverbindung:")
        y -= line_height
        if self.bank is not None:
            draw_text(margin, y, self._extract(self.bank, "BANK_NAME"))
            y -= line_height
            draw_text(margin, y, f"IBAN: {self._extract(self.bank, 'IBAN')}")
            y -= line_height
            draw_text(margin, y, f"BIC: {self._extract(self.bank, 'BIC')}")
        else:
            draw_text(margin, y, "(nicht angegeben)")
            y -= 2 * line_height

        y -= 5 * mm
        draw_text(margin, y, "Geschäftsführung:")
        y -= line_height
        draw_text(margin, y, self._extract(self.ceo, "CEO_NAME"))
        y -= line_height
        draw_text(margin, y, f"St.-Nr.: {self._extract(self.ceo, 'ST_NR')}")
        y -= line_height
        draw_text(margin, y, f"USt-IdNr.: {self._extract(self.invoice, 'FK_UST_IDNR')}")

        c.setFont("Helvetica", 8)
        c.drawString(margin, 10 * mm, "BackOffice 2020 – Das ideale Rechnungsprogramm für Handwerksbetriebe")
        c.drawRightString(width - margin, 10 * mm, "Seite 1 von 1")
        c.save()
        return output_path