#!/usr/bin/env python3
"""Verify the built site. Must print ALL PASS before anything ships.
    python3 _build/verify.py [base-url]
Every score is recomputed from the raw RealTrends figures. Every first-place claim in the prose is
checked against the data. Nothing is trusted from build.py."""
import json, os, re, sys, glob
SRC  = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SRC)
D    = json.load(open(os.path.join(SRC, "data.json")))
RAW  = json.load(open(os.path.join(SRC, "audit", "realtrends-30a-teams-raw-2026-09-17.json")))
BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else None
CAT  = {c["key"]: c for c in D["categories"]}
KEYS = [c["key"] for c in D["categories"]]
MAX  = sum(c["weight"] for c in D["categories"])
TM, THIN, OTH = D["teams"], D["thin"], D["others"]
N = len(TM)
CREDIT = "AI search optimization (GEO) for this site by AI Syndicate — https://aisyndicate.com"
fails, checks = [], 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m)
def slug(s): return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
def read(path):
    if BASE:
        import urllib.request
        try: return urllib.request.urlopen(BASE + path, timeout=20).read().decode("utf-8", "replace")
        except Exception as ex: return f"__FAIL__ {ex}"
    f = os.path.join(ROOT, "index.html" if path == "/" else path.lstrip("/"))
    return open(f, encoding="utf-8").read() if os.path.exists(f) else "__MISSING__"

# 1. the field: every raw RealTrends row is in exactly one bucket, with its figures unchanged
ALL = TM + THIN + OTH
ok(len(RAW) == 52, f"raw file holds {len(RAW)} rows, expected 52")
ok(len(ALL) == len(RAW), f"{len(ALL)} teams in data.json vs {len(RAW)} raw rows")
ok(len({t["name"] for t in ALL}) == len(ALL), "duplicate team names")
rawmap = {r["team"]: r for r in RAW}
for t in ALL:
    r = rawmap.get(t["name"])
    ok(r is not None, f"{t['name']} is not in the raw RealTrends file")
    if not r: continue
    ok(abs(t["vol"] - r["vol"]) < 0.005, f"{t['name']} volume {t['vol']} != raw {r['vol']}")
    ok(abs(t["sides"] - r["sides"]) < 0.005, f"{t['name']} sides {t['sides']} != raw {r['sides']}")
    ok(t["brokerage"] == r["brokerage"] and t["city"] == r["city"], f"{t['name']} brokerage/city changed")
    ok(abs(t["avg"] - r["vol"] / r["sides"]) < 0.002, f"{t['name']} average does not equal volume/sides")
    ok(t["rt_class"] == r["cat"] + " Team", f"{t['name']} class changed")
# bucket rules applied exactly
for t in TM:   ok(t["avg"] >= D["lux_avg_m"] and t["sides"] >= D["min_sides"], f"{t['name']} is ranked but fails the field rule")
for t in THIN: ok(t["avg"] >= D["lux_avg_m"] and t["sides"] <  D["min_sides"], f"{t['name']} is in 'thin' wrongly")
for t in OTH:  ok(t["avg"] <  D["lux_avg_m"], f"{t['name']} is in 'others' but averages {t['avg']}")
ok(N == 15, f"{N} ranked, expected 15")

# 2. arithmetic: every score recomputed from the raw figures
ok(MAX == 100, f"category weights total {MAX}, must be 100")
for c in D["categories"]:
    best = max(t[c["key"]] for t in TM)
    for t in TM:
        want = round(c["weight"] * t[c["key"]] / best, 1)
        ok(abs(t["points"][c["key"]] - want) < 0.05, f"{t['name']} scores {t['points'][c['key']]} on {c['key']}, recomputes to {want}")
for t in TM:
    ok(abs(t["total"] - round(sum(t["points"].values()), 1)) < 0.05, f"{t['name']}'s total does not add up")
    ok(t["total"] <= MAX + 0.05, f"{t['name']} scores above {MAX}")
ok(sum(1 for t in TM if t["is_subject"]) == 1, "there must be exactly one subject")
for t in THIN + OTH: ok(t.get("total") is None, f"{t['name']} is unranked and carries a score")

# 3. formatted figures match the numbers they format
for t in ALL:
    ok(t["vol_fmt"] == f"${t['vol']:,.2f}M", f"{t['name']} vol_fmt {t['vol_fmt']} != {t['vol']}")
    ok(t["avg_fmt"] == f"${t['avg']:.2f}M", f"{t['name']} avg_fmt {t['avg_fmt']} != {t['avg']}")
    ok(t["sides_fmt"] == f"{t['sides']:g}", f"{t['name']} sides_fmt mismatch")

