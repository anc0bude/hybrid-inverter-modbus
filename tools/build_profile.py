"""Baut inverter_definitions/deye_sg04lp3_vollstaendig.yaml (Format des Original-Parsers).

Eingaben: alte Profile (deye_sg04lp3.yaml, deye_hybrid.yaml) + deye_p3.yaml (davidrapan/ha-solarman, MIT)
          + optional Liste der in HA aktiven Entity-IDs (--ids ha_ids.json, nur Namensabgleich).
Regel: Bisher genutzte Sensoren bleiben unveraendert (Entity-IDs/Statistik). Neue lesbare Werte kommen aus p3.
Aufruf: python tools/build_profile.py --p3 PFAD/deye_p3.yaml [--ids ha_ids.json]
"""
import argparse, json, re, copy, pathlib, yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFS = ROOT / "custom_components/solarman/inverter_definitions"
LIVE_GROUPS = {"Info", "State", "Battery", "Grid", "Output", "UPS", "Load",
               "Generator/SmartLoad/Microinverter", "PV", "Meter", "BMS"}
DEV_CLASSES = {"power", "energy", "voltage", "current", "temperature", "frequency", "battery",
               "apparent_power", "reactive_power", "power_factor", "duration"}
STATE_CLASSES = {"measurement", "total", "total_increasing"}
EXCLUDE = {"internal_power", "external_power", "load_ups_l3_power", "load_ups_power"}  # liefern keinen Wert
slug = lambda n: re.sub(r"\W+", "_", n.strip().lower()).strip("_")

def items(path):
    d = yaml.safe_load(open(path, encoding="utf-8")); out = []
    def w(n, g=""):
        if isinstance(n, dict):
            if "registers" in n and "name" in n: out.append((g, n)); return
            for v in n.values(): w(v, n.get("group", g))
        elif isinstance(n, list):
            for v in n: w(v, g)
    w(d); return d, out

def convert(n):
    o = {"name": n["name"]}
    o["class"] = n["class"] if n.get("class") in DEV_CLASSES else ""
    if n.get("state_class") in STATE_CLASSES: o["state_class"] = n["state_class"]
    o["uom"] = n.get("uom", "")
    sc = n.get("scale")
    if isinstance(sc, list): sc = sc[0]
    if sc is not None: o["scale"] = sc
    for k in ("rule", "registers", "icon", "offset", "mask"):
        if k in n: o[k] = n[k]
    if isinstance(n.get("lookup"), list) and all(isinstance(x, dict) and "key" in x and "value" in x for x in n["lookup"]):
        o["lookup"] = n["lookup"]
    v = n.get("validation")
    if isinstance(v, dict) and ("min" in v or "max" in v):
        o["validation"] = {k: v[k] for k in ("min", "max") if k in v}
    return o

def requests(spans, maxspan=120, maxgap=60):
    """spans = [(min,max)] je Sensor; ein Sensor wird nie auf zwei Abfragen verteilt."""
    spans = sorted(set(spans)); out = []; s, e = spans[0]
    for lo, hi in spans[1:]:
        if lo - e <= maxgap and max(e, hi) - s < maxspan: e = max(e, hi)
        else: out.append((s, e)); s, e = lo, hi
    out.append((s, e)); return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--p3", required=True); ap.add_argument("--ids"); ap.add_argument("--scan", help="scan.json: nur lesbare Register verwenden"); ap.add_argument("--all", action="store_true", help="auch Einstellungen/Programme (lesend)")
    a = ap.parse_args()
    _, sg = items(DEFS / "deye_sg04lp3.yaml"); _, hy = items(DEFS / "deye_hybrid.yaml"); _, p3 = items(a.p3)
    keep, used_names, used_regs = [], set(), set()
    for g, n in sg:                       # alle sg04lp3-Sensoren bleiben (passen zum Geraet)
        keep.append((g, convert(n))); used_names.add(slug(n["name"])); used_regs.add(n["registers"][0])
    if a.ids:                             # aktive Hybrid-Namen, die in HA Werte liefern, nicht verlieren
        ids = {i.split("solarman_", 1)[1] for i in json.load(open(a.ids)) if "solarman_" in i}
        for g, n in hy:
            if slug(n["name"]) in ids and slug(n["name"]) not in used_names and n["registers"][0] not in used_regs:
                pass                      # hybrid-Register existieren auf dem Geraet nicht -> bewusst entfallen
    readable = {int(k) for k in json.load(open(a.scan))["regs"]} if a.scan else None
    new = []
    for g, n in p3:
        if (g not in LIVE_GROUPS and not a.all) or "attribute" in n: continue
        if not a.all and n.get("platform") not in (None, "sensor"): continue
        if readable is not None and not all(r in readable for r in n["registers"]): continue
        r0 = n["registers"][0]
        if r0 in used_regs: continue
        if n.get("rule") not in (1, 2, 3, 4, 5, 7, 9): continue   # 6/8/10 (Bits/Datum/Raw) liefern keine Sensor-Zustaende
        if re.match(r"PV[3-8] ", n["name"]) or slug(n["name"]) in EXCLUDE: continue   # Geraet hat nur 2 MPPT
        c = convert(n); s = slug(c["name"])
        if s in used_names: c["name"] = f'{g.split("/")[0]} {c["name"]}'; s = slug(c["name"])
        k = 2
        while s in used_names: c["name"] = f'{n["name"]} {k}'; s = slug(c["name"]); k += 1
        used_names.add(s); used_regs.add(r0); new.append((g, c))
    groups = {}
    for g, c in keep + new: groups.setdefault(g, []).append(c)
    spans = [(min(c["registers"]), max(c["registers"])) for it in groups.values() for c in it]
    reqs = [{"start": s, "end": e, "mb_functioncode": 3} for s, e in requests(spans)]
    out = {"requests": reqs, "parameters": [{"group": g, "items": it} for g, it in groups.items()]}
    hdr = ("# Deye SUN-xK-SG04LP3 (3-phasig, 2 MPPT) - vollstaendig. GENERIERT von tools/build_profile.py\n"
           "# Bisherige Sensoren aus deye_sg04lp3.yaml unveraendert; neue Werte nach davidrapan/ha-solarman deye_p3.yaml (MIT).\n")
    (DEFS / "deye_sg04lp3_vollstaendig.yaml").write_text(hdr + yaml.safe_dump(out, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print("alt:", len(keep), "neu:", len(new), "requests:", [(hex(r["start"]), hex(r["end"])) for r in reqs])

main()
