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

def print_pdf(pdf_path):
    """
    Send a PDF directly to the system default printer, then delete
    the temp file after a short delay to allow the print spooler to read it.
    """
    try:
        if os.name == 'nt':
            os.startfile(pdf_path, "print")
        else:
            import subprocess
            subprocess.run(["lp", pdf_path], check=True)
    except Exception:
        # Fallback: open normally so user can print via viewer
        if hasattr(os, "startfile"):
            os.startfile(pdf_path)

    # Clean up the temp file after a delay (give print spooler time)
    def _cleanup():
        time.sleep(15)
        try:
            os.remove(pdf_path)
        except:
            pass
    threading.Thread(target=_cleanup, daemon=True).start()

class PDFGenerator:
    def __init__(self):
        self.output_dir = os.path.join(os.getcwd(), "pdfs")
        os.makedirs(self.output_dir, exist_ok=True)
        self._cleanup_old_pdfs()
        
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _cleanup_old_pdfs(self):
        """Silently deletes any PDF file in the pdfs folder older than 24 hours."""
        try:
            current_time = time.time()
            for filename in os.listdir(self.output_dir):
                if filename.endswith(".pdf"):
                    filepath = os.path.join(self.output_dir, filename)
                    # If file is older than 24 hours (86400 seconds)
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
        
        # Professional margins
        doc = SimpleDocTemplate(filepath, pagesize=A4, leftMargin=0.5*inch, rightMargin=0.5*inch, topMargin=0.5*inch, bottomMargin=0.5*inch)
        elements = []
        PAGE_WIDTH = 7.27 * inch

        # 1. Header block
        comp_name = str(company_data.get("name") or "YOUR COMPANY NAME").upper()
        comp_addr = str(company_data.get("address") or "")
        comp_gst_raw = str(company_data.get("gst_details") or "")
        comp_gst = comp_gst_raw.replace("GSTIN:", "").replace("GSTIN :", "").strip()
        
        title_box = Table([[Paragraph("<b>SALES ORDER</b>", self.styles['CenterBold'])]], 
                          colWidths=[2.0*inch], 
                          style=[('BOX', (0,0), (-1,-1), 1, colors.black), ('ALIGN', (0,0), (-1,-1), 'CENTER')])
        
        header_data = [
            [title_box, ""],
            [Paragraph(f"<b><font size=16>{comp_name}</font></b>", self.styles['CenterBold']), ""],
            [Paragraph(f"<font size=10>{comp_addr}</font>", self.styles['CenterBold']), ""],
            [Paragraph(f"<b>GSTIN : {comp_gst}</b>", self.styles['Normal']), Paragraph(f"<b>Mob : {company_data.get('phone', '')}</b>", self.styles['RightAlign'])]
        ]
        
        header_t = Table(header_data, colWidths=[PAGE_WIDTH/2.0, PAGE_WIDTH/2.0])
        header_t.setStyle([
            ('SPAN', (0, 0), (1, 0)),
            ('SPAN', (0, 1), (1, 1)),
            ('SPAN', (0, 2), (1, 2)),
            ('ALIGN', (0, 0), (1, 2), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LINEABOVE', (0, 3), (1, 3), 1, colors.black),
            ('TOPPADDING', (0, 3), (1, 3), 6),
            ('BOTTOMPADDING', (0, 3), (1, 3), 6),
        ])

        # 2. Party Details & Salutation
        party_name = str(order_header.get('party_name') or "-")
        party_addr = str(order_header.get('party_address') or "")
        party_gst = str(order_header.get('party_gstin') or "").replace("GSTIN:", "").replace("GSTIN :", "").strip()
        party_mob = str(order_header.get('party_mob') or "")

        party_html = f"<b>M/S. &nbsp;&nbsp;&nbsp;&nbsp;{party_name}</b>"
        if party_addr:
            party_html += f"<br/>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{party_addr}"
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
            ('BOTTOMPADDING', (0, 4), (1, 4), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, 3), 4),
        ])

        # 3. Items Table
        col_widths = [0.5*inch, 2.77*inch, 0.8*inch, 0.6*inch, 0.7*inch, 0.9*inch, 1.0*inch]
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
            
        for _ in range(5 - min(5, len(items))):
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
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -2), 6),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 40),
        ])

        # 3.5 & 4. Footer1: Words and Total Breakdown
        breakdown_data = []
        gross = float(order_header.get("gross_amount") or sum([float(it.get("gross_amount") or (float(it.get("qty_pieces") or 0) * float(it.get('rate') or 0))) for it in items]))
        
        breakdown_data.append([Paragraph("<b>Gross Amount:</b>", self.styles['RightAlign']), f"{gross:,.2f}"])
        
        discs = [
            ("Trade Disc", "td_amount"),
            ("Scheme Disc", "spd_amount"),
            ("Festival Disc", "festival_amount"),
            ("Special Disc", "scd_amount"),
            ("Cash Disc", "cd_amount")
        ]
        has_disc = False
        for label, key in discs:
            val = float(order_header.get(key) or 0)
            if val > 0:
                has_disc = True
                breakdown_data.append([Paragraph(f"<b>{label}:</b>", self.styles['RightAlign']), f"(-) {val:,.2f}"])
        
        taxable = float(order_header.get("total_amount") or 0)
        cgst = float(order_header.get("cgst_amount") or 0)
        sgst = float(order_header.get("sgst_amount") or 0)
        igst = float(order_header.get("igst_amount") or 0)
        cess = float(order_header.get("cess_amount") or 0)
        tcs = float(order_header.get("tcs_amount") or 0)
        
        if has_disc or cgst > 0 or sgst > 0 or igst > 0 or cess > 0 or tcs > 0:
            breakdown_data.append([Paragraph("<b>Taxable Value:</b>", self.styles['RightAlign']), f"{taxable:,.2f}"])
            
        if cgst > 0: breakdown_data.append([Paragraph("<b>CGST:</b>", self.styles['RightAlign']), f"{cgst:,.2f}"])
        if sgst > 0: breakdown_data.append([Paragraph("<b>SGST:</b>", self.styles['RightAlign']), f"{sgst:,.2f}"])
        if igst > 0: breakdown_data.append([Paragraph("<b>IGST:</b>", self.styles['RightAlign']), f"{igst:,.2f}"])
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
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LINEBEFORE', (1, 0), (1, -1), 1, colors.black),
        ])

        # 5. Footer2: Delivery and Signature
        remarks = str(order_header.get('remarks') or "")
        footer2_data = [
            [Paragraph(f"<b>Delivery : </b>{remarks}", self.styles['Normal']), ""],
            ["", ""],
            ["", Paragraph("<b>For &nbsp;&nbsp;&nbsp;" + comp_name + "</b>", self.styles['CenterBold'])],
            ["", ""],
            ["", ""],
            ["", Paragraph("<b>Authorized signatory</b>", self.styles['CenterBold'])]
        ]
        footer2_t = Table(footer2_data, colWidths=[PAGE_WIDTH * 0.5, PAGE_WIDTH * 0.5])
        footer2_t.setStyle([
            ('SPAN', (0, 0), (1, 0)),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 30),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 10),
            ('ALIGN', (1, 2), (1, -1), 'CENTER'),
        ])

        # 6. Terms and Conditions
        terms_text = "<u>Terms & Conditions:</u><br/><br/>1. Send the duplicate Sales Order along with bill and materials.<br/>2. Our Sales Order No and Date should appear in all your communications<br/>3. Materials supplied be as per our approved samples<br/>4. Defective materials & excess quantities will NOT be accepted.<br/>5. We reserve our right to accept / reject delayed deliveries."
        footer3_data = [
            [Paragraph(terms_text, self.styles['Normal'])]
        ]
        footer3_t = Table(footer3_data, colWidths=[PAGE_WIDTH])
        footer3_t.setStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ])

        # Master Table
        master_data = [
            [header_t],
            [party_t],
            [item_t],
        ]
            
        master_data.extend([
            [footer1_t],
            [footer2_t],
            [footer3_t]
        ])
        
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

    def generate_cheque(self, payee_name, amount, date_str, ref_no=""):
        """
        Generate a cheque PDF on standard Indian bank cheque size (8 x 3.5 inches).
        Positions are calibrated for common Indian bank cheque formats.
        """
        cheque_width = 8 * inch
        cheque_height = 3.5 * inch
        safe_name = str(payee_name)[:15].replace(' ', '_').replace('/', '-')
        filename = f"Cheque_{safe_name}_{int(float(amount))}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        
        c = canvas.Canvas(filepath, pagesize=(cheque_width, cheque_height))
        
        # === A/C PAYEE crossing lines (top-left) ===
        c.setFont("Helvetica-Bold", 10)
        c.line(0.3 * inch, 3.15 * inch, 1.9 * inch, 3.15 * inch)
        c.drawString(0.5 * inch, 3.2 * inch, "A/C PAYEE ONLY")
        c.line(0.3 * inch, 3.35 * inch, 1.9 * inch, 3.35 * inch)
        
        # === Date (top-right) — spaced digits for DD MM YYYY boxes ===
        c.setFont("Helvetica-Bold", 12)
        try:
            parts = str(date_str).split('-')
            if len(parts) == 3:
                # ISO format YYYY-MM-DD
                yy, mm, dd = parts[0], parts[1], parts[2]
                date_display = f"{dd[0]}  {dd[1]}  {mm[0]}  {mm[1]}  {yy[0]}  {yy[1]}  {yy[2]}  {yy[3]}"
            else:
                date_display = str(date_str)
        except:
            date_display = str(date_str)
        c.drawString(5.5 * inch, 2.85 * inch, date_display)
        
        # === Pay / Payee Name (middle-left) ===
        c.setFont("Helvetica", 9)
        c.drawString(0.4 * inch, 2.3 * inch, "Pay")
        c.setFont("Helvetica-Bold", 13)
        c.drawString(0.8 * inch, 2.3 * inch, str(payee_name).upper())
        
        # === Amount in Words (below payee, two lines if needed) ===
        c.setFont("Helvetica", 9)
        c.drawString(0.4 * inch, 1.85 * inch, "Rupees")
        try:
            amt_float = float(amount)
            amt_words = num2words(int(amt_float), lang='en_IN').title()
            paise = int(round((amt_float - int(amt_float)) * 100))
            if paise > 0:
                amt_words += f" and {num2words(paise, lang='en_IN').title()} Paise"
            amt_words += " Only"
        except:
            amt_words = "Zero Only"
        
        c.setFont("Helvetica-Bold", 11)
        # Split long amount text across two lines if needed
        if len(amt_words) > 55:
            c.drawString(1.0 * inch, 1.85 * inch, amt_words[:55])
            c.drawString(0.4 * inch, 1.55 * inch, amt_words[55:])
        else:
            c.drawString(1.0 * inch, 1.85 * inch, amt_words)
        
        # === Amount in Figures (right side box) ===
        c.setFont("Helvetica-Bold", 14)
        c.drawString(6.0 * inch, 1.85 * inch, f"Rs. {float(amount):,.2f} /-")
        
        # === Reference/Voucher No (bottom-left, small) ===
        if ref_no:
            c.setFont("Helvetica", 8)
            c.drawString(0.4 * inch, 0.6 * inch, f"Ref: {ref_no}")
        
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
