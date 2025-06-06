from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from io import BytesIO
import xml.etree.ElementTree as ET
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph

class InvoicePDFBuilder:
    def __init__(self, xml_string: str, logo_bytes: bytes):
        self.root = ET.fromstring(xml_string)
        self.logo_bytes = logo_bytes
        self.canvas = None
        self.width, self.height = A4
        self.margin = 10 * mm
        self.line_height = 5 * mm
        self.y = self.height - self.margin
        self.page_num = 1
        self.min_y = 40 * mm
        self.styles = getSampleStyleSheet()
        
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

    def _check_page_break(self, required_height):
        if self.y - required_height < self.min_y:
            self._new_page()

    def _new_page(self):
        self._draw_footer_bar()
        self.canvas.showPage()
        self.page_num += 1
        self.y = self.height - self.margin
        self._draw_header()
        self._draw_footer_bar()

    def _draw_text(self, x, y, text, size=10, bold=False):
        font = "Helvetica-Bold" if bold else "Helvetica"
        self.canvas.setFont(font, size)
        self.canvas.drawString(x, y, text)

    def _draw_centered(self, y, text, size=12, bold=True):
        font = "Helvetica-Bold" if bold else "Helvetica"
        self.canvas.setFont(font, size)
        text_width = self.canvas.stringWidth(text, font, size)
        x = (self.width - text_width) / 2
        self.canvas.drawString(x, y, text)
        return y - self.line_height

    def _draw_right(self, x, y, text, size=10, bold=False):
        font = "Helvetica-Bold" if bold else "Helvetica"
        self.canvas.setFont(font, size)
        self.canvas.drawRightString(x, y, text)

    def _draw_logo(self):
        if self.logo_bytes:
            try:
                logo = ImageReader(BytesIO(self.logo_bytes))
                self.canvas.drawImage(logo, self.width - self.margin - 40*mm, 
                                     self.height - self.margin - 15*mm, 
                                     width=40*mm, preserveAspectRatio=True)
            except Exception:
                pass

    def _draw_header(self):
        self.y = self.height - self.margin - 5*mm
        self.y = self._draw_centered(self.y, self._extract(self.provider, "PROVIDER_NAME").upper(), 10, True)
        self._draw_centered(self.y, 
            f"{self._extract(self.provider, 'PROVIDER_NAME')} • {self._extract(self.provider, 'STREET')} {self._extract(self.provider, 'NUMBER')} • "
            f"{self._extract(self.provider, 'ZIP')} {self._extract(self.provider, 'CITY')}", 
            7, False
        )
        self.y -= 15*mm

    def _draw_recipient(self):
        self._check_page_break(25*mm)
        self._draw_text(self.margin, self.y, f"{self._extract(self.customer, 'FIRST_NAME')} {self._extract(self.customer, 'LAST_NAME')}")
        self.y -= self.line_height
        self._draw_text(self.margin, self.y, f"{self._extract(self.customer, 'STREET')} {self._extract(self.customer, 'NUMBER')}")
        self.y -= self.line_height
        self._draw_text(self.margin, self.y, f"{self._extract(self.customer, 'ZIP')} {self._extract(self.customer, 'CITY')}")
        self.y -= 20*mm

    def _draw_invoice_metadata(self):
        self._draw_centered(self.y, "RECHNUNG", 16, True)
        self.y -= 15*mm
        
        meta_y = self.height - self.margin - 40*mm
        self._draw_right(self.width - self.margin, meta_y, f"Rechnungsnummer: {self._extract(self.invoice, 'INVOICE_NR')}")
        meta_y -= self.line_height
        self._draw_right(self.width - self.margin, meta_y, f"Kundennummer: {self._extract(self.invoice, 'FK_CUSTID')}")
        meta_y -= self.line_height
        self._draw_right(self.width - self.margin, meta_y, f"Datum: {self._extract(self.invoice, 'CREATION_DATE')}")

    def _draw_sender(self):
        self._check_page_break(45*mm)
        self._draw_text(self.margin, self.y, self._extract(self.provider, "PROVIDER_NAME"), bold=True)
        self.y -= self.line_height
        self._draw_text(self.margin, self.y, self._extract(self.ceo, "CEO_NAME"))
        self.y -= self.line_height
        self._draw_text(self.margin, self.y, f"{self._extract(self.provider, 'STREET')} {self._extract(self.provider, 'NUMBER')}")
        self.y -= self.line_height
        self._draw_text(self.margin, self.y, f"{self._extract(self.provider, 'ZIP')} {self._extract(self.provider, 'CITY')}")
        self.y -= 8*mm

        contacts = [
            ("Mobil:", self._extract(self.provider, "MOBILTELNR")),
            ("Tel.:", self._extract(self.provider, "TELNR")),
            ("Fax:", self._extract(self.provider, "FAXNR")),
            ("E-Mail:", self._extract(self.provider, "EMAIL")),
            ("Web:", self._extract(self.provider, "WEBSITE"))
        ]
        
        for label, value in contacts:
            self._draw_text(self.margin, self.y, f"{label} {value}")
            self.y -= self.line_height

        self.y -= 10*mm

    def _draw_greeting(self):
        self._check_page_break(15*mm)
        self._draw_text(self.margin, self.y, f"Sehr geehrter Herr {self._extract(self.customer, 'LAST_NAME')},")
        self.y -= self.line_height
        self._draw_text(self.margin, self.y, "vielen Dank für Ihren Auftrag, den wir wie folgt in Rechnung stellen.")
        self.y -= 15*mm

    def _draw_positions(self):
        # Tabellenüberschrift
        self._check_page_break(10*mm)
        self._draw_text(self.margin, self.y, "Pos.", bold=True)
        self._draw_text(self.margin + 20*mm, self.y, "Bezeichnung", bold=True)
        self._draw_right(self.width - self.margin, self.y, "Preis", bold=True)
        self.y -= 8*mm
        
        # Positionsdaten
        self.netto_summe = 0
        for idx, pos in enumerate(self.positions, 1):
            name = self._extract(pos, "NAME")
            desc = self._extract(pos, "DESCRIPTION")
            area = float(self._extract(pos, "AREA") or 0)
            unit_price = float(self._extract(pos, "UNIT_PRICE") or 0)
            total = area * unit_price
            self.netto_summe += total
            
            # Prüfe Platz für diese Position (3-5 Zeilen)
            lines_needed = 3 + len(desc.splitlines()) if desc else 3
            required_height = lines_needed * self.line_height
            
            if self.y - required_height < self.min_y:
                self._new_page()
                # Überschrift auf neuer Seite neu zeichnen
                self._draw_text(self.margin, self.y, "Pos.", bold=True)
                self._draw_text(self.margin + 20*mm, self.y, "Bezeichnung", bold=True)
                self._draw_right(self.width - self.margin, self.y, "Preis", bold=True)
                self.y -= 8*mm
            
            # Positionskopf
            self._draw_text(self.margin, self.y, f"Pos. {idx} {name}")
            self.y -= self.line_height
            
            # Beschreibung (mehrzeilig)
            if desc:
                for line in desc.splitlines():
                    self._draw_text(self.margin + 5*mm, self.y, line)
                    self.y -= self.line_height
            
            # Mengenangabe und Preis
            self._draw_text(self.margin + 5*mm, self.y, f"{area:.2f} m² EP: {unit_price:.2f} €")
            self._draw_right(self.width - self.margin, self.y, f"{total:.2f} €")
            self.y -= 2*self.line_height

    def _draw_totals(self):
        self._check_page_break(30*mm)
        vat_rate = float(self._extract(self.invoice, "VAT_RATE_POSITIONS") or 19)
        vat = self.netto_summe * vat_rate / 100
        brutto = self.netto_summe + vat
        labor_cost = float(self._extract(self.invoice, "LABOR_COST") or 0)
        vat_labor = labor_cost * 19 / 119  # Enthaltene MwSt in Lohnkosten
        
        # Summenblock
        self.y -= 5*mm
        self._draw_right(self.width - 60*mm, self.y, "Nettobetrag:")
        self._draw_right(self.width - self.margin, self.y, f"{self.netto_summe:.2f} €")
        self.y -= self.line_height
        
        self._draw_right(self.width - 60*mm, self.y, f"zzgl. {vat_rate:.0f} % MwSt.:")
        self._draw_right(self.width - self.margin, self.y, f"{vat:.2f} €")
        self.y -= self.line_height
        
        self._draw_right(self.width - 60*mm, self.y, "Bruttobetrag:", bold=True)
        self._draw_right(self.width - self.margin, self.y, f"{brutto:.2f} €", bold=True)
        self.y -= 15*mm
        
        # Zahlungshinweis
        self._draw_text(self.margin, self.y, 
            f"Überweisen Sie bitte den offenen Betrag in Höhe von {brutto:.2f} € auf das unten aufgeführte Geschäftskonto.")
        self.y -= self.line_height
        if labor_cost > 0:
            self._draw_text(self.margin, self.y, 
                f"Im Bruttobetrag sind {labor_cost:.2f} € Lohnkosten enthalten. Die darin enthaltene Mehrwertsteuer beträgt {vat_labor:.2f} €.")
            self.y -= 15*mm

    def _draw_closing(self):
        self._check_page_break(30*mm)
        self._draw_text(self.margin, self.y, "Mit freundlichen Grüßen")
        self.y -= 2*self.line_height
        self._draw_text(self.margin, self.y, self._extract(self.ceo, "CEO_NAME"))
        self.y -= 15*mm
        
        # Fußnoten
        self._draw_text(self.margin, self.y, "Sie sind verpflichtet, die Rechnung zu Steuerzwecken zwei Jahre lang aufzubewahren.")
        self.y -= self.line_height
        self._draw_text(self.margin, self.y, f"Die aufgeführten Arbeiten wurden ausgeführt im {self._extract(self.invoice, 'SERVICE_PERIOD')}.")
        self.y -= 20*mm

    def _draw_footer(self):
        self._check_page_break(70*mm)
        # Drei Spalten: Sitz, Bank, Geschäftsführung
        col_width = (self.width - 2*self.margin) / 3
        
        # Spalte 1: Sitz des Unternehmens
        self._draw_text(self.margin, self.y, "Sitz des Unternehmens:", bold=True)
        self.y -= self.line_height
        self._draw_text(self.margin, self.y, self._extract(self.provider, "PROVIDER_NAME"))
        self.y -= self.line_height
        self._draw_text(self.margin, self.y, f"{self._extract(self.provider, 'STREET')} {self._extract(self.provider, 'NUMBER')}")
        self.y -= self.line_height
        self._draw_text(self.margin, self.y, f"{self._extract(self.provider, 'ZIP')} {self._extract(self.provider, 'CITY')}")
        self.y += 4*self.line_height  # Zurück zur Grundlinie
        
        # Spalte 2: Bankverbindung
        self._draw_text(self.margin + col_width, self.y, "Bankverbindung:", bold=True)
        self.y -= self.line_height
        if self.bank is not None:
            self._draw_text(self.margin + col_width, self.y, self._extract(self.bank, "BANK_NAME"))
            self.y -= self.line_height
            self._draw_text(self.margin + col_width, self.y, f"IBAN: {self._extract(self.bank, 'IBAN')}")
            self.y -= self.line_height
            self._draw_text(self.margin + col_width, self.y, f"BIC: {self._extract(self.bank, 'BIC')}")
        else:
            self._draw_text(self.margin + col_width, self.y, "(nicht angegeben)")
        self.y += 3*self.line_height
        
        # Spalte 3: Geschäftsführung
        self._draw_text(self.margin + 2*col_width, self.y, "Geschäftsführung:", bold=True)
        self.y -= self.line_height
        self._draw_text(self.margin + 2*col_width, self.y, self._extract(self.ceo, "CEO_NAME"))
        self.y -= self.line_height
        self._draw_text(self.margin + 2*col_width, self.y, f"St.-Nr.: {self._extract(self.ceo, 'ST_NR')}")
        self.y -= self.line_height
        self._draw_text(self.margin + 2*col_width, self.y, f"USt-IdNr.: {self._extract(self.invoice, 'FK_UST_IDNR')}")

    def _draw_footer_bar(self):
        self.canvas.setFont("Helvetica", 8)
        self.canvas.drawString(self.margin, 10*mm, 
            "BackOffice 2020 – Das ideale Rechnungsprogramm für Handwerksbetriebe")
        self.canvas.drawRightString(self.width - self.margin, 10*mm, f"Seite {self.page_num}")

    def build(self, output_path: str):
        self.canvas = canvas.Canvas(output_path, pagesize=A4)
        self._draw_logo()
        self._draw_header()
        self._draw_recipient()
        self._draw_invoice_metadata()
        self._draw_sender()
        self._draw_greeting()
        self._draw_positions()
        self._draw_totals()
        self._draw_closing()
        self._draw_footer()
        self._draw_footer_bar()
        self.canvas.save()
        return output_path