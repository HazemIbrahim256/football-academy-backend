from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_RIGHT

from django.conf import settings
from pathlib import Path


def _safe_image(path, width=100, height=100):
    try:
        return Image(path, width=width, height=height)
    except Exception:
        return None


# Rating label helpers (1–5)
RATING_LABELS = {
    1: "Bad",
    2: "Not bad",
    3: "Good",
    4: "Very Good",
    5: "Excellent",
}


def rating_label(value) -> str:
    if value is None:
        return "—"
    try:
        return RATING_LABELS.get(int(value), str(value))
    except Exception:
        return "—"


def rating_label_from_average(avg: float | None) -> str:
    if avg is None:
        return "—"
    try:
        rounded = max(1, min(5, round(float(avg))))
        return rating_label(rounded)
    except Exception:
        return "—"


# Arabic translations for skill labels
SKILL_TRANSLATIONS_AR = {
    # Technical Skills
    "Ball control": "التحكم في الكرة",
    "Passing": "التمرير",
    "Dribbling": "المراوغة",
    "Shooting": "التسديد",
    "Using both feet": "استخدام القدمين",
    # Physical Abilities
    "Speed": "السرعة",
    "Agility": "الرشاقة",
    "Endurance": "التحمل",
    "Strength": "القوة",
    # Technical Understanding
    "Positioning": "التمركز",
    "Decision making": "اتخاذ القرار",
    "Game awareness": "الوعي بالمباراة",
    "Teamwork": "العمل الجماعي",
    # Psychological and Social
    "Respect": "الاحترام",
    "Sportsmanship": "الروح الرياضية",
    "Confidence": "الثقة",
    "Leadership": "القيادة",
    # Overall
    "Attendance and punctuality": "الانضباط والالتزام بالمواعيد",
}


def with_translation(label: str) -> str:
    """Return label with Arabic translation appended in parentheses when available."""
    tr = SKILL_TRANSLATIONS_AR.get(label)
    return f"{label} ({tr})" if tr else label


# Arabic font registration and shaping
def _register_arabic_font() -> str:
    """Register a font that supports Arabic and return its name.

    Tries common Windows fonts and a local fonts directory; falls back to Helvetica.
    """
    candidates = [
        ("ArabicFont", r"C:\\Windows\\Fonts\\arial.ttf"),
        ("ArabicFont", r"C:\\Windows\\Fonts\\tahoma.ttf"),
        ("ArabicFont", r"C:\\Windows\\Fonts\\times.ttf"),
        ("ArabicFont", r"C:\\Windows\\Fonts\\segoeui.ttf"),
        ("ArabicFont", r"C:\\Windows\\Fonts\\nirmala.ttf"),
        ("ArabicFont", str((Path(__file__).resolve().parent / "fonts" / "DejaVuSans.ttf"))),
    ]
    for font_name, path in candidates:
        try:
            if Path(path).exists():
                pdfmetrics.registerFont(TTFont(font_name, path))
                return font_name
        except Exception:
            continue
    return "Helvetica"


def _shape_arabic(text: str) -> str:
    """Shape Arabic text using arabic_reshaper and python-bidi if available."""
    try:
        import arabic_reshaper  # type: ignore
        from bidi.algorithm import get_display  # type: ignore

        if not text:
            return text
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception:
        return text


def with_translation_text(label: str) -> str:
    tr = SKILL_TRANSLATIONS_AR.get(label)
    if tr:
        return f"{label} ({_shape_arabic(tr)})"
    return label


def with_translation_para(label: str, style) -> Paragraph:
    return Paragraph(with_translation_text(label), style)

# Section title translations (bilingual headers)
SECTION_TRANSLATIONS_AR = {
    "Technical Skills": "مهارات تقنية",
    "Physical Abilities": "القدرات البدنية",
    "Technical Understanding": "الفهم الفني",
    "Psychological and Social": "الجوانب النفسية والاجتماعية",
    "Average Level": "المستوى العام",
}

def with_section_title_text(title: str) -> str:
    tr = SECTION_TRANSLATIONS_AR.get(title)
    if tr:
        return f"{title} ({_shape_arabic(tr)})"
    return title


