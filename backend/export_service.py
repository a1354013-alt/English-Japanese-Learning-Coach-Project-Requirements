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
        metadata = lesson_data.get("metadata") or {}

        # Title
        title_style = styles["Title"]
        heading_style = styles["Heading2"]
        body_style = styles["Body"]

        elements.append(Paragraph(f"Language Lesson: {metadata.get('topic', 'Lesson')}", title_style))
        elements.append(
            Paragraph(
                f"Language: {metadata.get('language', 'N/A')} | Level: {metadata.get('level', 'N/A')}",
                body_style,
            )
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
                    correct = ex.get("correct_answer")
                    if correct:
                        elements.append(Paragraph(f"   Answer: {correct}", body_style))
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
                    if not isinstance(q, dict):
                        elements.append(Paragraph(f"{i}. {str(q)}", body_style))
                        continue
                    elements.append(Paragraph(f"{i}. {q.get('question', '')}", body_style))
                    correct = q.get("correct_answer")
                    if correct:
                        elements.append(Paragraph(f"   Answer: {correct}", body_style))
                elements.append(Spacer(1, 0.2 * inch))

        # Dialogue Section
        dialogue_section = lesson_data.get("dialogue") or {}
        lines = dialogue_section.get("dialogue") if isinstance(dialogue_section, dict) else None
        if isinstance(lines, list) and lines:
            elements.append(Paragraph("Dialogue", heading_style))
            elements.append(Spacer(1, 0.15 * inch))

            scenario = dialogue_section.get("scenario")
            context = dialogue_section.get("context")
            if scenario:
                elements.append(Paragraph(f"<b>{scenario}</b>", body_style))
            if context:
                elements.append(Paragraph(str(context), body_style))
            if scenario or context:
                elements.append(Spacer(1, 0.1 * inch))

            for line in lines:
                if not isinstance(line, dict):
                    continue
                speaker = line.get("speaker", "")
                text = line.get("text", "")
                translation = line.get("translation", "")
                if speaker and text:
                    elements.append(Paragraph(f"<b>{speaker}:</b> {text}", body_style))
                    if translation:
                        elements.append(Paragraph(f"<i>{translation}</i>", body_style))
            elements.append(Spacer(1, 0.2 * inch))

        # Evidence (RAG)
        evidence = lesson_data.get("evidence") or []
        if isinstance(evidence, list) and evidence:
            elements.append(Paragraph("Evidence", heading_style))
            elements.append(Spacer(1, 0.15 * inch))
            for item in evidence:
                if not isinstance(item, dict):
                    continue
                source = item.get("source", "unknown")
                text = item.get("text", "")
                if text:
                    elements.append(Paragraph(f"<b>{source}</b>", body_style))
                    elements.append(Paragraph(str(text).replace("\n", "<br/>"), body_style))
                    elements.append(Spacer(1, 0.1 * inch))

        return elements

    def export_lesson(self, lesson_data: Dict[str, Any]) -> Path:
        """Export a complete lesson to PDF with all sections."""
        metadata = lesson_data.get("metadata") or {}
        lesson_id = metadata.get("lesson_id") or "unknown"
        file_path = self.output_dir / f"lesson_{lesson_id}.pdf"

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
