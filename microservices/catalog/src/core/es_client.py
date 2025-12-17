import asyncio
import logging
from elasticsearch import AsyncElasticsearch, ConnectionError
from ..core.config import settings

logger = logging.getLogger(__name__)


class ESClient:
    def __init__(self):
        self.client: AsyncElasticsearch | None = None

    async def connect(self, retries: int = 5, delay: float = 2.0):
        """
        Initializes the Elasticsearch client and attempts to ping the server.

        This method implements a basic retry mechanism. This is particularly useful
        in Docker environments where the application might start before the
        Elasticsearch container is ready to accept connections.

        Arguments:
         retries (int): Total number of connection attempts. Defaults to 5.
         delay (float): Time in seconds to wait between attempts. Defaults to 2.0.

        Returns:
         None: The method modifies the internal self.client state.

        Raises:
         Exception: If the connection cannot be established after the specified
         number of retries.
        """
        if not settings.ELASTICSEARCH_URL:
            logger.warning("ELASTICSEARCH_URL not set; skipping ES client init")
            return

        for attempt in range(1, retries + 1):
            try:
                self.client = AsyncElasticsearch(
                    hosts=settings.ELASTICSEARCH_URL,
                    verify_certs=False,  # Dev mode
                )
                await self.client.ping()
                return
            except Exception as exc:
                logger.warning(f"ES connection attempt {attempt} failed: {exc}")
                if attempt == retries:
                    raise
                await asyncio.sleep(delay)

    async def close(self):
        if self.client:
            await self.client.close()

    async def create_index(self):
        if not self.client:
            return

        exists = await self.client.indices.exists(index="products")
        if not exists:
            # Define mapping
            mapping = {
                "mappings": {
                    "properties": {
                        "title": {"type": "text"},
                        "description": {"type": "text"},
                        "price": {"type": "float"},
                        "available": {"type": "boolean"},
                    }
                }
            }
            await self.client.indices.create(index="products", body=mapping)

    async def search(self, query: str, skip: int = 0, limit: int = 10):
        """
        Executes a boolean full-text search across product titles and descriptions.

        The search logic uses a 'should' clause (acting as an OR) to match keywords
        in either field. It also applies a hard 'filter' to ensure only available
        products are returned, which improves performance as filters are cacheable.

        Arguments:
         query (str): The text string to search for.
         skip (int): Offset for pagination (starting point).
         limit (int): The number of results to return per page.

        Returns:
         dict: The raw Elasticsearch response containing hits and total metadata.

        """
        if not self.client:
            return {"hits": {"hits": [], "total": {"value": 0}}}

        should_clauses = [
            {"match": {"title": query}},
            {"match": {"description": query}},
        ]

        body = {
            "from": skip,
            "size": limit,
            "query": {
                "bool": {
                    "should": should_clauses,
                    "minimum_should_match": 1,
                    "filter": [
                        {"term": {"available": True}},
                    ]
                }
            }
        }
        return await self.client.search(index="products", body=body)

    async def get(self, doc_id: str):
        if not self.client:
            return None
        try:
            return await self.client.get(index="products", id=doc_id)
        except Exception as ex:
            return f"Failed to get doc {doc_id}: {ex}, error: {ex}"


es_client = ESClient()
