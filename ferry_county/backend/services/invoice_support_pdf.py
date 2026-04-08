"""USDA invoice support package — official cover + line items (ReportLab)."""

from __future__ import annotations

import csv
from io import BytesIO, StringIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def build_invoice_support_pdf(data: dict[str, Any]) -> bytes:
    """
    PDF with cover page (Ferry County / CWDG / billing period / totals / signatories)
    and treatment line-item tables for USDA reimbursement.
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        pageCompression=0,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name="CoverTitle",
        parent=styles["Heading1"],
        fontSize=16,
        leading=20,
        alignment=TA_CENTER,
        spaceAfter=14,
        textColor=colors.HexColor("#1a1a2e"),
    )
    cover_body = ParagraphStyle(
        name="CoverBody",
        parent=styles["Normal"],
        fontSize=11,
        leading=15,
        alignment=TA_CENTER,
        spaceAfter=10,
    )
    cover_label = ParagraphStyle(
        name="CoverLabel",
        parent=styles["Normal"],
        fontSize=10,
        leading=13,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#333333"),
    )
    story: list[Any] = []

    ps = data.get("period_start") or ""
    pe = data.get("period_end") or ""
    totals = data.get("totals") or {}
    fed = totals.get("total_federal_claimed")
    fed_s = f"{float(fed):,.2f}" if fed is not None else "0.00"

    story.append(Spacer(1, 1.1 * inch))
    story.append(Paragraph("Ferry County, Washington", title_style))
    story.append(Paragraph("CWDG Grant — Fuel Reduction Program", title_style))
    story.append(Spacer(1, 0.35 * inch))
    story.append(Paragraph(f"<b>Billing period:</b> {ps} to {pe}", cover_body))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph(f"<b>Total federal amount claimed:</b> ${fed_s}", cover_body))
    story.append(Spacer(1, 0.55 * inch))
    story.append(Paragraph("Prepared by:", cover_label))
    story.append(Paragraph("<b>David R. Vitelle</b>, CWDG Project Manager", cover_body))
    story.append(Spacer(1, 0.25 * inch))
    story.append(Paragraph("Reviewed by:", cover_label))
    story.append(Paragraph("<b>Steven L. Bonner</b>, Emergency Management Director", cover_body))
    story.append(Spacer(1, 0.4 * inch))
    story.append(
        Paragraph(
            "<i>This document supports reimbursement documentation submitted to USDA.</i>",
            cover_label,
        )
    )

    story.append(PageBreak())
    story.append(Paragraph("Treatment line items (reimbursement support)", styles["Heading2"]))
    story.append(Spacer(1, 0.15 * inch))

    items = data.get("line_items") or []
    if not items:
        story.append(Paragraph("No treatments in this period.", styles["Normal"]))
    else:
        hdr = [
            "Date",
            "Road",
            "#",
            "Dist",
            "Type",
            "Mi",
            "Ac",
            "Contractor",
            "TO",
            "Match",
            "Federal $",
        ]
        rows = [hdr]
        for it in items:
            rows.append(
                [
                    str(it.get("treatment_date") or ""),
                    (it.get("road_name") or "")[:22],
                    str(it.get("road_number") or ""),
                    str(it.get("district") if it.get("district") is not None else ""),
                    (it.get("treatment_type") or "")[:14],
                    f"{float(it.get('miles_treated') or 0):.3f}",
                    f"{float(it.get('acres_treated') or 0):.3f}",
                    (it.get("contractor") or "")[:18],
                    (it.get("contractor_task_order") or "")[:8],
                    "Y" if it.get("match_documented") else "N",
                    f"{float(it.get('amount_federal') or 0):,.2f}",
                ]
            )
        # Second table for GPS (wider text) — add sub-table per row is heavy; add one summary table + detail
        t = Table(rows, repeatRows=1, colWidths=[58, 92, 28, 28, 68, 32, 32, 78, 36, 28, 52])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d6a4f")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 7),
                    ("FONTSIZE", (0, 1), (-1, -1), 7),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
                ]
            )
        )
        story.append(t)
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph("<b>GPS start / end (WGS84)</b>", styles["Heading3"]))
        gps_rows = [["Treatment ID", "Start (lat, lon)", "End (lat, lon)"]]
        for it in items:
            gs = it.get("gps_start") or {}
            ge = it.get("gps_end") or {}
            s = (
                f"{float(gs['lat']):.6f}, {float(gs['lon']):.6f}"
                if gs.get("lat") is not None and gs.get("lon") is not None
                else "—"
            )
            e = (
                f"{float(ge['lat']):.6f}, {float(ge['lon']):.6f}"
                if ge.get("lat") is not None and ge.get("lon") is not None
                else "—"
            )
            gps_rows.append([str(it.get("treatment_id")), s, e])
        gt = Table(gps_rows, repeatRows=1, colWidths=[72, 200, 200])
        gt.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d3557")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(gt)

    story.append(Spacer(1, 0.3 * inch))
    sum_style = ParagraphStyle(name="Sum", parent=styles["Normal"], fontSize=10, alignment=0)
    story.append(
        Paragraph(
            f"<b>Period totals:</b> {totals.get('treatment_count', 0)} treatments; "
            f"{float(totals.get('total_miles') or 0):,.3f} mi; "
            f"{float(totals.get('total_acres') or 0):,.3f} ac; "
            f"federal claimed ${float(totals.get('total_federal_claimed') or 0):,.2f}.",
            sum_style,
        )
    )

    doc.build(story)
    return buf.getvalue()


def build_invoice_support_csv(data: dict[str, Any]) -> bytes:
    """UTF-8 CSV of invoice support line items + summary row."""
    items = data.get("line_items") or []
    totals = data.get("totals") or {}
    out = StringIO()
    w = csv.writer(out)
    w.writerow(
        [
            "treatment_id",
            "road_name",
            "road_number",
            "district",
            "treatment_date",
            "treatment_type",
            "miles_treated",
            "acres_treated",
            "gps_start_lat",
            "gps_start_lon",
            "gps_end_lat",
            "gps_end_lon",
            "contractor",
            "contractor_task_order",
            "match_documented",
            "amount_federal",
        ]
    )
    for it in items:
        gs = it.get("gps_start") or {}
        ge = it.get("gps_end") or {}
        w.writerow(
            [
                it.get("treatment_id"),
                it.get("road_name"),
                it.get("road_number"),
                it.get("district"),
                it.get("treatment_date"),
                it.get("treatment_type"),
                it.get("miles_treated"),
                it.get("acres_treated"),
                gs.get("lat"),
                gs.get("lon"),
                ge.get("lat"),
                ge.get("lon"),
                it.get("contractor"),
                it.get("contractor_task_order"),
                it.get("match_documented"),
                it.get("amount_federal"),
            ]
        )
    w.writerow([])
    w.writerow(
        [
            "TOTALS",
            "",
            "",
            "",
            "",
            "",
            totals.get("total_miles"),
            totals.get("total_acres"),
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            totals.get("total_federal_claimed"),
        ]
    )
    return out.getvalue().encode("utf-8")
