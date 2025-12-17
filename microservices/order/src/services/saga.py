import httpx
import logging
import asyncio
import time
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.order import Order, OrderStatus
from ..core.config import settings

INVENTORY_SERVICE_URL = settings.INVENTORY_SERVICE_URL
PAYMENT_SERVICE_URL = settings.PAYMENT_SERVICE_URL

logger = logging.getLogger(__name__)


class CircuitBreakerOpen(Exception):
    """Raised when a circuit breaker is open and rejects calls."""


class AsyncCircuitBreaker:
    """
    Implements a minimal, thread-safe asynchronous Circuit Breaker pattern.

    It tracks consecutive failures for a wrapped coroutine. Once the failure count
    exceeds `max_failures`, the circuit opens, immediately rejecting new calls
    until `reset_timeout` has elapsed.

    Arguments:
     max_failures (int): The number of consecutive exceptions required to switch
      the state from CLOSED to OPEN. Defaults to 3.
     reset_timeout (float): The duration in seconds the circuit remains OPEN
      before transitioning to HALF_OPEN to attempt a probe call. Defaults to 30.0.
    """

    def __init__(self, max_failures: int = 3, reset_timeout: float = 30.0):
        self.max_failures = max_failures
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.state = "CLOSED"
        self._lock = asyncio.Lock()

    async def call(self, func, *args, **kwargs):
        """
        Execute a coroutine under circuit breaker protection.

        Returns:
            The awaited result of `func`.
        Raises:
            CircuitBreakerOpen: if the circuit is open and timeout has not elapsed.
            Exception: any exception raised by the wrapped coroutine.
        """
        async with self._lock:
            if self.state == "OPEN":
                if self.last_failure_time and (time.time() - self.last_failure_time) >= self.reset_timeout:
                    self.state = "HALF_OPEN"
                else:
                    raise CircuitBreakerOpen("Circuit breaker is open")

        try:
            result = await func(*args, **kwargs)
        except Exception:
            async with self._lock:
                self.failure_count += 1
                self.last_failure_time = time.time()
                if self.failure_count >= self.max_failures:
                    self.state = "OPEN"
            raise

        async with self._lock:
            self.state = "CLOSED"
            self.failure_count = 0
            self.last_failure_time = None
        return result


class SagaOrchestrator:
    def __init__(self, db: AsyncSession, order: Order):
        """
        Coordinates the order creation saga across inventory and payment services.

        Args:
            db: Async SQLAlchemy session for persisting order updates.
            order: Order entity to transition through the saga.
        """
        self.db = db
        self.order = order
        self.reserved_items = []
        self.inventory_breaker = AsyncCircuitBreaker()
        self.payment_breaker = AsyncCircuitBreaker()

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
            await self._process_payment(simulate_failure)

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
        We assume Service B supports single item reserve, so we loop.
        If any fails, we catch triggers rollback for ALREADY reserved items.

        Service C calls Service B for each item.
        We track reserved items to rollback only them.
        """
        async with httpx.AsyncClient() as client:
            for item in self.order.items:
                pid = item["product_id"]
                qty = item["quantity"]

                async def reserve():
                    response = await client.post(
                        f"{INVENTORY_SERVICE_URL}/reserve",
                        json={"product_id": pid, "quantity": qty},
                    )
                    if response.status_code != 200:
                        raise Exception(f"Failed to reserve stock for {pid}: {response.text}")
                    return response

                await self.inventory_breaker.call(reserve)
                self.reserved_items.append({"product_id": pid, "quantity": qty})
                logger.info(f"Reserved {qty} of {pid}")

    async def _process_payment(self, simulate_failure: bool):
        """
        Mock payment processing with a circuit breaker guard.

        Args:
            simulate_failure: When True, forces a payment rejection for testing.
        """

        async def _mock_payment():
            await asyncio.sleep(0.5)  # Simulate latency
            if simulate_failure:
                raise Exception("Payment rejected")
            return True

        await self.payment_breaker.call(_mock_payment)
        logger.info("Payment Successful")

    async def _rollback(self, reason: str):
        """
        Compensating Transactions.
        1. Release Stock (for items successfully reserved).
        2. Set Order to CANCELED/FAILED.

        Args:
            reason: Human readable explanation of why rollback executed.
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
