# order_service/app/tests/test_webhook_idempotency.py
"""
Unit tests for payment confirmation idempotency.

Replaying the same Chapa tx_ref must not republish order.paid, otherwise
the product consumer would double-decrement stock.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.use_cases.manage_orders import OrderUseCases


def _make_order(*, status: str, tx_ref: str = "chapa-tx-abc123"):
    item = SimpleNamespace(product_id=1, quantity=2)
    return SimpleNamespace(
        id=42,
        status=status,
        tx_ref=tx_ref,
        items=[item],
    )


@pytest.mark.asyncio
async def test_confirm_payment_publishes_once_for_pending_order():
    order = _make_order(status="PENDING")
    paid = _make_order(status="PAID")

    repo = MagicMock()
    repo.get_by_tx_ref = AsyncMock(return_value=order)
    repo.update_status = AsyncMock(return_value=paid)

    publisher = MagicMock()
    use_cases = OrderUseCases(
        order_repo=repo,
        product_client=MagicMock(),
        chapa_client=MagicMock(),
        publisher=publisher,
    )

    result = await use_cases.confirm_payment("chapa-tx-abc123")

    assert result.status == "PAID"
    repo.update_status.assert_awaited_once_with(42, "PAID")
    publisher.publish_event.assert_called_once()
    assert publisher.publish_event.call_args.kwargs["routing_key"] == "order.paid"


@pytest.mark.asyncio
async def test_confirm_payment_skips_republish_when_already_paid():
    already_paid = _make_order(status="PAID")

    repo = MagicMock()
    repo.get_by_tx_ref = AsyncMock(return_value=already_paid)
    repo.update_status = AsyncMock()

    publisher = MagicMock()
    use_cases = OrderUseCases(
        order_repo=repo,
        product_client=MagicMock(),
        chapa_client=MagicMock(),
        publisher=publisher,
    )

    result = await use_cases.confirm_payment("chapa-tx-abc123")

    assert result.status == "PAID"
    repo.update_status.assert_not_awaited()
    publisher.publish_event.assert_not_called()
