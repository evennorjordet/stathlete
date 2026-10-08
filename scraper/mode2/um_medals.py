"""UM-medal counter for minfriidrettsstatistikk.info 'ALLE RESULTATER' pages (local HTML only)."""
import re, sys
from bs4 import BeautifulSoup

UM_RE = re.compile(r"\bUM\b")                      # whole word: excludes KFUM, UNM, ...
MANGE_RE = re.compile(r"mangekamp|m[åa]ngkamp", re.I)  # Mangekamp / Mångkamp
COMBINED_EVENT_RE = re.compile(r"^\s*\d+\s*Kamp\b", re.I)  # '6 Kamp (...)', '7 Kamp (...) Jr'
PLACE_RE = re.compile(r"^(\d+)(?:-fi)?$")          # bare number or 'N-fi'


def parse_rows(html):
    """Walk the page in document order, tracking section (UTE/INNE), event (h3) and
    whether we're inside an 'Ikke godkjente resultater' (h4) sub-table."""
    soup = BeautifulSoup(html, "html.parser")
    season = event = None
    unapproved = False
    for el in soup.find_all(["h2", "h3", "h4", "table"]):
        txt = el.get_text(" ", strip=True)
        if el.name == "h2":
            if txt.upper() in ("UTENDØRS", "INNENDØRS"):
                season = txt.upper()
        elif el.name == "h3":
            if txt:                      # the page emits an empty <h3> before each table
                event, unapproved = txt, False
        elif el.name == "h4":
            unapproved = "ikke godkjent" in txt.lower()
        else:
            for tr in el.find_all("tr")[1:]:
                c = [x.get_text(" ", strip=True) for x in tr.find_all("td")]
                if len(c) < 6:
                    continue
                yield dict(season=season, event=event, unapproved=unapproved,
                           year=c[0], result=c[1], place=c[2], club=c[3], date=c[4], sted=c[5])


def is_um_medal(r):
    if not UM_RE.search(r["sted"]):
        return None
    m = PLACE_RE.match(r["place"])
    if not m or int(m.group(1)) not in (1, 2, 3):
        return None
    # Inside a mangekamp meet only the combined-event row itself counts.
    if MANGE_RE.search(r["sted"]) and not COMBINED_EVENT_RE.match(r["event"]):
        return None
    return int(m.group(1))


def tally(html):
    medals = []
    for r in parse_rows(html):
        p = is_um_medal(r)
        if p:
            medals.append((p, r))
    return medals

if __name__ == "__main__":
    html = open(sys.argv[1], encoding="utf-8", errors="replace").read()
    ms = tally(html)
    from collections import Counter
    print("TOTAL", len(ms), dict(sorted(Counter(p for p, _ in ms).items())))
    for p, r in sorted(ms, key=lambda x: x[1]["date"][::-1]):
        print(p, r["season"][:3], r["year"], "|", r["event"][:28], "|", r["result"], r["place"], "|", r["sted"], "| uapp" if r["unapproved"] else "")
