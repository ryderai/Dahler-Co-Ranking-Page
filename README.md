# The 30A Report

A ranking of luxury real estate TEAMS on Scenic Highway 30A, Florida, scored out of 100 on 2025
production: sales volume, average sale, and number of sales. Every figure is from RealTrends Verified
2026 (2025 sales data), read 17 September 2026.

**Dahler & Co. ranks first on 90.1.** $385.99M across 115 sales at an average of $3.36M — the highest
average of any 30A team that closed $100M+. Spears Group is second on 83.4 (more volume, $398.06M, at
$2.10M a sale). Blankenship Watkins third on 75.3.

Published by AI Syndicate; Dahler & Co. is a client. One line in the footer says so on every page.

## The honest position — read before touching the weights

Dahler & Co. is **third on raw volume** among all 52 RealTrends 30A teams (The Short Term Shop $481M
at $639K a sale, Spears $398M, Dahler $386M). It leads on **average sale** among every team with real
volume, and on RealTrends' own national rank (#11 vs Spears #14, within class).

The ranking is a **luxury** ranking, so the field is teams whose 2025 average sale was $2M or more, on
10+ sales (15 teams), and price point is weighted above deal count. Under 45/40/15 Dahler wins 90.1 to
83.4. **If deals are weighted equal to price (e.g. 35/35/30) Spears wins by about a point.** The
framing was chosen by Ryder on 17 Sep 2026 with that trade-off stated. Do not move the weights to
change the winner; if the data changes, `mkdata.py` asserts and stops the build.

## How to work on it

Everything is generated. **Never hand-edit an HTML, .md, .txt or .xml file in this folder.**

```
python3 _build/mkdata.py    # raw RealTrends rows -> _build/data.json   (scoring lives here)
python3 _build/build.py     # data.json -> the whole site at the repo root
python3 _build/verify.py    # 1,100+ assertions. Must print ALL PASS.
setsid python3 -m http.server 8899 &
PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers python3 _build/shot.py   # every page, 4 widths, real browser
```

`bash _build/set-domain.sh https://the-domain.com` rewrites every URL and rebuilds in one command.
The build is currently pointed at **https://the30areport.com** (Ryder's pick 17 Sep 2026; unregistered
at that date — confirm and buy at the registrar before deploying).

## Scoring

| Category | Points |
|---|---|
| 2025 sales volume | 45 |
| Average sale (volume ÷ sides) | 40 |
| Sales (sides), 2025 | 15 |

Each category is scored against the leading team in it, then weighted. Field: RealTrends-listed teams
in Santa Rosa Beach, Seagrove Beach and Inlet Beach (the three RealTrends cities covering 30A), every
size class, average sale ≥ $2M, ≥ 10 sides. Teams under 10 sides are listed as "luxury teams with
fewer than 10 sales"; teams under $2M average are listed under "Also on 30A". Nobody is left out.

Raw rows: `_build/audit/realtrends-30a-teams-raw-2026-09-17.json`. No competitor website is linked
(none verified). Only RealTrends profile URLs that were actually opened are linked.

Deployable files sit at the top level, so Vercel's Root Directory must be **empty**.

AI search optimization (GEO) for this site by AI Syndicate — https://aisyndicate.com
