# California $500,000 TPP (AB 147 / RTC 6203)

CDTFA: register and collect California **use tax** if combined sales of **tangible personal property** for delivery in California by the retailer **and related persons** (IRC 267(b)) **exceed $500,000** during the preceding or current calendar year.

| CA TPP | result |
| --- | --- |
| $480,000 | under |
| $520,000 | **triggered** |

Marketplace volume is **included** in the STA compilation for CA.

CDTFA also says charges for computer programs / other digital products are generally **not** TPP. Downloaded canned software is still often taxed — use `--product`.

```bash
python3 desk/quote.py --check CA --sales 480000 --txns 900 --product downloaded_software
python3 desk/quote.py --check CA --sales 520000 --txns 80 --product saas
```

Not tax advice. Confirm https://cdtfa.ca.gov/industry/wayfair/
