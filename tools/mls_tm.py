"""Parse the Transfermarkt MLS 1997 squad statistics pages (internal/mls97/<club>.apps.html, saison 1996 = MLS 1997)."""
import glob, html, os, re

SRC = os.path.join(os.path.dirname(__file__), '..', 'internal', 'mls97')


def squad(path):
    t = open(path, encoding='utf-8', errors='ignore').read()
    out = []
    for row in re.split(r'<tr class="(?:odd|even)">', t)[1:]:
        m = re.search(r'<td class="hauptlink">.*?title="([^"]+)" href="/[^"]+/profil/spieler/\d+"', row, re.S)
        p = re.search(r'</tr><tr><td>([^<]+)</td></tr></table>', row)
        if not m or not p:
            continue
        nats = re.findall(r'title="([^"]+)" alt="[^"]*" class="flaggenrahmen"', row)
        cells = re.findall(r'<td[^>]*class="zentriert[^"]*"[^>]*>([^<]*)</td>', row)
        mins = re.search(r'<td class="rechts ">([\d.]+)\'</td>', row)
        apps = cells[2] if len(cells) > 2 else '-'
        out.append(dict(name=html.unescape(m.group(1)), pos=p.group(1).strip(), nat=nats[0] if nats else '',
                        apps=int(apps) if apps.isdigit() else 0,
                        mins=int(mins.group(1).replace('.', '')) if mins else 0))
    return out


if __name__ == '__main__':
    for f in sorted(glob.glob(os.path.join(SRC, '*.apps.html'))):
        s = squad(f)
        print(os.path.basename(f), len(s), [(x['name'], x['pos'][:3], x['nat'][:3], x['apps'], x['mins']) for x in s[:5]])
