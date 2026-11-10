from decimal import Decimal

import pytest

from app.modules.finance import allocate_payouts, validate_ledger_entries
from app.modules.payments import OrderCreateRequest


def test_payout_allocation_uses_whole_naira_and_conserves_pool() -> None:
    allocations = allocate_payouts(
        14_250_000,
        {
            "farmer-a": Decimal("5"),
            "farmer-b": Decimal("3"),
            "farmer-c": Decimal("2"),
        },
    )

    assert allocations == {
        "farmer-a": 7_125_000,
        "farmer-b": 4_275_000,
        "farmer-c": 2_850_000,
    }
    assert sum(allocations.values()) == 14_250_000
    assert all(amount % 100 == 0 for amount in allocations.values())


def test_payout_allocation_ties_are_deterministic() -> None:
    claims = {"farmer-b": Decimal("1"), "farmer-a": Decimal("1")}

    assert allocate_payouts(10_100, claims) == {
        "farmer-b": 5_000,
        "farmer-a": 5_100,
    }


@pytest.mark.parametrize(
    ("amount", "claims"),
    [
        (-100, {"farmer": Decimal("1")}),
        (101, {"farmer": Decimal("1")}),
        (100, {}),
        (100, {"farmer": Decimal("0")}),
    ],
)
def test_payout_allocation_rejects_invalid_inputs(amount: int, claims: dict[str, Decimal]) -> None:
    with pytest.raises(ValueError):
        allocate_payouts(amount, claims)


def test_ledger_requires_equal_positive_debits_and_credits() -> None:
    validate_ledger_entries([("debit", 100), ("credit", 100)])

    with pytest.raises(ValueError, match="balance"):
        validate_ledger_entries([("debit", 100), ("credit", 99)])
    with pytest.raises(ValueError, match="positive"):
        validate_ledger_entries([("debit", 0), ("credit", 0)])


def test_order_request_rejects_duplicate_credit_serials() -> None:
    with pytest.raises(ValueError, match="duplicates"):
        OrderCreateRequest(credit_serials=["EC-1", "EC-1"])