def build_group_report(group) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    title = f"Group Report: {group.name}"
    story.append(Paragraph(title, styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Coach: {group.coach}", styles["Heading2"]))
    story.append(Spacer(1, 12))

    # Summary table with phone and average rating
    data = [["Photo", "Player", "Phone", "Avg"]]
    for p in group.players.select_related("evaluation").all():
        img = None
        if p.photo:
            img_path = Path(settings.MEDIA_ROOT) / p.photo.name
            img = _safe_image(str(img_path), width=50, height=50)
        row = [img if img else "", p.name, getattr(p, "phone", "")]
        ev = getattr(p, "evaluation", None)
        if ev:
            row.append(rating_label_from_average(ev.average_rating))
        else:
            row.append("-")
        data.append(row)

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(table)

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


def build_player_report(player) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=24, rightMargin=24, topMargin=24, bottomMargin=24)
    styles = getSampleStyleSheet()
    story = []

    # Compact styles to fit on a single page
    small_title = styles["Title"].clone("SmallTitle")
    small_title.fontSize = 16
    small_title.leading = 18
    small_h2 = styles["Heading2"].clone("SmallH2")
    small_h2.fontSize = 11
    small_h2.leading = 13
    small_h3 = styles["Heading3"].clone("SmallH3")
    small_h3.fontSize = 10
    small_h3.leading = 12
    normal_small = styles["Normal"].clone("NormalSmall")
    normal_small.fontSize = 9
    normal_small.leading = 11

    # Arabic-capable styles
    arabic_font = _register_arabic_font()
    arabic_label_style = normal_small.clone("ArabicLabel")
    arabic_label_style.fontName = arabic_font
    small_h3_ar = small_h3.clone("SmallH3Arabic")
    small_h3_ar.fontName = arabic_font
    arabic_right_heading = small_h3_ar.clone("ArabicRightHeading")
    arabic_right_heading.alignment = TA_RIGHT

    # Header with photo on the right
    title_para = Paragraph("Player Report", small_title)
    details_lines = [
        f"Name: {player.name}",
        f"Group: {player.group.name}",
        f"Age: {player.age}",
    ]
    if getattr(player, "phone", None):
        details_lines.append(f"Phone: {player.phone}")
    details_para = Paragraph("<br/>".join(details_lines), normal_small)

    img = None
    if player.photo:
        img_path = Path(settings.MEDIA_ROOT) / player.photo.name
        img = _safe_image(str(img_path), width=100, height=100)

    header_table = Table(
        [[title_para, img if img else ""], [details_para, ""]],
        colWidths=[None, 110],
    )
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 8))

    ev = getattr(player, "evaluation", None)
    if ev:
        # Technical Skills
        story.append(Paragraph(with_section_title_text("Technical Skills"), small_h3_ar))
        tech_data = [
            ["Skill", "Rating"],
            [with_translation_para("Ball control", arabic_label_style), Paragraph(rating_label(ev.ball_control), normal_small)],
            [with_translation_para("Passing", arabic_label_style), Paragraph(rating_label(ev.passing), normal_small)],
            [with_translation_para("Dribbling", arabic_label_style), Paragraph(rating_label(ev.dribbling), normal_small)],
            [with_translation_para("Shooting", arabic_label_style), Paragraph(rating_label(ev.shooting), normal_small)],
            [with_translation_para("Using both feet", arabic_label_style), Paragraph(rating_label(ev.using_both_feet), normal_small)],
        ]
        tech_table = Table(tech_data, repeatRows=1)
        tech_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(tech_table)
        story.append(Spacer(1, 6))

        # Physical Abilities
        story.append(Paragraph(with_section_title_text("Physical Abilities"), small_h3_ar))
        phys_data = [
            ["Attribute", "Rating"],
            [with_translation_para("Speed", arabic_label_style), Paragraph(rating_label(ev.speed), normal_small)],
            [with_translation_para("Agility", arabic_label_style), Paragraph(rating_label(ev.agility), normal_small)],
            [with_translation_para("Endurance", arabic_label_style), Paragraph(rating_label(ev.endurance), normal_small)],
            [with_translation_para("Strength", arabic_label_style), Paragraph(rating_label(ev.strength), normal_small)],
        ]
        phys_table = Table(phys_data, repeatRows=1)
        phys_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(phys_table)
        story.append(Spacer(1, 6))

        # Technical Understanding
        story.append(Paragraph(with_section_title_text("Technical Understanding"), small_h3_ar))
        tu_data = [
            ["Aspect", "Rating"],
            [with_translation_para("Positioning", arabic_label_style), Paragraph(rating_label(ev.positioning), normal_small)],
            [with_translation_para("Decision making", arabic_label_style), Paragraph(rating_label(ev.decision_making), normal_small)],
            [with_translation_para("Game awareness", arabic_label_style), Paragraph(rating_label(ev.game_awareness), normal_small)],
            [with_translation_para("Teamwork", arabic_label_style), Paragraph(rating_label(ev.teamwork), normal_small)],
        ]
        tu_table = Table(tu_data, repeatRows=1)
        tu_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(tu_table)
        story.append(Spacer(1, 6))

        # Psychological and Social
        story.append(Paragraph(with_section_title_text("Psychological and Social"), small_h3_ar))
        psy_data = [
            ["Aspect", "Rating"],
            [with_translation_para("Respect", arabic_label_style), Paragraph(rating_label(ev.respect), normal_small)],
            [with_translation_para("Sportsmanship", arabic_label_style), Paragraph(rating_label(ev.sportsmanship), normal_small)],
            [with_translation_para("Confidence", arabic_label_style), Paragraph(rating_label(ev.confidence), normal_small)],
            [with_translation_para("Leadership", arabic_label_style), Paragraph(rating_label(ev.leadership), normal_small)],
        ]
        psy_table = Table(psy_data, repeatRows=1)
        psy_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(psy_table)
        story.append(Spacer(1, 6))

        # Overall
        story.append(Paragraph(with_section_title_text("Average Level") + f": {rating_label_from_average(ev.average_rating)}", small_h3_ar))
        story.append(Paragraph(f"{with_translation_text('Attendance and punctuality')}: {rating_label(ev.attendance_and_punctuality)}", arabic_label_style))
        story.append(Paragraph(f"Coach: {ev.coach}", normal_small))
        if ev.notes:
            story.append(Spacer(1, 4))
            story.append(Paragraph(f"Notes: {ev.notes}", normal_small))
    else:
        story.append(Paragraph("No evaluation available.", styles["Normal"]))

    # Final Arabic note section requested: رأي المدرب وما يحتاج اللاعب تطويره
    try:
        story.append(Spacer(1, 10))
        story.append(Paragraph(_shape_arabic("رأي المدرب وما يحتاج اللاعب تطويره"), arabic_right_heading))
    except Exception:
        # Fallback without shaping
        story.append(Spacer(1, 10))
        story.append(Paragraph("رأي المدرب وما يحتاج اللاعب تطويره", arabic_right_heading))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf