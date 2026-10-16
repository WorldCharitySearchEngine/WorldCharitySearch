"""Tests for the charity list builder and payout planner: python -m unittest discover scripts"""

import csv
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
import build_charities  # noqa: E402
import payout  # noqa: E402

FIELDS = ["EIN", "NAME", "CITY", "STATE", "SUBSECTION", "DEDUCTIBILITY", "STATUS",
          "FOUNDATION", "TAX_PERIOD", "REVENUE_AMT", "NTEE_CD"]
NOW = datetime(2026, 10, 1, tzinfo=timezone.utc)


def row(ein, ntee, revenue=1_000_000, **overrides):
    base = {"EIN": ein, "NAME": f"TEST ORG {ein} OF THE USA", "CITY": "SPRINGFIELD", "STATE": "IL",
            "SUBSECTION": "03", "DEDUCTIBILITY": "1", "STATUS": "01", "FOUNDATION": "15",
            "TAX_PERIOD": "202512", "REVENUE_AMT": str(revenue), "NTEE_CD": ntee}
    base.update(overrides)
    return base


class BuildCharitiesTest(unittest.TestCase):
    def build(self, rows, **kwargs):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        try:
            return build_charities.build([f.name], now=NOW, **kwargs)
        finally:
            os.unlink(f.name)

    def test_sorts_into_pools_and_filters_ineligible(self):
        result = self.build([
            row("000000001", "K31"),                          # food bank -> humanitarian
            row("000000002", "C32"),                          # environment -> nature
            row("000000003", "E20"),                          # hospital -> excluded
            row("000000009", "E310"),                         # health plan -> excluded
            row("000000010", "S500"),                         # donor-advised fund -> excluded
            row("000000004", "B20", FOUNDATION="04"),         # private foundation -> excluded
            row("000000005", "P20", SUBSECTION="04"),         # not a 501(c)(3) -> excluded
            row("000000006", "S20", TAX_PERIOD="201812"),     # stale filing -> excluded
            row("000000007", "O50", revenue=1000),            # too small -> excluded
            row("000000008", "Z99"),                          # unknown category -> excluded
            row("000000001", "K31"),                          # duplicate EIN -> ignored
        ])
        pools = {c["ein"]: c["pool"] for c in result["charities"]}
        self.assertEqual(pools, {"000000001": "humanitarian", "000000002": "nature"})

    def test_keeps_largest_per_pool(self):
        result = self.build([row(f"{i:09d}", "B20", revenue=300_000 + i) for i in range(10)], per_pool=3)
        self.assertEqual(sorted(c["ein"] for c in result["charities"]), ["000000007", "000000008", "000000009"])

    def test_pretty_name(self):
        self.assertEqual(build_charities.pretty_name("FEEDING AMERICA OF THE USA"), "Feeding America of the USA")
        self.assertEqual(build_charities.pretty_name("BOYS & GIRLS CLUB-METRO"), "Boys & Girls Club-Metro")


class PayoutTest(unittest.TestCase):
    def charities(self, per_pool):
        return [{"ein": f"{p}{i:04d}", "name": f"{p} {i}", "pool": p}
                for p in payout.POOL_ORDER for i in range(per_pool)]

    def test_even_split_adds_up_exactly(self):
        rows = payout.plan(self.charities(3), "1000.01", "2026-11", "10")
        self.assertEqual(len(rows), 15)
        self.assertEqual(sum(round(float(r["amount"]) * 100) for r in rows), 100001)
        amounts = [float(r["amount"]) for r in rows]
        self.assertLessEqual(max(amounts) - min(amounts), 0.011)

    def test_rotates_when_gifts_would_be_too_small(self):
        charities = self.charities(100)
        month1 = payout.plan(charities, "500", "2026-11", "10")   # $100 per pool -> 10 charities each
        month2 = payout.plan(charities, "500", "2026-12", "10")
        self.assertEqual(len(month1), 50)
        self.assertTrue(all(r["amount"] == "10.00" for r in month1))
        self.assertFalse({r["ein"] for r in month1} & {r["ein"] for r in month2})

    def test_everyone_gets_a_turn(self):
        charities = self.charities(25)
        paid = set()
        for m in range(1, 6):  # 5 charities per pool per month, 25 in each pool
            paid |= {r["ein"] for r in payout.plan(charities, "250", f"2027-{m:02d}", "10")}
        self.assertEqual(len(paid), len(charities))


if __name__ == "__main__":
    unittest.main()
