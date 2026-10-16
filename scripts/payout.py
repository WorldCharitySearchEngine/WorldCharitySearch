#!/usr/bin/env python3
"""Work out each charity's share of a monthly donation.

The donation is split evenly across the five pools, then evenly across the
charities in each pool. If an even split would give charities less than the
minimum gift, this month's share goes to a rotating group of charities instead,
so over the following months every charity in the pool gets its turn and the
totals stay (almost) even. Leftover cents go to the first charities in the group.

    python scripts/payout.py 5000 --month 2026-11
    python scripts/payout.py 5000 --month 2026-11 --out payout-2026-11.csv
"""

import argparse
import csv
import json
import sys
from decimal import ROUND_DOWN, Decimal

POOL_ORDER = ["humanitarian", "nature", "health", "education", "community"]


def month_index(month):
    year, mon = (int(part) for part in month.split("-"))
    return year * 12 + (mon - 1)


def split_cents(total_cents, count):
    base, extra = divmod(total_cents, count)
    return [base + (1 if i < extra else 0) for i in range(count)]


def plan(charities, amount, month, min_gift):
    total_cents = int((Decimal(amount) * 100).to_integral_value(ROUND_DOWN))
    min_cents = int(Decimal(min_gift) * 100)
    pools = [p for p in POOL_ORDER if any(c["pool"] == p for c in charities)]
    if not pools:
        raise ValueError("charity list is empty")

    rows = []
    for pool, pool_cents in zip(pools, split_cents(total_cents, len(pools))):
        members = sorted((c for c in charities if c["pool"] == pool), key=lambda c: c["ein"])
        n = len(members)
        group_size = max(1, min(n, pool_cents // min_cents if min_cents else n))
        start = (month_index(month) * group_size) % n
        group = [members[(start + i) % n] for i in range(group_size)]
        for charity, cents in zip(group, split_cents(pool_cents, group_size)):
            rows.append({
                "pool": pool,
                "ein": charity["ein"],
                "name": charity["name"],
                "amount": f"{cents / 100:.2f}",
            })
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("amount", help="total to donate this month (90%% of net profits), e.g. 5000")
    parser.add_argument("--month", required=True, help="payout month as YYYY-MM; drives the rotation")
    parser.add_argument("--charities", default="charities.json")
    parser.add_argument("--min-gift", default="10", help="smallest gift to send one charity (default $10)")
    parser.add_argument("--out", help="write a CSV instead of printing")
    args = parser.parse_args()

    with open(args.charities, encoding="utf-8") as f:
        charities = json.load(f)["charities"]
    rows = plan(charities, args.amount, args.month, args.min_gift)

    out = open(args.out, "w", newline="", encoding="utf-8") if args.out else sys.stdout
    writer = csv.DictWriter(out, fieldnames=["pool", "ein", "name", "amount"])
    writer.writeheader()
    writer.writerows(rows)
    if args.out:
        out.close()

    total = sum(Decimal(r["amount"]) for r in rows)
    print(f"{len(rows)} gifts totalling ${total:,.2f}", file=sys.stderr)


if __name__ == "__main__":
    main()
