#!/usr/bin/env python3
"""
M8TWY Solar Data Fetcher
Fetches N0NBH solar XML and writes it as JSON to ~/shack/solar.json
Run on a cron job every 3 hours.
"""
import urllib.request
import xml.etree.ElementTree as ET
import json
import os
import sys
from datetime import datetime, timezone

OUTPUT = os.path.expanduser("~/shack/solar.json")

def get(root, tag):
    el = root.find(tag)
    return el.text.strip() if el is not None and el.text else "—"

def fetch():
    url = "https://www.hamqsl.com/solarxml.php"
    req = urllib.request.Request(url, headers={"User-Agent": "ShackDash/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = r.read()

    root = ET.fromstring(data).find("solardata")

    bands = {}
    for band in root.findall("calculatedconditions/band"):
        name = band.get("name")
        time = band.get("time")
        if name not in bands:
            bands[name] = {}
        bands[name][time] = band.text.strip() if band.text else "—"

    vhf = []
    for p in root.findall("calculatedvhfconditions/phenomenon"):
        vhf.append({
            "name": p.get("name"),
            "loc":  str(p.get("location")),
            "val":  p.text.strip() if p.text else "—"
        })

    output = {
        "fetched":     datetime.now(timezone.utc).strftime("%d %b %Y %H%MZ"),
        "updated":     get(root, "updated"),
        "solarflux":   get(root, "solarflux"),
        "aindex":      get(root, "aindex"),
        "kindex":      get(root, "kindex"),
        "sunspots":    get(root, "sunspots"),
        "xray":        get(root, "xray"),
        "geomagfield": get(root, "geomagfield"),
        "signalnoise": get(root, "signalnoise"),
        "protonflux":  get(root, "protonflux"),
        "electonflux": get(root, "electonflux"),
        "aurora":      get(root, "aurora"),
        "normalization": get(root, "normalization"),
        "latdegree":   get(root, "latdegree"),
        "bands":       bands,
        "vhf":         vhf,
    }

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w") as f:
        json.dump(output, f, indent=2)

    print(f"OK — written to {OUTPUT}")
    print(f"VHF phenomena found: {[v['name']+'|'+v['loc'] for v in vhf]}")

if __name__ == "__main__":
    try:
        fetch()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
