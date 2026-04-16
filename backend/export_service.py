"""PDF export service."""
from pathlib import Path
from typing import Any, Dict

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from config import settings


class PDFExporter:
    def __init__(self, output_dir: str | None = None):
        self.output_dir = Path(output_dir or settings.exports_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.font_name = "Helvetica"
        # Cross-platform font paths for CJK support
        font_paths = [
            # Linux (Noto CJK)
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
            # macOS (system fonts)
            "/System/Library/Fonts/PingFang.ttc",
            "/Library/Fonts/Arial Unicode.ttf",
            # Windows (common locations)
            "C:/Windows/Fonts/msyh.ttc",  # Microsoft YaHei
            "C:/Windows/Fonts/simsun.ttc",  # SimSun
        ]
        for path in font_paths:
            p = Path(path)
            if p.exists():
                try:
                    pdfmetrics.registerFont(TTFont("CJKFont", str(p)))
                    self.font_name = "CJKFont"
                    break
                except Exception:
                    continue

    def export_lesson(self, lesson_data: Dict[str, Any]) -> Path:
        metadata = lesson_data["metadata"]
        file_path = self.output_dir / f"lesson_{metadata['lesson_id']}.pdf"

        doc = SimpleDocTemplate(str(file_path), pagesize=letter)
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("Title", parent=styles["Title"], fontName=self.font_name)
        heading_style = ParagraphStyle("Heading", parent=styles["Heading2"], fontName=self.font_name)
        body_style = ParagraphStyle("Body", parent=styles["Normal"], fontName=self.font_name, leading=14)

        elements = [
            Paragraph(f"Language Lesson: {metadata['topic']}", title_style),
            Paragraph(f"Language: {metadata['language']} | Level: {metadata['level']}", body_style),
            Spacer(1, 0.2 * inch),
            Paragraph("Vocabulary", heading_style),
        ]

        for item in lesson_data.get("vocabulary", []):
            elements.append(Paragraph(f"<b>{item.get('word', '')}</b>", body_style))
            elements.append(Paragraph(f"Definition: {item.get('definition_zh', '')}", body_style))
            elements.append(Paragraph(f"Example: {item.get('example_sentence', '')}", body_style))
            elements.append(Paragraph(f"Translation: {item.get('example_translation', '')}", body_style))
            elements.append(Spacer(1, 0.1 * inch))

        doc.build(elements)
        return file_path


pdf_exporter = PDFExporter()
