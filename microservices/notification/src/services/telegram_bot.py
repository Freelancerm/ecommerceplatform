import logging
import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from ..core.config import settings

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()


@dp.message(F.contact)
async def handle_contact(message: Message):
    """
    Handles 'Share Contact' message.
    Extracts phone and chat_id, then calls Auth Service to bind them.
    """
    contact = message.contact
    phone = contact.phone_number
    chat_id = message.chat.id

    # Normalize phone: ensure it starts with + if missing (Telegram might send without)
    if not phone.startswith('+'):
        phone = f"+{phone}"

    logging.info(f"Recieved contact: {phone} for chat_id {chat_id}")

    # Call Auth Service Internal API
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.AUTH_SERVICE_URL}/internal/users/bind-telegram",
                json={"phone_number": phone, "chat_id": chat_id},
            )
            response.raise_for_status()
            await message.answer(f"Phone: {phone} successfully linked! You can now request OTP on the website")
        except Exception as ex:
            logging.error(f"Failed to bind telegram user: {ex}")
            await message.answer(f"Failed to link account. Please try again later.")


@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    kb = [
        [KeyboardButton(text="Share Contact", request_contact=True)]
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=True)
    await message.answer("Welcome! Please share your contact to enable 2FA login.", reply_markup=keyboard)


async def send_telegram_message(chat_id: int, text: str):
    if bot:
        try:
            await bot.send_message(chat_id=chat_id, text=text)
        except Exception as ex:
            logging.error(f"Failed to send telegram message: {ex}")
    else:
        logging.warning("Telegram Bot Token not set. Message not sent.")
