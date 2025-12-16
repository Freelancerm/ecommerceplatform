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
    Admin: List all inventory items.
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
    Admin: Manually set/create stock for an item (Correction).
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
