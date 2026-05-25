"""
IAM Guardian - PDF Report Generator
Generates downloadable PDF reports from scan results
"""

import json
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

REPORTS_DIR = "/tmp/iam-guardian-reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

RED_COLOR   = colors.HexColor("#E63946")
AMBER_COLOR = colors.HexColor("#F4A261")
GREEN_COLOR = colors.HexColor("#2EC4B6")
NAVY_COLOR  = colors.HexColor("#0A1628")
GRAY_COLOR  = colors.HexColor("#8BA0B4")


def get_risk_color(classification: str):
    return {"RED": RED_COLOR, "AMBER": AMBER_COLOR, "GREEN": GREEN_COLOR}.get(classification, GRAY_COLOR)


def generate_pdf_report(scan_data: dict, scan_id: str) -> str:
    pdf_path = os.path.join(REPORTS_DIR, f"iam-guardian-{scan_id[:8]}.pdf")
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
    )

    styles = getSampleStyleSheet()
    title_style    = ParagraphStyle("Title", parent=styles["Title"], textColor=NAVY_COLOR, fontSize=22, spaceAfter=6)
    heading_style  = ParagraphStyle("Heading", parent=styles["Heading2"], textColor=NAVY_COLOR, fontSize=14, spaceBefore=12, spaceAfter=4)
    body_style     = ParagraphStyle("Body", parent=styles["Normal"], fontSize=9, leading=14)
    small_style    = ParagraphStyle("Small", parent=styles["Normal"], fontSize=8, leading=12, textColor=colors.HexColor("#444444"))
    center_style   = ParagraphStyle("Center", parent=styles["Normal"], alignment=TA_CENTER, fontSize=9)

    elements = []

    # ── Header ─────────────────────────────────────────────────────
    elements.append(Paragraph("IAM Guardian", title_style))
    elements.append(Paragraph("Security Risk Assessment Report", styles["Heading2"]))
    elements.append(HRFlowable(width="100%", thickness=2, color=NAVY_COLOR))
    elements.append(Spacer(1, 0.3*cm))

    meta = [
        ["Account", scan_data.get("account_name", "—") + f"  ({scan_data.get('account_id', '—')})"],
        ["Scan ID", scan_id],
        ["Generated", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")],
        ["Total Policies", str(scan_data.get("total", 0))],
    ]
    meta_table = Table(meta, colWidths=[4*cm, 12*cm])
    meta_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), GRAY_COLOR),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 0.5*cm))

    # ── Summary ─────────────────────────────────────────────────────
    elements.append(Paragraph("Risk Summary", heading_style))
    summary_data = [
        ["🔴  RED (Critical)", "🟡  AMBER (Moderate)", "🟢  GREEN (Low Risk)"],
        [str(scan_data.get("red", 0)), str(scan_data.get("amber", 0)), str(scan_data.get("green", 0))],
    ]
    summary_table = Table(summary_data, colWidths=[5.5*cm, 5.5*cm, 5.5*cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#FFE5E7")),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#FFF3E0")),
        ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#E0F7F5")),
        ("BACKGROUND", (0, 1), (0, 1), RED_COLOR),
        ("BACKGROUND", (1, 1), (1, 1), AMBER_COLOR),
        ("BACKGROUND", (2, 1), (2, 1), GREEN_COLOR),
        ("TEXTCOLOR", (0, 1), (-1, 1), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, 1), 18),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [None, None]),
        ("BOX", (0, 0), (-1, -1), 0.5, GRAY_COLOR),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, GRAY_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.5*cm))

    # ── Policy Details ───────────────────────────────────────────────
    elements.append(Paragraph("Policy Details", heading_style))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_COLOR))
    elements.append(Spacer(1, 0.3*cm))

    policies = scan_data.get("policies", [])

    # Sort: RED first, then AMBER, then GREEN
    order = {"RED": 0, "AMBER": 1, "GREEN": 2}
    policies_sorted = sorted(policies, key=lambda x: order.get(x.get("classification", "GREEN"), 3))

    for i, policy in enumerate(policies_sorted):
        classification = policy.get("classification", "UNKNOWN")
        original = policy.get("original", {})
        risk_color = get_risk_color(classification)

        # Policy header row
        header_data = [[
            Paragraph(f"<b>{classification}</b>", ParagraphStyle("badge", fontSize=9, textColor=colors.white)),
            Paragraph(f"<b>{original.get('policy_name', 'Unknown Policy')}</b>", ParagraphStyle("ph", fontSize=10, textColor=NAVY_COLOR)),
            Paragraph(f"Attached to: {original.get('entity_name', '—')} ({original.get('attached_to', '—')})", small_style),
        ]]
        header_table = Table(header_data, colWidths=[2*cm, 8*cm, 6*cm])
        header_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), risk_color),
            ("BACKGROUND", (1, 0), (2, 0), colors.HexColor("#F8F9FA")),
            ("ALIGN", (0, 0), (0, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("BOX", (0, 0), (-1, -1), 0.5, GRAY_COLOR),
        ]))
        elements.append(header_table)

        # Justification
        justification = policy.get("justification", "")
        elements.append(Paragraph(f"<b>Risk Assessment:</b> {justification}", small_style))
        elements.append(Spacer(1, 0.1*cm))

        # Risk factors
        risk_factors = policy.get("risk_factors", [])
        if risk_factors:
            factors_text = "  •  ".join(risk_factors)
            elements.append(Paragraph(f"<b>Risk Factors:</b> {factors_text}", small_style))
            elements.append(Spacer(1, 0.1*cm))

        # Suggested policy
        suggested = policy.get("suggested_policy", {})
        if suggested:
            elements.append(Paragraph("<b>Suggested Least-Privilege Policy:</b>", small_style))
            suggested_str = json.dumps(suggested, indent=2)
            # Truncate if too long
            if len(suggested_str) > 800:
                suggested_str = suggested_str[:800] + "\n  ... (truncated)"
            elements.append(Paragraph(
                f"<font name='Courier' size='7'>{suggested_str.replace(chr(10), '<br/>')}</font>",
                ParagraphStyle("code", fontSize=7, leading=10, leftIndent=10)
            ))

        elements.append(Spacer(1, 0.4*cm))
        elements.append(HRFlowable(width="100%", thickness=0.3, color=colors.HexColor("#DDDDDD")))
        elements.append(Spacer(1, 0.3*cm))

        # Page break every 3 policies to avoid overflow
        if (i + 1) % 3 == 0 and i + 1 < len(policies_sorted):
            elements.append(PageBreak())

    # ── Footer ───────────────────────────────────────────────────────
    elements.append(PageBreak())
    elements.append(Paragraph("About This Report", heading_style))
    elements.append(Paragraph(
        "This report was generated by IAM Guardian, an AI-powered security tool that analyses "
        "AWS IAM policies for misconfigurations and excessive permissions. Classifications are "
        "provided as guidance and should be reviewed by a qualified security professional before "
        "applying any changes to production environments.",
        body_style
    ))

    doc.build(elements)
    print(f"PDF report generated: {pdf_path}")
    return pdf_path
