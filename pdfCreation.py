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
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

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
        self.min_y = 20 * mm
        self.styles = getSampleStyleSheet()
        
        # Custom styles
        self.styles.add(ParagraphStyle(
            name='NormalWrap',
            fontName='Helvetica',
            fontSize=10,
            leading=12,
            alignment=TA_LEFT
        ))

        self.styles.add(ParagraphStyle(
            name='RightWrap',
            fontName='Helvetica',
            fontSize=10,
            leading=12,
            alignment=TA_RIGHT
        ))

        self.styles.add(ParagraphStyle(
            name='CenterWrap',
            fontName='Helvetica',
            fontSize=10,
            leading=12,
            alignment=TA_CENTER
        ))

        self.styles.add(ParagraphStyle(
            name='Bold',
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=12,
            alignment=TA_LEFT
        ))

        self.styles.add(ParagraphStyle(
            name='RightBold',
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=12,
            alignment=TA_RIGHT
        ))

        self.styles.add(ParagraphStyle(
            name='CenterBold',
            fontName='Helvetica-Bold',
            fontSize=12,
            leading=14,
            alignment=TA_CENTER
        ))
        
        # Parse XML with null checks
        self.invoice = self.root.find("invoice") or ET.Element("dummy")
        self.customer = self.root.find("customer") or ET.Element("dummy")
        self.provider = self.root.find("service_provider") or ET.Element("dummy")
        ceo_elem = self.root.find("ceos")
        self.ceos = ceo_elem.findall("ceo") if ceo_elem is not None else []
        positions_elem = self.root.find("positions")
        self.positions = positions_elem.findall("position") if positions_elem is not None else []
        self.bank = self.root.find("bank") or ET.Element("dummy")
        
    def _extract(self, element, tag, default=""):
        if element is None:
            return default
        child = element.find(tag)
        return child.text.strip() if child is not None and child.text else default

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
        return self.canvas.stringWidth(text, font, size)

    def _draw_centered(self, y, text, size=10, bold=False):
        font = "Helvetica-Bold" if bold else "Helvetica"
        self.canvas.setFont(font, size)
        text_width = self.canvas.stringWidth(text, font, size)
        x = (self.width - text_width) / 2
        self.canvas.drawString(x, y, text)
        return text_width

    def _draw_right(self, x, y, text, size=10, bold=False):
        font = "Helvetica-Bold" if bold else "Helvetica"
        self.canvas.setFont(font, size)
        text_width = self.canvas.stringWidth(text, font, size)
        self.canvas.drawString(x - text_width, y, text)
        return text_width

    def _draw_paragraph(self, x, y, text, style, max_width):
        if not text:
            return 0
        p = Paragraph(text, style)
        w, h = p.wrap(max_width, 1000)
        if w > max_width or h > 1000:  # Fallback if text too long
            text = text[:50] + '...'
            p = Paragraph(text, style)
            w, h = p.wrap(max_width, 1000)
        p.drawOn(self.canvas, x, y - h)
        return h

    def _draw_logo(self):
        if not self.logo_bytes:
            return 0
            
        try:
            logo = ImageReader(BytesIO(self.logo_bytes))
            logo_width = 60 * mm
            
            # Always position on right with margin
            logo_x = self.width - self.margin - logo_width
            
            # Fixed position below header
            logo_y = self.height - self.margin - 20 * mm
            logo_height = 20 * mm
                
            self.canvas.drawImage(logo, logo_x, logo_y, 
                                 width=logo_width, 
                                 height=logo_height,
                                 preserveAspectRatio=True,
                                 mask='auto',
                                 anchor = 'ne')
            return logo_height
        except Exception as e:
            print(f"Logo error: {str(e)}")
            return 0

    def _draw_header(self):
        # Draw logo first to reserve space
        logo_height = self._draw_logo() or 0
        self.y = self.height - self.margin - 5 * mm
        
        # Provider name with dynamic wrapping
        provider_name = self._extract(self.provider, "PROVIDER_NAME")
        max_width = self.width - 2*self.margin - 45*mm  # Reserve space for logo
        
        # Center text only if it fits, otherwise left-align
        if self.canvas and self.canvas.stringWidth(provider_name, "Helvetica-Bold", 12) < max_width:
            h = self._draw_paragraph(self.margin, self.y, provider_name.upper(), ParagraphStyle(name = 'ProviderName', fontName='Helvetica-Bold', fontSize=12, leading=12, alignment=TA_LEFT), 105*mm)
            if h > 0:
                self.y -= h + 1*mm

            self.y -= 15 * mm
        else:
            h = self._draw_paragraph(
                self.margin, 
                self.y, 
                provider_name.upper(), 
                self.styles['Bold'], 
                max_width
            )
            self.y -= h + 2*mm if h > 0 else 15*mm

    def _draw_recipient(self):
        self._check_page_break(40*mm)
        
        # Customer address with proper wrapping
        elements = [
            f"{self._extract(self.customer, 'FIRST_NAME')} {self._extract(self.customer, 'LAST_NAME')}",
            f"{self._extract(self.customer, 'STREET')} {self._extract(self.customer, 'NUMBER')}",
            f"{self._extract(self.customer, 'ZIP')} {self._extract(self.customer, 'CITY')}"
        ]
        
        for text in elements:
            h = self._draw_paragraph(
                self.margin, 
                self.y, 
                text, 
                self.styles['NormalWrap'], 
                80*mm
            )
            if h > 0:
                self.y -= h + 1*mm
            
        self.y -= 15*mm

    def _draw_invoice_metadata(self):
        self.y -= 20*mm
        self._draw_text(self.margin, self.y, "RECHNUNG", 16, True)
        self.y -= 10*mm
        
        invoice_data = [
            f"Rechnungsnummer: {self._extract(self.invoice, 'INVOICE_NR')}",
            f"Kundennummer: {self._extract(self.invoice, 'FK_CUSTID')}",
            f"Datum: {self._extract(self.invoice, 'CREATION_DATE')}"
        ]

        for text in invoice_data:
            h = self._draw_paragraph(
                self.margin, 
                self.y, 
                text, 
                self.styles['NormalWrap'], 
                80*mm
            )
            if h > 0:
                self.y -= h + 1*mm
        self.y -= 10*mm
        

    def _draw_sender(self):
        
        # Sender info with wrapping
        elements = [
            (self._extract(self.provider, "PROVIDER_NAME"), True)
        ]

        for ceo in self.ceos:
            elements += [(self._extract(ceo, "CEO_NAME"), False)]

        elements += [
            (self._extract(self.provider, 'STREET') + self._extract(self.provider, 'NUMBER'), False),
            (self._extract(self.provider, 'ZIP') + self._extract(self.provider, 'CITY'), False)
        ]

        meta_y = self.height - self.margin - 30*mm

        for text, bold in elements:
            if not text:
                continue
            style = self.styles['RightBold'] if bold else self.styles['RightWrap']
            h = self._draw_paragraph(
                self.width - self.margin - 80*mm, 
                meta_y, 
                text, 
                style, 
                80*mm
            )
            if h > 0:
                meta_y -= h + 1*mm
            
        meta_y -= 8*mm

        # Contact info with wrapping
        contacts = [
            ("Mobil:", self._extract(self.provider, "MOBILTELNR")),
            ("Tel.:", self._extract(self.provider, "TELNR")),
            ("Fax:", self._extract(self.provider, "FAXNR")),
            ("E-Mail:", self._extract(self.provider, "EMAIL")),
            ("Web:", self._extract(self.provider, "WEBSITE"))
        ]
        
        for label, value in contacts:
            if not value:
                continue
            text = f"{label} {value}"
            h = self._draw_paragraph(
                self.width - self.margin - 80*mm, 
                meta_y, 
                text, 
                self.styles['RightWrap'], 
                80*mm
            )
            if h > 0:
                meta_y -= h + 1*mm

    def _draw_greeting(self):
        self._check_page_break(20*mm)
        
        last_name = self._extract(self.customer, 'LAST_NAME')
        greeting = [
            f"Sehr geehrte Damen und Herren, ",
            "vielen Dank für Ihren Auftrag, den wir wie folgt in Rechnung stellen."
        ]
        
        for text in greeting:
            h = self._draw_paragraph(
                self.margin, 
                self.y, 
                text, 
                self.styles['NormalWrap'], 
                self.width - 2*self.margin
            )
            if h > 0:
                self.y -= h + 1*mm
            
        self.y -= 10*mm

    def _draw_positions(self):
        # Table header
        self._check_page_break(15*mm)
        self._draw_text(self.margin, self.y, "Pos.", bold=True)
        self._draw_text(self.margin + 20*mm, self.y, "Bezeichnung", bold=True)
        self._draw_right(self.width - self.margin, self.y, "Preis", bold=True)
        self.y -= 8*mm
        
        # Positions data
        self.netto_summe = 0
        for idx, pos in enumerate(self.positions, 1):
            name = self._extract(pos, "NAME")
            desc = self._extract(pos, "DESCRIPTION")
            try:
                area = float(self._extract(pos, "AREA") or 0)
                unit_price = float(self._extract(pos, "UNIT_PRICE") or 0)
                total = area * unit_price
                self.netto_summe += total
            except:
                area = 0
                unit_price = 0
                total = 0
            
            # Calculate space needed
            desc_lines = len(desc.split('\n')) if desc else 1
            required_height = (3 + desc_lines) * self.line_height
            
            if self.y - required_height < self.min_y:
                self._new_page()
                # Re-draw header
                self._draw_text(self.margin, self.y, "Pos.", bold=True)
                self._draw_text(self.margin + 20*mm, self.y, "Bezeichnung", bold=True)
                self._draw_right(self.width - self.margin, self.y, "Preis", bold=True)
                self.y -= 8*mm
            
            # Position header
            self._draw_paragraph(
                self.margin, 
                self.y, 
                f"Pos. {idx}", 
                self.styles['Bold'], 
                self.width - 2*self.margin
            )
            h = self._draw_paragraph(
                self.margin + 20*mm, 
                self.y, 
                f"{name}", 
                self.styles['Bold'], 
                self.width - 2*self.margin
            )
            if h > 0:
                self.y -= h + 2*mm
            
            # Description
            if desc != None:
                h = self._draw_paragraph(
                    self.margin + 5*mm, 
                    self.y, 
                    desc, 
                    self.styles['NormalWrap'], 
                    self.width - 2*self.margin - 30*mm
                )
                if h > 0:
                    self.y -= h + 2*mm  # This is the space after description
                self.y -= 3*mm  # Add this line to create additional spacing

            # Quantity and price
            qty_text = f"{area:.2f} m²         EP: {unit_price:.2f} €"
            self._draw_text(self.margin + 5*mm, self.y, qty_text)
            self._draw_right(self.width - self.margin, self.y, f"{total:.2f} €")
            self.y -= self.line_height

    def _draw_totals(self):
        self._check_page_break(50*mm)  # Increased space for expanded table
        self.y -= 25*mm
        
        # Extract values with null checks
        positions_netto = self.netto_summe
        try:
            labor_netto = float(self._extract(self.invoice, "LABOR_COST", "0"))
        except ValueError:
            labor_netto = 0.0
            
        vat_rate_positions = float(self._extract(self.invoice, "VAT_RATE_POSITIONS", "19")) / 100
        vat_rate_labor = float(self._extract(self.invoice, "VAT_RATE_LABOR", "19")) / 100
        
        # Calculate values
        tax_positions = positions_netto * vat_rate_positions
        tax_labor = labor_netto * vat_rate_labor
        total_netto = positions_netto + labor_netto
        total_tax = tax_positions + tax_labor
        total_brutto = total_netto + total_tax
        
        # Build table data
        data = [
            ["Nettobetrag Positionen:", f"{positions_netto:.2f} €"],
            ["Nettobetrag Arbeitskosten:", f"{labor_netto:.2f} €"],
            ["Zwischensumme Netto:", f"{total_netto:.2f} €", ""],
            [f"Umsatzsteuer {vat_rate_positions*100:.0f}% (Positionen):", f"{tax_positions:.2f} €"],
            [f"Umsatzsteuer {vat_rate_labor*100:.0f}% (Arbeitskosten):", f"{tax_labor:.2f} €"],
            ["Gesamt Umsatzsteuer:", f"{total_tax:.2f} €"],
            ["Rechnungsbetrag (Brutto):", f"{total_brutto:.2f} €"]
        ]
        
        table = Table(data, colWidths=[110*mm, 40*mm])
        table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -2), 'Helvetica', 10),
            ('FONT', (0, -1), (-1, -1), 'Helvetica-Bold', 10),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('LINEABOVE', (0, 3), (-1, 3), 0.5, colors.grey),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        table.wrapOn(self.canvas, self.width - 2*self.margin, self.height)
        table.drawOn(self.canvas, self.width - self.margin - 150*mm, self.y - 20*mm)
        self.y -= 30*mm  # More space for expanded table
        self.total_brutto = total_brutto  # Store for closing section

    def _draw_closing(self):
        self._check_page_break(100*mm)  # More space for bank info
        
        closing = [
            "Vielen Dank für Ihren Auftrag.",
            f"Überweisen Sie bitte den offenen Betrag in Höhe von {self.total_brutto:.2f} € auf eines der unten aufgeführten Geschäftskonten.",
            ""
        ]
        
        for text in closing:
            h = self._draw_paragraph(
                self.margin, 
                self.y, 
                text, 
                self.styles['NormalWrap'], 
                self.width - 2*self.margin
            )
            if h > 0:
                self.y -= h + 1*mm
            
        self.y -= 8*mm
        
        # Add bank information header
        h = self._draw_paragraph(
            self.margin,
            self.y,
            "Bankverbindung:",
            self.styles['Bold'],
            self.width - 2*self.margin
        )
        self.y -= h + 3*mm if h > 0 else 5*mm
        
        # Add bank accounts
        accounts = self.root.findall(".//account")
        if not accounts:
            h = self._draw_paragraph(
                self.margin + 5*mm,  # Indent slightly
                self.y, 
                "Bankverbindung ist in diesem Dokument nicht enthalten. Für weitere Informationen wenden Sie sich bitte an uns.", 
                self.styles['NormalWrap'], 
                self.width - 2*self.margin - 5*mm
            )
            if h > 0:
                self.y -= h + 2*mm
        for account in accounts:
            bank_name = self._extract(account, "BANK_NAME")  
            iban = self._extract(account, "IBAN")
            bic = self._extract(account, "BIC")
            
            bank_info = f"{bank_name}: IBAN {iban} • BIC {bic}"
            h = self._draw_paragraph(
                self.margin + 5*mm,  # Indent slightly
                self.y, 
                bank_info, 
                self.styles['NormalWrap'], 
                self.width - 2*self.margin - 5*mm
            )
            if h > 0:
                self.y -= h + 2*mm
                
        self.y -= 10*mm

    def _draw_footer(self):
        self._check_page_break(40*mm)

        footer = [
            "Mit freundlichen Grüßen",
            "",
            f"{self._extract(self.provider, 'PROVIDER_NAME')}"
        ]
        
        for ceo in self.ceos:
            ceo = f"{self._extract(ceo, 'CEO_NAME')} - Geschäftsführung" if self._extract(ceo, 'CEO_NAME') else ""
            footer += [ceo]

        for text in footer:
            h = self._draw_paragraph(
                self.margin, 
                self.y, 
                text, 
                self.styles['NormalWrap'], 
                self.width - 2*self.margin
            )
            if h > 0:
                self.y -= h + 1*mm
            if text == "":
                self.y -= self.line_height
            

    def _draw_footer_bar(self):
        # Draw separator line
        self.canvas.setStrokeColor(colors.black)
        self.canvas.setLineWidth(0.5)
        self.canvas.line(self.margin, self.min_y + 5*mm, self.width - self.margin, self.min_y + 5*mm)
        
        # Draw page number
        footer_text = f"Seite {self.page_num}"
        self._draw_centered(self.min_y, footer_text, 8)
        
        # Draw footer info
        provider_name = self._extract(self.provider, 'PROVIDER_NAME')
        street = self._extract(self.provider, 'STREET')
        number = self._extract(self.provider, 'NUMBER')
        zip_code = self._extract(self.provider, 'ZIP')
        city = self._extract(self.provider, 'CITY')
        tel = self._extract(self.provider, 'TELNR')
        email = self._extract(self.provider, 'EMAIL')
        
        footer_info = " | ".join(filter(None, [
            provider_name,
            f"{street} {number}" if street or number else None,
            f"{zip_code} {city}" if zip_code or city else None,
            f"Tel: {tel}" if tel else None,
            f"Email: {email}" if email else None
        ]))
        
        if footer_info:
            self._draw_paragraph(
                self.margin, 
                self.min_y - 5*mm, 
                footer_info, 
                self.styles['CenterWrap'], 
                self.width - 2*self.margin
            )

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
        self._draw_footer_bar()
        self.canvas.save()
        return output_path
    