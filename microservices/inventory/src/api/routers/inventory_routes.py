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
    if not settings.REDIS_URL:
        return None
    return redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)


@router.post("/", response_model=InventoryResponse)
async def create_inventory_item(item: InventoryCreate, db: AsyncSession = Depends(get_db)):
    """
    Create initial stock for a product
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
    Reserve stock (ACID + Optimistic Locking).
    Decrements stock only if stock >= qty and version matches
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
        event = {
            "product_id": request.product_id,
            "stock": (item.stock - request.quantity) > 0
        }
        await redis_client.publish("inventory_updates", json.dumps(event))
        await redis_client.close()

    return {"status": "reserved", "product_id": request.product_id}


@router.post("/release")
async def release_stock(request: InventoryRelease, db: AsyncSession = Depends(get_db)):
    """
    Release Stock(Compensating Transaction)
    Adds stock back.
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
