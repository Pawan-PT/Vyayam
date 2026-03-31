"""
VYAYAM Pre-Match Stretching PDF Report Generator
Uses reportlab to generate a single-page A4 PDF report.
"""

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT


VYAYAM_PURPLE = colors.HexColor('#667eea')
VYAYAM_PURPLE_DARK = colors.HexColor('#764ba2')
ROW_ALT = colors.HexColor('#f3f4f6')


def generate_stretch_pdf(patient, session_obj):
    """
    Generate a PDF report for a StretchSession.
    Returns an io.BytesIO buffer ready for HttpResponse.
    """
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'VyayamTitle',
        fontSize=28,
        fontName='Helvetica-Bold',
        textColor=VYAYAM_PURPLE,
        alignment=TA_CENTER,
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        'VyayamSubtitle',
        fontSize=14,
        fontName='Helvetica',
        textColor=colors.HexColor('#475569'),
        alignment=TA_CENTER,
        spaceAfter=12,
    )
    section_style = ParagraphStyle(
        'SectionHeader',
        fontSize=11,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#1e293b'),
        spaceBefore=10,
        spaceAfter=4,
    )
    footer_style = ParagraphStyle(
        'Footer',
        fontSize=8,
        fontName='Helvetica',
        textColor=colors.HexColor('#94a3b8'),
        alignment=TA_CENTER,
    )

    story = []

    # ── Header ──────────────────────────────────────────────────────────────
    story.append(Paragraph('VYAYAM', title_style))
    story.append(Paragraph('Pre-Match Stretching Report', subtitle_style))
    story.append(HRFlowable(width='100%', thickness=1, color=VYAYAM_PURPLE, spaceAfter=10))

    # ── Patient Info Table ───────────────────────────────────────────────────
    story.append(Paragraph('Patient Information', section_style))

    session_date_str = session_obj.session_date.strftime('%B %d, %Y at %I:%M %p')
    info_data = [
        ['Name', patient.name, 'Patient ID', patient.patient_id],
        ['Date', session_date_str, 'Protocol', session_obj.protocol_name],
    ]
    info_table = Table(info_data, colWidths=[35 * mm, 65 * mm, 35 * mm, 50 * mm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#475569')),
        ('TEXTCOLOR', (2, 0), (2, -1), colors.HexColor('#475569')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, ROW_ALT]),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 8))

    # ── Summary Box ──────────────────────────────────────────────────────────
    story.append(Paragraph('Session Summary', section_style))

    total_dur = session_obj.total_duration_seconds
    mins, secs = divmod(total_dur, 60)
    dur_str = f'{mins}m {secs}s'

    total = session_obj.total_stretches or 1
    rate = round((session_obj.stretches_completed / total) * 100)

    summary_data = [
        ['Stretches Completed', f"{session_obj.stretches_completed}/{session_obj.total_stretches}",
         'Total Duration', dur_str],
        ['Camera Used', 'Yes' if session_obj.camera_used else 'No',
         'Completion Rate', f'{rate}%'],
    ]
    summary_table = Table(summary_data, colWidths=[45 * mm, 40 * mm, 45 * mm, 40 * mm])
    summary_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#475569')),
        ('TEXTCOLOR', (2, 0), (2, -1), colors.HexColor('#475569')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8faff')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 8))

    # ── Stretch Details Table ─────────────────────────────────────────────────
    story.append(Paragraph('Stretch Details', section_style))

    results = session_obj.stretch_results_json or []

    detail_header = ['#', 'Stretch Name', 'Side', 'Target (s)', 'Actual (s)', 'Status', 'Posture Note']
    detail_data = [detail_header]

    for i, r in enumerate(results, start=1):
        status = 'Done' if r.get('completed') else 'Skipped'
        posture = r.get('posture_note', '') or ''
        detail_data.append([
            str(i),
            r.get('name', ''),
            r.get('side', '').capitalize(),
            str(r.get('prescribed_duration', '')),
            str(r.get('actual_duration', 0)),
            status,
            posture[:40],
        ])

    col_widths = [8 * mm, 45 * mm, 18 * mm, 20 * mm, 20 * mm, 18 * mm, 40 * mm]
    detail_table = Table(detail_data, colWidths=col_widths, repeatRows=1)

    row_count = len(detail_data)
    detail_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), VYAYAM_PURPLE),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        # Data rows
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, row_count - 1), [colors.white, ROW_ALT]),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('ALIGN', (3, 1), (5, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#e2e8f0')),
    ]))
    story.append(detail_table)

    # ── Posture Notes Section ─────────────────────────────────────────────────
    notes_list = [
        r.get('posture_note', '') for r in results
        if r.get('posture_note', '').strip()
    ]
    if notes_list:
        story.append(Spacer(1, 8))
        story.append(Paragraph('Posture Notes', section_style))
        for idx, note in enumerate(notes_list, start=1):
            story.append(Paragraph(
                f'{idx}. {note}',
                ParagraphStyle('Note', fontSize=9, fontName='Helvetica', spaceAfter=3)
            ))

    # ── Footer ───────────────────────────────────────────────────────────────
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#e2e8f0'), spaceAfter=6))
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    story.append(Paragraph(
        f'Generated by VYAYAM Strength Training System | {timestamp}',
        footer_style,
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer
