#!/usr/bin/env python3
"""
M8TWY Setup Wizard
Looks up lat/lon from postcode via postcodes.io then calculates
Maidenhead, WAB, OS grid, CQ Zone and ITU Zone locally.
"""
import urllib.request
import json
import os

SHACK_JSON = os.path.expanduser('~/shack/shack.json')

# ── BNG 100km grid squares ────────────────────────────────────────────────────
BNG = {
    (0,0):'SV',(1,0):'SW',(2,0):'SX',(3,0):'SY',(4,0):'SZ',(5,0):'TV',
    (0,1):'SQ',(1,1):'SR',(2,1):'SS',(3,1):'ST',(4,1):'SU',(5,1):'TQ',(6,1):'TR',
    (0,2):'SL',(1,2):'SM',(2,2):'SN',(3,2):'SO',(4,2):'SP',(5,2):'TL',(6,2):'TM',
    (0,3):'SF',(1,3):'SG',(2,3):'SH',(3,3):'SJ',(4,3):'SK',(5,3):'TF',(6,3):'TG',
    (0,4):'SA',(1,4):'SB',(2,4):'SC',(3,4):'SD',(4,4):'SE',(5,4):'TA',(6,4):'TB',
    (0,5):'NV',(1,5):'NW',(2,5):'NX',(3,5):'NY',(4,5):'NZ',(5,5):'OV',(6,5):'OW',
    (0,6):'NQ',(1,6):'NR',(2,6):'NS',(3,6):'NT',(4,6):'NU',(5,6):'OQ',(6,6):'OR',
    (0,7):'NL',(1,7):'NM',(2,7):'NN',(3,7):'NO',(4,7):'NP',
    (0,8):'NF',(1,8):'NG',(2,8):'NH',(3,8):'NJ',(4,8):'NK',
    (0,9):'NA',(1,9):'NB',(2,9):'NC',(3,9):'ND',(4,9):'NE',
    (1,10):'HW',(2,10):'HX',(3,10):'HY',(4,10):'HZ',
    (1,11):'HR',(2,11):'HS',(3,11):'HT',(4,11):'HU',
    (2,12):'HN',(3,12):'HO',(4,12):'HP',
}

# ── Postcode lookup ───────────────────────────────────────────────────────────
def lookup_postcode(postcode):
    pc  = postcode.replace(' ', '').upper()
    url = f'https://api.postcodes.io/postcodes/{pc}'
    req = urllib.request.Request(url, headers={'User-Agent': 'ShackDash/1.0'})
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
    if data['status'] != 200:
        raise ValueError(f"Postcode not found: {postcode}")
    res = data['result']
    # QTH: prefer parish, fall back to admin_ward, then admin_district
    qth = (res.get('parish') or
           res.get('admin_ward') or
           res.get('admin_district') or '')
    return {
        'lat':      res['latitude'],
        'lon':      res['longitude'],
        'county':   res.get('admin_county') or res.get('admin_district', ''),
        'country':  res.get('country', 'England'),
        'eastings': res.get('eastings') or 0,
        'northings':res.get('northings') or 0,
        'qth':      qth,
    }

# ── Maidenhead locator ────────────────────────────────────────────────────────
def calc_maidenhead(lat, lon):
    lon += 180
    lat += 90
    field_lon = int(lon / 20)
    field_lat = int(lat / 10)
    sq_lon    = int((lon % 20) / 2)
    sq_lat    = int(lat % 10)
    sub_lon   = int(((lon % 20) % 2) * 12)
    sub_lat   = int((lat % 1) * 24)
    return (
        chr(ord('A') + field_lon) +
        chr(ord('A') + field_lat) +
        str(sq_lon) + str(sq_lat) +
        chr(ord('a') + sub_lon) +
        chr(ord('a') + sub_lat)
    )

# ── WAB square ────────────────────────────────────────────────────────────────
def calc_wab(e, n):
    if not e or not n:
        return ''
    col    = int(e / 100000)
    row    = int(n / 100000)
    prefix = BNG.get((col, row), '')
    if not prefix:
        return ''
    e10 = int((e % 100000) / 10000)
    n10 = int((n % 100000) / 10000)
    return f"{prefix}{e10}{n10}"

# ── OS grid reference ─────────────────────────────────────────────────────────
def calc_os_grid(e, n):
    if not e or not n:
        return ''
    col    = int(e / 100000)
    row    = int(n / 100000)
    prefix = BNG.get((col, row), '')
    if not prefix:
        return ''
    return f"{prefix} {int(e % 100000):05d} {int(n % 100000):05d}"

# ── CQ / ITU zones (global approximation) ────────────────────────────────────
def calc_cq_zone(lat, lon):
    """Approximate CQ zone from lat/lon - covers major regions"""
    if lat > 60 and -170 < lon < -50:
        return '1' if lon < -130 else ('2' if lon < -60 else '4')
    if 25 < lat <= 60 and -170 < lon < -50:
        if lon < -100: return '3' if lat > 49 else '4' if lat > 49 else '5'
        return '4' if lat > 49 else '5'
    if 10 < lat <= 25 and -120 < lon < -60: return '7'
    if -60 < lat <= 13 and -90 < lon < -30:
        return '9' if lat > 0 else ('10' if lon < -60 else '11')
    if 10 < lat <= 25 and -90 < lon < -60: return '8'
    if 36 < lat <= 75 and -12 < lon < 40: return '14'
    if 36 < lat <= 45 and 15 < lon < 40: return '20'
    if 0 < lat <= 40 and 40 < lon < 60: return '21'
    if 0 < lat <= 36 and -20 < lon < 55: return '33'
    if -40 < lat <= 0 and -20 < lon < 55: return '38' if lon > 40 else '35'
    if 50 < lat and 40 < lon < 100: return '17'
    if 50 < lat and 100 < lon < 140: return '18' if lon < 120 else '19'
    if 50 < lat and 140 < lon: return '19'
    if 0 < lat <= 50 and 40 < lon < 80: return '21'
    if 0 < lat <= 50 and 80 < lon < 100: return '26'
    if 0 < lat <= 25 and 100 < lon < 140: return '26' if lon < 115 else '28'
    if 25 < lat <= 50 and 100 < lon < 135: return '24' if lon < 115 else '25'
    if 30 < lat <= 50 and 125 < lon < 146: return '25'
    if -10 < lat <= 25 and 95 < lon < 140: return '26' if lon < 115 else '28'
    if -50 < lat <= 0 and 110 < lon: return '29'
    return '14'  # fallback

def calc_itu_zone(lat, lon):
    """Approximate ITU zone from lat/lon"""
    # Europe
    if 36 < lat <= 75 and -12 < lon < 40: return '27' if lat > 50 else '28'
    # North America
    if 25 < lat <= 60 and -130 < lon < -50: return '7' if lon < -100 else '8'
    # Default rough zones
    if lat > 60: return '1' if lon < 0 else '20'
    if lat > 0 and lon < -30: return '8'
    if lat > 0 and lon < 40: return '28'
    if lat > 0 and lon < 100: return '41'
    if lat > 0: return '50'
    return '58'

# ── Main ──────────────────────────────────────────────────────────────────────
def parse_latlon(text):
    """Try to parse 'lat,lon' format e.g. '51.5,-0.1'"""
    import re
    m = re.match(r'^\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*$', text.strip())
    if m:
        return float(m.group(1)), float(m.group(2))
    return None

def calculate_all(callsign, name, postcode, qth=''):
    # Check if input is lat,lon rather than a postcode
    latlon = parse_latlon(postcode)
    if latlon:
        lat, lon = latlon
        pc = {
            'lat': lat, 'lon': lon,
            'eastings': 0, 'northings': 0,
            'qth': qth, 'county': '', 'country': ''
        }
        # Try to get location name via reverse geocode
        try:
            import urllib.request as _ur, json as _js
            req = _ur.Request(
                f'https://api.postcodes.io/postcodes?lon={lon}&lat={lat}&limit=1',
                headers={'User-Agent': 'ShackDash/1.0'})
            with _ur.urlopen(req, timeout=8) as r:
                res = _js.loads(r.read())
            if res.get('result'):
                pc['qth'] = res['result'][0].get('parish', '') or res['result'][0].get('admin_district', '') or qth
                pc['county'] = res['result'][0].get('admin_county', '')
                pc['country'] = res['result'][0].get('country', '')
        except Exception:
            pass
    else:
        pc  = lookup_postcode(postcode)
    lat = pc['lat']
    lon = pc['lon']
    e   = pc['eastings']
    n   = pc['northings']

    is_uk = e != 0 and n != 0  # UK postcodes provide eastings/northings
    return {
        'callsign':    callsign.upper(),
        'name':        name,
        'qth':         pc.get('qth', '') or qth,
        'county':      pc['county'],
        'country':     pc['country'],
        'lat':         f"{abs(lat):.4f}° {'N' if lat >= 0 else 'S'}",
        'lon':         f"{abs(lon):.4f}° {'E' if lon >= 0 else 'W'}",
        'maidenhead':  calc_maidenhead(lat, lon),
        'wab':         calc_wab(e, n) if is_uk else 'N/A',
        'os_grid':     calc_os_grid(e, n) if is_uk else 'N/A',
        'cq_zone':     calc_cq_zone(lat, lon),
        'itu_zone':    calc_itu_zone(lat, lon),
        'licence':     '',
        'qrz':         f'https://qrz.com/db/{callsign.upper()}',
        # Equipment fields intentionally omitted — save_shack preserves existing values
    }

def save_shack(data):
    """Merge new location data with existing shack.json, preserving equipment fields."""
    existing = {}
    try:
        with open(SHACK_JSON) as f:
            existing = json.load(f)
    except Exception:
        pass

    # Always preserve equipment and operational fields from existing data
    preserve = ['rigs','antenna','antenna2',
                'qsl','modes','licence']
    for key in preserve:
        if existing.get(key):
            data[key] = existing[key]
        elif key not in data:
            # Sensible defaults if no existing data
            defaults = {
                'rigs': [{'label': 'Rig 1', 'value': ''}],
                'antenna': '', 'antenna2': '', 'qsl': 'QRZ Logbook',
                'modes': 'FM', 'licence': ''
            }
            data[key] = defaults.get(key, '')

    with open(SHACK_JSON, 'w') as f:
        json.dump(data, f, indent=2)
    return data
