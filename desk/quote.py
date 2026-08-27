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
  python3 desk/quote.py --sst
  python3 desk/quote.py --split KY --direct 80000 --marketplace 40000 --txns 400
  python3 desk/quote.py --check KY --sales 95000 --txns 400 --as-of 2026-07-31
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
THRESH = DATA / "nexus_thresholds.csv"
DIGITAL = DATA / "digital_goods_flags.csv"
SST = DATA / "sst_membership.csv"

NO_TAX = {"no", "n/a", "none", ""}
KY_HB757_ON = date(2026, 8, 1)


def load_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def rows() -> list[dict]:
    return load_csv(THRESH)


def by_abbr() -> dict[str, dict]:
    return {r["abbr"].upper(): r for r in rows()}


def digital_by_abbr() -> dict[str, dict]:
    return {r["abbr"].upper(): r for r in load_csv(DIGITAL)}


def sst_by_abbr() -> dict[str, dict]:
    return {r["abbr"].upper(): r for r in load_csv(SST)}


def parse_as_of(s: str | None) -> date:
    if not s:
        return datetime.now().date()
    return datetime.strptime(s, "%Y-%m-%d").date()


def overlay_as_of(row: dict, as_of: date) -> dict:
    """KY HB 757 (Acts Ch. 161): 200-txn test dies 2026-08-01."""
    if row.get("abbr") != "KY":
        return row
    r = dict(row)
    if as_of < KY_HB757_ON:
        r["txn_test"] = "either"
        r["txn_threshold"] = "200"
        r["txn_op"] = "gte"
        r["watch_2026"] = "pre_HB757_either_test"
        r["notes"] = (
            "Before 2026-08-01: $100k OR 200 txns. HB 757 (26RS, Acts Ch. 161) "
            "not yet effective."
        )
        r["source_id"] = "KY-HB-757"
        r["authority"] = "KRS 139.340 as in force before HB 757"
    else:
        r["watch_2026"] = "dropped_200_txn_2026-08-01"
        r["notes"] = (
            "HB 757 / Acts Ch. 161: 200-txn gone 2026-08-01; $100k TPP + digital "
            "+ services; register by first of month ≤60 days after crossing"
        )
        r["source_id"] = "KY-HB-757"
    return r


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
        hit = cmp_hit(sales, sales_th, row["sales_op"] or "gte")
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


def cmd_list(abbr: str | None, as_of: date) -> int:
    table = by_abbr()
    sst = sst_by_abbr()
    if abbr:
        key = abbr.upper()
        if key not in table:
            print(f"unknown state {abbr}", file=sys.stderr)
            return 1
        print_row(overlay_as_of(table[key], as_of))
        if key in sst:
            print(f"  sst: {sst[key]['status']} — {sst[key]['note']}")
        return 0
    print(
        f"{'ST':<4} {'threshold':<32} {'txn':<8} {'mkt':<10} {'sst':<10} {'watch'}"
    )
    for r in rows():
        r = overlay_as_of(r, as_of)
        watch = r.get("watch_2026") or ""
        sm = sst.get(r["abbr"], {}).get("status", "out")
        print(
            f"{r['abbr']:<4} {fmt_threshold(r):<32} {r['txn_test']:<8} "
            f"{r['marketplace_sales']:<10} {sm:<10} {watch}"
        )
    print(f"\n{len(rows())} jurisdictions as of {as_of.isoformat()}. Not tax advice.")
    return 0


def cmd_check(
    abbr: str, sales: float, txns: int, product: str | None, as_of: date
) -> int:
    table = by_abbr()
    key = abbr.upper()
    if key not in table:
        print(f"unknown state {abbr}", file=sys.stderr)
        return 1
    row = overlay_as_of(table[key], as_of)
    ev = evaluate(row, sales, txns)
    print_row(row)
    print(f"  as of: {as_of.isoformat()}")
    print(f"  your sales: {money(sales)} / {txns} txns")
    print(f"  result: {ev['status']}")
    print(f"  why: {ev['reason']}")
    sst = sst_by_abbr()
    if key in sst:
        print(f"  sst: {sst[key]['status']} — {sst[key]['note']}")
    if product:
        cmd_digital(key, product, quiet=False)
    return 0


def cmd_batch(path: Path, as_of: date) -> int:
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
        ev = evaluate(overlay_as_of(table[key], as_of), sales, txns)
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
    print(
        f"\n{triggered}/{len(recs)} rows triggered or local-watch as of {as_of.isoformat()}. "
        "Not tax advice."
    )
    return 0


