"""Tyrvingpoeng scorer (Tyrvingtabellen 2014). Formulas copied from the NFF spreadsheet:
  timed:  floor(1000 + (ref - time) * kvot)          units: hundredths (<=500 m / hurdles <=400 m), tenths otherwise
  jumps:  floor(1000 - (mark - ref) * kvot * -1)  i.e. 1000 - (ref_cm - mark_cm) * kvot
  throws/pole vault: 3-tier. mark >= 80% ref: kvot = f1 above ref, f2 below; mark < 80% ref: first 20% of ref at f2, remainder at f3.
"""
import json, math, os, re
_T = json.load(open(os.path.join(os.path.dirname(__file__), "tyrving_tables.json")))
MANUAL_ADD = {60: .20, 80: .20, 300: .20, 100: .24, 110: .24, 200: .24, 400: .14}
FIELD = ("Høyde", "Lengde", "Tresteg", "Stav", "Kule", "Diskos", "Slegge", "Spyd")


def parse_result(txt):
    """'8,30(-0,5)' -> (8.30, False); '1,39,07' -> (99.07, False); '5,86' -> 5.86. Returns (value, manual_timing)."""
    t = re.sub(r"\(.*?\)", "", txt).strip().replace(" ", "")
    parts = t.split(",")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 60 + int(parts[1]) + int(parts[2]) / 100, False
        if len(parts) == 2:
            return float(parts[0] + "." + parts[1]), False
        return float(parts[0]), False
    except ValueError:
        return None, False


def find_row(rows, event):
    e = event.lower()
    m = re.match(r"(\d+) meter( hekk)?(?: \(([\d,]+)\s*cm\))?", e)
    if m:
        dist, hekk, h = m.group(1), m.group(2), m.group(3)
        for r in rows:
            if r["event"].lower().startswith(f"{dist} m") and r["qual"].lower() != "kappgang":
                is_h = "hekk" in r["event"].lower()
                if bool(hekk) != is_h: continue
                if hekk and h and not r["qual"].replace(" ", "").startswith(h.replace(" ", "") + "cm"): continue
                if not hekk and "hinder" in r["event"].lower(): continue
                return r
        return None
    for name in FIELD:
        if e.startswith(name.lower()):
            w = re.search(r"([\d,]+)\s*(kg|gram)", e)
            for r in rows:
                if not r["event"].lower().startswith(name.lower()): continue
                if name.lower() in ("kule", "diskos", "spyd", "slegge"):
                    if not w: continue
                    kg = float(w.group(1).replace(",", ".")) / (1000 if w.group(2) == "gram" else 1)
                    rk = re.match(r"([\d,]+)\s*kg", r["qual"])
                    if not rk or abs(float(rk.group(1).replace(",", ".")) - kg) > 1e-6: continue
                if name == "Høyde" and ("uten" in e) != ("uten" in r["event"].lower()): continue
                if name == "Lengde" and ("uten" in e) != ("uten" in r["event"].lower()): continue
                if "sone" in e: continue
                return r
    return None


def score(gender, age, event, result, hand_timed=None):
    """gender 'Gutter'/'Jenter'; age 10..19 (older -> 19). Returns int points or None (event not in table)."""
    rows = _T.get(f"{gender}-{min(max(age, 10), 19)}")
    if not rows: return None
    row = find_row(rows, event)
    val, _ = parse_result(result)
    if row is None or val is None: return None
    ref = row["ref"]
    if any(event.startswith(n) for n in FIELD):
        N, M = ref * 100, val * 100
        O = N - M
        if row["f1"] is None:
            p = 1000 - O * row["kvot"]
        else:
            if val < 0.8 * ref:
                p = 1000 - ((N - 0.8 * N) * row["f2"] + (O - (N - 0.8 * N)) * row["f3"])
            else:
                p = 1000 - O * (row["f1"] if val > ref else row["f2"])
        return max(0, math.floor(p + 1e-9)) if val else 0
    dist = int(re.match(r"(\d+)", event).group(1))
    hundredths = dist <= 500 or ("hekk" in event and dist <= 400)
    if hand_timed is None:
        hand_timed = hundredths and re.search(r",\d(?!\d)", re.sub(r"\(.*?\)", "", result)) is not None and result.count(",") == 1
    if hand_timed and dist in MANUAL_ADD: val += MANUAL_ADD[dist]
    f = 100 if hundredths else 10
    M = round(val * 100) if hundredths else math.floor(val * 10 + 1e-9)
    p = 1000 + (ref * f - M) * row["kvot"]
    return max(0, math.floor(p + 1e-9))

if __name__ == "__main__":
    # Validation vs a real published result from the earlier session: 400 m, 53.64, age 18, Jenter -> 1146
    print("Jenter 18, 400 m 53,64 ->", score("Jenter", 18, "400 meter", "53,64"), "(expected 1146)")
