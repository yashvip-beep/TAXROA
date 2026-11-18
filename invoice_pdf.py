"""Printable invoice PDF. Uses 'Rs.' because the standard PDF font has no rupee sign."""
from html import escape
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def build_invoice_pdf(seller: dict, buyer: dict, inv: dict, result: dict, disclaimer: str) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=14 * mm, rightMargin=14 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
        title=f"Invoice {inv['number']}",
    )
    ss = getSampleStyleSheet()
    small = ParagraphStyle("small", parent=ss["Normal"], fontSize=8.5, leading=11)
    cell = ParagraphStyle("cell", parent=ss["Normal"], fontSize=8, leading=10)

    story = [
        Paragraph("TAX INVOICE (DRAFT)", ss["Title"]),
        Paragraph("Draft prepared with GST TAXORA. Check invoice content requirements under "
                  "GST law before issuing.", small),
        Spacer(1, 6),
    ]

    seller_block = (f"<b>Seller</b><br/><b>{escape(seller['name'])}</b><br/>"
                    f"{escape(seller['address'])}<br/>GSTIN: {escape(seller['gstin'] or 'Not provided')}")
    buyer_block = (f"<b>Buyer</b><br/><b>{escape(buyer['name'])}</b><br/>"
                   f"{escape(buyer['address'])}<br/>GSTIN: {escape(buyer['gstin'] or 'Not provided')}")
    parties = Table([[Paragraph(seller_block, small), Paragraph(buyer_block, small)]],
                    colWidths=[91 * mm, 91 * mm])
    parties.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [parties, Spacer(1, 8)]

    supply_text = "Intra-State (CGST + SGST/UTGST)" if inv["supply"] == "intra" else "Inter-State (IGST)"
    story.append(Paragraph(
        f"<b>Invoice no.:</b> {escape(inv['number'])} &nbsp;&nbsp; <b>Date:</b> "
        f"{escape(inv['date'])} &nbsp;&nbsp; <b>Supply:</b> {supply_text}", small))
    story.append(Spacer(1, 8))

    header = ["Item", "HSN/SAC", "Qty", "Unit price", "Taxable", "GST %", "Tax", "Total"]
    rows = [header]
    for ln in result["lines"]:
        rows.append([
            Paragraph(escape(ln["description"]), cell),
            escape(ln["hsn"]),
            ln["qty"],
            f"Rs. {ln['unit_price']}",
            f"Rs. {ln['taxable']}",
            f"{ln['gst_pct']}%",
            f"Rs. {ln['tax']}",
            f"Rs. {ln['total']}",
        ])
    items = Table(rows, colWidths=[52 * mm, 20 * mm, 12 * mm, 22 * mm, 24 * mm, 14 * mm, 18 * mm, 20 * mm],
                  repeatRows=1)
    items.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#AF002D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
    ]))
    story += [items, Spacer(1, 10)]

    summary_rows = [["Taxable value", f"Rs. {result['taxable']}"]]
    if inv["supply"] == "intra":
        summary_rows += [["CGST", f"Rs. {result['cgst']}"], ["SGST/UTGST", f"Rs. {result['sgst']}"]]
    else:
        summary_rows.append(["IGST", f"Rs. {result['igst']}"])
    summary_rows += [["Total tax", f"Rs. {result['total_tax']}"],
                     ["Grand total", f"Rs. {result['grand_total']}"]]
    summary = Table(summary_rows, colWidths=[50 * mm, 40 * mm], hAlign="RIGHT")
    summary.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]))
    story += [summary, Spacer(1, 12)]

    story.append(Paragraph("Amounts are rounded to 2 decimal places (half-up). In intra-State supply, "
                           "CGST is half the tax and SGST takes any paise remainder.", small))
    story.append(Spacer(1, 6))
    story.append(Paragraph(escape(disclaimer), small))

    doc.build(story)
    return buf.getvalue()
