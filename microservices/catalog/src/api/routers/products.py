from fastapi import APIRouter, HTTPException, Query
from ...schemas.product import Product, ProductSearchResponse
from ...core.es_client import es_client
from ...services.cache import cache_service

router = APIRouter()


@router.get("/search", response_model=ProductSearchResponse)
async def search_products(
        q: str = Query(..., min_length=2),
        skip: int = 0,
        limit: int = 10
):
    """
    Full-text search for products using Elasticsearch with Redis Caching.
    """
    cache_key = f"search:{q}:{skip}:{limit}"

    # Try Cache
    cached_data = await cache_service.get(cache_key)
    if cached_data:
        return ProductSearchResponse(**cached_data)

    # Search ES
    result = await es_client.search(query=q, skip=skip, limit=limit)

    hits_data = result.get("hits", {})
    total = hits_data.get("total", {}).get("value", 0)
    hits = hits_data.get("hits", [])

    products = []
    for hit in hits:
        source = hit["_source"]
        product_data = source.copy()
        if "id" in product_data:
            del product_data["id"]
            # -----------------

        # Тепер id передається тільки один раз: явно, через hit["_id"]
        products.append(Product(id=hit["_id"], **product_data))

    response = ProductSearchResponse(hits=products, total=total)

    # Set Cache (TTL 1 min for search results)
    await cache_service.set(cache_key, response.model_dump(), ttl=60)

    return response


router.get("/{product_id}", response_model=Product)


async def get_product(product_id: str):
    """
    Get single product by ID from Elasticsearch.
    """
    result = await es_client.get(doc_id=product_id)
    if not result or not result.get("found"):
        raise HTTPException(status_code=404, detail="Product not found")

    source = result("_source")
    return Product(id=result["_id"], **source)
