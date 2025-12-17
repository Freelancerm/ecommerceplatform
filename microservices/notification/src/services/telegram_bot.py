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
    Handles a message containing the user's shared contact information.

    This function is the critical piece of the 2FA setup flow:
    1. It extracts the phone number and the unique Telegram chat_id.
    2. It normalizes the phone number (ensuring the leading '+' is present).
    3. It calls an internal API endpoint on the Auth Service to bind the phone
       number (user ID) with the chat_id for OTP delivery.

    Arguments:
     message (Message): The incoming Aiogram message object which contains
      the contact data in the `message.contact` field.

    Returns:
     None: Sends an answer message back to the user confirming the success or failure
      of the linking process.

    External Calls:
     POST to {settings.AUTH_SERVICE_URL}/internal/users/bind-telegram
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
    """
    Handles the standard '/start' command.

    It sends a welcoming message and presents a specialized reply keyboard
    button that prompts the user to share their contact information.

    Arguments:
     message (Message): The incoming Aiogram message object.

    Returns:
     None: Sends the welcome message and the contact sharing keyboard back to the user.
    """
    kb = [
        [KeyboardButton(text="Share Contact", request_contact=True)]
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=True)
    await message.answer("Welcome! Please share your contact to enable 2FA login.", reply_markup=keyboard)


async def send_telegram_message(chat_id: int, text: str):
    """
    A utility function to send a text message to a specific Telegram chat ID.

    This function wraps the Bot's send_message method, providing error handling
    and a check for the bot's initialization status. It is used by external services
    (like the notification consumer) to deliver one-time codes and receipts.

    Arguments:
     chat_id (int): The target Telegram chat identifier (unique per user).
     text (str): The message content to be sent.

    Returns:
     None: Logs a warning if the bot token is not set, or logs an error if the
      message delivery fails (e.g., user blocked the bot).
    """
    if bot:
        try:
            await bot.send_message(chat_id=chat_id, text=text)
        except Exception as ex:
            logging.error(f"Failed to send telegram message: {ex}")
    else:
        logging.warning("Telegram Bot Token not set. Message not sent.")
