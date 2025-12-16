import asyncio
from elasticsearch import AsyncElasticsearch

ES_URL = "http://elasticsearch:9200"


async def seed_data():
    # Increase timeout and max retries
    es = AsyncElasticsearch(
        hosts=ES_URL,
        verify_certs=False,
        request_timeout=30,
        retry_on_timeout=True,
        max_retries=3
    )

    print("Waiting for Elasticsearch to be ready...")
    for _ in range(60):
        try:
            if await es.ping():
                print("Elasticsearch is ready.")
                break
        except Exception as e:
            print(f"Waiting for ES... {e}")
        await asyncio.sleep(1)
    else:
        print("Elasticsearch failed to become ready.")
        await es.close()
        return

    # DEV ONLY: Disable disk allocation thresholds to prevent read-only mode on low disk space
    try:
        print("Disabling disk allocation thresholds...")
        await es.cluster.put_settings(body={
            "transient": {
                "cluster.routing.allocation.disk.threshold_enabled": "false"
            }
        })
        # Unlock all indices in case they are already read-only
        await es.indices.put_settings(body={
            "index.blocks.read_only_allow_delete": None
        }, index="_all")
    except Exception as e:
        print(f"Warning: Could not update cluster settings: {e}")

    print("Creating index...")
    if not await es.indices.exists(index="products"):
        try:
            await es.indices.create(index="products")
        except Exception as e:
            print(f"Index creation failed (might already exist): {e}")

    products = [
        {"id": "1", "title": "iPhone 15 Pro", "description": "Apple smartphone", "price": 999.0, "available": True},
        {"id": "2", "title": "Samsung Galaxy S24", "description": "Android flagship", "price": 899.0,
         "available": True},
        {"id": "3", "title": "MacBook Pro", "description": "M3 Chip Laptop", "price": 1999.0, "available": True},
        {"id": "4", "title": "Sony WH-1000XM5", "description": "Noise cancelling headphones", "price": 349.0,
         "available": True},
        {"id": "5", "title": "Dyson Vacuum", "description": "Powerful cleaning", "price": 499.0, "available": False},
    ]

    print("Indexing products...")
    for p in products:
        await es.index(index="products", id=p["id"], document=p)
        print(f"Indexed {p['title']}")

    await es.close()
    print("Done!")


if __name__ == "__main__":
    asyncio.run(seed_data())
