import httpx
import logging
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.order import Order, OrderStatus
from ..core.config import settings

INVENTORY_SERVICE_URL = settings.INVENTORY_SERVICE_URL
PAYMENT_SERVICE_URL = settings.PAYMENT_SERVICE_URL

logger = logging.getLogger(__name__)


class SagaOrchestrator:
    def __init__(self, db: AsyncSession, order: Order):
        self.db = db
        self.order = order

    async def execute(self, simulate_failure: bool = False):
        """
        Executes the 'Create Order' Saga.
        Steps:
        1. Reserve Stock (Service B)
        2. Process Payment (Mock)
        3. Confirm Order
        """
        try:
            # Reserve stock
            await self._reserve_stock()

            # Process payment
            await self._proccess_payment(simulate_failure)

            # Success - Update Order to Paid
            self.order.status = OrderStatus.PAID
            await self.db.commit()
            logger.info(f"Saga Completed: Order {self.order.id} PAID")

        except Exception as ex:
            logger.error(f"Saga failed: {ex}. Initiating Rollback")
            await self._rollback(str(ex))
            raise ex

    async def _reserve_stock(self):
        """
        Calls Service B to reserve stock for each item.
        If partially successful, we might need complex rollback,
        but for simple Saga we treat the whole batch reservation as one unit
        (Service B should ideally support batch or we loop).
        For this MVP: We assume Service B supports single item reserve, so we loop.
        If any fails, we catch triggers rollback for ALREADY reserved items.

        To simplify MVP: Service C calls Service B for each item.
        We track reserved items to rollback only them.
        """
        self.reserved_items = []

        async with httpx.AsyncClient() as client:
            for item in self.order.items:
                pid = item["product_id"]
                qty = item["quantity"]

                response = await client.post(
                    f"{INVENTORY_SERVICE_URL}/reserve",
                    json={"product_id": pid, "quantity": qty},
                )

                if response.status_code != 200:
                    raise Exception(f"Failed to reserve stock for {pid}: {response.text}")

                self.reserved_items.append({"product_id": pid, "quantity": qty})
                logger.info(f"Reserved {qty} of {pid}")

        async def _proccess_payment(self, simulate_failure: bool):
            """
            Mock payment processing
            """
            await asyncio.sleep(0.5)  # Simulate latency
            if simulate_failure:
                raise Exception("Payment rejected")
            logger.info("Payment Successful")

        async def _rollback(self, reason: str):
            """
            Compensating Transactions.
            1. Release Stock (for items successfully reserved).
            2. Set Order to CANCELED/FAILED.
            """
            # Release Stock
            async with httpx.AsyncClient() as client:
                for item in getattr(self, "reserved_items", []):
                    pid = item["product_id"]
                    qty = item["quantity"]
                    try:
                        await client.post(
                            f"{INVENTORY_SERVICE_URL}/release",
                            json={"product_id": pid, "quantity": qty},
                        )
                        logger.info(f"Rolled back stock for {pid}")
                    except Exception as ex:
                        logger.error(f"Failed to release stock for {pid}: {ex}")

            # Cancel Order
            self.order.status = OrderStatus.CANCELED  # or Failed
            self.order.items = self.order.items
            await self.db.commit()
            logger.info(f"Order {self.order.id} Canceled. Reason: {reason}")
