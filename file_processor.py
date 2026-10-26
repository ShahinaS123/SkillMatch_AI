import io
import pytesseract
from PIL import Image
from pypdf import PdfReader

def extract_text_from_file(uploaded_file):
    """Extracts text from PDF, Image, or TXT files."""
    if uploaded_file is None:
        return ""
        
    file_type = uploaded_file.type
    
    # 1. Handle Images (JPG, PNG) using OCR
    if file_type in ["image/jpeg", "image/png"]:
        image = Image.open(uploaded_file)
        # Extract text using Tesseract OCR
        text = pytesseract.image_to_string(image)
        return text
        
    # 2. Handle PDFs
    elif file_type == "application/pdf":
        pdf_reader = PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text
        
    # 3. Handle Text Files
    elif file_type == "text/plain":
        return uploaded_file.read().decode("utf-8")
        
    return "Unsupported file format."