import json
import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from ...core.database import get_db
from ...models.inventory import InventoryItem
from ...schemas.inventory import InventoryCreate, InventoryResponse, InventoryRelease, InventoryReserve
from ...core.config import settings

router = APIRouter()


# Redis client for publishing updates
async def get_redis():
    """
    Initializes an asynchronous Redis connection for event broadcasting.

    This helper provides a transient Redis client used to publish stock updates
    to other microservices (like the search or catalog service).

    Returns:
     redis.Redis | None: An active Redis client if REDIS_URL is configured,
      otherwise None.
    """
    if not settings.REDIS_URL:
        return None
    return redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)


@router.post("/", response_model=InventoryResponse)
async def create_inventory_item(item: InventoryCreate, db: AsyncSession = Depends(get_db)):
    """
    Initializes a new stock record for a product.

    Attempts to insert a new InventoryItem into the database. If a record for the
    specified product_id already exists, the database triggers a unique constraint
    violation handled by an IntegrityError.

    Arguments:
     item (InventoryCreate): Schema containing product_id and initial stock count.
     db (AsyncSession): Asynchronous SQLAlchemy database session.

    Returns:
     InventoryResponse: The created inventory object.

    Raises:
     HTTPException (409): If an inventory record for the product already exists.
    """
    db_item = InventoryItem(product_id=item.product_id, stock=item.stock)
    db.add(db_item)
    try:
        await db.commit()
        await db.refresh(db_item)
        return db_item
    except IntegrityError as ex:
        await db.rollback()
        if "duplicate key value violates unique constraint" in str(ex):
            raise HTTPException(
                status_code=409,  # 409 Conflict
                detail=f"Inventory item for product_id='{item.product_id}' already exists. Use the /reserve or /release endpoints to modify stock."
            )
        raise


@router.post("/reserve")
async def reserve_stock(request: InventoryReserve, db: AsyncSession = Depends(get_db)):
    """
    Safely decrements stock for an order using Optimistic Locking.

    This method ensures data integrity under high concurrency:
    1. It fetches the current stock and version of the item.
    2. It executes an update only if the 'version' in the database matches
       the version retrieved in step 1.
    3. If rowcount is 0, it means another process updated the item in the
       interim, triggering a retry requirement.
    4. Upon success, it publishes an 'inventory_updates' event to Redis.

    Arguments:
     request (InventoryReserve): Schema containing product_id and quantity to reserve.
     db (AsyncSession): Asynchronous database session.

    Returns:
     dict: Status message confirming the reservation.

    Raises:
     HTTPException (404): If product is missing or stock is insufficient.
     HTTPException (409): If a concurrent update (race condition) is detected.
    """
    # Fetch current state
    stmt = select(InventoryItem).where(InventoryItem.product_id == request.product_id)
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Product not found in inventory")

    if item.stock < request.quantity:
        raise HTTPException(status_code=404, detail="Insufficient stock")

    update_stmt = (
        update(InventoryItem)
        .where(
            InventoryItem.id == item.id,
            InventoryItem.version == item.version
        )
        .values(
            stock=InventoryItem.stock - request.quantity,
            version=InventoryItem.version + 1
        )
        .execution_options(synchronize_session=False)  # Skip session sync for performance
    )

    result = await db.execute(update_stmt)
    await db.commit()

    # Check if update actually hapenned
    if result.rowcount == 0:
        raise HTTPException(
            status_code=409,
            detail="Concurrent update detected. Please retry."
        )

    # Publish event
    redis_client = await get_redis()
    if redis_client:
        remaining_stock = item.stock - request.quantity
        event = {
            "product_id": request.product_id,
            "available": remaining_stock > 0,
            "stock": remaining_stock
        }
        await redis_client.publish("inventory_updates", json.dumps(event))
        await redis_client.close()

    return {"status": "reserved", "product_id": request.product_id}


@router.post("/release")
async def release_stock(request: InventoryRelease, db: AsyncSession = Depends(get_db)):
    """
    Increments stock back to the inventory (Compensating Transaction).

    Typically called by a Saga orchestrator when a subsequent order step
    (like payment) fails. It adds the quantity back to the stock and
    broadcasts the updated availability to the system.

    Arguments:
     request (InventoryRelease): Schema containing product_id and quantity to return.
     db (AsyncSession): Asynchronous database session.

    Returns:
     dict: Status message confirming the release.

    Raises:
     HTTPException (404): If the product record does not exist in inventory.
    """
    stmt = select(InventoryItem).where(InventoryItem.product_id == request.product_id)
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Product not found in inventory")

    # Increment stock
    item.stock += request.quantity
    item.version += 1

    await db.commit()

    # Publish event

    redis_client = await get_redis()
    if redis_client:
        event = {
            "product_id": request.product_id,
            "stock": item.stock,
            "available": item.stock > 0
        }
        await redis_client.publish("inventory_updates", json.dumps(event))
        await redis_client.close()

    return {"status": "released", "product_id": request.product_id}
