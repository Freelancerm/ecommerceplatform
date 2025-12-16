from pydantic import BaseModel
from typing import List
from ..models.order import OrderStatus


class OrderItem(BaseModel):
    product_id: str
    quantity: int


class OrderCreate(BaseModel):
    items: List[OrderItem]
    simulate_failure: bool = False  # testing Saga rollback


class OrderResponse(BaseModel):
    id: int
    user_id: str
    status: OrderStatus
    items: List[dict]
    total_amount: float

    class Config:
        from_attributes = True
