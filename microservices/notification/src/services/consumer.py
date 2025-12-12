import json
import logging
import asyncio
import redis.asyncio as redis
from ..core.config import settings
from ..services.telegram_bot import send_telegram_message
from ..webosckets.manager import manager
from ..core.redis_client import redis_client


async def notification_consumer():
    """
    Connects to Redis Pub/Sub and listens for notifications.
    """
    red = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    pubsub = red.pubsub()
    await pubsub.subscribe("notifications")

    logging.info("Started Redis Notifications Consumer")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                msg_type = data.get("type")

                # OTP Telegram
                if msg_type == "otp_send":
                    phone = data.get("phone")  # Отримуємо номер телефону
                    if not phone:
                        logging.error("OTP event received without phone number.")
                        return

                    chat_id = await redis_client.get_chat_id(phone)

                    if not chat_id:
                        logging.warning(f"Could not find chat_id for phone {phone}. User did not share contact.")
                        return

                    code = data.get("otp_code")
                    text = f"Your login code is {code}"
                    logging.info(f"Processing OTP for chat_id {chat_id}")
                    await send_telegram_message(int(chat_id), text)

                # New Order (Admin broadcast + User Receipt)
                elif msg_type == "new_order":
                    order_id = data.get("order_id")
                    user_id = data.get("user_id")  # Phone number
                    text = f"New order created! ID: {order_id}"

                    # Admin WS
                    logging.info(f"Broadcasting new order {order_id}")
                    await manager.broadcast_admin(text)

                    # User Telegram Receipt
                    if user_id:
                        chat_id = await redis_client.get_chat_id(user_id)
                        if chat_id:
                            receipt_text = f"✅ Order #{order_id} Confirmed!\nAmount: {data.get('amount')}"
                            await send_telegram_message(int(chat_id), receipt_text)

                    # Order Update (User Notification)
                    elif msg_type == "order_update":
                        user_id = data.get("user_id")
                        status = data.get("status")
                        text = f"Your order is now {status}"
                        logging.info(f"Notifying user {user_id}: {status}")
                        await manager.send_personal_message(text, user_id)

    except asyncio.CancelledError:
        logging.info("Redis consumer cancelled")
    except Exception as ex:
        logging.error(f"Redis consumer error: {ex}")
    finally:
        await red.close()
