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

# Функция для отправки сообщения с кнопкой
async def send_button_message(chat_id, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("Хочу получить отформатированный текст", callback_data="start_formatting")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=chat_id,
        text="Нажми кнопку, чтобы получить ещё один отформатированный текст.",
        reply_markup=reply_markup
    )

# Обработчик нажатия кнопки
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()  # Подтверждаем нажатие кнопки
    
    if query.data == "start_formatting":
        chat_id = query.message.chat_id
        await query.message.reply_text("Бот запускается, пожалуйста, подождите...")
        
        # Сохраняем chat_id для отправки уведомления о готовности
        context.bot_data['last_chat_id'] = chat_id
        
        # Проверяем, что job_queue доступен
        if context.job_queue is None:
            logger.error("JobQueue не инициализирован")
            await context.bot.send_message(
                chat_id=chat_id,
                text="Произошла ошибка при запуске. Пожалуйста, попробуйте снова через минуту."
            )
            return
            
        # Планируем отправку сообщения "Теперь отправляй мне файл" через 50 секунд
        context.job_queue.run_once(
            callback=send_ready_message,
            when=50,
            data={'chat_id': chat_id},
            name=f"ready_{chat_id}"
        )

# Функция для отправки сообщения о готовности
async def send_ready_message(context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = context.job.data['chat_id']
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Теперь отправляй мне файл"
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения о готовности: {e}")

# Обработчик документов
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    document = message.document
    chat_id = message.chat_id

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
            
            # Отправляем сообщение с кнопкой после успешной отправки файла
            await send_button_message(chat_id, context)
            
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

    # Создание приложения с включённым JobQueue
    application = (
        Application.builder()
        .token(token)
        .job_queue(True)  # Включаем JobQueue
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

if __name__ == "__main__":
    main()