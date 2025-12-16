from elasticsearch import AsyncElasticsearch
from ..core.config import settings


class ESClient:
    def __init__(self):
        self.client: AsyncElasticsearch | None = None

    def connect(self):
        if settings.ELASTICSEARCH_URL:
            self.client = AsyncElasticsearch(
                hosts=settings.ELASTICSEARCH_URL,
                verify_certs=False  # Dev mode
            )

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
