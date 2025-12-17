from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import String
import enum
from ..core.database import Base


class OrderStatus(str, enum.Enum):
    """Possible lifecycle states for an order."""
    PENDING = "PENDING"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    CANCELED = "CANCELED"
    FAILED = "FAILED"


class Order(Base):
    """SQLAlchemy model for customer orders."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(index=True, nullable=False)
    status: Mapped[OrderStatus] = mapped_column(String, default=OrderStatus.PENDING)
    items: Mapped[dict] = mapped_column(JSONB, nullable=False, default={})
    total_amount: Mapped[float] = mapped_column(default=0.0)
