# Arabic Fonts for PDF Rendering

Place an Arabic-capable TrueType font (`.ttf`) in this folder so ReportLab can render Arabic text correctly in generated PDFs.

## Filenames auto-detected
The PDF code (`core/pdf.py`) will automatically register these filenames if present:

- `NotoNaskhArabic-Regular.ttf` (recommended)
- `DejaVuSans.ttf` (fallback)

You may use other Arabic-capable fonts, but if you do, rename the file to one of the above names so it’s picked up automatically.

## Why this is needed
On minimal Linux environments (e.g., Railway), common system fonts like Arial/Tahoma are not available. Without a font containing Arabic glyphs, ReportLab falls back to Helvetica, which renders boxes.

## Verify locally
1. Add the font file here (matching one of the names above).
2. Restart the backend.
3. Generate a player PDF (`/api/players/{id}/report-pdf/`) and confirm the Arabic heading renders.

## Licensing
Ensure any font you add is permitted for your use and redistribution. Recommended:
- Noto Naskh Arabic — SIL Open Font License (OFL)
- DejaVu Sans — DejaVu Fonts License