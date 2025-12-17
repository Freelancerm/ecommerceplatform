import json
import logging
import asyncio
import redis.asyncio as redis
from ..core.config import settings
from ..core.es_client import es_client


async def inventory_update_consumer():
    """
    Listens for real-time inventory updates via Redis and synchronizes them with Elasticsearch.

    This consumer acts as an event listener on the 'inventory_updates' Redis channel.
    When a message is received, it extracts the availability status and performs
    a partial document update in the Elasticsearch 'products' index. This ensures
    that search results remain consistent with the actual warehouse stock.

    Expected Message Format:
    {
        "product_id": "string",
        "available": boolean,
        "stock": integer (optional)
    }
    """
    if not settings.REDIS_URL:
        logging.warning("Redis URL not configured, skipping consumer start")
        return

    redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("inventory_updates")

    logging.info("Started Redis Inventory Update Consumer...")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])

                # Expected format: {"product_id": "123", "available": true, "stock": 10}
                product_id = data.get("product_id")
                available = data.get("available")

                if product_id and available is not None:
                    logging.info(f"Updating product {product_id} availability to {available}")
                    if es_client.client:
                        try:
                            await es_client.client.update(
                                index="products",
                                id=product_id,
                                body={"doc": {"available": available}}
                            )
                        except Exception as ex:
                            logging.error(f"Failed to update ES for product {product_id}: {ex}")

    except asyncio.CancelledError:
        logging.info("Redis consumer cancelled")
    except Exception as ex:
        logging.error(f"Redis consumer error: {ex}")
    finally:
        await redis_client.close()
