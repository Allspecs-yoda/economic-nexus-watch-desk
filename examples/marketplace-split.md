# Marketplace split (direct vs platform)

Same $120k Kentucky / Georgia year. Half is Amazon, half is your own cart.

```bash
python3 desk/quote.py --split KY --direct 80000 --marketplace 40000 --txns 90
python3 desk/quote.py --split GA --direct 80000 --marketplace 40000 --txns 90
python3 desk/quote.py --split KY --direct 80000 --marketplace 40000 --txns 90 --as-of 2026-07-31
```

- **KY** (`marketplace_sales=included`): $120k counts. After 2026-08-01 that is over $100k → triggered even though the platform remitted the Amazon slice.
- **GA** (`marketplace_sales=excluded`): only $80k direct counts → under the dollar line. The 200-txn prong still uses the `--txns` you pass; if those 90 are direct-only, GA stays under.

The desk does **not** invent whether Amazon already collected. It only answers: does this state's published threshold **count** marketplace receipts toward *your* remote-seller line.

Not tax advice.
