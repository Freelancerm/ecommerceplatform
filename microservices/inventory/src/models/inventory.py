from sqlalchemy.orm import Mapped, mapped_column
from ..core.database import Base


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    product_id: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    stock: Mapped[int] = mapped_column(default=0, nullable=False)
    version: Mapped[int] = mapped_column(default=1, nullable=False)
