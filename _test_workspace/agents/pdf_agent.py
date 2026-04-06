from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit
import os
import uuid

class PDFAgent:
    def __init__(self):
        self.output_dir = "generated_pdfs"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def generate_pdf(self, content):
        file_name = f"{uuid.uuid4().hex}.pdf"
        file_path = os.path.join(self.output_dir, file_name)

        c = canvas.Canvas(file_path, pagesize=letter)
        width, height = letter
        y = height - 40
        line_height = 14  # Slightly more spacing
        
        # 🔥 Handle long lines with word wrap
        for line in content.split("\n"):
            # Split long lines
            wrapped_lines = simpleSplit(line, c._fontname, c._fontsize, width - 80)
            
            for wrapped_line in wrapped_lines:
                c.drawString(40, y, wrapped_line)
                y -= line_height
                
                if y < 40:
                    c.showPage()
                    y = height - 40

        c.save()
        return file_path