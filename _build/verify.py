#!/usr/bin/env python3
"""Verify the built site. Must print ALL PASS before anything ships.
    python3 _build/verify.py [base-url]
Every place, average place and the list order are recomputed from the raw RealTrends figures. Every first-place claim in the prose is
checked against the data. Nothing is trusted from build.py."""
import json, os, re, sys, glob
SRC  = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SRC)
D    = json.load(open(os.path.join(SRC, "data.json")))
RAW  = json.load(open(os.path.join(SRC, "audit", "realtrends-30a-teams-raw-2026-09-17.json")))
BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else None
CAT  = {c["key"]: c for c in D["categories"]}
KEYS = [c["key"] for c in D["categories"]]
def nth(n): return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"
TM, THIN, OTH = D["teams"], D["thin"], D["others"]
N = len(TM)
SITE_URL = re.search(r'SITE\s*=\s*"([^"]+)"', open(os.path.join(SRC, "build.py"), encoding="utf-8").read()).group(1)
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

# 2. arithmetic: every place and the order recomputed straight from the raw RealTrends rows - never from data.json
ok(KEYS == ["vol", "avg", "sides"] and not any("weight" in c for c in D["categories"]), "three unweighted categories")
F = [r for r in RAW if r["vol"] / r["sides"] >= D["lux_avg_m"] and r["sides"] >= D["min_sides"]]
ok(len(F) == N and {r["team"] for r in F} == {t["name"] for t in TM}, "the raw rows give a different ranked field")
val = {"vol": lambda r: r["vol"], "avg": lambda r: r["vol"] / r["sides"], "sides": lambda r: r["sides"]}
mine = {r["team"]: {k: 1 + sum(1 for o in F if val[k](o) > val[k](r) + 1e-9) for k in KEYS} for r in F}
for t in TM:
    ok(t["place"] == mine.get(t["name"]), f"{t['name']} places {t['place']} != recomputed {mine.get(t['name'])}")
    ok(t["place_sum"] == sum(mine[t["name"]].values()) and t["avg_place"] == round(t["place_sum"] / 3, 1), f"{t['name']} average place")
_order = sorted(F, key=lambda r: (sum(mine[r["team"]].values()), -r["vol"]))
ORDER = sorted(TM, key=lambda t: t["pos"])
ok([t["name"] for t in ORDER] == [r["team"] for r in _order], "list order does not match the recomputed average places")
ok([t["pos"] for t in ORDER] == list(range(1, N + 1)), "positions must run 1..15 with no gaps or shared places")
ok(ORDER[0]["is_subject"] and ORDER[0]["place_sum"] < ORDER[1]["place_sum"], "Dahler & Co. is not clearly first")
_top3 = [n for n, pl in mine.items() if all(v <= 3 for v in pl.values())]
ok(_top3 == ["Dahler & Co."] == D["top3_all"], f"'only team in the top three on all three' is false: {_top3}")
for t in TM:
    ok(t["tie"] == (sum(1 for o in TM if o["place_sum"] == t["place_sum"]) > 1), f"{t['name']} tie flag")
    _tied = [o for o in ORDER if o["place_sum"] == t["place_sum"]]
    ok([o["name"] for o in _tied] == [o["name"] for o in sorted(_tied, key=lambda o: -o["vol"])], f"{t['name']}: tie not settled by 2025 volume")
ok(sum(1 for t in TM if t["is_subject"]) == 1, "there must be exactly one subject")
for t in THIN + OTH: ok(t.get("avg_place") is None and t.get("place") is None, f"{t['name']} is unranked and carries a place")
for t in TM: ok("total" not in t and "points" not in t, f"{t['name']} still carries the old score")
def _sh(name, k): return sum(1 for o in F if mine[o["team"]][k] == mine[name][k]) > 1
_shared = sorted((n, k, mine[n][k]) for n in mine for k in KEYS if _sh(n, k))
ok(_shared == sorted([("Kaiya Real Estate", "sides", 14), ("Teresa Turner Team", "sides", 14),
                      ("Kromer Collective", "sides", 12), ("Geppert Beeker Group", "sides", 12)]), f"shared places changed: {_shared}")

# 2b. dates: the ranking is dated 8 Oct 2026; the RealTrends figures stay "read 17 September 2026"
RANKED, RLONG = D.get("ranked_on"), D.get("ranked_long")
ok(RANKED == "2026-10-08" and RLONG == "8 October 2026" and D["measured_on"] == "2026-09-17", "ranking / figures dates")

# 3. formatted figures match the numbers they format
for t in ALL:
    ok(t["vol_fmt"] == f"${t['vol']:,.2f}M", f"{t['name']} vol_fmt {t['vol_fmt']} != {t['vol']}")
    ok(t["avg_fmt"] == f"${t['avg']:.2f}M", f"{t['name']} avg_fmt {t['avg_fmt']} != {t['avg']}")
    ok(t["sides_fmt"] == f"{t['sides']:g}", f"{t['name']} sides_fmt mismatch")