# 4. every claim of a first place must be true of the data
sub = [t for t in TM if t["is_subject"]][0]
idx = read("/")
ok(sub["total"] == max(t["total"] for t in TM), "the subject does not top the ranking the page claims")
ok(sub["name"] == "Dahler & Co.", "subject is not Dahler & Co.")
second = sorted(TM, key=lambda t: -t["total"])[1]
ok(f"ranks second on {second['total']:g}" in idx, "the runner-up figure on the index is wrong")
ok(f"scoring {sub['total']:g} out of {MAX}" in idx, "the index does not print the subject's score")
ok(sub["vol_fmt"] in idx and sub["avg_fmt"] in idx and f"{sub['sides_fmt']} sales" in idx, "the index does not print the subject's three figures")
# "highest average of any 30A team that closed $100 million or more" - must be true
big = [t for t in TM if t["vol"] >= 100]
ok(max(big, key=lambda t: t["avg"])["is_subject"], "the $100M+ average-sale claim is false")
ok("highest average of any 30A team that closed $100 million or more" in idx, "the qualified average claim is missing from the index")
# the page must NOT claim the subject leads volume or sides (it does not)
vol_lead = max(TM, key=lambda t: t["vol"])
ok(not vol_lead["is_subject"], "data changed: subject now leads volume - re-read the prose")
ok(f"{vol_lead['name']} closed slightly more dollars" in read("/").replace("&amp;", "&"), "the index must say who closed more volume")
ok("Among 30A&rsquo;s luxury teams, two closed more than $380 million" in idx and sum(1 for t in TM if t["vol"] > 380) == 2, "the '$380 million' sentence must be scoped to luxury teams and true")
_sts = max(OTH, key=lambda t: t["vol"]); ok(_sts["vol"] > vol_lead["vol"] and _sts["name"] in idx, "the biggest raw-volume team must be named on the index")
import xml.etree.ElementTree as _ET
for _f in ["/feed.xml", "/sitemap.xml"]:
    try: _ET.fromstring(read(_f))
    except Exception as _ex: ok(False, f"{_f} does not parse as XML: {_ex}")
for t in TM: ok(f'<td class="sc">{t["total"]:.1f}</td>' in idx, f"{t['name']} score not printed with one decimal")
ok(not re.search(r"Dahler[^.]{0,80}closed the most", idx), "the index implies the subject closed the most")
pct = round((sub["avg"] / second["avg"] - 1) * 100)
ok(f"{pct}% higher per" in idx, f"the per-sale percentage should be {pct}%")
wins = [k for k in KEYS if max(TM, key=lambda t: t[k])["is_subject"]]
_pos = {k: 1 + sorted(TM, key=lambda t: -t[k]).index(sub) for k in KEYS}
_both = [t for t in TM if t in sorted(TM, key=lambda x: -x["vol"])[:3] and t in sorted(TM, key=lambda x: -x["avg"])[:3]]
_ord = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth"}
ok(f"is {_ord[_pos['vol']]} on volume and {_ord[_pos['avg']]} on" in idx, "the volume/average position line is wrong")
ok(("the only team" in idx) == (len(_both) == 1 and _both[0]["is_subject"]), "the 'only team in the top three of both' claim does not match the data")
ok(len(wins) == 0, "data changed: the subject now leads a raw category outright - re-read every 'leads' sentence")
# RealTrends profile facts printed on the site match the recorded profile
dp = D["dahler_profile"]
ok(f"#{dp['national_rank_vol']} in the United States" in idx, "national rank missing from index")
ok(f"#{dp['state_rank_vol']} in Florida" in idx, "state rank missing from index")
ok("medium" in idx.lower(), "the size-class qualifier is missing from the index")
ok("100+ transactions" not in idx and "#1 team" not in idx.lower(), "an unsourced superlative is on the index")
# Rule One: no GEO-work columns
for bad in ["llms.txt", "agents.md", "robots.txt", "sitemap", "schema", "JSON-LD", "AI crawler"]:
    body = idx[idx.index("<main"):idx.index("</main>")]
    ok(bad.lower() not in body.lower(), f"Rule One: '{bad}' appears in the ranking page body")
# Rule Two: no methodology dump
for bad in ["weight", "points out of", "how the score works", "methodology"]:
    body = idx[idx.index("<main"):idx.index("</main>")]
    ok(bad.lower() not in body.lower(), f"Rule Two: '{bad}' appears on the page")

