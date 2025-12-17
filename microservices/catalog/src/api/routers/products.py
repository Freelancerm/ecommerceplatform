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
    Performs a full-text search for products using Elasticsearch with a Redis caching layer.

    This function first checks Redis for a cached version of the specific search query and
    pagination parameters. If a cache miss occurs, it queries Elasticsearch, cleans up
    the document source data to avoid ID duplication, and hydrates the Pydantic models.
    The final result is stored in Redis with a 60-second expiration.

    Arguments:
     q (str): The search query string. Must be at least 2 characters long.
     skip (int): The number of documents to skip for pagination. Defaults to 0.
     limit (int): The maximum number of documents to return. Defaults to 10.

    Returns:
     ProductSearchResponse: A response object containing a list of Product models and the total hit count.
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

        products.append(Product(id=hit["_id"], **product_data))

    response = ProductSearchResponse(hits=products, total=total)

    # Set Cache (TTL 1 min for search results)
    await cache_service.set(cache_key, response.model_dump(), ttl=60)

    return response


@router.get("/{product_id}", response_model=Product)
async def get_product(product_id: str):
    """
   Retrieves a single product detail from Elasticsearch by its document ID.

    This function performs a direct document lookup. If the document is found,
    the metadata ID and source fields are merged to create a Product schema instance.
    If the document does not exist, a 404 error is returned.

    Arguments:
     product_id (str): The unique identifier of the product document in Elasticsearch.

    Returns:
     Product: A hydrated Product schema containing the full document details.

    Raises:
     HTTPException (404): If the result is null or the 'found' flag in the Elasticsearch response is false.
    """
    result = await es_client.get(doc_id=product_id)
    if not result or not result.get("found"):
        raise HTTPException(status_code=404, detail="Product not found")

    source = result["_source"]
    return Product(id=result["_id"], **source)
