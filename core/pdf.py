from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab import rl_config
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.utils import ImageReader

from django.conf import settings
from pathlib import Path
from datetime import datetime
from urllib.request import urlopen
from urllib.parse import urljoin


def _safe_image(path, width=100, height=100):
    """Return an Image flowable if the resource is readable; otherwise None.

    ReportLab often loads images lazily at build time, which can trigger
    OSError later. Proactively verify readability via ImageReader first.
    """
    try:
        p = Path(path)
        if not p.exists() or not p.is_file():
            return None
        # Attempt to read to ensure the file is a valid image
        ImageReader(str(p))
        return Image(str(p), width=width, height=height)
    except Exception:
        return None


def _url_image(url: str, width: int = 100, height: int = 100):
    """Return an Image from an HTTP(S) URL if retrievable; otherwise None."""
    try:
        if not url or not (url.startswith("http://") or url.startswith("https://")):
            return None
        with urlopen(url, timeout=6) as resp:
            data = resp.read()
        img_reader = ImageReader(BytesIO(data))
        return Image(img_reader, width=width, height=height)
    except Exception:
        return None


def _image_from_field(field, width: int = 100, height: int = 100):
    """Return an Image from a Django FileField/FieldFile, reading bytes via storage.

    This avoids reliance on local filesystem paths and works with remote storages.
    """
    try:
        # FieldFile.open sets up the file object on the storage; ensure close afterwards
        field.open("rb")
        try:
            data = field.read()
        finally:
            field.close()
        img_reader = ImageReader(BytesIO(data))
        return Image(img_reader, width=width, height=height)
    except Exception:
        return None


def _logo_image(width: int = 60, height: int = 60):
    """Return the academy logo Image flowable if found.

    Tries multiple likely locations across this repo so development and
    deployment both work without configuration.
    """
    try:
        base = Path(__file__).resolve().parent
        backend_root = base.parent
        # Typical Django BASE_DIR points at the project dir (academy)
        base_dir = Path(getattr(settings, "BASE_DIR", backend_root)).resolve()

        candidates = [
            base / "logo.png",
            base / "fonts" / "logo.png",
            backend_root / "core" / "logo.png",
            backend_root / "core" / "fonts" / "logo.png",
            # Frontend public assets in monorepo
            base_dir.parent / "football-academy-frontend" / "public" / "logo.png",
            base_dir.parent.parent / "football-academy-frontend" / "public" / "logo.png",
        ]

        for p in candidates:
            img = _safe_image(p, width=width, height=height)
            if img:
                try:
                    img.hAlign = "LEFT"
                except Exception:
                    pass
                return img
    except Exception:
        pass
    # Final fallback: configurable logo URL
    try:
        logo_url = getattr(settings, "LOGO_URL", "")
        img = _url_image(logo_url, width=width, height=height)
        if img:
            try:
                img.hAlign = "LEFT"
            except Exception:
                pass
            return img
    except Exception:
        pass
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
    """Register and return an Arabic-capable TrueType font name.

    - Searches common font locations across Windows, Linux, and macOS.
    - Prefers Noto Naskh Arabic or DejaVu Sans when available.
    - Falls back to system fonts like Arial/Tahoma on Windows.
    - As a last resort, returns "Helvetica" (which will not render Arabic properly).
    """
    # Reuse previously registered font if available
    if "ArabicFont" in pdfmetrics.getRegisteredFontNames():
        return "ArabicFont"

    base = Path(__file__).resolve().parent
    local_fonts = [
        base / "fonts" / "NotoNaskhArabic-Regular.ttf",
        base / "fonts" / "DejaVuSans.ttf",
    ]

    windows_candidates = [
        Path(r"C:\\Windows\\Fonts\\NotoNaskhArabic-Regular.ttf"),
        Path(r"C:\\Windows\\Fonts\\arial.ttf"),
        Path(r"C:\\Windows\\Fonts\\tahoma.ttf"),
        Path(r"C:\\Windows\\Fonts\\times.ttf"),
        Path(r"C:\\Windows\\Fonts\\segoeui.ttf"),
        Path(r"C:\\Windows\\Fonts\\TraditionalArabic.ttf"),
    ]

    linux_candidates = [
        Path("/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf"),
        Path("/usr/share/fonts/opentype/noto/NotoNaskhArabic-Regular.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/ttf-dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/freefont/FreeSans.ttf"),
    ]

    mac_candidates = [
        Path("/Library/Fonts/Arial Unicode.ttf"),
        Path("/Library/Fonts/Arial Unicode MS.ttf"),
        Path("/Library/Fonts/Tahoma.ttf"),
        # Geeza Pro is Arabic-capable but often in TTC; skip TTC to avoid errors
        Path("/Library/Fonts/DejaVuSans.ttf"),
    ]

    candidates: list[Path] = local_fonts + windows_candidates + linux_candidates + mac_candidates

    # Add local fonts directory to ReportLab TTF search path (harmless if duplicate)
    try:
        rl_config.TTFSearchPath = list({*rl_config.TTFSearchPath, str(base / "fonts")} )
    except Exception:
        pass

    for path in candidates:
        try:
            if path.exists():
                pdfmetrics.registerFont(TTFont("ArabicFont", str(path)))
                return "ArabicFont"
        except Exception:
            # Try next candidate
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


