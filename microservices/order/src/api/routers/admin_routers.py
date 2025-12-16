from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ...core.database import get_db
from ...models.order import Order, OrderStatus
from ...schemas.order import OrderResponse
from jwt_core_lib.dependencies import get_current_admin, TokenData
from typing import List

router = APIRouter()


@router.get("/", response_model=List[OrderResponse])
async def list_orders(
        skip: int = 0,
        limit: int = 100,
        status: OrderStatus | None = None,
        db: AsyncSession = Depends(get_db),
        admin: TokenData = Depends(get_current_admin)
):
    """
    Admin: List all orders.
    """
    query = select(Order).offset(skip).limit(limit)
    if status:
        query = query.where(Order.status == status)

    result = await db.execute(query)
    return result.scalars().all()


@router.put("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
        order_id: int,
        new_status: OrderStatus,
        db: AsyncSession = Depends(get_db),
        admin: TokenData = Depends(get_current_admin),
):
    """
    Admin: Force update order status (e.g. SHIPPED).
    """
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = new_status
    await db.commit()
    await db.refresh(order)
    return order
