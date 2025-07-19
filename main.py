import logging
import os
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from utils import convert_docx_to_markdown

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Отправь мне документ Word, и я верну его в формате Markdown."
    )

# Обработчик документов
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    document = message.document

    if document.mime_type in [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ]:
        try:
            file = await context.bot.get_file(document.file_id)
            file_bytes = await file.download_as_bytearray()
            markdown_text = convert_docx_to_markdown(file_bytes)
            await message.reply_text(markdown_text, parse_mode="MarkdownV2")
        except Exception as e:
            logger.error(f"Ошибка при обработке документа: {e}")
            await message.reply_text("Произошла ошибка. Попробуйте снова.")
    else:
        await message.reply_text("Отправьте документ в формате .doc или .docx.")

# Обработчик ошибок
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Update {update} вызвал ошибку: {context.error}")

async def main() -> None:
    # Получение переменных окружения
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN не установлен")
        raise ValueError("TELEGRAM_TOKEN не установлен")

    webhook_url = os.getenv("WEBHOOK_URL")
    if not webhook_url:
        logger.error("WEBHOOK_URL не установлен")
        raise ValueError("WEBHOOK_URL не установлен")

    port = int(os.getenv("PORT", 10000))

    # Создание приложения
    application = (
        Application.builder()
        .token(token)
        .build()
    )

    # Добавление обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_error_handler(error_handler)

    # Установка вебхука
    await application.bot.set_webhook(
        url=webhook_url,
        allowed_updates=["message"],
        drop_pending_updates=True,
    )
    logger.info(f"Вебхук установлен на {webhook_url}")

    # Запуск вебхука
    await application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=token,
        webhook_url=webhook_url,
    )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())