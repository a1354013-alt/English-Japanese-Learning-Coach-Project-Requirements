"""
Export service for generating PDF lessons using ReportLab for CJK support
"""
import os
from typing import Dict, Any
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

class PDFExporter:
    """Export lesson data to PDF with CJK support (P1 Fix)"""
    
    def __init__(self, output_dir: str = "../data/exports"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Try to register a CJK font if available in the system
        # Common paths for Noto Sans CJK or similar
        font_paths = [
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"
        ]
        
        self.font_name = "Helvetica" # Default fallback
        for path in font_paths:
            if os.path.exists(path):
                try:
                    pdfmetrics.registerFont(TTFont("CJKFont", path))
                    self.font_name = "CJKFont"
                    break
                except:
                    continue

    def export_lesson(self, lesson_data: Dict[str, Any]) -> str:
        """Create a PDF file for the lesson using ReportLab"""
        metadata = lesson_data['metadata']
        file_path = os.path.join(self.output_dir, f"lesson_{metadata['lesson_id']}.pdf")
        
        doc = SimpleDocTemplate(file_path, pagesize=letter)
        styles = getSampleStyleSheet()
        
        # Create custom styles with CJK font
        title_style = ParagraphStyle(
            'CJKTitle',
            parent=styles['Title'],
            fontName=self.font_name,
            fontSize=18,
            spaceAfter=12
        )
        
        heading_style = ParagraphStyle(
            'CJKHeading',
            parent=styles['Heading2'],
            fontName=self.font_name,
            fontSize=14,
            spaceBefore=12,
            spaceAfter=6
        )
        
        body_style = ParagraphStyle(
            'CJKBody',
            parent=styles['Normal'],
            fontName=self.font_name,
            fontSize=11,
            leading=14
        )
        
        elements = []
        
        # Title
        elements.append(Paragraph(f"Language Lesson: {metadata['topic']}", title_style))
        elements.append(Paragraph(f"Language: {metadata['language']} | Level: {metadata['level']}", body_style))
        elements.append(Spacer(1, 0.2 * inch))
        
        # Vocabulary
        elements.append(Paragraph("1. Vocabulary", heading_style))
        for item in lesson_data['vocabulary']:
            word_text = f"<b>{item['word']}</b>"
            if item.get('reading'): word_text += f" ({item['reading']})"
            if item.get('phonetic'): word_text += f" {item['phonetic']}"
            
            elements.append(Paragraph(word_text, body_style))
            elements.append(Paragraph(f"<i>Definition:</i> {item['definition_zh']}", body_style))
            elements.append(Paragraph(f"<i>Example:</i> {item['example_sentence']}", body_style))
            elements.append(Paragraph(f"<i>Translation:</i> {item['example_translation']}", body_style))
            elements.append(Spacer(1, 0.1 * inch))
            
        # Grammar
        elements.append(Paragraph(f"2. Grammar: {lesson_data['grammar']['title']}", heading_style))
        elements.append(Paragraph(lesson_data['grammar']['explanation'], body_style))
        
        # Reading
        elements.append(Paragraph(f"3. Reading: {lesson_data['reading']['title']}", heading_style))
        elements.append(Paragraph(lesson_data['reading']['content'], body_style))
        
        doc.build(elements)
        return file_path

pdf_exporter = PDFExporter()
