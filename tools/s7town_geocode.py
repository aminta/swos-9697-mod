"""Geocode club towns with OpenStreetMap Nominatim (S7 redraw, Panchina 15/11): `python3 tools/s7town_geocode.py in.txt out.csv`,
in.txt = one `key|town` per line, out.csv = key,town,lat,lon (2 decimals, the town's centre as Nominatim gives it). One request a
second (the usage policy), a generic user agent, countrycodes=it, every point inside the Italy box (35.4-47.2 N, 6.5-18.6 E) or the
town is listed as FAILED. Only town names go out. The result is reviewed by eye and merged into tools/s7pack_towns.csv."""
import csv
import json
import sys
import time
import urllib.parse
import urllib.request

BOX = (35.4, 47.2, 6.5, 18.6)


def geocode(town):
    r = []
    for kw in ({'city': town}, {'q': town + ', Italia'}):      # (the structured city= query returns the COMUNE; a free-text one can return the province's point)
        u = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode(dict(kw, format='json', limit=1, countrycodes='it'))
        r = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'geocode-script/1.0'}), timeout=30).read())
        if r:
            break
        time.sleep(1.1)
    return (round(float(r[0]['lat']), 2), round(float(r[0]['lon']), 2), r[0].get('display_name', '')) if r else None


def main(src, dst):
    out, bad = [], []
    for ln in open(src, encoding='utf-8'):
        if '|' not in ln:
            continue
        key, town = ln.strip().split('|', 1)
        try:
            g = geocode(town)
        except Exception as e:
            g = None
            print('ERR', key, town, e, file=sys.stderr)
        time.sleep(1.1)
        if not g or not (BOX[0] <= g[0] <= BOX[1] and BOX[2] <= g[1] <= BOX[3]):
            bad.append((key, town, g))
            continue
        out.append((key, town, g[0], g[1], g[2][:70]))
    with open(dst, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['key', 'town', 'lat', 'lon', 'osm'])
        w.writerows(out)
    print(len(out), 'ok', len(bad), 'FAILED', bad)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
