#!/usr/bin/env python3
"""Build charities.json from the IRS Exempt Organizations Business Master File.

The IRS publishes every U.S. tax-exempt organization as four regional CSV files.
This script keeps active, tax-deductible 501(c)(3) public charities that file
recent returns, sorts them into the five donation pools by their NTEE category,
and keeps the largest PER_POOL charities in each pool by reported revenue.

Every.org lists IRS-registered 501(c)(3)s, so each charity can be found there
by its EIN.

    python scripts/build_charities.py                     # download from irs.gov
    python scripts/build_charities.py --input eo1.csv ... # use local CSV files
"""

import argparse
import csv
import io
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone

IRS_FILES = [f"https://www.irs.gov/pub/irs-soi/eo{i}.csv" for i in range(1, 5)]

PER_POOL = 500
MIN_REVENUE = 250_000
MAX_FILING_AGE_YEARS = 3

# NTEE major groups (first letter of the code) for each pool.
# https://urbaninstitute.github.io/nccs-legacy/ntee/ntee.html
POOLS = {
    "humanitarian": "KMPQR",  # food, disaster relief, human services, international, civil rights
    "nature": "CD",           # environment, animals
    "health": "EFGH",         # health care, mental health, diseases, medical research
    "education": "BO",        # education, youth development
    "community": "JLS",       # employment, housing, community improvement
}
GROUP_TO_POOL = {letter: pool for pool, letters in POOLS.items() for letter in letters}

# Organizations whose revenue is mostly fees or government contracts rather than
# charitable giving. Ranked by revenue they would crowd out everyone else, and they
# rarely need small donations. Excluded by NTEE code prefix.
EXCLUDED_NTEE_PREFIXES = (
    "E20", "E21", "E22", "E24",                # hospitals
    "E31",                                     # health insurance plans / HMOs
    "E90", "E91", "E92",                       # nursing homes, home health agencies
    "E11", "E12",                              # hospital and health-system foundations
    "B40", "B41", "B42", "B43", "B50",         # colleges and universities
    "B11", "B12",                              # university and school foundations
    "B90",                                     # testing and educational services companies
    "L22", "L40",                              # retirement communities, student housing
    "S30", "S31", "S32", "S40", "S41", "S43",  # economic development, business leagues
    "S50",                                     # donor-advised funds, nonprofit management
)

# 15 = publicly supported (170(b)(1)(A)(vi)), 16 = 509(a)(2). Excludes private
# foundations, churches, schools, hospitals and supporting organizations.
PUBLIC_CHARITY_FOUNDATION_CODES = {"15", "16"}

SMALL_WORDS = {"a", "an", "and", "at", "by", "for", "in", "of", "on", "or", "the", "to", "with"}
UPPER_WORDS = {"usa", "us", "ymca", "ywca", "aids", "hiv", "nyc", "lgbt", "lgbtq", "ii", "iii", "iv", "uk", "un", "unicef"}


def pretty_name(raw):
    """IRS names are ALL CAPS; turn them into readable title case."""
    words = raw.strip().lower().split()
    out = []
    for i, word in enumerate(words):
        bare = re.sub(r"[^a-z]", "", word)
        if bare in UPPER_WORDS:
            out.append(word.upper())
        elif i > 0 and word in SMALL_WORDS:
            out.append(word)
        else:
            out.append(re.sub(r"(^|[-/(&])([a-z])", lambda m: m.group(1) + m.group(2).upper(), word))
    return " ".join(out)


def pool_for(ntee):
    ntee = (ntee or "").strip().upper()
    if not ntee or ntee.startswith(EXCLUDED_NTEE_PREFIXES):
        return None
    return GROUP_TO_POOL.get(ntee[0])


def is_eligible(row, min_tax_period):
    return (
        row.get("SUBSECTION") == "03"
        and row.get("DEDUCTIBILITY") == "1"
        and row.get("STATUS") == "01"
        and row.get("FOUNDATION") in PUBLIC_CHARITY_FOUNDATION_CODES
        and (row.get("TAX_PERIOD") or "0") >= min_tax_period
    )


def revenue_of(row):
    try:
        return int(row.get("REVENUE_AMT") or 0)
    except ValueError:
        return 0


def read_rows(sources):
    for source in sources:
        if source.startswith("http"):
            print(f"Downloading {source}", file=sys.stderr)
            request = urllib.request.Request(source, headers={"User-Agent": "WorldCharitySearch charity list builder"})
            with urllib.request.urlopen(request, timeout=300) as response:
                text = io.TextIOWrapper(response, encoding="utf-8", errors="replace", newline="")
                yield from csv.DictReader(text)
        else:
            with open(source, encoding="utf-8", errors="replace", newline="") as f:
                yield from csv.DictReader(f)


def build(sources, per_pool=PER_POOL, min_revenue=MIN_REVENUE, now=None):
    now = now or datetime.now(timezone.utc)
    min_tax_period = f"{now.year - MAX_FILING_AGE_YEARS}{now.month:02d}"

    candidates = {pool: [] for pool in POOLS}
    seen = set()
    for row in read_rows(sources):
        ein = (row.get("EIN") or "").strip()
        if not ein or ein in seen or not is_eligible(row, min_tax_period):
            continue
        pool = pool_for(row.get("NTEE_CD"))
        revenue = revenue_of(row)
        if pool is None or revenue < min_revenue:
            continue
        seen.add(ein)
        candidates[pool].append({
            "ein": ein.zfill(9),
            "name": pretty_name(row.get("NAME", "")),
            "city": (row.get("CITY") or "").strip().title(),
            "state": (row.get("STATE") or "").strip(),
            "pool": pool,
            "ntee": row.get("NTEE_CD", "").strip().upper(),
            "revenue": revenue,
        })

    charities = []
    for pool, items in candidates.items():
        items.sort(key=lambda c: c["revenue"], reverse=True)
        charities.extend(items[:per_pool])
    charities.sort(key=lambda c: (c["pool"], c["name"]))

    return {
        "generatedAt": now.strftime("%Y-%m-%d"),
        "source": "IRS Exempt Organizations Business Master File (irs.gov/charities-non-profits/exempt-organizations-business-master-file-extract-eo-bmf)",
        "criteria": (
            f"Active, tax-deductible 501(c)(3) public charities that filed a return in the last "
            f"{MAX_FILING_AGE_YEARS} years with at least ${min_revenue:,} in revenue; the {per_pool} "
            f"largest per pool by revenue. Hospitals and universities excluded."
        ),
        "counts": {pool: sum(1 for c in charities if c["pool"] == pool) for pool in POOLS},
        "charities": charities,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", nargs="+", default=IRS_FILES, help="IRS EO BMF CSV files or URLs")
    parser.add_argument("--out", default="charities.json")
    parser.add_argument("--per-pool", type=int, default=PER_POOL)
    parser.add_argument("--min-revenue", type=int, default=MIN_REVENUE)
    args = parser.parse_args()

    result = build(args.input, per_pool=args.per_pool, min_revenue=args.min_revenue)
    total = len(result["charities"])
    if total == 0:
        sys.exit("No charities matched; refusing to overwrite the list with an empty file.")

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))
    print(f"Wrote {total} charities to {args.out}: {result['counts']}", file=sys.stderr)


if __name__ == "__main__":
    main()
