import docx

def extract_text_from_docx(file_path):
    doc = docx.Document(file_path)   
    text = ""

    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    
    return text