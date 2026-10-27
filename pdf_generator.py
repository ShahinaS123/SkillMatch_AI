from fpdf import FPDF
import matplotlib.pyplot as plt
import io
import re
import os

class PDFReport(FPDF):
    def header(self):
        # Add Logo
        current_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(current_dir, "logo.png")
        if os.path.exists(logo_path):
            self.image(logo_path, x=10, y=8, w=25)
        
        self.set_font('Times', 'B', 16)
        self.set_text_color(40, 40, 40)
        self.set_y(12)
        self.cell(30, 10, '', 0, 0) # Space for logo
        self.cell(0, 10, 'SkillMatch AI - Professional Analysis Report', 0, 1, 'C')
        
        self.set_draw_color(200, 200, 200)
        self.line(10, 25, 200, 25)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Times', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def clean_text(text):
    if not text: return ""
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F" u"\U0001F300-\U0001F5FF" u"\U0001F680-\U0001F6FF"
        u"\U0001F1E0-\U0001F1FF" u"\U00002702-\U000027B0" u"\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE)
    text = emoji_pattern.sub(r'', text)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = text.replace('**', '').replace('##', '').replace('*', '').replace('#', '')
    text = text.replace('‑', '-').replace('–', '-').replace('—', '-').replace('•', '-')
    text = text.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
    text = text.replace('&quot;', '"').replace('&amp;', '&').replace('&amp;amp;', '&')
    return text.encode('ascii', 'ignore').decode('ascii').strip()

def generate_pie_chart(matched_count, missing_count):
    fig, ax = plt.subplots(figsize=(4, 2.5))
    
    # Custom function to show both percentage and value
    def make_autopct(values):
        def my_autopct(pct):
            total = sum(values)
            val = int(round(pct*total/100.0))
            return f'{pct:.1f}%\n({val})'
        return my_autopct

    # Draw the pie chart with autopct
    wedges, texts, autotexts = ax.pie(
        [matched_count, missing_count], 
        colors=['#28a745', '#dc3545'], 
        startangle=90, 
        wedgeprops=dict(width=0.4),
        autopct=make_autopct([matched_count, missing_count]),
        pctdistance=0.8, # Distance of the percentage text from the center
        textprops={'color': 'white', 'weight': 'bold'} # Make text white and bold
    )
    
    # Add legend
    ax.legend(['Matched', 'Missing'], loc="center left", bbox_to_anchor=(1, 0.5), frameon=False)
    ax.axis('equal')
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', transparent=True, bbox_inches='tight', dpi=300)
    buf.seek(0)
    plt.close(fig)
    return buf

def render_markdown_table(pdf, table_lines):
    if not table_lines: return
    rows = []
    for line in table_lines:
        if '---' in line: continue
        cells = [clean_text(c.strip()) for c in line.strip('|').split('|')]
        rows.append(cells)
    if not rows: return

    num_cols = len(rows[0])
    col_width = 190 / num_cols
    
    # Header
    pdf.set_font('Times', 'B', 9)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_text_color(0, 0, 0)
    for cell in rows[0]:
        pdf.cell(col_width, 8, cell, border=1, align='L', fill=True)
    pdf.ln()
    
    # Rows
    pdf.set_font('Times', '', 9)
    for row in rows[1:]:
        while len(row) < num_cols: row.append("")
        
        # Calculate height
        line_counts = [len(pdf.multi_cell(col_width, 5, cell, split_only=True)) for cell in row]
        max_lines = max(line_counts) if line_counts else 1
        row_height = max_lines * 5
        
        # Page break check
        if pdf.get_y() + row_height > 270:
            pdf.add_page()
            pdf.set_font('Times', 'B', 9)
            pdf.set_fill_color(240, 240, 240)
            for cell in rows[0]:
                pdf.cell(col_width, 8, cell, border=1, align='L', fill=True)
            pdf.ln()
            pdf.set_font('Times', '', 9)
            
        x_start, y_start = pdf.get_x(), pdf.get_y()
        for i, cell in enumerate(row):
            pdf.multi_cell(col_width, 5, cell, border=1, align='L')
            pdf.set_xy(x_start + (i + 1) * col_width, y_start)
        pdf.set_xy(x_start, y_start + row_height)
    pdf.ln(8)

def generate_pdf_report(report_text, score, matched_skills, missing_skills):
    pdf = PDFReport()
    pdf.add_page()
    
    # --- 1. SCORE & CHART ---
    pdf.set_y(35)
    pdf.set_font('Times', 'B', 14)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(80, 10, 'Overall Matching Score:', 0, 1)
    pdf.set_font('Times', 'B', 36)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(80, 15, f'{score}%', 0, 1)
    
    matched_count = len(matched_skills.split(',')) if matched_skills else 0
    missing_count = len(missing_skills.split(',')) if missing_skills else 0
    if matched_count > 0 or missing_count > 0:
        chart_img = generate_pie_chart(matched_count, missing_count)
        # Move the chart slightly down to align with the score text
        pdf.image(chart_img, x=90, y=35, w=100) 
    
    pdf.set_y(95)
    
    # --- 2. SKILLS BOXES ---
    pdf.set_fill_color(212, 237, 218)
    pdf.set_text_color(21, 87, 36)
    pdf.set_font('Times', 'B', 12)
    pdf.cell(0, 8, ' Matched Skills:', 0, 1, fill=True)
    pdf.set_font('Times', '', 10)
    pdf.multi_cell(0, 6, clean_text(matched_skills), fill=True)
    pdf.ln(5)
    
    pdf.set_fill_color(248, 215, 218)
    pdf.set_text_color(114, 28, 36)
    pdf.set_font('Times', 'B', 12)
    pdf.cell(0, 8, ' Missing Skills (Gaps):', 0, 1, fill=True)
    pdf.set_font('Times', '', 10)
    pdf.multi_cell(0, 6, clean_text(missing_skills), fill=True)
    pdf.ln(12)
    
    # --- 3. REPORT PARSER ---
    pdf.set_text_color(0, 0, 0)
    report_text = re.sub(r'<table.*?</table>', '', report_text, flags=re.DOTALL)
    
    lines = report_text.split('\n')
    current_table = []
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        if line.startswith('|') and line.endswith('|'):
            current_table.append(line)
        else:
            if current_table:
                render_markdown_table(pdf, current_table)
                current_table = []
            
            clean_line = clean_text(line)
            if not clean_line: continue
                
            # Section Headers
            if clean_line.startswith('###'):
                header_text = clean_line.replace('###', '').strip()
                pdf.set_font('Times', 'B', 14)
                pdf.set_text_color(0, 102, 204)
                pdf.ln(6)
                pdf.cell(0, 10, header_text, 0, 1)
                pdf.ln(2)
                pdf.set_text_color(0, 0, 0)
                pdf.set_font('Times', '', 11)
                
            # Bullet points
            elif clean_line.startswith('-'):
                pdf.set_font('Times', '', 11)
                pdf.multi_cell(0, 6, f"* {clean_line[1:].strip()}")
                pdf.ln(2)
                
            # Normal text
            else:
                pdf.set_font('Times', '', 11)
                pdf.multi_cell(0, 6, clean_line)
                pdf.ln(3)
                
    if current_table:
        render_markdown_table(pdf, current_table)
    
    return bytes(pdf.output())