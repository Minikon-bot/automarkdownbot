import re
from io import BytesIO
from docx import Document

# Зарезервированные символы для экранирования
ESCAPE_CHARS = r'.!?)([]%:;-'

def escape_markdown_v2(text):
    """
    Экранирует зарезервированные символы для Telegram MarkdownV2.
    
    Args:
        text: Входной текст.
        
    Returns:
        str: Текст с экранированными символами.
    """
    return re.sub(f'([{re.escape(ESCAPE_CHARS)}])', r'\\\1', text)

def format_run(run):
    """
    Форматирует текст отдельного run в соответствии с правилами MarkdownV2.
    
    Args:
        run: Объект Run из python-docx.
        
    Returns:
        str: Отформатированный текст.
    """
    original_text = run.text
    if not original_text.strip():
        return escape_markdown_v2(original_text)

    leading_spaces = len(original_text) - len(original_text.lstrip())
    trailing_spaces = len(original_text) - len(original_text.rstrip())
    leading = original_text[:leading_spaces]
    trailing = original_text[len(original_text.rstrip()):]
    core = original_text.strip()

    core = escape_markdown_v2(core)

    # Проверка стилей
    try:
        strike = run.font.strike
    except AttributeError:
        strike = False

    # Приоритеты: подчёркнутый + курсив → только подчёркнутый
    if run.underline and run.italic:
        core = f"__{core}__"
    else:
        if run.bold:
            core = f"*{core}*"
        if run.italic:
            core = f"_{core}_"
        if run.underline:
            core = f"__{core}__"
        if strike:
            core = f"~{core}~"

    return f"{leading}{core}{trailing}"

def convert_docx_to_markdown(docx_bytes):
    """
    Конвертирует содержимое DOCX файла в Markdown, совместимый с правилами.
    
    Args:
        docx_bytes: Байтовое представление DOCX файла.
        
    Returns:
        str: Текст в формате Markdown для сохранения в .txt.
    """
    doc = Document(BytesIO(docx_bytes))
    markdown = []

    for para in doc.paragraphs:
        if not para.text.strip():
            continue

        # Обработка стилей параграфа
        if para.style.name.startswith('Code'):
            # Код (оборачиваем в обратные апострофы)
            text = escape_markdown_v2(para.text.strip())
            markdown.append(f"`{text}`")
        elif para.style.name.startswith('Quote'):
            # Спойлер (оборачиваем в ||)
            text = escape_markdown_v2(para.text.strip())
            markdown.append(f"||{text}||")
        else:
            # Обычный параграф с обработкой run-ов
            formatted_text = ''.join(format_run(run) for run in para.runs)
            markdown.append(formatted_text)

    return '\n\n'.join(markdown)