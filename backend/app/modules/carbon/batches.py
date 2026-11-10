from decimal import Decimal, ROUND_DOWN
from typing import Sequence


QUANTUM = Decimal("0.0001")


def allocate_batch_units(
    claims: Sequence[tuple[str, Decimal]],
    units: int,
) -> dict[str, Decimal]:
    if units < 0:
        raise ValueError("units must be non-negative.")
    if not claims:
        if units:
            raise ValueError("Cannot allocate units without claims.")
        return {}
    if len({claim_id for claim_id, _ in claims}) != len(claims):
        raise ValueError("Claim identifiers must be unique.")
    if any(claim <= 0 or claim != claim.quantize(QUANTUM) for _, claim in claims):
        raise ValueError("Claims must be positive and quantized to four decimal places.")

    total = sum((claim for _, claim in claims), Decimal(0))
    target = Decimal(units)
    if target > total:
        raise ValueError("Allocated units cannot exceed claimed tonnes.")
    if not units:
        return {claim_id: Decimal("0.0000") for claim_id, _ in claims}

    shares: dict[str, Decimal] = {}
    remainders: list[tuple[Decimal, str, Decimal]] = []
    for claim_id, claim in claims:
        exact = claim * target / total
        share = exact.quantize(QUANTUM, rounding=ROUND_DOWN)
        shares[claim_id] = share
        remainders.append((exact - share, claim_id, claim))

    remaining = int((target - sum(shares.values(), Decimal(0))) / QUANTUM)
    remainders.sort(key=lambda item: (-item[0], item[1]))
    while remaining:
        progressed = False
        for _, claim_id, claim in remainders:
            if shares[claim_id] + QUANTUM <= claim:
                shares[claim_id] += QUANTUM
                remaining -= 1
                progressed = True
                if remaining == 0:
                    break
        if not progressed:
            raise ValueError("Unable to allocate all units without exceeding a claim.")
    return shares
