# New York still requires BOTH tests

Lookback: immediately preceding **four sales tax quarters**
(Mar–May, Jun–Aug, Sep–Nov, Dec–Feb). Source: tax.ny.gov nexus.htm.

| receipts | TPP sales | result |
| --- | --- | --- |
| $510,000 | 90 | short — missing the 100-sale prong |
| $510,000 | 120 | **triggered** — both prongs |
| $40,000 | 250 ebooks | short on dollars; also check whether the SKU is TPP |

```bash
python3 desk/quote.py --check NY --sales 510000 --txns 90
python3 desk/quote.py --check NY --sales 510000 --txns 120
python3 desk/quote.py --check NY --sales 40000 --txns 250 --product ebooks
```

Digital flag (secondary): NY ebooks often **exempt**; SaaS / prewritten software often **taxed**. Nexus presumption in the statute is still about **TPP**.

Not tax advice.
