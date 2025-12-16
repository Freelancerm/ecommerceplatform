from pydantic import BaseModel


class ProductBase(BaseModel):
    title: str
    description: str | None = None
    price: float
    available: bool = True


class ProductCreate(ProductBase):
    pass


class Product(ProductBase):
    id: str


class ProductSearchResponse(BaseModel):
    hits: list[Product]
    total: int
