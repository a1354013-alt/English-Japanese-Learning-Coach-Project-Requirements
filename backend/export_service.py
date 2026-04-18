"""PDF export service with full lesson support."""
from pathlib import Path
from typing import Any, Dict, List

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

    def _add_lesson_sections(self, lesson_data: Dict[str, Any], styles: Dict[str, ParagraphStyle]) -> List:
        """Build PDF elements for a complete lesson."""
        elements = []
        metadata = lesson_data["metadata"]

        # Title
        title_style = styles["Title"]
        heading_style = styles["Heading2"]
        body_style = styles["Body"]

        elements.append(Paragraph(f"Language Lesson: {metadata['topic']}", title_style))
        elements.append(
            Paragraph(f"Language: {metadata['language']} | Level: {metadata['level']}", body_style)
        )
        elements.append(Spacer(1, 0.3 * inch))

        # Vocabulary Section
        elements.append(Paragraph("Vocabulary", heading_style))
        elements.append(Spacer(1, 0.15 * inch))
        for item in lesson_data.get("vocabulary", []):
            word = item.get("word", "")
            definition = item.get("definition_zh", "")
            example = item.get("example_sentence", "")
            translation = item.get("example_translation", "")
            
            elements.append(Paragraph(f"<b>{word}</b>", body_style))
            if definition:
                elements.append(Paragraph(f"Definition: {definition}", body_style))
            if example:
                elements.append(Paragraph(f"Example: {example}", body_style))
            if translation:
                elements.append(Paragraph(f"Translation: {translation}", body_style))
            elements.append(Spacer(1, 0.1 * inch))

        # Grammar Section
        grammar = lesson_data.get("grammar", {})
        if grammar:
            elements.append(Paragraph("Grammar", heading_style))
            elements.append(Spacer(1, 0.15 * inch))
            
            if grammar.get("title"):
                elements.append(Paragraph(f"<b>{grammar['title']}</b>", body_style))
                elements.append(Spacer(1, 0.1 * inch))
            
            if grammar.get("explanation"):
                elements.append(Paragraph(grammar["explanation"], body_style))
                elements.append(Spacer(1, 0.15 * inch))
            
            # Grammar Exercises
            exercises = grammar.get("exercises", [])
            if exercises:
                elements.append(Paragraph("<i>Exercises:</i>", body_style))
                for i, ex in enumerate(exercises, 1):
                    elements.append(Paragraph(f"{i}. {ex.get('question', '')}", body_style))
                    if ex.get("answer"):
                        elements.append(Paragraph(f"   Answer: {ex['answer']}", body_style))
                elements.append(Spacer(1, 0.2 * inch))

        # Reading Section
        reading = lesson_data.get("reading", {})
        if reading:
            elements.append(Paragraph("Reading", heading_style))
            elements.append(Spacer(1, 0.15 * inch))
            
            content = reading.get("content", "")
            if content:
                elements.append(Paragraph(content.replace("\n", "<br/>"), body_style))
                elements.append(Spacer(1, 0.15 * inch))
            
            # Reading Questions
            questions = reading.get("questions", [])
            if questions:
                elements.append(Paragraph("<i>Comprehension Questions:</i>", body_style))
                for i, q in enumerate(questions, 1):
                    elements.append(Paragraph(f"{i}. {q}", body_style))
                elements.append(Spacer(1, 0.2 * inch))

        # Dialogue Section
        dialogue = lesson_data.get("dialogue", [])
        if dialogue:
            elements.append(Paragraph("Dialogue", heading_style))
            elements.append(Spacer(1, 0.15 * inch))
            
            for line in dialogue:
                speaker = line.get("speaker", "")
                text = line.get("text", "")
                if speaker and text:
                    elements.append(Paragraph(f"<b>{speaker}:</b> {text}", body_style))
            elements.append(Spacer(1, 0.2 * inch))

        return elements

    def export_lesson(self, lesson_data: Dict[str, Any]) -> Path:
        """Export a complete lesson to PDF with all sections."""
        metadata = lesson_data["metadata"]
        file_path = self.output_dir / f"lesson_{metadata['lesson_id']}.pdf"

        doc = SimpleDocTemplate(str(file_path), pagesize=letter)
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle("Title", parent=styles["Title"], fontName=self.font_name, fontSize=18, spaceAfter=12)
        heading_style = ParagraphStyle("Heading", parent=styles["Heading2"], fontName=self.font_name, fontSize=14, spaceAfter=8)
        body_style = ParagraphStyle("Body", parent=styles["Normal"], fontName=self.font_name, fontSize=11, leading=14)

        style_dict = {"Title": title_style, "Heading2": heading_style, "Body": body_style}

        elements = self._add_lesson_sections(lesson_data, style_dict)
        doc.build(elements)
        return file_path


pdf_exporter = PDFExporter()
