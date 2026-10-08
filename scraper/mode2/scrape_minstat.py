"""Mode 2 scraper: builds data/athletes_mode2.json from the minfriidrettsstatistikk.info
'ALLE RESULTATER' pages you have saved into  pages/<id>.html  (e.g. pages/36971.html).
It never contacts the site itself (its robots.txt disallows automated access).

pages/manifest.csv   columns: id,gender      gender = Gutter or Jenter (the page doesn't say)

Usage (from this folder):
    python scrape_minstat.py --out ../../data/athletes_mode2.json
"""
import argparse, csv, glob, json, os, re, sys
from collections import Counter
from bs4 import BeautifulSoup
from um_medals import parse_rows, is_um_medal
from tyrving import score, parse_result
import regions

HERE = os.path.dirname(os.path.abspath(__file__))
COMBINED = re.compile(r"^\s*\d+\s*Kamp\b", re.I)
FIELD = re.compile(r"^(Høyde|Stav|Lengde|Tresteg|Kule|Diskos|Spyd|Slegge)")
GENDERS = {"gutt": "Gutter", "gutter": "Gutter", "g": "Gutter", "m": "Gutter",
           "jente": "Jenter", "jenter": "Jenter", "j": "Jenter", "k": "Jenter"}
TOP_N = 5


def header(html):
    soup = BeautifulSoup(html, "html.parser")
    name = soup.find("h2").get_text(" ", strip=True)
    txt = re.sub(r"\s+", " ", soup.get_text(" "))
    m = re.search(r"Født:\s*(\d{2})\.(\d{2})\.(\d{4})", txt)
    return name, (f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None)


def lower_is_better(event):
    return not (COMBINED.match(event) or FIELD.match(event))


def mark_value(event, result):
    if COMBINED.match(event):
        try: return float(result)
        except ValueError: return None
    return parse_result(result)[0]


def display(event, result):
    if COMBINED.match(event): return result + " p"
    m = re.match(r"^([\d,]+)(\(.*\))?$", result.strip())
    if not m: return result
    core, wind = m.group(1), m.group(2) or ""
    if core.count(",") == 2:                      # 1,39,07 -> 1:39,07
        a, b, c = core.split(","); core = f"{a}:{b},{c}"
    return core + wind


def build(athlete_id, html, gender, table):
    name, born = header(html)
    rows = list(parse_rows(html))
    # club = most common club in the most recent competing year
    latest = max(int(re.match(r"(\d{4})", r["year"]).group(1)) for r in rows)
    club = Counter(r["club"] for r in rows if r["year"].startswith(str(latest))).most_common(1)[0][0]
    # UM medals (wind-assisted placings count; mangekamp = combined row only)
    medals = {"gold": 0, "silver": 0, "bronze": 0}
    for r in rows:
        p = is_um_medal(r)
        if p: medals[("gold", "silver", "bronze")[p - 1]] += 1
    # PBs, ALL events, approved results only. dict insertion order == the page's own order
    # (outdoor first, then indoor; events in the site's order), which we keep for "show all".
    best = {}
    for r in rows:
        if r["unapproved"]: continue
        v = mark_value(r["event"], r["result"])
        if v is None or v <= 0: continue
        age = int(re.search(r"\((\d+)\)", r["year"]).group(1))
        key = (r["season"], r["event"])
        lib = lower_is_better(r["event"])
        if key not in best or (v < best[key][0] if lib else v > best[key][0]):
            best[key] = (v, r, age)
    pbs = {"outdoor": [], "indoor": []}
    top_score = (0, None)
    for (season, event), (v, r, age) in best.items():
        pts = None if COMBINED.match(event) else score(gender, age, event, r["result"])
        pbs["outdoor" if season == "UTENDØRS" else "indoor"].append(dict(
            event=event, result=r["result"], display=display(event, r["result"]), value=v,
            lower_is_better=lower_is_better(event), points=pts, date=r["date"], age=age))
        if pts and pts > top_score[0]: top_score = (pts, event)
    # Top-N across indoor + outdoor by Tyrving points -> flagged for the "first view"
    allpb = [p for k in pbs for p in pbs[k] if p["points"]]
    for p in sorted(allpb, key=lambda p: -p["points"])[:TOP_N]:
        p["featured"] = True
    return dict(id=athlete_id, name=name, gender=gender, born=int(born[:4]), birth_date=born,
                club=club, region=regions.resolve(club, table),
                um_medals=dict(medals, total=sum(medals.values())),
                score=top_score[0] or None, main_event=top_score[1],
                last_season=latest, personal_bests=pbs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", default=os.path.join(HERE, "pages"))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    genders = {}
    mpath = os.path.join(a.pages, "manifest.csv")
    if os.path.exists(mpath):
        for row in csv.DictReader(open(mpath, encoding="utf-8")):
            genders[row["id"].strip()] = GENDERS.get((row.get("gender") or "").strip().lower())

    out, seen_clubs = [], []
    table = regions.load()
    for path in sorted(glob.glob(os.path.join(a.pages, "*.html"))):
        aid = os.path.splitext(os.path.basename(path))[0]
        if not genders.get(aid):
            print(f"  skipped {aid}: no valid gender (Gutter/Jenter) in manifest.csv", file=sys.stderr); continue
        try:
            ath = build(aid, open(path, encoding="utf-8", errors="replace").read(), genders[aid], table)
        except Exception as exc:
            print(f"  skipped {aid}: {exc}", file=sys.stderr); continue
        out.append(ath); seen_clubs.append(ath["club"])
        print(f"{aid} {ath['name']}: {ath['club']} / {ath['region']}  UM={ath['um_medals']['total']}  score={ath['score']}", file=sys.stderr)

    table = regions.add_unknown(seen_clubs)            # new clubs get a null entry to fill in
    missing = sorted(c for c in set(seen_clubs) if not table.get(c))
    open(os.path.join(HERE, "missing_clubs.txt"), "w", encoding="utf-8").write("\n".join(missing) + ("\n" if missing else ""))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    for x in out:
        x["region"] = regions.resolve(x["club"], table)
    json.dump({"source_note": "Built from saved minfriidrettsstatistikk.info profile pages. UM medals = whole-word 'UM' meets, places 1-3 (mangekamp: combined row only). Points = Tyrvingtabellen 2014 at the age of the result.",
               "athletes": out}, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"Wrote {len(out)} athletes to {a.out}; clubs without region: {missing or 'none'}", file=sys.stderr)


if __name__ == "__main__":
    main()