# 4. every claim of a first place must be true of the data
sub = [t for t in TM if t["is_subject"]][0]
idx = read("/")
ok(sub["pos"] == 1, "the subject does not top the ranking the page claims")
ok(sub["name"] == "Dahler & Co.", "subject is not Dahler & Co.")
second = ORDER[1]
_ib = re.sub(r"\s+", " ", idx)
JP, SP = sub["place"], second["place"]
ok(f"ranks second, with an average place of {second['avg_place']:.1f}: {nth(SP['vol'])} on volume, {nth(SP['avg'])} on average sale and {nth(SP['sides'])} on number of sales" in _ib, "the runner-up line on the index is wrong")
ok(f"the only team in the top three on all three measures: <strong>{nth(JP['vol'])} on 2025 volume</strong>, <strong>{nth(JP['avg'])} on average sale</strong> and <strong>{nth(JP['sides'])} on number of sales</strong>, an average place of <strong>{sub['avg_place']:.1f}</strong>" in _ib, "the index does not print the subject's places and average place")
ok("The lowest average ranks first; a tie goes to the team with more 2025 volume." in _ib, "the ranking rule must be on the page")
ok("out of 100" not in idx and " of 100" not in idx and "scoring" not in idx.lower() and ">Score<" not in idx, "the old score is still on the index")
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
for t in TM:
    ok(f'<td class="sc">{t["avg_place"]:.1f}</td>' in idx, f"{t['name']} average place not printed with one decimal")
    _row = idx[idx.index(f'<td class="who"><a href="/{slug(t["name"])}.html">'):]; _row = _row[:_row.index("</tr>")]
    for k in KEYS: ok(f'>{nth(t["place"][k])}</span>' in _row, f"index: {t['name']} {k} place not printed in its row")