def with_translation_html(label: str, english_font_name: str = "Helvetica", arabic_font_name: str | None = None) -> str:
    """Return inline bilingual HTML: English - Arabic (shaped), with fonts."""
    ar_font = arabic_font_name or _register_arabic_font()
    tr = SKILL_TRANSLATIONS_AR.get(label)
    if tr:
        shaped = _shape_arabic(tr)
        return f'<font name="{english_font_name}">{label}</font> - <font name="{ar_font}">{shaped}</font>'
    return f'<font name="{english_font_name}">{label}</font>'


def with_translation_para(label: str, style) -> Paragraph:
    # Use a Latin-capable font for English part to ensure visibility,
    # while the paragraph style controls size/leading.
    html = with_translation_html(label, english_font_name="Helvetica", arabic_font_name=_register_arabic_font())
    return Paragraph(html, style)

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

def with_section_title_html(title: str, english_font_name: str = "Helvetica", arabic_font_name: str | None = None) -> str:
    """Inline bilingual section title: English / Arabic (shaped)."""
    ar_font = arabic_font_name or _register_arabic_font()
    tr = SECTION_TRANSLATIONS_AR.get(title)
    if tr:
        shaped = _shape_arabic(tr)
        return f'<font name="{english_font_name}">{title}</font> / <font name="{ar_font}">{shaped}</font>'
    return f'<font name="{english_font_name}">{title}</font>'

# Arabic translations for rating labels
RATING_TRANSLATIONS_AR = {
    "Bad": "سيئ",
    "Not bad": "ليس سيئًا",
    "Good": "جيد",
    "Very Good": "جيد جدًا",
    "Excellent": "ممتاز",
}

def rating_bilingual_html(value) -> str:
    label = rating_label(value)
    ar = RATING_TRANSLATIONS_AR.get(label)
    if ar:
        return f'<font name="Helvetica">{label}</font> / <font name="{_register_arabic_font()}">{_shape_arabic(ar)}</font>'
    return f'<font name="Helvetica">{label}</font>'

def rating_bilingual_html_from_average(avg: float | None) -> str:
    return rating_bilingual_html(rating_label_from_average(avg))


def _latest_evaluation(player):
    """Return the most recent evaluation for a player, or None.

    Handles the current FK relationship (player.evaluations) and orders by
    evaluated_at then updated_at, descending.
    """
    try:
        # Use in-memory prefetch when available; otherwise query.
        qs = getattr(player, "evaluations", None)
        if qs is None:
            return None
        return qs.order_by("-evaluated_at", "-updated_at").first()
    except Exception:
        return None


