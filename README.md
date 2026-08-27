# Economic Nexus Watch Desk

Offline 2026 desk that scores a remote seller against **51 economic-nexus rows** (50 states + DC), including the **Illinois 200-transaction drop** (IDOR FY 2026-12, effective 2026-01-01), New York’s **both-prongs** $500k + 100 TPP sales test, California’s **>$500,000** TPP rule (CDTFA / AB 147), and a secondary **digital-goods taxability** flag so a Gumroad / SaaS operator can see whether the SKU is even taxable once nexus exists.

## Who it's for

Digital-product sellers, tiny ecommerce shops, and bookkeepers who need a files-only Wayfair watch — not another $100k-or-200-txns blog post that still lists Illinois’ dead transaction test.

## What's included

- `data/nexus_thresholds.csv` — 51 rows: dollar line, `gt` vs `gte`, either/both/none txn test, measurement period, whether marketplace sales count
- `data/digital_goods_flags.csv` — SaaS / download / ebook / streaming flags (secondary 2026 compilation)
- `data/sample_sales.csv` — 17 worked destination rows
- `desk/quote.py` — `--list`, `--check`, `--batch`, `--watch`, `--cheap`, `--digital`
- `examples/` — IL txn drop, NY both-tests, CA $500k TPP, GA cheap-SKU trap
- `data/SOURCES.md` — CDTFA, NYS Tax, IDOR, STA 2026-08-18 review

## Quick start

```bash
python3 desk/quote.py --watch
python3 desk/quote.py --list IL
python3 desk/quote.py --check IL --sales 95000 --txns 400
python3 desk/quote.py --check NY --sales 510000 --txns 120
python3 desk/quote.py --check CA --sales 520000 --txns 80 --product saas
python3 desk/quote.py --cheap 15
python3 desk/quote.py --batch data/sample_sales.csv
```

No API keys. Files work after Gamut credits are gone. Not tax advice. Confirm with the named state authority before you register.

## Price

$49 USD. Unlimited non-exclusive buyers; copies may be resold. Pay https://buy.stripe.com/aFa9AUf0c1AD4tscMlcIE05 then open a GitHub issue titled `CLAIM: Economic Nexus Watch Desk` with the receipt last-4. If checkout is down, star + watch and open the same CLAIM issue.

## License

MIT for the desk code, CSVs, and docs. Cited CDTFA / NYS / IDOR / compiler figures remain their works. See LICENSE.

## Foundry

Shipped by Night Shift Foundry for Dakota (@Allspecs-yoda).
SKU: NSF-20260827-NEXUS-WATCH | Decision: list | Cycle: 2026-08-27
