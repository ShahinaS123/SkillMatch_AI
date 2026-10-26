import csv
import os
from datetime import datetime

def save_result_to_csv(jd_text, cv_text, score, matched, missing):
    file_exists = os.path.isfile('research_data.csv')
    
    with open('research_data.csv', mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        
        # Write headers if file is new
        if not file_exists:
            writer.writerow(['Timestamp', 'Job Description', 'CV Text', 'Match Score', 'Matched Skills', 'Missing Skills'])
            
        # Write the data
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            jd_text[:500],  # Only save first 500 chars to keep file clean
            cv_text[:500],
            score,
            "; ".join(matched),
            "; ".join(missing)
        ])