def cmd_watch(as_of: date) -> int:
    print(f"2026 watches as of {as_of.isoformat()} (not the whole table):")
    for r in rows():
        r = overlay_as_of(r, as_of)
        if r.get("watch_2026"):
            print(f"- {r['abbr']}: {r['watch_2026']} — {r['notes']}")
    print(
        "\nIL: 200-txn test gone 2026-01-01 (IDOR FY 2026-12). "
        "A 400-order / $95k Illinois seller who would have triggered in 2025 does not on sales-only."
    )
    print(
        "KY: HB 757 / Acts Ch. 161 — 200-txn dies 2026-08-01. "
        "A 400-order / $95k Kentucky seller triggered on 2026-07-31 and is under on 2026-08-01. "
        "Register by first of month ≤60 days after crossing $100k (Thompson / KRS 139.340)."
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


def cmd_cheap(price: float, as_of: date) -> int:
    """Show states where N cheap orders can trip a transaction test."""
    n = 200
    revenue = n * price
    print(
        f"If every order is {money(price)}, {n} orders = {money(revenue)}. "
        f"As of {as_of.isoformat()}."
    )
    print("Either-test states where the txn prong can fire below the dollar line.\n")
    print(f"{'ST':<4} {'test':<32} {'$ at txn line':>14} {'note'}")
    for r in rows():
        r = overlay_as_of(r, as_of)
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
    if as_of >= KY_HB757_ON:
        print("KY is absent: the 200-txn test died 2026-08-01 (HB 757).")
    else:
        print("KY still either-test until 2026-08-01.")
    return 0


def cmd_sst() -> int:
    recs = load_csv(SST)
    print("SSTGB membership as of 2026-08-14 public notice (23 full + TN associate).\n")
    print(f"{'ST':<4} {'status':<12} {'sstrs':<8} note")
    full = assoc = out = 0
    for r in recs:
        print(f"{r['abbr']:<4} {r['status']:<12} {r['sstrs']:<8} {r['note']}")
        if r["status"] == "full":
            full += 1
        elif r["status"] == "associate":
            assoc += 1
        else:
            out += 1
    print(
        f"\n{full} full / {assoc} associate / {out} out. "
        "SSTRS is one registration into selected member states — it does not create nexus. "
        "CA/TX/NY/FL/IL are out. Not tax advice."
    )
    return 0


def cmd_split(
    abbr: str, direct: float, marketplace: float, txns: int, as_of: date
) -> int:
    table = by_abbr()
    key = abbr.upper()
    if key not in table:
        print(f"unknown state {abbr}", file=sys.stderr)
        return 1
    row = overlay_as_of(table[key], as_of)
    mkt = (row.get("marketplace_sales") or "").strip()
    combined = direct + marketplace
    print_row(row)
    print(f"  as of: {as_of.isoformat()}")
    print(f"  direct: {money(direct)}  marketplace: {money(marketplace)}")
    if mkt == "excluded":
        counted = direct
        note = (
            "Marketplace volume is EXCLUDED from the seller threshold in this row. "
            "Platform may still collect on those orders; seller watches the direct channel."
        )
    elif mkt == "included":
        counted = combined
        note = (
            "Marketplace volume is INCLUDED toward the seller threshold. "
            "Amazon/Etsy receipts can trip nexus even if the platform remits."
        )
    else:
        counted = combined
        note = (
            f"marketplace_sales={mkt!r} — confirm with the named authority; "
            "desk treats unknown as included for a conservative watch."
        )
    ev = evaluate(row, counted, txns)
    print(f"  counted toward threshold: {money(counted)}")
    print(f"  result: {ev['status']}")
    print(f"  why: {ev['reason']}")
    print(f"  split: {note}")
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
    p.add_argument("--sst", action="store_true", help="print SSTGB 23+TN membership")
    p.add_argument("--split", metavar="ST", help="direct vs marketplace split")
    p.add_argument("--direct", type=float, default=0.0)
    p.add_argument("--marketplace", type=float, default=0.0)
    p.add_argument(
        "--as-of",
        dest="as_of",
        default="",
        help="YYYY-MM-DD; KY HB 757 overlay uses 2026-08-01",
    )
    args = p.parse_args()
    as_of = parse_as_of(args.as_of or None)

    if args.watch:
        return cmd_watch(as_of)
    if args.cheap is not None:
        return cmd_cheap(args.cheap, as_of)
    if args.sst:
        return cmd_sst()
    if args.split:
        return cmd_split(args.split, args.direct, args.marketplace, args.txns, as_of)
    if args.batch:
        return cmd_batch(Path(args.batch), as_of)
    if args.check:
        return cmd_check(args.check, args.sales, args.txns, args.product or None, as_of)
    if args.digital:
        return cmd_digital(args.digital, args.product or "saas")
    if args.list:
        return cmd_list(None if args.list == "ALL" else args.list, as_of)
    p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