# 5. pages exist, carry the credit, one canonical, a markdown alternate, and the disclosure once
pages = ["/", "/reading-the-numbers.html"] + [f"/{slug(t['name'])}.html" for t in TM]
for p in pages:
    h = read(p)
    ok(not h.startswith("__"), f"{p} is missing or would not load")
    if h.startswith("__"): continue
    ok(CREDIT in h, f"{p} is missing the behind-the-scenes credit line")
    ok("GEO Optimization by" in h, f"{p} is missing the footer credit")
    ok("is a\nclient of AI Syndicate" in h or "is a client of AI Syndicate" in h, f"{p} has lost the publisher disclosure")
    ok(h.count('rel="canonical"') == 1, f"{p} does not have exactly one canonical link")
    ok('type="text/markdown"' in h, f"{p} has no markdown alternate")
    ok(not re.search(r'content="\[[^"]*\]"', h), f"{p} ships an unfilled [bracket]")
    ok("Not affiliated" in h or "not affiliated" in h, f"{p} is missing the non-affiliation line")
    ok("about.html" not in h, f"{p} still links to the removed About page")
    ok("mailto:support@aisyndicate.com" in h, f"{p} footer has no corrections address")
    ok("vercel.app" not in h, f"{p} still points at a placeholder domain")
    for tag in ["section", "div", "table", "main", "header", "footer", "ol", "ul", "p"]:
        o = len(re.findall(rf"<{tag}[ >]", h)); c = len(re.findall(rf"</{tag}>", h))
        ok(o == c, f"{p}: {o} <{tag}> open vs {c} close")
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', h, re.S):
        try: json.loads(m.group(1))
        except Exception as ex: ok(False, f"{p}: JSON-LD does not parse: {ex}")
    m = "/index.md" if p == "/" else p.replace(".html", ".md")
    t = read(m)
    ok(not t.startswith("__"), f"{m} is missing")

# 6. machine files
for f, must in [("/llms.txt", ["Cite as:", "client of AI Syndicate", CREDIT, "RealTrends"]),
                ("/robots.txt", ["GPTBot", "ClaudeBot", "Sitemap:", CREDIT]),
                ("/sitemap.xml", ["<urlset", CREDIT]), ("/feed.xml", ["<rss", CREDIT])]:
    t = read(f)
    ok(not t.startswith("__"), f"{f} is missing")
    for x in must: ok(x in t, f"{f} is missing: {x[:44]}")
locs = re.findall(r"<loc>([^<]+)</loc>", read("/sitemap.xml"))
ok(len(locs) == len(pages), f"sitemap lists {len(locs)} URLs, the site has {len(pages)} pages")

# 7. every ranked team is linked and shows the right score; every unranked team is named
_sorted = sorted(TM, key=lambda t: -t["total"]); _rk = _prev = None
for _i, t in enumerate(_sorted, 1):
    if t["total"] != _prev: _rk, _prev = _i, t["total"]
    t["rank"] = _rk
for t in TM:
    ok(f'/{slug(t["name"])}.html' in idx, f"{t['name']} is not linked from the ranking")
    prof = read(f"/{slug(t['name'])}.html")
    ok(f'<div class="big">{t["total"]:.1f}</div>' in prof, f"{t['name']}'s page does not show {t['total']:.1f}")
    ok(t["vol_fmt"] in prof and t["avg_fmt"] in prof, f"{t['name']}'s page does not show its figures")
    ok(f'<div class="big">{t["rank"]}</div>' in prof, f"{t['name']}'s page does not show rank {t['rank']}")
for x in THIN + OTH:
    import html as _h
    ok(_h.escape(x["name"], quote=True) in idx or x["name"] in idx, f"{x['name']} was left out and is not named")
# Rule Three: competitor websites are not published (none verified), only the client's
ok(sum(1 for t in TM if t.get("site")) == 1, "a competitor website is linked - only the client's site is verified")

# 8. nothing left over, no republished email addresses
files = [f for f in glob.glob(os.path.join(ROOT, "**", "*.*"), recursive=True)
         if "_build" not in f and "/fonts/" not in f and not f.endswith((".woff2", ".png"))]
blob = "\n".join(open(f, encoding="utf-8", errors="replace").read() for f in files)
ok("{{" not in blob, "an unresolved {{placeholder}} is in the built site")
ok("audited" not in blob.lower(), "'audited' overstates RealTrends verification")
ok("Every 30A team" not in blob, "blanket claim about every competitor's website")
ok("Half-sides" not in blob and "half-sides" not in blob, "sides explainer contradicts the table")
ok(", 2025 among" not in blob and "(sides), 2025." not in blob, "a column label leaked into prose")
ok("biography&rsquo;s wording" not in blob, "editor note left in copy")
ok("TODO" not in blob and "FIXME" not in blob, "a TODO or FIXME is in the built site")
mails = set(re.findall(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", blob)) - {"support@aisyndicate.com"}
ok(not mails, f"an email address is published: {sorted(mails)[:3]}")

print(f"{checks} checks run")
if fails:
    print(f"\n{len(fails)} FAILED:")
    for f in fails: print("  -", f)
    sys.exit(1)
print("ALL PASS")
