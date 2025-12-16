from pydantic import BaseModel


class InventoryBase(BaseModel):
    product_id: str
    stock: int


class InventoryCreate(InventoryBase):
    pass


class InventoryReserve(BaseModel):
    product_id: str
    quantity: int


class InventoryRelease(BaseModel):
    product_id: str
    quantity: int


class InventoryResponse(InventoryBase):
    id: int
    version: int

    class Config:
        from_attributes = True
