"""Parse the 1996-97 NSL line-ups (ozfootball.net archive, Wayback copies in internal/nsl9697) into appearance counts."""
import re, html, glob, os, collections

FIXES = {'(Billy Mitroulas 45 (sent off 93)': '(Billy Mitroulas 45) (sent off 93)'}   # bracket missing in the source
SRC = os.path.join(os.path.dirname(__file__), '..', 'internal', 'nsl9697')


def matches(files=None):
    """Yield (file, date, team, starters, subs) for every team line-up found."""
    for f in sorted(files or glob.glob(os.path.join(SRC, '*.html'))):
        t = open(f, encoding='latin-1').read()
        date = None
        for cell in re.split(r'<T[DH]\b', t, flags=re.I):
            m = re.search(r'Played \(([\d/]+)\)', cell)
            if m:
                date = m.group(1)
            m = re.match(r'[^>]*>\s*<B>([^<]+)</B>\s*<BR>(.*?)(?:<BR>\s*<I>|</T[DR]>|$)', cell, re.S | re.I)
            if not m:
                continue
            team = html.unescape(m.group(1)).strip()
            body = html.unescape(re.sub(r'<[^>]+>', ' ', m.group(2)))
            body = ' '.join(body.split())
            for a, b in FIXES.items():
                body = body.replace(a, b)
            if body.count(',') < 6:
                continue
            body = re.sub(r'\s+\)', ')', body)
            body = re.sub(r'\(([^()]*?\d+)(?=\s*(?:,|$))', r'(\1)', body)          # '(Billy Mitroulas 45' unclosed
            subs, start = [], body
            while '(' in start:                        # nested: '(David Milin (Tomy Lemezina 77) 60)'
                subs += re.findall(r'\(([^()]*?)\s*\d+\s*\)', start)
                new = re.sub(r'\s+\)', ')', re.sub(r'\([^()]*\)', '', start))
                if new == start:
                    start = start.replace('(', ' ')
                    break
                start = new
            subs = [' '.join(s.split()) for s in subs if not s.lower().startswith(('sent', 'og', 'pen', 'to '))]
            starters = []
            for p in (p.strip() for p in start.split(',')):
                w = p.split()
                if len(w) == 4:                        # 'Glen Gwynne Matt Bell': a comma missing in the source
                    starters += [' '.join(w[:2]), ' '.join(w[2:])]
                elif p:
                    starters.append(' '.join(w))
            yield os.path.basename(f), date, team, starters, [s.strip() for s in subs]


def appearances(files=None):
    app = collections.defaultdict(collections.Counter)
    for _, _, team, st, sb in matches(files):
        for p in st:
            app[team][p] += 1
        for p in sb:
            app[team][p] += 1
    return app


if __name__ == '__main__':
    app = appearances([f for f in glob.glob(os.path.join(SRC, 'Round*.html'))] + [os.path.join(SRC, 'Playoff.html')])
    for team in sorted(app):
        c = app[team]
        print(f'{team} ({len(c)}): ' + ', '.join(f'{p} {n}' for p, n in c.most_common()))
