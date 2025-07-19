from docx import Document
from io import BytesIO

def convert_docx_to_markdown(docx_bytes):
    """
    Конвертирует содержимое DOCX файла в Markdown.
    
    Args:
        docx_bytes: Байтовое представление DOCX файла.
        
    Returns:
        str: Текст в формате Markdown.
    """
    doc = Document(BytesIO(docx_bytes))
    markdown = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
            
        # Обработка стилей
        if para.style.name.startswith('Heading'):
            level = int(para.style.name.split()[-1]) if para.style.name.split()[-1].isdigit() else 1
            markdown.append(f"{'#' * level} {text}")
        elif para.runs:
            run = para.runs[0]
            if run.bold:
                markdown.append(f"**{text}**")
            elif run.italic:
                markdown.append(f"_{text}_")
            else:
                markdown.append(text)
        else:
            markdown.append(text)
            
    return "\n\n".join(markdown)