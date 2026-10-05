#!/usr/bin/env python3
"""Research -> _build/data.json. ALL scoring lives here.

Source: RealTrends Verified 2026 rankings (2025 sales data), city list pages for the three
RealTrends cities that cover Scenic Highway 30A - Santa Rosa Beach, Seagrove Beach and Inlet Beach -
in every team-size class (Small / Medium / Large / Mega / Enterprise). Read in Chrome on
17 September 2026, 00:05-00:20 CT. Raw rows: _build/audit/realtrends-30a-teams-raw-2026-09-17.json.

Rosemary Beach, Seacrest, Alys Beach, WaterSound, Seaside, Grayton Beach and Blue Mountain Beach have
no RealTrends city page (the URL falls through to the national list), so teams based there are filed
by RealTrends under one of the three cities above.

Average sale = RealTrends volume / RealTrends sides. RealTrends prints the same figure on each
team profile as "Avg Price" (checked on the Dahler & Co. profile: $3.36M).
"""
import json, os

SRC = os.path.dirname(os.path.abspath(__file__))
RAW = json.load(open(os.path.join(SRC, "audit", "realtrends-30a-teams-raw-2026-09-17.json")))

# What makes the ranked field: a luxury team is one whose 2025 average sale was $2M or more.
# Ten or more sides so that one or two sales cannot set a team's average.
LUX_AVG_M   = 2.0
MIN_SIDES   = 10

CATEGORIES = [
 {"key": "vol",   "label": "2025 sales volume",  "weight": 45, "unit": "money"},
 {"key": "avg",   "label": "Average sale",        "weight": 40, "unit": "money"},
 {"key": "sides", "label": "Sales (sides), 2025", "weight": 15, "unit": "count"},
]

SITES = {  # only the client's site is linked. Competitor sites are not published here.
 "Dahler & Co.": "https://30arealestatefl.com",
}
RT_PROFILE = {
 "Dahler & Co.": "https://www.realtrends.com/team-profile/dahler-co-florida-scenic-sotheby-s-international-realty/",
 "Spears Group": "https://www.realtrends.com/team-profile/spears-group-florida-compass/",
 "Blankenship Watkins Advisory Group": "https://www.realtrends.com/team-profile/blankenship-watkins-advisory-group-florida-christie-s-international-real-estate-emerald-coast/",
 "The Morar Group": "https://www.realtrends.com/team-profile/the-morar-group-florida-scenic-sotheby-s-international-realty/",
 "The Richards Group": "https://www.realtrends.com/team-profile/the-richards-group-florida-compass/",
 "Stroop Group": "https://www.realtrends.com/team-profile/stroop-group-florida-compass/",
}
RT_CITY = {
 "Santa Rosa Beach": "https://www.realtrends.com/ranking/best-real-estate-agents-santa-rosa-beach-florida/",
 "Seagrove Beach":   "https://www.realtrends.com/ranking/best-real-estate-agents-seagrove-beach-florida/",
 "Inlet Beach":      "https://www.realtrends.com/ranking/best-real-estate-agents-inlet-beach-florida/",
}
# From the Dahler & Co. RealTrends profile, read 16 Sep 2026 (ranks are within the Medium Team class)
DAHLER_PROFILE = {"national_rank_vol": 11, "state_rank_vol": 2, "city_rank_vol": 1, "city_rank_sides": 1,
                  "agents": 8, "lists": ["The Thousand by Volume", "Top Team by Volume", "Top Team by Sides"]}

def money(m):  # m in $M
    return f"${m:,.2f}M" if m < 1000 else f"${m/1000:.2f}B"
def money_avg(m):
    return f"${m:.2f}M"

teams = []
for r in RAW:
    vol, sides = float(r["vol"]), float(r["sides"])
    avg = vol / sides
    teams.append({
        "name": r["team"], "brokerage": r["brokerage"], "city": r["city"], "rt_class": r["cat"] + " Team",
        "vol": round(vol, 2), "sides": sides, "avg": round(avg, 3),
        "vol_fmt": money(vol), "avg_fmt": money_avg(avg),
        "sides_fmt": f"{sides:g}",
        "is_subject": r["team"] == "Dahler & Co.",
        "site": SITES.get(r["team"]), "rt_profile": RT_PROFILE.get(r["team"]),
        "rt_city_url": RT_CITY[r["city"]],
    })

ranked   = [t for t in teams if t["avg"] >= LUX_AVG_M and t["sides"] >= MIN_SIDES]
thin     = [t for t in teams if t["avg"] >= LUX_AVG_M and t["sides"] <  MIN_SIDES]
others   = [t for t in teams if t["avg"] <  LUX_AVG_M]

MAXW = sum(c["weight"] for c in CATEGORIES)
assert MAXW == 100
for c in CATEGORIES:
    best = max(t[c["key"]] for t in ranked)
    for t in ranked:
        t.setdefault("points", {})[c["key"]] = round(c["weight"] * t[c["key"]] / best, 1)
for t in ranked:
    t["total"] = round(sum(t["points"].values()), 1)
ranked.sort(key=lambda t: -t["total"])
for t in thin + others:
    t["total"] = None; t["points"] = None

# Guard: the subject must actually lead on the honest numbers, or this build stops here.
assert ranked[0]["is_subject"], f"Dahler & Co. does not rank first: {[(t['name'], t['total']) for t in ranked[:3]]}"
# Guard: the field is complete - every RealTrends 30A team is either ranked, thin, or listed.
assert len(ranked) + len(thin) + len(others) == len(teams) == 52

data = {
 "index_name": "The 30A Report",
 "measured_on": "2026-09-17",
 "measured_long": "17 September 2026",
 "data_label": "RealTrends Verified 2026 rankings, 2025 sales data",
 "area": "Scenic Highway 30A, Florida — Santa Rosa Beach, Seagrove Beach and Inlet Beach",
 "short_area": "30A",
 "publisher": "AI Syndicate",
 "publisher_url": "https://aisyndicate.com",
 "subject": "Dahler & Co.",
 "subject_lead": "Brad Dahler",
 "subject_brokerage": "Scenic Sotheby's International Realty",
 "lux_avg_m": LUX_AVG_M, "min_sides": MIN_SIDES,
 "categories": CATEGORIES,
 "teams": ranked, "thin": thin, "others": others,
 "dahler_profile": DAHLER_PROFILE,
}
json.dump(data, open(os.path.join(SRC, "data.json"), "w"), indent=1, ensure_ascii=False)
print(f"{len(teams)} teams on RealTrends' three 30A city pages -> {len(ranked)} ranked, {len(thin)} luxury but under {MIN_SIDES} sides, {len(others)} under ${LUX_AVG_M:g}M average")
for i, t in enumerate(ranked, 1):
    print(f"{i:2d} {t['name']:36s} {t['vol_fmt']:>10} {t['avg_fmt']:>7} {t['sides_fmt']:>5}  {t['total']}")
