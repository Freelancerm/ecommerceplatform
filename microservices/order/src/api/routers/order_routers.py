from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ...core.database import get_db
from ...models.order import Order, OrderStatus
from ...schemas.order import OrderCreate, OrderResponse
from ...services.saga import SagaOrchestrator
from jwt_core_lib.dependencies import get_current_user, TokenData
import redis.asyncio as redis
import json
from ...core.config import settings

router = APIRouter()


@router.post("/", response_model=OrderResponse)
async def create_order(
        order_in: OrderCreate,
        db: AsyncSession = Depends(get_db),
        user: TokenData = Depends(get_current_user),
):
    """
    Creates an initial order record in the database and initiates the execution of a Saga.

    The function follows these critical steps:
    1. Local Transaction: A new Order record is created in the local database with a PENDING status.
    2. Saga Execution: The SagaOrchestrator takes over, coordinating distributed transactions
       (e.g., reserving inventory, processing payment).
    3. Failure Handling: The Saga handles its own rollback. If the Saga fails, the Order
       status is updated (e.g., to FAILED) before being returned.
    4. Notification: Upon successful completion of the Saga, an event is published to Redis
       to notify admins and confirm the order with the user.

    Arguments:
     order_in (OrderCreate): The desired items and simulation flags for the new order.
     db (AsyncSession): The asynchronous database session for local transaction management.
     user (TokenData): Injected dependency containing the authenticated user's details (phone).

    Returns:
     OrderResponse: The final order object, which will have a status of FAILED or COMPLETED
      after the Saga execution.

    Side Effects:
     Starts a distributed transaction via SagaOrchestrator.
     Publishes a 'new_order' event to the Redis 'notifications' channel upon success.
    """
    # Create Local Order (Pending)
    # Convert Pydantic items to dict list for JSON storage
    items_json = [item.model_dump() for item in order_in.items]

    order = Order(
        user_id=user.phone,
        status=OrderStatus.PENDING,
        items=items_json,
        total_amount=0.0
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)

    # Run Saga
    saga = SagaOrchestrator(db, order)
    try:
        await saga.execute(simulate_failure=order_in.simulate_failure)

        # Publish new order event for admins
        if settings.REDIS_URL:
            redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
            event = {
                "type": "new_order",
                "order_id": order.id,
                "user_id": order.user_id,
                "amount": order.total_amount
            }
            await redis_client.publish("notifications", json.dumps(event))
            await redis_client.close()

    except Exception as ex:
        # Saga has already handled rollback and status update
        await db.refresh(order)
        return order

    await db.refresh(order)
    return order
