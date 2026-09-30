"""Dump the db bytes of a data label from swos.asm (ENGLISH.EXE disassembly)."""
import re, sys
ASM = __file__.rsplit('/', 2)[0] + '/ref/swos.asm'

def label_bytes(name, n):
    out = []
    started = False
    for line in open(ASM, encoding='latin1'):
        s = line.split(';')[0].rstrip()
        if not started:
            if re.match(rf'^{name}\s+db\b', s):
                started = True
                s = s[len(name):]
            else:
                continue
        elif re.match(r'^[A-Za-z_]\w*\s+d[bwd]\b', s) and not s.startswith(('db', 'dw', 'dd')):
            break
        m = re.match(r'^\s*db\s+(.*)$', s)
        if not m:
            if s.strip() == '':
                continue
            break
        for tok in re.split(r',(?=(?:[^\']*\'[^\']*\')*[^\']*$)', m.group(1)):
            tok = tok.strip()
            d = re.match(r'(\S+)\s+dup\((\S+)\)', tok)
            if d:
                out += [conv(d.group(2))] * conv(d.group(1))
            elif tok.startswith("'"):
                out += list(tok.strip("'").encode('latin1'))
            else:
                out.append(conv(tok))
        if len(out) >= n:
            break
    return out[:n]

def conv(t):
    t = t.strip()
    neg = t.startswith('-')
    t = t.lstrip('-')
    v = int(t[:-1], 16) if t.lower().endswith('h') else int(t)
    return (-v) & 0xff if neg else v

if __name__ == '__main__':
    b = label_bytes(sys.argv[1], int(sys.argv[2]))
    for i in range(0, len(b), 16):
        print(f'{i:3d}: ' + ' '.join(f'{x:02x}' for x in b[i:i+16]))
