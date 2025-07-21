import logging
import os
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from utils import convert_docx_to_markdown
from io import BytesIO

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Создаём кнопку
    keyboard = [
        [InlineKeyboardButton("Хочу получить отформатированный текст", callback_data="start_formatting")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Привет! Нажми кнопку, чтобы запустить бота и получить отформатированный текст.",
        reply_markup=reply_markup
    )

# Обработчик нажатия кнопки
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()  # Подтверждаем нажатие кнопки
    
    if query.data == "start_formatting":
        await query.message.reply_text("Бот запускается, пожалуйста, подождите...")
        # Сообщение о готовности будет отправлено после инициализации вебхука в main()

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
            
            # Создаём .txt файл
            output = BytesIO()
            output.write(markdown_text.encode('utf-8'))
            output.seek(0)
            
            await message.reply_document(
                document=InputFile(output, filename='formatted.txt'),
                caption="Вот твой отформатированный текст в .txt файле"
            )
        except Exception as e:
            logger.error(f"Ошибка при обработке документа: {e}")
            await message.reply_text("Произошла ошибка. Попробуйте снова.")
    else:
        await message.reply_text("Отправьте документ в формате .doc или .docx.")

# Обработчик ошибок
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Update {update} вызвал ошибку: {context.error}")

def main() -> None:
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
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_error_handler(error_handler)

    # Запуск вебхука
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=token,
        webhook_url=webhook_url,
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True,
    )

    # Отправка сообщения о готовности всем пользователям, ожидающим ответа
    async def notify_ready():
        if application.bot:
            # Можно хранить chat_id пользователей, нажавших кнопку, в context.bot_data
            # Для простоты отправляем в последний чат, но это можно улучшить
            if hasattr(context, 'bot') and hasattr(context.bot, 'send_message'):
                await application.bot.send_message(
                    chat_id=context.bot_data.get('last_chat_id', None),
                    text="Теперь отправляй мне файл"
                )

    # Запускаем уведомление о готовности после старта вебхука
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(notify_ready())

if __name__ == "__main__":
    main()