def build_group_report(group) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Header with logo on the top-left
    logo = _logo_image(width=60, height=60)
    title_para = Paragraph(f"Group Report: {group.name}", styles["Title"])
    coach_para = Paragraph(f"Coach: {group.coach}", styles["Heading2"])
    header = Table(
        [[logo if logo else "", title_para], ["", coach_para]],
        colWidths=[70, None],
    )
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header)
    story.append(Spacer(1, 12))

    # Summary table with phone and average rating
    data = [["Photo", "Player", "Phone", "Avg"]]
    # Prefetch evaluations to avoid N+1 queries after relationship change
    for p in group.players.prefetch_related("evaluations").all():
        img = None
        if p.photo:
            # Prefer storage bytes (works for local and remote storages)
            img = _image_from_field(p.photo, width=50, height=50)
            if not img:
                # Fallback to local filesystem path
                img_path = getattr(p.photo, "path", None)
                if not img_path:
                    img_path = str(Path(settings.MEDIA_ROOT) / p.photo.name)
                img = _safe_image(img_path, width=50, height=50)
                if not img:
                    # Last resort: try via PUBLIC_BASE_URL + relative media URL
                    url = getattr(p.photo, "url", None)
                    base = getattr(settings, "PUBLIC_BASE_URL", "")
                    if url and base and url.startswith("/"):
                        img = _url_image(urljoin(base + "/", url.lstrip("/")), width=50, height=50)
        row = [img if img else "", p.name, getattr(p, "phone", "")]
        ev = _latest_evaluation(p)
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

    try:
        doc.build(story)
    except OSError:
        # Fallback minimal PDF without images to avoid 500 errors
        fallback_buffer = BytesIO()
        fallback_doc = SimpleDocTemplate(fallback_buffer, pagesize=A4)
        fallback_story = [Paragraph("Group Report", styles["Title"]), Spacer(1, 12), Paragraph(f"Group: {group.name}", styles["Normal"])]
        fallback_doc.build(fallback_story)
        pdf = fallback_buffer.getvalue()
        fallback_buffer.close()
        buffer.close()
        return pdf
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

    # Header with logo on the left and photo on the right
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
        # Prefer reading bytes directly from storage
        img = _image_from_field(player.photo, width=100, height=100)
        if not img:
            # Fallback to local filesystem path
            img_path = getattr(player.photo, "path", None)
            if not img_path:
                img_path = str(Path(settings.MEDIA_ROOT) / player.photo.name)
            img = _safe_image(img_path, width=100, height=100)
            if not img:
                # Last resort: attempt via PUBLIC_BASE_URL + relative media URL
                url = getattr(player.photo, "url", None)
                base = getattr(settings, "PUBLIC_BASE_URL", "")
                if url and base and url.startswith("/"):
                    img = _url_image(urljoin(base + "/", url.lstrip("/")), width=100, height=100)

    logo = _logo_image(width=60, height=60)
    header_table = Table(
        [[logo if logo else "", title_para, img if img else ""], ["", details_para, ""]],
        colWidths=[70, None, 110],
    )
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 8))

    # Use the latest evaluation for the player (FK relation)
    ev = _latest_evaluation(player)
    if ev:
        # Technical Skills
        story.append(Paragraph(with_section_title_html("Technical Skills", english_font_name=small_h3.fontName, arabic_font_name=arabic_font), small_h3))
        tech_data = [
            ["Skill", "Rating"],
            [with_translation_para("Ball control", arabic_label_style), Paragraph(rating_bilingual_html(ev.ball_control), normal_small)],
            [with_translation_para("Passing", arabic_label_style), Paragraph(rating_bilingual_html(ev.passing), normal_small)],
            [with_translation_para("Dribbling", arabic_label_style), Paragraph(rating_bilingual_html(ev.dribbling), normal_small)],
            [with_translation_para("Shooting", arabic_label_style), Paragraph(rating_bilingual_html(ev.shooting), normal_small)],
            [with_translation_para("Using both feet", arabic_label_style), Paragraph(rating_bilingual_html(ev.using_both_feet), normal_small)],
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
        story.append(Paragraph(with_section_title_html("Physical Abilities", english_font_name=small_h3.fontName, arabic_font_name=arabic_font), small_h3))
        phys_data = [
            ["Attribute", "Rating"],
            [with_translation_para("Speed", arabic_label_style), Paragraph(rating_bilingual_html(ev.speed), normal_small)],
            [with_translation_para("Agility", arabic_label_style), Paragraph(rating_bilingual_html(ev.agility), normal_small)],
            [with_translation_para("Endurance", arabic_label_style), Paragraph(rating_bilingual_html(ev.endurance), normal_small)],
            [with_translation_para("Strength", arabic_label_style), Paragraph(rating_bilingual_html(ev.strength), normal_small)],
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
        story.append(Paragraph(with_section_title_html("Technical Understanding", english_font_name=small_h3.fontName, arabic_font_name=arabic_font), small_h3))
        tu_data = [
            ["Aspect", "Rating"],
            [with_translation_para("Positioning", arabic_label_style), Paragraph(rating_bilingual_html(ev.positioning), normal_small)],
            [with_translation_para("Decision making", arabic_label_style), Paragraph(rating_bilingual_html(ev.decision_making), normal_small)],
            [with_translation_para("Game awareness", arabic_label_style), Paragraph(rating_bilingual_html(ev.game_awareness), normal_small)],
            [with_translation_para("Teamwork", arabic_label_style), Paragraph(rating_bilingual_html(ev.teamwork), normal_small)],
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
        story.append(Paragraph(with_section_title_html("Psychological and Social", english_font_name=small_h3.fontName, arabic_font_name=arabic_font), small_h3))
        psy_data = [
            ["Aspect", "Rating"],
            [with_translation_para("Respect", arabic_label_style), Paragraph(rating_bilingual_html(ev.respect), normal_small)],
            [with_translation_para("Sportsmanship", arabic_label_style), Paragraph(rating_bilingual_html(ev.sportsmanship), normal_small)],
            [with_translation_para("Confidence", arabic_label_style), Paragraph(rating_bilingual_html(ev.confidence), normal_small)],
            [with_translation_para("Leadership", arabic_label_style), Paragraph(rating_bilingual_html(ev.leadership), normal_small)],
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
        story.append(Paragraph(with_section_title_html("Average Level", english_font_name=small_h3.fontName, arabic_font_name=arabic_font) + f": {rating_bilingual_html_from_average(ev.average_rating)}", small_h3))
        attendance_html = with_translation_html("Attendance and punctuality", english_font_name=normal_small.fontName, arabic_font_name=arabic_font)
        story.append(Paragraph(f"{attendance_html}: {rating_bilingual_html(ev.attendance_and_punctuality)}", normal_small))
        story.append(Paragraph(f"Coach: {ev.coach}", normal_small))
        if ev.notes:
            story.append(Spacer(1, 4))
            story.append(Paragraph(f"Notes: {ev.notes}", normal_small))
    else:
        story.append(Paragraph("No evaluation available.", styles["Normal"]))

    # Final Arabic note section split into two questions
    try:
        story.append(Spacer(1, 10))
        story.append(Paragraph(_shape_arabic("رأي المدرب"), arabic_right_heading))
        story.append(Spacer(1, 6))
        story.append(Paragraph(_shape_arabic("ما يحتاج اللاعب تطويره"), arabic_right_heading))
    except Exception:
        # Fallback without shaping
        story.append(Spacer(1, 10))
        story.append(Paragraph("رأي المدرب", arabic_right_heading))
        story.append(Spacer(1, 6))
        story.append(Paragraph("ما يحتاج اللاعب تطويره", arabic_right_heading))

    try:
        doc.build(story)
    except OSError:
        # Fallback minimal PDF to avoid 500 errors
        SimpleDocTemplate(buffer, pagesize=A4).build([
            Paragraph("Player Report", styles["Title"]),
            Spacer(1, 12),
            Paragraph(f"Name: {player.name}", styles["Normal"]),
        ])
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
