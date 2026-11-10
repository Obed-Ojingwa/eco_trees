from collections.abc import Mapping, Sequence
from decimal import Decimal


def validate_ledger_entries(entries: Sequence[tuple[str, int]]) -> None:
    if not entries:
        raise ValueError("A ledger transaction must contain entries.")
    if any(side not in {"debit", "credit"} or amount <= 0 for side, amount in entries):
        raise ValueError("Ledger entries require a valid side and a positive amount.")
    debits = sum(amount for side, amount in entries if side == "debit")
    credits = sum(amount for side, amount in entries if side == "credit")
    if debits != credits:
        raise ValueError("Ledger debits and credits must balance.")


def allocate_payouts(pool_kobo: int, claims: Mapping[str, Decimal]) -> dict[str, int]:
    if pool_kobo < 0 or pool_kobo % 100:
        raise ValueError("The payout pool must be a non-negative whole-naira amount.")
    if not claims or any(not farmer_id or claim <= 0 for farmer_id, claim in claims.items()):
        raise ValueError("Payout claims must contain positive amounts for identified farmers.")
    pool_naira = pool_kobo // 100
    total_claim = sum(claims.values(), Decimal(0))
    shares: dict[str, int] = {}
    remainders: list[tuple[Decimal, str]] = []
    for farmer_id, claim in claims.items():
        exact = Decimal(pool_naira) * claim / total_claim
        whole_naira = int(exact)
        shares[farmer_id] = whole_naira * 100
        remainders.append((exact - whole_naira, farmer_id))
    remaining_naira = pool_naira - sum(shares.values()) // 100
    remainders.sort(key=lambda item: (-item[0], item[1]))
    for _, farmer_id in remainders[:remaining_naira]:
        shares[farmer_id] += 100
    return shares
