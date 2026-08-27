#!/usr/bin/env python3
"""Economic Nexus Watch Desk — offline 2026 threshold checker.

No network. No API keys. Planning only — not tax advice.

  python3 desk/quote.py --list CA
  python3 desk/quote.py --check CA --sales 520000 --txns 80
  python3 desk/quote.py --check NY --sales 510000 --txns 120
  python3 desk/quote.py --batch data/sample_sales.csv
  python3 desk/quote.py --watch
  python3 desk/quote.py --cheap 15
  python3 desk/quote.py --digital CA --product downloaded_software
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
THRESH = DATA / "nexus_thresholds.csv"
DIGITAL = DATA / "digital_goods_flags.csv"

NO_TAX = {"no", "n/a", "none", ""}


def load_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def rows() -> list[dict]:
    return load_csv(THRESH)


def by_abbr() -> dict[str, dict]:
    return {r["abbr"].upper(): r for r in rows()}


def digital_by_abbr() -> dict[str, dict]:
    return {r["abbr"].upper(): r for r in load_csv(DIGITAL)}


def money(n: float) -> str:
    return f"${n:,.0f}" if n == int(n) else f"${n:,.2f}"


def parse_int(s: str | None) -> int | None:
    if s is None:
        return None
    s = str(s).strip()
    if s in NO_TAX:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def cmp_hit(value: float, threshold: int | None, op: str) -> bool | None:
    if threshold is None:
        return None
    if op == "gt":
        return value > threshold
    return value >= threshold


def evaluate(row: dict, sales: float, txns: int) -> dict:
    has = row["has_sales_tax"]
    if has in ("no",):
        return {
            "status": "no_state_sales_tax",
            "reason": f"{row['state']} has no general sales tax.",
            "sales_hit": False,
            "txn_hit": False,
        }
    if has == "no_state":
        sales_th = parse_int(row["sales_threshold_usd"])
        hit = sales_hit(sales, sales_th, row["sales_op"] or "gte")
        return {
            "status": "watch_local" if hit else "under_remote_seller",
            "reason": (
                f"{row['state']} has no statewide sales tax; remote-seller / local rules "
                f"use {money(sales_th or 0)}. Confirm ARSSTC / locals."
            ),
            "sales_hit": bool(hit),
            "txn_hit": False,
        }

    sales_th = parse_int(row["sales_threshold_usd"])
    txn_th = parse_int(row["txn_threshold"])
    op = row["sales_op"] or "gte"
    txn_op = row.get("txn_op") or "gte"
    test = row["txn_test"]
    s_hit = cmp_hit(sales, sales_th, op)
    t_hit = cmp_hit(txns, txn_th, txn_op) if test not in ("none", "n/a", "") else False

    if test == "both":
        triggered = bool(s_hit) and bool(t_hit)
        missing = []
        if not s_hit:
            missing.append("sales")
        if not t_hit:
            missing.append("transactions")
        reason = (
            "BOTH tests met — presumed nexus."
            if triggered
            else f"BOTH tests required; still short on {', '.join(missing)}."
        )
        status = "triggered" if triggered else "short_both"
    elif test == "either":
        triggered = bool(s_hit) or bool(t_hit)
        why = []
        if s_hit:
            why.append("sales")
        if t_hit:
            why.append("transactions")
        reason = (
            f"EITHER test; triggered on {', '.join(why)}."
            if triggered
            else "EITHER test; under both sales and transaction lines."
        )
        status = "triggered" if triggered else "under"
    else:
        triggered = bool(s_hit)
        reason = (
            "Sales-only test met — presumed nexus."
            if triggered
            else "Sales-only test; still under the dollar line."
        )
        status = "triggered" if triggered else "under"

    return {
        "status": status,
        "reason": reason,
        "sales_hit": bool(s_hit),
        "txn_hit": bool(t_hit),
    }


def op_sym(op: str) -> str:
    return ">" if op == "gt" else "≥"


def fmt_threshold(row: dict) -> str:
    if row["has_sales_tax"] == "no":
        return "no general sales tax"
    sales_th = parse_int(row["sales_threshold_usd"])
    sales_bit = f"{op_sym(row['sales_op'] or 'gte')}{money(sales_th or 0)}"
    test = row["txn_test"]
    txn_th = parse_int(row["txn_threshold"])
    txn_bit = f"{op_sym(row.get('txn_op') or 'gte')}{txn_th} txns"
    if test == "both":
        return f"{sales_bit} AND {txn_bit}"
    if test == "either":
        return f"{sales_bit} OR {txn_bit}"
    return f"{sales_bit} sales-only"


def print_row(row: dict) -> None:
    print(f"{row['abbr']}  {row['state']}")
    print(f"  tax: {row['has_sales_tax']}")
    print(f"  test: {fmt_threshold(row)}")
    print(f"  period: {row['measurement_period']}")
    print(f"  marketplace counts toward threshold: {row['marketplace_sales']}")
    if row.get("watch_2026"):
        print(f"  2026 watch: {row['watch_2026']}")
    print(f"  authority: {row['authority']}")
    print(f"  source: {row['source_id']}")
    if row.get("notes"):
        print(f"  notes: {row['notes']}")


def cmd_list(abbr: str | None) -> int:
    table = by_abbr()
    if abbr:
        key = abbr.upper()
        if key not in table:
            print(f"unknown state {abbr}", file=sys.stderr)
            return 1
        print_row(table[key])
        return 0
    print(
        f"{'ST':<4} {'threshold':<28} {'txn':<8} {'mkt':<10} {'watch'}"
    )
    for r in rows():
        watch = r.get("watch_2026") or ""
        print(
            f"{r['abbr']:<4} {fmt_threshold(r):<28} {r['txn_test']:<8} "
            f"{r['marketplace_sales']:<10} {watch}"
        )
    print(f"\n{len(rows())} jurisdictions. Not tax advice.")
    return 0


def cmd_check(abbr: str, sales: float, txns: int, product: str | None) -> int:
    table = by_abbr()
    key = abbr.upper()
    if key not in table:
        print(f"unknown state {abbr}", file=sys.stderr)
        return 1
    row = table[key]
    ev = evaluate(row, sales, txns)
    print_row(row)
    print(f"  your sales: {money(sales)} / {txns} txns")
    print(f"  result: {ev['status']}")
    print(f"  why: {ev['reason']}")
    if product:
        cmd_digital(key, product, quiet=False)
    return 0


def cmd_batch(path: Path) -> int:
    table = by_abbr()
    digital = digital_by_abbr()
    recs = load_csv(path)
    print(
        f"{'ST':<4} {'sales':>10} {'txn':>5} {'ch':<12} {'prod':<20} {'result':<18} digital"
    )
    triggered = 0
    for rec in recs:
        key = rec["state"].upper()
        if key not in table:
            print(f"{key:<4} unknown state")
            continue
        sales = float(rec["sales_usd"])
        txns = int(float(rec["txns"]))
        ev = evaluate(table[key], sales, txns)
        if ev["status"] in ("triggered", "watch_local"):
            triggered += 1
        prod = rec.get("product") or ""
        dflag = ""
        if prod and key in digital:
            dflag = digital[key].get(prod, "")
        print(
            f"{key:<4} {money(sales):>10} {txns:>5} {rec.get('channel',''):<12} "
            f"{prod:<20} {ev['status']:<18} {dflag}"
        )
    print(f"\n{triggered}/{len(recs)} rows triggered or local-watch. Not tax advice.")
    return 0


def cmd_watch() -> int:
    print("2026 watches (not the whole table):")
    for r in rows():
        if r.get("watch_2026"):
            print(f"- {r['abbr']}: {r['watch_2026']} — {r['notes']}")
    print(
        "\nIL: 200-txn test gone 2026-01-01 (IDOR FY 2026-12). "
        "A 400-order / $95k Illinois seller who would have triggered in 2025 does not on sales-only."
    )
    print(
        "NY: still BOTH >$500k AND >100 TPP sales in prior four quarters "
        "(tax.ny.gov nexus.htm)."
    )
    print(
        "CA: still >$500k TPP, preceding or current calendar year "
        "(cdtfa.ca.gov/industry/wayfair)."
    )
    return 0


def cmd_cheap(price: float) -> int:
    """Show states where N cheap orders can trip a transaction test."""
    n = 200
    revenue = n * price
    print(
        f"If every order is {money(price)}, {n} orders = {money(revenue)}."
    )
    print("Either-test states where the txn prong can fire below the dollar line.\n")
    print(f"{'ST':<4} {'test':<32} {'$ at txn line':>14} {'note'}")
    for r in rows():
        test = r["txn_test"]
        if test != "either":
            continue
        txn_th = parse_int(r["txn_threshold"]) or 0
        sales_th = parse_int(r["sales_threshold_usd"]) or 0
        at_txn = txn_th * price
        flag = "TXN CAN BEAT $" if at_txn < sales_th else "dollar still first"
        print(f"{r['abbr']:<4} {fmt_threshold(r):<32} {money(at_txn):>14} {flag}")
    print(
        "\nBOTH-test states (NY, CT) need the dollar prong too — txn volume alone does not trigger."
    )
    print("IL is absent: the 200-txn test died 2026-01-01.")
    return 0


def cmd_digital(abbr: str, product: str, quiet: bool = False) -> int:
    d = digital_by_abbr()
    key = abbr.upper()
    if key not in d:
        print(f"no digital flags for {abbr}", file=sys.stderr)
        return 1
    row = d[key]
    allowed = ("saas", "downloaded_software", "ebooks", "streaming")
    if product not in allowed:
        print(f"product must be one of {allowed}", file=sys.stderr)
        return 1
    flag = row[product]
    if not quiet:
        print(f"  digital ({product}): {flag}  [{row['source_id']}]")
        if row.get("caveat"):
            print(f"  caveat: {row['caveat']}")
        print("  flags are secondary compilations, not statutes.")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Economic Nexus Watch Desk (offline)")
    p.add_argument("--list", nargs="?", const="ALL", help="print table or one state")
    p.add_argument("--check", metavar="ST", help="evaluate one jurisdiction")
    p.add_argument("--sales", type=float, default=0.0)
    p.add_argument("--txns", type=int, default=0)
    p.add_argument("--batch", metavar="CSV")
    p.add_argument("--watch", action="store_true")
    p.add_argument("--cheap", type=float, metavar="PRICE", help="txn-trap at this unit price")
    p.add_argument("--digital", metavar="ST")
    p.add_argument("--product", default="", help="saas|downloaded_software|ebooks|streaming")
    args = p.parse_args()

    if args.watch:
        return cmd_watch()
    if args.cheap is not None:
        return cmd_cheap(args.cheap)
    if args.batch:
        return cmd_batch(Path(args.batch))
    if args.check:
        return cmd_check(args.check, args.sales, args.txns, args.product or None)
    if args.digital:
        return cmd_digital(args.digital, args.product or "saas")
    if args.list:
        return cmd_list(None if args.list == "ALL" else args.list)
    p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