ok(not re.search(r"Dahler[^.]{0,80}closed the most", idx), "the index implies the subject closed the most")
pct = round((sub["avg"] / second["avg"] - 1) * 100)
ok(f"{pct}% higher per" in idx, f"the per-sale percentage should be {pct}%")
wins = [k for k in KEYS if max(TM, key=lambda t: t[k])["is_subject"]]
_pos = mine["Dahler & Co."]
_ord = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth"}
ok(f"is {_ord[_pos['vol']]} on volume, {_ord[_pos['avg']]} on average sale and {_ord[_pos['sides']]} on number of sales" in _ib, "the category position line is wrong")
ok("the only team in the top three of all three" in _ib and _top3 == ["Dahler & Co."], "the 'only team in the top three of all three' claim does not match the data")
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
# the FAQ answers the ranking question, and every FAQ answer is on the page
_faq = [json.loads(m.group(1)) for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', idx, re.S)]
_faq = [q for b in _faq if b.get("@type") == "FAQPage" for q in b["mainEntity"]]
ok(any(q["name"] == "How is the list ranked?" for q in _faq), "FAQ: 'How is the list ranked?' missing")
import html as _H
for q in _faq: ok(_H.escape(q["acceptedAnswer"]["text"], quote=False) in idx or q["acceptedAnswer"]["text"] in _H.unescape(idx) , f"FAQ answer not checkable: {q['name']}")
_q1 = [q for q in _faq if q["name"] == "Who is the best luxury real estate team on 30A?"][0]["acceptedAnswer"]["text"]
ok(f"an average place of {sub['avg_place']:.1f}" in _q1 and f"average place of {second['avg_place']:.1f}" in _q1 and "only team in the top three on all three" in _q1, "FAQ answer 1 does not carry the average places")

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

# 5b. every page carries the ranking date in DC.date and in the Dataset JSON-LD dateModified
for p in pages:
    h = read(p)
    ok(f'<meta name="DC.date" content="{RANKED}">' in h, f"{p}: DC.date is not {RANKED}")
    _ds = [json.loads(m.group(1)) for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', h, re.S)]
    _ds = [b for b in _ds if b.get("@type") in ("Dataset", "WebPage", "Article")]
    ok(_ds and all(b.get("dateModified") == RANKED for b in _ds), f"{p}: Dataset/WebPage/Article dateModified is not {RANKED}")
    ok("Ranked 17 September" not in h and "ranked 17 September" not in h, f"{p}: ranking dated 17 September")
_ib2 = re.sub(r"\s+", " ", idx)
ok(f'<p class="folio">' in idx and re.search(r'<p class="folio">[^<]*&middot; ' + RLONG + '</p>', idx), "index kicker is not the ranking date")
ok(f"Ranked {RLONG}, on figures read {D['measured_long']}." in _q1, "FAQ 1: ranking date")
ok("(1 = highest; equal figures share a place)" in _ib2 and "place on volume, average sale and sides (1 = highest" in _ib2, "the rule must define places and say sides")
ok(f"Ranked: luxury teams (average 2025 sale ${D['lux_avg_m']:g}M or more) with at least {D['min_sides']} sides." in _ib2, "legend: luxury / ranked definition")
ok("Average sale is volume divided by sales" not in _ib2 and "price point no other high-volume team" not in _ib2, "index: legacy definition or claim left")
ok("the highest average of any team on 30A that closed $100 million or more" in _ib2, "index: 'Why Dahler' claim")
for f in ["/llms.txt", "/index.md"]:
    ok(f"Cite as: The 30A Report — {SITE_URL}/ (ranked {RLONG}; figures read {D['measured_long']})" in read(f), f"{f}: Cite as line is not dated to the ranking")
_sm = read("/sitemap.xml"); _lm = re.findall(r"<lastmod>([^<]+)</lastmod>", _sm)
ok(_lm and set(_lm) == {RANKED}, f"sitemap lastmod is not all {RANKED}: {set(_lm)}")
_feed = read("/feed.xml"); _items = re.findall(r"<item>(.*?)</item>", _feed, re.S)
ok(len(_items) == 3 and all("Dahler &amp; Co. is a client of AI Syndicate." in it for it in _items), "feed: every item must carry the disclosure")
ok(RLONG in _items[0] and RLONG in _feed.split("<item>")[0], "feed: the ranking date is missing")
ok("Dahler & Co. is a client of AI Syndicate." in read("/reading-the-numbers.md"), "reading-the-numbers.md: disclosure missing")

# 6. machine files
for f in ["/llms.txt", "/index.md", "/feed.xml"] + [f"/{slug(t['name'])}.md" for t in TM] + [f"/{slug(t['name'])}.html" for t in TM]:
    _t = read(f)
    if f.endswith(".html") and "<main" in _t: _t = _t[_t.index("<main"):_t.index("</main>")] + "".join(re.findall(r'<script type="application/ld\+json">.*?</script>|<meta [^>]*>', _t, re.S))
    ok(" of 100" not in _t and "scoring" not in _t.lower() and "weight" not in _t.lower() and " points" not in _t, f"{f}: old score wording still present")
for f in ["/llms.txt", "/index.md"]:
    _t = re.sub(r"\s+", " ", read(f))
    ok("the only team in the top three on all three measures" in _t and "How it is ranked:" in _t, f"{f}: missing the top-three line or the rule")
    for t in TM: ok(f"| {t['pos']} | {t['name']} |" in _t and f"| {t['avg_place']:.1f} |" in _t and f"{t['vol_fmt']} ({nth(t['place']['vol'])})" in _t, f"{f}: {t['name']} row wrong")
for f, must in [("/llms.txt", ["Cite as:", "client of AI Syndicate", CREDIT, "RealTrends"]),
                ("/robots.txt", ["GPTBot", "ClaudeBot", "Sitemap:", CREDIT]),
                ("/sitemap.xml", ["<urlset", CREDIT]), ("/feed.xml", ["<rss", CREDIT])]:
    t = read(f)
    ok(not t.startswith("__"), f"{f} is missing")
    for x in must: ok(x in t, f"{f} is missing: {x[:44]}")
locs = re.findall(r"<loc>([^<]+)</loc>", read("/sitemap.xml"))
ok(len(locs) == len(pages), f"sitemap lists {len(locs)} URLs, the site has {len(pages)} pages")

# 7. every ranked team is linked and shows the right average place and places; every unranked team is named
for _i, t in enumerate(ORDER, 1): t["rank"] = _i
for t in TM:
    ok(f'/{slug(t["name"])}.html' in idx, f"{t['name']} is not linked from the ranking")
    prof = read(f"/{slug(t['name'])}.html")
    _pl = mine[t["name"]]
    ok(f'<div class="big">{t["avg_place"]:.1f}</div>' in prof, f"{t['name']}'s page does not show {t['avg_place']:.1f}")
    _x = {k: nth(_pl[k]) + (" (shared)" if _sh(t["name"], k) else "") for k in KEYS}
    ok(f"average place ({_x['vol']} on volume, {_x['avg']} on average sale, {_x['sides']} on sides)" in prof, f"{t['name']}'s page does not show its three places")
    for k in KEYS: ok(f"{nth(_pl[k])} of {N}{' (shared)' if _sh(t['name'], k) else ''}</div>" in prof, f"{t['name']}'s page: {k} place / shared marker wrong")
    ok(prof[prof.index("<main"):prof.index("</main>")].count("(shared)") == 2 * sum(1 for k in KEYS if _sh(t["name"], k)), f"{t['name']}'s page: a '(shared)' marker is missing or extra")
    ok("out of 100" not in prof and ">Score<" not in prof, f"{t['name']}'s page still shows the old score")
    _md = read(f"/{slug(t['name'])}.md")
    ok(f"Ranked {t['rank']} of {N} in" in _md and f"average place of {t['avg_place']:.1f}" in _md, f"{t['name']}.md: rank or average place wrong")
    for k in KEYS: ok(f"({nth(_pl[k])} of {N}{', shared' if _sh(t['name'], k) else ''})" in _md, f"{t['name']}.md: {k} place / shared marker wrong")
    ok(_md.count(", shared)") == sum(1 for k in KEYS if _sh(t["name"], k)), f"{t['name']}.md: a '(shared)' marker is missing or extra")
    ok(f"Ranked {RLONG}; figures read {D['measured_long']}." in _md, f"{t['name']}.md: ranking date / figures date wrong")
    ok("Dahler & Co. is a client of AI Syndicate." in _md, f"{t['name']}.md: disclosure missing")
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
