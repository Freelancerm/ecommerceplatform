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
    Retrieves a paginated list of all orders, optionally filtered by status.

    This endpoint is secured and accessible only by administrative users. It constructs
    an asynchronous SQLAlchemy query, allowing filtering based on the OrderStatus enum.

    Arguments:
     skip (int): The number of orders to skip (pagination offset). Defaults to 0.
     limit (int): The maximum number of orders to return. Defaults to 100.
     status (OrderStatus | None): Optional filter to only return orders matching a specific status (e.g., 'SHIPPED').
     db (AsyncSession): The asynchronous database session dependency.
     admin (TokenData): Dependency ensuring the requester has valid administrator credentials.

    Returns:
     List[OrderResponse]: A list of order objects.
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
    Manually updates the status of a specific order.

    This is typically used for administrative overrides or external system synchronization
    (e.g., marking an order as 'SHIPPED' after receiving confirmation from a carrier).

    Arguments:
     order_id (int): The unique identifier of the order to be updated.
     new_status (OrderStatus): The new status to be assigned to the order (must be a valid enum value).
     db (AsyncSession): The asynchronous database session.
     admin (TokenData): Dependency ensuring administrative access.

    Returns:
     OrderResponse: The order object with the newly updated status.

    Raises:
     HTTPException (404): If no order with the given order_id is found in the database.
    """
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = new_status
    await db.commit()
    await db.refresh(order)
    return order
