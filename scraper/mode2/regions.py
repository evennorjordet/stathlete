"""Club -> region (krets) lookup from a local JSON file you maintain.

clubs_regions.json:  { "IL Koll": "Oslo", "IK Tjalve": "Oslo", "Fana IL": null, ... }
A null/missing entry means "unknown": the scraper then writes region = null and lists the
club in <out>.missing_clubs.txt so you can fill it in. (An OpenTrack lookup can be plugged
into resolve() once a real endpoint that returns club -> region has been confirmed.)
"""
import json, os
_PATH = os.path.join(os.path.dirname(__file__), "clubs_regions.json")


def load():
    try:
        return json.load(open(_PATH, encoding="utf-8"))
    except FileNotFoundError:
        return {}


def resolve(club, table):
    return table.get(club) or None


def add_unknown(clubs):
    """Append never-seen clubs to clubs_regions.json as null, so they're easy to fill in."""
    t = load(); changed = False
    for c in clubs:
        if c and c not in t:
            t[c] = None; changed = True
    if changed:
        json.dump(dict(sorted(t.items())), open(_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return t
