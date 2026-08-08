import os
import os.path
import tempfile
import threading
import time
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.pdfgen import canvas
from num2words import num2words
from datetime import date

def format_inr(number):
    return f"INR {number:,.2f}"

def print_pdf(pdf_path, page=None):
    """
    Send or view a PDF directly.
    Supports both Web mode (opens PDF in browser tab & shows printable notification)
    and Desktop mode (opens in native PDF viewer / spooler).
    """
    import flet as ft
    if not page:
        from core.state import state
        page = getattr(state, "page", None)

    filename = os.path.basename(pdf_path)
    web_url = f"/pdfs/{filename}"

    # Sync PDF to both assets/pdfs (for Web serving) and root pdfs/ (for Desktop/local)
    try:
        assets_dir = os.path.join(os.getcwd(), "assets", "pdfs")
        os.makedirs(assets_dir, exist_ok=True)
        asset_target = os.path.join(assets_dir, filename)
        if pdf_path != asset_target and os.path.exists(pdf_path):
            import shutil
            shutil.copy2(pdf_path, asset_target)

        legacy_dir = os.path.join(os.getcwd(), "pdfs")
        os.makedirs(legacy_dir, exist_ok=True)
        legacy_target = os.path.join(legacy_dir, filename)
        if pdf_path != legacy_target and os.path.exists(pdf_path):
            import shutil
            shutil.copy2(pdf_path, legacy_target)
    except Exception as ex:
        print(f"[PDF Sync Error] {ex}")

    opened_in_web = False
    if page:
        try:
            # 1. Trigger browser launch_url
            page.launch_url(web_url)
            opened_in_web = True

            # 2. Display persistent SnackBar with explicit button to open/print PDF
            page.snack_bar = ft.SnackBar(
                content=ft.Row([
                    ft.Icon(ft.icons.PICTURE_AS_PDF, color="white"),
                    ft.Text(f"PDF Generated: {filename}", color="white", weight="bold"),
                ], spacing=10),
                action="OPEN / PRINT PDF",
                action_color="#FEF08A",  # Pastel Yellow
                on_action=lambda e: page.launch_url(web_url),
                duration=12000,
                bgcolor="#166534"  # Forest Green
            )
            page.snack_bar.open = True
            page.update()
        except Exception as ex:
            print(f"[PDF Web Launch Error] {ex}")

    if not opened_in_web:
        try:
            if os.name == 'nt':
                os.startfile(pdf_path)
            else:
                import subprocess
                subprocess.run(["xdg-open", pdf_path], check=False)
        except Exception as ex:
            print(f"[PDF Native Desktop Error] {ex}")


