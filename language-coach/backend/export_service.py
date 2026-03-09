"""
Export service for generating PDF lessons
"""
from fpdf import FPDF
import os
from typing import Dict, Any

class PDFExporter:
    """Export lesson data to PDF"""
    
    def __init__(self, output_dir: str = "../data/exports"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
    def export_lesson(self, lesson_data: Dict[str, Any]) -> str:
        """Create a PDF file for the lesson"""
        pdf = FPDF()
        pdf.add_page()
        
        # Title
        metadata = lesson_data['metadata']
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, f"Language Lesson: {metadata['topic']}", ln=True, align='C')
        pdf.set_font("Arial", '', 12)
        pdf.cell(0, 10, f"Language: {metadata['language']} | Level: {metadata['level']}", ln=True, align='C')
        pdf.ln(10)
        
        # Vocabulary
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "1. Vocabulary", ln=True)
        pdf.set_font("Arial", '', 11)
        for item in lesson_data['vocabulary']:
            word_line = f"- {item['word']}"
            if item.get('reading'): word_line += f" ({item['reading']})"
            if item.get('phonetic'): word_line += f" {item['phonetic']}"
            pdf.cell(0, 8, word_line, ln=True)
            pdf.set_font("Arial", 'I', 10)
            pdf.cell(0, 6, f"  Definition: {item['definition_zh']}", ln=True)
            pdf.cell(0, 6, f"  Example: {item['example_sentence']}", ln=True)
            pdf.set_font("Arial", '', 11)
            pdf.ln(2)
            
        # Grammar
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, f"2. Grammar: {lesson_data['grammar']['title']}", ln=True)
        pdf.set_font("Arial", '', 11)
        pdf.multi_cell(0, 8, lesson_data['grammar']['explanation'])
        pdf.ln(5)
        
        # Save
        file_path = os.path.join(self.output_dir, f"lesson_{metadata['lesson_id']}.pdf")
        pdf.output(file_path)
        return file_path

pdf_exporter = PDFExporter()
