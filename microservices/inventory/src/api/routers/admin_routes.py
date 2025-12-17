from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ...core.database import get_db
from ...models.inventory import InventoryItem
from ...schemas.inventory import InventoryResponse, InventoryCreate
from jwt_core_lib.dependencies import get_current_admin, TokenData
from typing import List

router = APIRouter()


@router.get("/", response_model=List[InventoryResponse])
async def list_inventory(
        skip: int = 0,
        limit: int = 100,
        db: AsyncSession = Depends(get_db),
        admin: TokenData = Depends(get_current_admin),
):
    """
    Retrieves a paginated list of all inventory items from the database.

    This endpoint is restricted to administrative users. It performs an
    asynchronous select query on the InventoryItem model, supporting
    standard pagination via skip and limit parameters.

    Arguments:
     skip (int): The number of records to skip for pagination. Defaults to 0.
     limit (int): The maximum number of records to return. Defaults to 100.
     db (AsyncSession): The asynchronous database session provided by dependency injection.
     admin (TokenData): Injected dependency that validates the requester has admin privileges.

    Returns:
     List[InventoryResponse]: A list of inventory objects containing product IDs and stock levels.
    """
    stmt = select(InventoryItem).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/correction", response_model=InventoryResponse)
async def correct_inventory(
        item_in: InventoryCreate,
        db: AsyncSession = Depends(get_db),
        admin: TokenData = Depends(get_current_admin)
):
    """
    Performs a manual stock correction or initializes a new inventory record.

    This function implements an 'upsert' logic:
    1. It searches for an existing inventory record by product_id.
    2. If found, it updates the stock level and increments the version number
       to assist with optimistic locking or cache invalidation.
    3. If not found, it creates and persists a new InventoryItem record.

    Arguments:
     item_in (InventoryCreate): Payload containing the product_id and the new stock count.
     db (AsyncSession): The asynchronous database session.
     admin (TokenData): Validated admin token data.

    Returns:
     InventoryResponse: The updated or newly created inventory record.
    """
    stmt = select(InventoryItem).where(InventoryItem.product_id == item_in.product_id)
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if item:
        item.stock = item_in.stock
        item.version += 1  # Force version bump
    else:
        item = InventoryItem(product_id=item_in.product_id, stock=item_in.stock)
        db.add(item)

    await db.commit()
    await db.refresh(item)
    return item
