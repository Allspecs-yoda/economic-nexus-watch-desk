# Cheap SKU transaction trap (Georgia and friends)

Illinois **no longer** has this trap in 2026. Georgia, Ohio, Virginia, New Jersey, and other **either-test** states still do.

200 orders at **$15** = $3,000 — well under $100,000, enough to trip a 200-txn alternative.

```bash
python3 desk/quote.py --cheap 15
python3 desk/quote.py --check GA --sales 4000 --txns 210 --product ebooks
```

Connecticut is the other way: **both** $100k **and** 200 retail sales, measured on the 12 months ending **September 30**.

```bash
python3 desk/quote.py --check CT --sales 120000 --txns 150
python3 desk/quote.py --check CT --sales 120000 --txns 220
```

Not tax advice.