class PDFGenerator:
    def __init__(self):
        self.output_dir = os.path.join(os.getcwd(), "assets", "pdfs")
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(os.path.join(os.getcwd(), "pdfs"), exist_ok=True)
        self._cleanup_old_pdfs()
        
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _cleanup_old_pdfs(self):
        """Silently deletes any PDF file in assets/pdfs and pdfs folders older than 24 hours."""
        current_time = time.time()
        for folder in [self.output_dir, os.path.join(os.getcwd(), "pdfs")]:
            try:
                if os.path.exists(folder):
                    for filename in os.listdir(folder):
                        if filename.endswith(".pdf"):
                            filepath = os.path.join(folder, filename)
                            if os.path.isfile(filepath) and (current_time - os.path.getmtime(filepath)) > 86400:
                                os.remove(filepath)
            except Exception as e:
                print(f"Cleanup error: {e}")

    def _setup_custom_styles(self):
        self.styles.add(ParagraphStyle(
            name='CenterBold',
            parent=self.styles['Normal'],
            alignment=1,
            fontSize=14,
            leading=18,
            fontName='Helvetica-Bold'
        ))
        self.styles.add(ParagraphStyle(
            name='DocTitle',
            parent=self.styles['Normal'],
            alignment=1,
            fontSize=18,
            leading=22,
            fontName='Helvetica-Bold',
            spaceAfter=12
        ))
        self.styles.add(ParagraphStyle(
            name='Small',
            parent=self.styles['Normal'],
            fontSize=8,
            leading=10
        ))
        self.styles.add(ParagraphStyle(
            name='RightAlign',
            parent=self.styles['Normal'],
            alignment=2
        ))

    def _get_company_header(self, company_data):
        # Coerce None to safe defaults
        name = str(company_data.get("name") or "YOUR COMPANY NAME")
        addr = str(company_data.get("address") or "123, Tirupur Textile Hub, Tamil Nadu")
        gst  = str(company_data.get("gst_details") or "GSTIN: 33AAAAA0000A1Z5")

        header = [
            Paragraph(name.upper(), self.styles['DocTitle']),
            Paragraph(addr, self.styles['Normal']),
            Paragraph(gst, self.styles['Normal']),
            Spacer(1, 0.2 * inch),
            HRFlowable(width="100%", thickness=1, color=colors.black, spaceBefore=5, spaceAfter=5)
        ]
        return header

    def generate_packing_slip(self, slip_header, items, company_data={}):
        filename = f"Packing_Slip_{slip_header.get('slip_no', 'TEMP')}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        doc = SimpleDocTemplate(filepath, pagesize=A4)
        elements = []

        # 1. Header
        elements.extend(self._get_company_header(company_data))
        elements.append(Paragraph("PACKING SLIP", self.styles['CenterBold']))
        elements.append(Spacer(1, 0.1 * inch))

        # 2. Info Grid
        info_data = [
            [f"Slip No: {slip_header.get('slip_no')}", f"Date: {slip_header.get('slip_date')}"],
            [f"Party: {slip_header.get('party_name')}", f"Order No: {slip_header.get('order_no', '-')}"],
            [f"Party Order No: {slip_header.get('party_order_no', '-')}", f"Destination: {slip_header.get('destination', '-')}"],
            [f"Cases: {slip_header.get('no_of_cases', 0)}", ""]
        ]
        t = Table(info_data, colWidths=[3 * inch, 3 * inch])
        t.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 0.2 * inch))

        # 3. Items Table
        data = [["Item Description", "Size", "Qty (Pcs)", "Boxes"]]
        for it in items:
            data.append([
                str(it.get("item_name") or ""),
                str(it.get("size_value") or ""),
                str(it.get("qty_pieces") or 0),
                f"{float(it.get('qty_boxes') or 0):.1f}"
            ])

        # Totals Row
        data.append(["TOTAL", "", str(slip_header.get("total_pcs") or 0), f"{float(slip_header.get('total_boxes') or 0):.1f}"])

        t = Table(data, colWidths=[2.5*inch, 1.5*inch, 1*inch, 1*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'), # Item name left aligned
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -2), 1, colors.grey),
            ('LINEBELOW', (0, -1), (-1, -1), 2, colors.black), # Total line
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        elements.append(t)

        # 4. Footer
        elements.append(Spacer(1, 0.5 * inch))
        elements.append(Paragraph("Prepared By: ____________________", self.styles['Normal']))
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph("Checked By: ____________________", self.styles['Normal']))

        doc.build(elements)
        return filepath

    def generate_tax_invoice(self, inv_header, items, company_data={}):
        filename = f"Tax_Invoice_{inv_header.get('invoice_no', 'TEMP')}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        
        # Professional margins
        doc = SimpleDocTemplate(filepath, pagesize=A4, leftMargin=0.4*inch, rightMargin=0.4*inch, topMargin=0.4*inch, bottomMargin=0.4*inch)
        elements = []
        PAGE_WIDTH = 7.47 * inch

        # --- 1. Top Title ---
        title_box = Table([[Paragraph("<b><font color='maroon'>TAX INVOICE</font></b>", self.styles['CenterBold'])]], 
                          colWidths=[1.5*inch], 
                          style=[('BOX', (0,0), (-1,-1), 1, colors.black), ('ALIGN', (0,0), (-1,-1), 'CENTER')])
        
        top_header_data = [
            ["", title_box, Paragraph("<b>ORIGINAL</b>", self.styles['RightAlign'])]
        ]
        top_t = Table(top_header_data, colWidths=[PAGE_WIDTH*0.35, PAGE_WIDTH*0.3, PAGE_WIDTH*0.35])
        top_t.setStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')])
        elements.append(top_t)
        elements.append(Spacer(1, 0.1 * inch))

        # --- 2. Company Info ---
        comp_name = str(company_data.get("name") or "YOUR COMPANY NAME").upper()
        comp_addr = str(company_data.get("address") or "Address Here")
        phone = str(company_data.get("phone") or "0421 - XXXXXXX")
        mobile = str(company_data.get("mobile") or "XXXXXXXXXX")
        web = str(company_data.get("website") or "www.example.com")
        email = str(company_data.get("email") or "mail@example.com")
        comp_gst = str(company_data.get("gst_details") or "GSTIN: XXXXXXXXXX").replace("GSTIN:", "").strip()
        pan = str(company_data.get("pan_no") or "XXXXXXXXXX")
        state_code = str(company_data.get("state_code") or "33")
        
        addr_html = f"<font color='maroon'><b>{comp_addr}</b></font><br/><font color='maroon'><b>Web : {web}, Mail : {email}</b></font><br/><font color='maroon'><b>TAMILNADU. STATE CODE : &nbsp;&nbsp;&nbsp;&nbsp;{state_code}</b></font>"
        
        header_data = [
            [Paragraph(f"<b>Ph : {phone}</b>", self.styles['Normal']), Paragraph(f"<b><font size=20>{comp_name}</font></b>", self.styles['CenterBold']), Paragraph(f"<b>Mob : {mobile}</b>", self.styles['RightAlign'])],
            ["", Paragraph(addr_html, self.styles['CenterBold']), ""],
            ["", Paragraph(f"<b>GSTIN : {comp_gst}, &nbsp;&nbsp;&nbsp;&nbsp;PAN : {pan}</b>", self.styles['CenterBold']), ""]
        ]
        header_t = Table(header_data, colWidths=[PAGE_WIDTH*0.2, PAGE_WIDTH*0.6, PAGE_WIDTH*0.2])
        header_t.setStyle([
            ('SPAN', (0, 1), (2, 1)),
            ('SPAN', (0, 2), (2, 2)),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ])

        # --- 3. Party Details ---
        party_name = str(inv_header.get('party_name') or "-")
        party_addr = str(inv_header.get('party_address') or "")
        party_gst = str(inv_header.get('party_gstin') or "-")
        
        party_html = f"<b>{party_name}</b><br/><br/>{party_addr}"
        
        inv_no = str(inv_header.get('invoice_no', '-'))
        inv_date = str(inv_header.get('invoice_date', '-'))
        
        party_data = [
            [Paragraph("To M/s.", self.styles['Normal']), Paragraph(party_html, self.styles['Normal']), Paragraph(f"<b>Invoice No &nbsp;&nbsp;&nbsp;: &nbsp;&nbsp;{inv_no}</b><br/><br/><b>Date &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;: &nbsp;&nbsp;{inv_date}</b>", self.styles['Normal'])],
            ["", "", ""],
            [Paragraph("<b>GSTIN</b>", self.styles['Normal']), Paragraph(f"<b>{party_gst}</b>", self.styles['Normal']), ""]
        ]
        party_t = Table(party_data, colWidths=[0.8*inch, PAGE_WIDTH * 0.5 - 0.8*inch, PAGE_WIDTH * 0.5])
        party_t.setStyle([
            ('SPAN', (2, 0), (2, 2)),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LINEBEFORE', (2, 0), (2, -1), 1, colors.black),
            ('LINEABOVE', (0, 0), (-1, 0), 1, colors.black),
        ])

        # --- 4. Delivery Info ---
        dest = str(inv_header.get('destination', '-'))
        carrier = str(inv_header.get('transporter', 'DIRECT PARTY'))
        
        deliv_data = [
            [Paragraph(f"GOODS TO &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;: &nbsp;&nbsp;<b>{dest}</b>", self.styles['Normal']), Paragraph(f"Booking Charges &nbsp;&nbsp;&nbsp;: &nbsp;&nbsp;To Pay", self.styles['Normal'])],
            [Paragraph(f"CARRIER &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;: &nbsp;&nbsp;<b>{carrier}</b>", self.styles['Normal']), ""]
        ]
        deliv_t = Table(deliv_data, colWidths=[PAGE_WIDTH * 0.6, PAGE_WIDTH * 0.4])
        deliv_t.setStyle([
            ('SPAN', (1, 0), (1, 1)),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LINEBEFORE', (1, 0), (1, -1), 1, colors.black),
            ('LINEABOVE', (0, 0), (-1, 0), 1, colors.black),
        ])

        # --- 5. Items Table ---
        col_widths = [0.5*inch, 1.2*inch, PAGE_WIDTH - 5.0*inch, 0.9*inch, 1.0*inch, 1.4*inch]
        item_data = [
            [Paragraph("<b>S.No</b>", self.styles['CenterBold']),
             Paragraph("<b>HSN / SAC</b>", self.styles['CenterBold']),
             Paragraph("<b>Description</b>", self.styles['CenterBold']),
             Paragraph("<b>No of Pcs</b>", self.styles['CenterBold']),
             Paragraph("<b>Rate / Pcs</b>", self.styles['CenterBold']),
             Paragraph("<b>Amount</b>", self.styles['CenterBold'])]
        ]
        
        tot_pcs = 0
        for i, it in enumerate(items, 1):
            pcs = float(it.get("qty_pieces") or 0)
            tot_pcs += pcs
            rate = float(it.get('rate') or 0)
            amt = float(it.get("amount") or 0)
            if not amt: amt = pcs * rate
            
            item_data.append([
                str(i),
                str(it.get("hsn_code") or ""),
                Paragraph(str(it.get("item_name") or ""), self.styles['Normal']),
                str(int(pcs)),
                f"{rate:,.2f}",
                f"{amt:,.2f}"
            ])
            
        for _ in range(8 - min(8, len(items))):
            item_data.append(["", "", "", "", "", ""])
            
        item_t = Table(item_data, colWidths=col_widths)
        item_t.setStyle([
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
            ('LINEBEFORE', (1, 0), (1, -1), 1, colors.black),
            ('LINEBEFORE', (2, 0), (2, -1), 1, colors.black),
            ('LINEBEFORE', (3, 0), (3, -1), 1, colors.black),
            ('LINEBEFORE', (4, 0), (4, -1), 1, colors.black),
            ('LINEBEFORE', (5, 0), (5, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (2, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -2), 6),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 80), # Pad out the empty space
            ('LINEABOVE', (0, 0), (-1, 0), 1, colors.black),
        ])

        # --- 6. Totals Row ---
        net_amt = float(inv_header.get("net_amount") or 0)
        cases = str(inv_header.get('no_of_cases', 0))
        
        tot_data = [
            [Paragraph(f"<b>No Of Bags / Ctns &nbsp;&nbsp;&nbsp;&nbsp;: &nbsp;&nbsp;{cases}</b>", self.styles['Normal']),
             Paragraph("<b>T O T A L</b>", self.styles['CenterBold']),
             Paragraph(f"<b>{int(tot_pcs)}</b>", self.styles['CenterBold']),
             Paragraph(f"<b>{net_amt:,.2f}</b>", self.styles['RightAlign'])]
        ]
        # Spans: col 0 spans col_widths[0]+[1]+[2] minus some space for "TOTAL", actually let's just make it align to the vertical lines.
        # S.No(0.5) + HSN(1.2) + Desc(W-5.0) = W-3.3. Let's split it: Bags (W-4.3), TOTAL (1.0), Pcs (0.9), Space (1.0), Amt (1.4)
        tot_t = Table(tot_data, colWidths=[col_widths[0]+col_widths[1]+col_widths[2] - 1.0*inch, 1.0*inch, col_widths[3], col_widths[4], col_widths[5]])
        tot_t.setStyle([
            ('SPAN', (1, 0), (1, 0)),
            ('LINEBEFORE', (2, 0), (2, -1), 1, colors.black),
            ('LINEBEFORE', (4, 0), (4, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LINEABOVE', (0, 0), (-1, 0), 1, colors.black),
        ])

        # --- 7. Footer ---
        words = num2words(int(net_amt), lang='en_IN').title() + " Only"
        
        # Bank Details
        bank_name = str(company_data.get("bank_name") or "HDFC BANK")
        bank_ac = str(company_data.get("bank_acc") or "50200118898514")
        bank_ifsc = str(company_data.get("bank_ifsc") or "HDFC0000269")
        bank_branch = str(company_data.get("bank_branch") or "RS PURAM, COIMBATORE")
        
        bank_html = f"A/C NAME &nbsp;&nbsp;&nbsp;: <b>{comp_name}</b><br/>BANK &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;: <b>{bank_name}</b><br/>BRANCH &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;: <b>{bank_branch}</b><br/>CC A /C NO &nbsp;&nbsp;&nbsp;: <b>{bank_ac}</b><br/>IFSC &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;: <b>{bank_ifsc}</b>"
        
        tax_pct = float(inv_header.get("tax_percent") or 5)
        igst_amt = float(inv_header.get("igst_amount") or 0)
        
        footer_data = [
            [Paragraph("<u><b>Rupees In Words (In INR)</b></u><br/><br/>" + words, self.styles['Normal']), Paragraph(f"<b>IGST @ &nbsp;&nbsp;{tax_pct}%</b>", self.styles['CenterBold']), Paragraph(f"<b>{igst_amt:,.2f}</b>", self.styles['RightAlign'])],
            ["", Paragraph("<b>Nett Amount</b>", self.styles['CenterBold']), Paragraph(f"<b>{net_amt:,.2f}</b>", self.styles['RightAlign'])],
            [Paragraph(bank_html, self.styles['Normal']), Paragraph(f"<b>For {comp_name}</b><br/><br/><br/><br/><br/>AUTHORISED SIGNATORY", self.styles['CenterBold']), ""]
        ]
        footer_t = Table(footer_data, colWidths=[PAGE_WIDTH - 2.4*inch, 1.0*inch, 1.4*inch])
        footer_t.setStyle([
            ('SPAN', (0, 0), (0, 1)),
            ('SPAN', (1, 2), (2, 2)),
            ('LINEBEFORE', (1, 0), (1, 2), 1, colors.black),
            ('LINEBEFORE', (2, 0), (2, 1), 1, colors.black),
            ('LINEABOVE', (0, 0), (-1, 0), 1, colors.black),
            ('LINEABOVE', (1, 1), (2, 1), 1, colors.black),
            ('LINEABOVE', (0, 2), (-1, 2), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (1, 2), (2, 2), 20),
        ])

        # 8. Master Table
        master_data = [
            [header_t],
            [party_t],
            [deliv_t],
            [item_t],
            [tot_t],
            [footer_t],
            [Paragraph("This is a computer generated Invoice. Subject To Tirupur Jurisdiction.", self.styles['Small'])]
        ]
        master_t = Table(master_data, colWidths=[PAGE_WIDTH])
        master_t.setStyle([
            ('BOX', (0, 0), (-1, -2), 1, colors.black), # Box around everything except the last line
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('ALIGN', (0, -1), (0, -1), 'CENTER'),
            ('TOPPADDING', (0, -1), (0, -1), 4),
        ])
        
        elements.append(master_t)
        doc.build(elements)
        return filepath

    def generate_voucher(self, v_header, company_data={}):
        filename = f"Cheque_{v_header.get('voucher_no', 'TEMP')}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        doc = SimpleDocTemplate(filepath, pagesize=A4)
        elements = []

        elements.extend(self._get_company_header(company_data))
        v_type = v_header.get('type', 'RECEIPT').upper()
        elements.append(Paragraph(f"{v_type} CHEQUE", self.styles['DocTitle']))
        elements.append(Spacer(1, 0.2 * inch))

        direction = v_header.get("direction_label", "Paid To / Received From")

        data = [
            ["Cheque No:", str(v_header.get("voucher_no") or "-"), "Date:", str(v_header.get("voucher_date") or "-")],
            [f"{direction}:", str(v_header.get("party_name") or "-"), "Mode:", str(v_header.get("mode") or "Cash")],
            ["Amount:", format_inr(float(v_header.get("amount") or 0)), "", ""]
        ]
        t = Table(data, colWidths=[1.5*inch, 2.5*inch, 1*inch, 1.5*inch])
        t.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 11),
            ('BOTTOMPADDING', (0,0), (-1,-1), 12),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 0.3 * inch))

        elements.append(Paragraph(f"<b>Narration:</b> {v_header.get('narration', '-')}", self.styles['Normal']))
        elements.append(Spacer(1, 0.5 * inch))

        words = num2words(int(v_header.get("amount", 0)), lang='en_IN').capitalize() + " Rupees Only"
        elements.append(Paragraph(f"<b>Amount in Words:</b> {words}", self.styles['Normal']))
        elements.append(Spacer(1, 0.8 * inch))

        # Footer Signatures
        sig_data = [
            [Paragraph("____________________<br/>Receiver's Signature", self.styles['Normal']),
             Paragraph("____________________<br/>Authorised Signatory", self.styles['RightAlign'])]
        ]
        sig_table = Table(sig_data, colWidths=[3.5*inch, 3.5*inch])
        elements.append(sig_table)

        doc.build(elements)
        return filepath

    def generate_order(self, order_header, items, company_data={}):
        filename = f"Order_{order_header.get('order_no', 'TEMP')}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        
        # Professional compact margins (forces single-page output)
        doc = SimpleDocTemplate(filepath, pagesize=A4, leftMargin=0.4*inch, rightMargin=0.4*inch, topMargin=0.4*inch, bottomMargin=0.4*inch)
        elements = []
        PAGE_WIDTH = 7.47 * inch

        # 1. Header block
        comp_name = str(company_data.get("name") or "YOUR COMPANY NAME").upper()
        comp_addr = str(company_data.get("address") or "")
        comp_gst_raw = str(company_data.get("gst_details") or "")
        comp_gst = comp_gst_raw.replace("GSTIN:", "").replace("GSTIN :", "").strip()
        comp_mob = str(company_data.get("mobile") or company_data.get("phone") or company_data.get("phone_no") or "").strip()
        mob_text = f"<b>Mob : {comp_mob}</b>" if comp_mob else ""
        
        title_box = Table([[Paragraph("<b>SALES ORDER</b>", self.styles['CenterBold'])]], 
                          colWidths=[2.0*inch], 
                          style=[('BOX', (0,0), (-1,-1), 1, colors.black), ('ALIGN', (0,0), (-1,-1), 'CENTER')])
        
        header_data = [
            [title_box, ""],
            [Paragraph(f"<b><font size=16>{comp_name}</font></b>", self.styles['CenterBold']), ""],
            [Paragraph(f"<font size=10>{comp_addr}</font>", self.styles['CenterBold']), ""],
            [Paragraph(f"<b>GSTIN : {comp_gst}</b>", self.styles['Normal']), Paragraph(mob_text, self.styles['RightAlign'])]
        ]
        
        header_t = Table(header_data, colWidths=[PAGE_WIDTH/2.0, PAGE_WIDTH/2.0])
        header_t.setStyle([
            ('SPAN', (0, 0), (1, 0)),
            ('SPAN', (0, 1), (1, 1)),
            ('SPAN', (0, 2), (1, 2)),
            ('ALIGN', (0, 0), (1, 2), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LINEABOVE', (0, 3), (1, 3), 1, colors.black),
            ('TOPPADDING', (0, 3), (1, 3), 4),
            ('BOTTOMPADDING', (0, 3), (1, 3), 4),
        ])

        # 2. Party Details & Salutation
        party_name = str(order_header.get('party_name') or "-")
        party_addr = str(order_header.get('party_address') or "")
        delivery_addr = str(order_header.get('delivery_address') or "")
        party_gst = str(order_header.get('party_gstin') or "").replace("GSTIN:", "").replace("GSTIN :", "").strip()
        party_mob = str(order_header.get('party_mob') or "")

        party_html = f"<b>M/S. &nbsp;&nbsp;&nbsp;&nbsp;{party_name}</b>"
        if party_addr:
            party_html += f"<br/>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>Address:</b> {party_addr}"
        if party_gst:
            party_html += f"<br/>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>GSTIN:</b> {party_gst}"
        if party_mob:
            party_html += f"<br/>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>Mob:</b> {party_mob}"
        
        order_no = str(order_header.get('order_no', '-'))
        order_date = str(order_header.get('order_date', '-'))
        destination = str(order_header.get('destination', '-'))
        
        party_data = [
            ["To", ""],
            [Paragraph(party_html, self.styles['Normal']), Paragraph(f"<b>ORDER NO &nbsp;&nbsp;&nbsp;: &nbsp;&nbsp;{order_no}</b>", self.styles['Normal'])],
            ["", Paragraph(f"<b>Date &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;: &nbsp;&nbsp;{order_date}</b>", self.styles['Normal'])],
            ["", Paragraph(f"<b>DESTINATION &nbsp;: &nbsp;&nbsp;{destination}</b>", self.styles['Normal'])],
            [Paragraph("<br/>Dear Sir,<br/>&nbsp;&nbsp;&nbsp;&nbsp;We release this sales order for material / service to be<br/>&nbsp;&nbsp;&nbsp;&nbsp;supplied by you as per details given Below<br/>", self.styles['Normal']), ""]
        ]
        party_t = Table(party_data, colWidths=[PAGE_WIDTH * 0.6, PAGE_WIDTH * 0.4])
        party_t.setStyle([
            ('SPAN', (0, 0), (1, 0)),
            ('SPAN', (0, 4), (1, 4)),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 4), (1, 4), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, 3), 3),
        ])

        # 3. Items Table
        col_widths = [0.5*inch, 2.97*inch, 0.8*inch, 0.6*inch, 0.7*inch, 0.9*inch, 1.0*inch]
        item_data = [
            [Paragraph("<font size=9><b>SL.No</b></font>", self.styles['CenterBold']),
             Paragraph("<font size=9><b>Description</b></font>", self.styles['CenterBold']),
             Paragraph("<font size=9><b>Size</b></font>", self.styles['CenterBold']),
             Paragraph("<font size=9><b>Qty</b></font>", self.styles['CenterBold']),
             Paragraph("<font size=9><b>Rate</b></font>", self.styles['CenterBold']),
             Paragraph("<font size=9><b>Amount</b></font>", self.styles['CenterBold']),
             Paragraph("<font size=9><b>Total Amount</b></font>", self.styles['CenterBold'])]
        ]
        
        for i, it in enumerate(items, 1):
            pcs = float(it.get("qty_pieces") or 0)
            rate = float(it.get('rate') or 0)
            row_gross = float(it.get("gross_amount") or 0)
            if not row_gross: row_gross = pcs * rate
            
            tax_p = float(it.get("tax_percent") or 0)
            tax_amt = row_gross * (tax_p / 100)
            total_row_amt = row_gross + tax_amt
            
            item_data.append([
                str(i),
                Paragraph(str(it.get("item_name") or ""), self.styles['Normal']),
                str(it.get("size_value") or ""),
                str(int(pcs)),
                f"{rate:,.2f}",
                f"{row_gross:,.2f}",
                f"{total_row_amt:,.2f}"
            ])
            
        for _ in range(3 - min(3, len(items))):
            item_data.append(["", "", "", "", "", "", ""])
            
        item_t = Table(item_data, colWidths=col_widths)
        item_t.setStyle([
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
            ('LINEBEFORE', (1, 0), (1, -1), 1, colors.black),
            ('LINEBEFORE', (2, 0), (2, -1), 1, colors.black),
            ('LINEBEFORE', (3, 0), (3, -1), 1, colors.black),
            ('LINEBEFORE', (4, 0), (4, -1), 1, colors.black),
            ('LINEBEFORE', (5, 0), (5, -1), 1, colors.black),
            ('LINEBEFORE', (6, 0), (6, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -2), 4),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 15),
        ])

        # 3.5 & 4. Footer1: Words and Total Breakdown
        breakdown_data = []
        gross = float(order_header.get("gross_amount") or sum([float(it.get("gross_amount") or (float(it.get("qty_pieces") or 0) * float(it.get('rate') or 0))) for it in items]))
        
        breakdown_data.append([Paragraph("<b>Gross Amount:</b>", self.styles['RightAlign']), f"{gross:,.2f}"])
        
        disc_amt = float(order_header.get("discount_amount") or 0)
        disc_p = float(order_header.get("discount_percent") or 0)
        if disc_amt > 0 or disc_p > 0:
            breakdown_data.append([Paragraph(f"<b>Discount ({disc_p:g}%):</b>", self.styles['RightAlign']), f"(-) {disc_amt:,.2f}"])
            
        taxable = float(order_header.get("total_amount") or order_header.get("taxable_amount") or (gross - disc_amt))
        if disc_amt > 0:
            breakdown_data.append([Paragraph("<b>Taxable Value:</b>", self.styles['RightAlign']), f"{taxable:,.2f}"])
            
        tax_type = str(order_header.get("tax_type") or "GST").upper()
        tax_per = float(order_header.get("tax_per") or 0)
        cgst = float(order_header.get("cgst_amount") or 0)
        sgst = float(order_header.get("sgst_amount") or 0)
        igst = float(order_header.get("igst_amount") or 0)
        gst_tot = float(order_header.get("gst_amount") or 0)
        
        if tax_per > 0 and taxable > 0:
            val = round(taxable * (tax_per / 100), 2)
        else:
            val = gst_tot if gst_tot > 0 else (cgst + sgst + igst)
            
        if tax_type == "GST":
            if val > 0 or tax_per > 0:
                label = f"<b>GST ({tax_per:g}%):</b>" if tax_per > 0 else "<b>GST:</b>"
                breakdown_data.append([Paragraph(label, self.styles['RightAlign']), f"{val:,.2f}"])
        else: # IGST
            if val > 0 or tax_per > 0:
                label = f"<b>IGST ({tax_per:g}%):</b>" if tax_per > 0 else "<b>IGST:</b>"
                breakdown_data.append([Paragraph(label, self.styles['RightAlign']), f"{val:,.2f}"])
                
        cess = float(order_header.get("cess_amount") or 0)
        tcs = float(order_header.get("tcs_amount") or 0)
        if cess > 0: breakdown_data.append([Paragraph("<b>CESS:</b>", self.styles['RightAlign']), f"{cess:,.2f}"])
        if tcs > 0:  breakdown_data.append([Paragraph("<b>TCS:</b>", self.styles['RightAlign']), f"{tcs:,.2f}"])
        
        roff = float(order_header.get("round_off") or 0)
        if roff != 0:
            breakdown_data.append([Paragraph("<b>Round Off:</b>", self.styles['RightAlign']), f"{roff:.2f}"])
            
        net_amt = float(order_header.get("net_amount") or 0)
        breakdown_data.append([Paragraph("<b>TOTAL:</b>", self.styles['RightAlign']), Paragraph(f"<b>{net_amt:,.2f}</b>", self.styles['RightAlign'])])
        
        breakdown_t = Table(breakdown_data, colWidths=[PAGE_WIDTH * 0.23, PAGE_WIDTH * 0.15])
        breakdown_t.setStyle([
            ('ALIGN', (0, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LINEABOVE', (0, -1), (1, -1), 1, colors.black),
        ])

        try:
            words = num2words(int(net_amt), lang='en_IN').title()
        except:
            words = ""
            
        footer1_data = [
            [Paragraph(f"<b>Rs In Words : </b><br/>{words}", self.styles['Normal']), breakdown_t]
        ]
        footer1_t = Table(footer1_data, colWidths=[PAGE_WIDTH * 0.6, PAGE_WIDTH * 0.4])
        footer1_t.setStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LINEBEFORE', (1, 0), (1, -1), 1, colors.black),
        ])

        # 5. Footer2: Delivery and Signature
        deliv = str(order_header.get('delivery_address') or order_header.get('destination') or "")
        rem = str(order_header.get('remarks') or "")
        deliv_text = f"<b>Delivery : </b>{deliv}" if deliv else (f"<b>Remarks : </b>{rem}" if rem else "<b>Delivery : </b>-")
        
        footer2_data = [
            [Paragraph(deliv_text, self.styles['Normal']), ""],
            ["", Paragraph("<b>For &nbsp;&nbsp;&nbsp;" + comp_name + "</b>", self.styles['CenterBold'])],
            ["", ""],
            ["", Paragraph("<b>Authorized signatory</b>", self.styles['CenterBold'])]
        ]
        footer2_t = Table(footer2_data, colWidths=[PAGE_WIDTH * 0.5, PAGE_WIDTH * 0.5])
        footer2_t.setStyle([
            ('SPAN', (0, 0), (1, 0)),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, 0), 4),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 6),
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),
        ])

        # Master Table
        master_data = [
            [header_t],
            [party_t],
            [item_t],
            [footer1_t],
            [footer2_t]
        ]
        
        master_t = Table(master_data, colWidths=[PAGE_WIDTH])
        master_t.setStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 1, colors.black),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ])
        
        elements.append(master_t)
        doc.build(elements)
        return filepath

    def generate_yarn_po(self, po_header, items, company_data={}):
        filename = f"YarnPO_{po_header.get('po_no', 'TEMP')}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        doc = SimpleDocTemplate(filepath, pagesize=A4, leftMargin=0.5*inch, rightMargin=0.5*inch)
        elements = []
        PAGE_WIDTH = 7.27 * inch

        # 1. Header
        elements.extend(self._get_company_header(company_data))
        elements.append(Paragraph("<b>PURCHASE ORDER (YARN)</b>", self.styles['DocTitle']))

        # 2. Party Details
        party_info = [
            [Paragraph(f"<b>Supplier:</b><br/>{po_header.get('supplier_name') or '-'}<br/>{po_header.get('supplier_address') or ''}", self.styles['Normal']),
             Paragraph(f"PO No: <b>{po_header.get('po_no') or '-'}</b><br/>Date: {po_header.get('po_date') or '-'}<br/>Delivery: {po_header.get('delivery') or '-'}", self.styles['Normal'])]
        ]
        t = Table(party_info, colWidths=[3.5 * inch, 3.5 * inch])
        t.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
        elements.append(t)
        elements.append(Spacer(1, 0.2 * inch))

        # 3. Items
        data = [["Sl", "Item", "Bags", "Qty in Kgs", "Rate", "Amount", "Tax %", "Total Amt"]]
        for i, it in enumerate(items, 1):
            rate = float(it.get('rate') or 0)
            qty = float(it.get("qty_kgs") or 0)
            amt = qty * rate
            tax_p = float(it.get("tax_percent") or 5)
            tax_amt = amt * (tax_p / 100)
            data.append([
                str(i), str(it.get('item_name') or ''), str(it.get("bags") or 0),
                f"{qty:.3f}", f"{rate:.2f}", f"{amt:.2f}", f"{tax_p}%", f"{(amt+tax_amt):.2f}"
            ])
            
        t = Table(data, colWidths=[0.3*inch, 2.0*inch, 0.7*inch, 0.8*inch, 0.7*inch, 0.9*inch, 0.6*inch, 0.9*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 0.3 * inch))
        
        # 4. Remarks
        elements.append(Paragraph(f"<b>Remarks:</b> {po_header.get('remarks') or '-'}", self.styles['Normal']))
        elements.append(Spacer(1, 0.5 * inch))
        elements.append(Paragraph("Authorised Signatory", self.styles['RightAlign']))

        doc.build(elements)
        return filepath

    def generate_knitting_program(self, prog_header, items, company_data={}):
        filename = f"Knitting_{prog_header.get('prog_no', 'TEMP')}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        doc = SimpleDocTemplate(filepath, pagesize=A4, leftMargin=0.5*inch, rightMargin=0.5*inch)
        elements = []

        elements.extend(self._get_company_header(company_data))
        elements.append(Paragraph("<b>KNITTING PROGRAM</b>", self.styles['DocTitle']))

        party_info = [
            [Paragraph(f"<b>Party:</b><br/>{prog_header.get('party_name') or '-'}", self.styles['Normal']),
             Paragraph(f"Prog No: <b>{prog_header.get('prog_no') or '-'}</b><br/>Date: {prog_header.get('prog_date') or '-'}", self.styles['Normal'])]
        ]
        t = Table(party_info, colWidths=[3.5 * inch, 3.5 * inch])
        t.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
        elements.append(t)
        elements.append(Spacer(1, 0.2 * inch))

        data = [["Sl", "Item", "Yarn Description", "GSM / LL", "GG", "Dia", "Weight", "Roll/Pcs"]]
        for i, it in enumerate(items, 1):
            data.append([
                str(i), str(it.get('item_name') or ''), str(it.get("yarn_desc") or ''),
                str(it.get('gsm') or ''), str(it.get('gg') or ''), str(it.get('dia') or ''),
                str(it.get('weight') or ''), str(it.get('rolls') or '')
            ])
            
        t = Table(data, colWidths=[0.3*inch, 1.5*inch, 1.5*inch, 0.7*inch, 0.5*inch, 0.5*inch, 1.0*inch, 0.8*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (3, 1), (-1, -1), 'CENTER'),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 0.3 * inch))
        
        elements.append(Paragraph(f"<b>Remarks:</b> {prog_header.get('remarks') or '-'}", self.styles['Normal']))
        elements.append(Spacer(1, 0.5 * inch))
        elements.append(Paragraph("Authorised Signatory", self.styles['RightAlign']))

        doc.build(elements)
        return filepath

    def generate_dyeing_program(self, prog_header, items, company_data={}):
        filename = f"Dyeing_{prog_header.get('prog_no', 'TEMP')}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        doc = SimpleDocTemplate(filepath, pagesize=A4, leftMargin=0.5*inch, rightMargin=0.5*inch)
        elements = []

        elements.extend(self._get_company_header(company_data))
        elements.append(Paragraph("<b>DYEING PROGRAM</b>", self.styles['DocTitle']))

        party_info = [
            [Paragraph(f"<b>Party:</b><br/>{prog_header.get('party_name') or '-'}", self.styles['Normal']),
             Paragraph(f"Prog No: <b>{prog_header.get('prog_no') or '-'}</b><br/>Date: {prog_header.get('prog_date') or '-'}", self.styles['Normal'])]
        ]
        t = Table(party_info, colWidths=[3.5 * inch, 3.5 * inch])
        t.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
        elements.append(t)
        elements.append(Spacer(1, 0.2 * inch))

        data = [["Sl", "Item", "Colour", "Process", "Weight (Kgs)", "Batch"]]
        for i, it in enumerate(items, 1):
            data.append([
                str(i), str(it.get('item_name') or ''), str(it.get("colour") or ''),
                str(it.get('process') or ''), str(it.get('weight') or ''), str(it.get('batch') or '')
            ])
            
        t = Table(data, colWidths=[0.5*inch, 2.0*inch, 1.5*inch, 1.5*inch, 1.0*inch, 0.77*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (4, 1), (-1, -1), 'CENTER'),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 0.3 * inch))
        
        elements.append(Paragraph(f"<b>Remarks:</b> {prog_header.get('remarks') or '-'}", self.styles['Normal']))
        elements.append(Spacer(1, 0.5 * inch))
        elements.append(Paragraph("Authorised Signatory", self.styles['RightAlign']))

        doc.build(elements)
        return filepath

    def generate_cheque(self, payee_name, amount, date_str, ref_no="", company_data={}, bank_data={}):
        """
        Generate a professional bank cheque PDF (8 x 3.5 inches).
        Includes Company details, Bank details, A/C Payee stamp, Date grid, Amount box, and MICR line.
        """
        cheque_width = 8 * inch
        cheque_height = 3.5 * inch
        safe_name = str(payee_name)[:15].replace(' ', '_').replace('/', '-')
        filename = f"Cheque_{safe_name}_{int(float(amount))}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        
        c = canvas.Canvas(filepath, pagesize=(cheque_width, cheque_height))
        
        # 1. Outer Border & Frame
        c.setLineWidth(1)
        c.setStrokeColor(colors.HexColor("#1E3A8A")) # Deep Navy Blue
        c.rect(0.12 * inch, 0.12 * inch, cheque_width - 0.24 * inch, cheque_height - 0.24 * inch)
        c.setLineWidth(0.5)
        c.rect(0.15 * inch, 0.15 * inch, cheque_width - 0.3 * inch, cheque_height - 0.3 * inch)

        # 2. Company & Bank Header Box (Top Banner)
        comp_name = str(company_data.get("name") or "YOUR COMPANY NAME").upper()
        comp_addr = str(company_data.get("address") or "")
        comp_city = str(company_data.get("city") or "")
        comp_gst = str(company_data.get("gst_details") or "").replace("GSTIN:", "").strip()
        comp_mob = str(company_data.get("mobile") or company_data.get("phone") or "").strip()

        bank_name = str(bank_data.get("name") or bank_data.get("bank_name") or "STATE BANK OF INDIA").upper()
        bank_branch = str(bank_data.get("branch") or "MAIN BRANCH")
        bank_ifsc = str(bank_data.get("ifsc_code") or bank_data.get("ifsc") or "")
        acc_no = str(bank_data.get("account_no") or "")

        # Top Header Background Tint
        c.setFillColor(colors.HexColor("#F8FAFC"))
        c.rect(0.15 * inch, cheque_height - 0.85 * inch, cheque_width - 0.3 * inch, 0.7 * inch, fill=1, stroke=0)
        c.setStrokeColor(colors.HexColor("#CBD5E1"))
        c.line(0.15 * inch, cheque_height - 0.85 * inch, cheque_width - 0.15 * inch, cheque_height - 0.85 * inch)

        # 3. A/C PAYEE ONLY Crossing Stamp (Top Left)
        c.setStrokeColor(colors.HexColor("#000000"))
        c.setLineWidth(1)
        c.line(0.25 * inch, cheque_height - 0.22 * inch, 1.35 * inch, cheque_height - 0.22 * inch)
        c.line(0.25 * inch, cheque_height - 0.38 * inch, 1.35 * inch, cheque_height - 0.38 * inch)
        c.setFont("Helvetica-Bold", 7)
        c.setFillColor(colors.black)
        c.drawCentredString(0.80 * inch, cheque_height - 0.32 * inch, "A/C PAYEE ONLY")

        # Draw Company Name & Subtext (Left Header - Indented to clear A/C Payee stamp)
        c.setFillColor(colors.HexColor("#1E1B4B"))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(1.45 * inch, cheque_height - 0.35 * inch, comp_name[:32])
        
        c.setFont("Helvetica", 7)
        c.setFillColor(colors.HexColor("#475569"))
        sub_parts = [p for p in [comp_addr, comp_city] if p]
        sub_info = ", ".join(sub_parts)
        if comp_gst: sub_info += f" | GST: {comp_gst}"
        c.drawString(1.45 * inch, cheque_height - 0.48 * inch, sub_info[:36])

        # Draw Bank Info (Center-Right Header)
        c.setFont("Helvetica-Bold", 8.5)
        c.setFillColor(colors.HexColor("#1E3A8A"))
        c.drawRightString(cheque_width - 2.15 * inch, cheque_height - 0.35 * inch, bank_name[:25])
        c.setFont("Helvetica", 7)
        c.setFillColor(colors.HexColor("#475569"))
        b_sub = bank_branch
        if bank_ifsc: b_sub += f" ({bank_ifsc})"
        c.drawRightString(cheque_width - 2.15 * inch, cheque_height - 0.48 * inch, b_sub[:30])
        if acc_no:
            c.setFont("Helvetica-Bold", 7)
            c.drawRightString(cheque_width - 2.15 * inch, cheque_height - 0.60 * inch, f"A/C: {acc_no}")

        # 4. DATE Boxes (Top Right Grid)
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(colors.HexColor("#1E3A8A"))
        c.drawString(cheque_width - 2.05 * inch, cheque_height - 0.35 * inch, "DATE:")
        
        # Format Date string into 8 digits
        date_digits = [" "] * 8
        try:
            d_parts = str(date_str).replace("/", "-").split("-")
            if len(d_parts) == 3:
                if len(d_parts[0]) == 4: # YYYY-MM-DD
                    yy, mm, dd = d_parts[0], d_parts[1], d_parts[2]
                else: # DD-MM-YYYY
                    dd, mm, yy = d_parts[0], d_parts[1], d_parts[2]
                d_str = f"{dd.zfill(2)}{mm.zfill(2)}{yy.zfill(4)}"
                date_digits = [ch for ch in d_str[:8]]
        except:
            pass

        box_start_x = cheque_width - 1.7 * inch
        box_y = cheque_height - 0.50 * inch
        box_w = 0.16 * inch
        box_h = 0.20 * inch
        
        c.setLineWidth(0.7)
        c.setStrokeColor(colors.HexColor("#1E3A8A"))
        c.setFont("Helvetica-Bold", 10)
        
        for i, digit in enumerate(date_digits):
            bx = box_start_x + (i * 0.18 * inch)
            c.rect(bx, box_y, box_w, box_h)
            c.setFillColor(colors.black)
            c.drawCentredString(bx + box_w/2.0, box_y + 0.04 * inch, digit)

        # 5. PAY Line
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.HexColor("#1E3A8A"))
        c.drawString(0.3 * inch, 2.15 * inch, "PAY")
        
        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(colors.black)
        payee_str = str(payee_name).upper()
        c.drawString(0.8 * inch, 2.15 * inch, payee_str)
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor("#64748B"))
        c.drawRightString(cheque_width - 0.3 * inch, 2.15 * inch, "OR ORDER")
        
        c.setLineWidth(0.5)
        c.setStrokeColor(colors.HexColor("#CBD5E1"))
        c.line(0.8 * inch, 2.08 * inch, cheque_width - 0.3 * inch, 2.08 * inch)

        # 6. RUPEES Line
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.HexColor("#1E3A8A"))
        c.drawString(0.3 * inch, 1.65 * inch, "RUPEES")
        
        try:
            amt_float = float(amount)
            amt_words = num2words(int(amt_float), lang='en_IN').title()
            paise = int(round((amt_float - int(amt_float)) * 100))
            if paise > 0:
                amt_words += f" and {num2words(paise, lang='en_IN').title()} Paise"
            amt_words += " Only"
        except:
            amt_words = "Zero Only"

        c.setFont("Helvetica-Bold", 10.5)
        c.setFillColor(colors.black)
        
        if len(amt_words) > 50:
            c.drawString(1.0 * inch, 1.65 * inch, amt_words[:50])
            c.line(1.0 * inch, 1.58 * inch, cheque_width - 2.2 * inch, 1.58 * inch)
            
            c.drawString(0.3 * inch, 1.30 * inch, amt_words[50:])
            c.line(0.3 * inch, 1.23 * inch, cheque_width - 2.2 * inch, 1.23 * inch)
        else:
            c.drawString(1.0 * inch, 1.65 * inch, amt_words)
            c.line(1.0 * inch, 1.58 * inch, cheque_width - 2.2 * inch, 1.58 * inch)

        # 7. AMOUNT Box (Right Side)
        amt_box_x = cheque_width - 2.1 * inch
        amt_box_y = 1.35 * inch
        amt_box_w = 1.8 * inch
        amt_box_h = 0.38 * inch

        c.setFillColor(colors.HexColor("#F1F5F9"))
        c.rect(amt_box_x, amt_box_y, amt_box_w, amt_box_h, fill=1, stroke=0)
        c.setLineWidth(1)
        c.setStrokeColor(colors.HexColor("#1E3A8A"))
        c.rect(amt_box_x, amt_box_y, amt_box_w, amt_box_h, fill=0, stroke=1)
        
        c.setFont("Helvetica-Bold", 13)
        c.setFillColor(colors.HexColor("#0F172A"))
        c.drawString(amt_box_x + 0.1 * inch, amt_box_y + 0.12 * inch, "Rs.")
        c.drawRightString(amt_box_x + amt_box_w - 0.1 * inch, amt_box_y + 0.12 * inch, f"{float(amount):,.2f} /-")

        # 8. Signature Block (Bottom Right)
        c.setFont("Helvetica-Bold", 8.5)
        c.setFillColor(colors.HexColor("#1E3A8A"))
        c.drawRightString(cheque_width - 0.3 * inch, 0.95 * inch, f"For {comp_name}")

        c.setFont("Helvetica", 7.5)
        c.setFillColor(colors.HexColor("#64748B"))
        c.drawRightString(cheque_width - 0.3 * inch, 0.40 * inch, "Authorized Signatory")

        # 9. Reference / Voucher No (Bottom Left)
        if ref_no:
            c.setFont("Helvetica", 8)
            c.setFillColor(colors.HexColor("#475569"))
            c.drawString(0.3 * inch, 0.45 * inch, f"Chq/Ref No: {ref_no}")

        # 10. MICR Band at Bottom Center
        c.setFillColor(colors.HexColor("#F8FAFC"))
        c.rect(0.15 * inch, 0.15 * inch, cheque_width - 0.3 * inch, 0.22 * inch, fill=1, stroke=0)
        c.setFont("Courier-Bold", 9)
        c.setFillColor(colors.HexColor("#334155"))
        micr_code = f"||' {ref_no or '123456'} ||'  600024002|:  000123||'  10"
        c.drawCentredString(cheque_width / 2.0, 0.20 * inch, micr_code)

        c.showPage()
        c.save()
        return filepath

    def generate_report_pdf(self, title, subtitle, columns, rows, company_data={}):
        filename = f"Report_{title.replace(' ', '_')}_{int(time.time())}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        
        doc = SimpleDocTemplate(filepath, pagesize=A4, leftMargin=0.5*inch, rightMargin=0.5*inch)
        elements = []
        PAGE_WIDTH = 7.27 * inch

        # 1. Header
        elements.extend(self._get_company_header(company_data))
        elements.append(Paragraph(f"<b>{title.upper()}</b>", self.styles['DocTitle']))
        if subtitle:
            elements.append(Paragraph(subtitle, self.styles['CenterBold']))
            elements.append(Spacer(1, 0.2 * inch))

        # 2. Table Data
        # Extract headers
        headers = [col["label"] for col in columns]
        
        # Calculate col widths
        col_width = PAGE_WIDTH / max(len(headers), 1)
        col_widths = [col_width] * len(headers)
        
        data = [headers]
        for row in rows:
            row_data = [str(row.get(col["key"], "")) for col in columns]
            data.append(row_data)

        t = Table(data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(t)

        doc.build(elements)
        return filepath

# Singleton instance
pdf_engine = PDFGenerator()
