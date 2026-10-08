"""One-off: extract Tyrvingtabellen reference values from the NFF spreadsheet into JSON,
so the scraper never needs xlrd/LibreOffice at runtime."""
import json, re, sys, xlrd
wb = xlrd.open_workbook(sys.argv[1])
out = {}
for name in wb.sheet_names():
    m = re.match(r"(Gutter|Jenter) (\d+) år", name)
    if not m: continue
    sh = wb.sheet_by_name(name); rows = []
    for r in range(5, sh.nrows):
        ev = str(sh.cell_value(r, 1)).strip(); ref = sh.cell_value(r, 7)
        if not ev or not isinstance(ref, float): continue
        def num(c):
            v = sh.cell_value(r, c); return v if isinstance(v, float) else None
        rows.append(dict(event=ev, qual=str(sh.cell_value(r, 2)).strip(), ref=ref, kvot=num(8), f1=num(9), f2=num(10), f3=num(11)))
    out[f"{m.group(1)}-{m.group(2)}"] = rows
json.dump(out, open("tyrving_tables.json", "w"), ensure_ascii=False, indent=1)
print({k: len(v) for k, v in out.items()})
