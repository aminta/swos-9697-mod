"""68000 disassembly of the Amiga image (capstone). usage: m68dis.py ADDR [N]"""
import sys, capstone
sys.path.insert(0, __import__('os').path.dirname(__file__)); from amimg import Img, BASE
md = capstone.Cs(capstone.CS_ARCH_M68K, capstone.CS_MODE_BIG_ENDIAN | capstone.CS_MODE_M68K_000)
def dis(m, a, n=40):
    out = []
    for i in md.disasm(m.d[a-BASE:a-BASE+n*10], a):
        out.append(f'{i.address:06x}  {i.mnemonic} {i.op_str}')
        if len(out) >= n: break
    return out
if __name__ == '__main__':
    print('\n'.join(dis(Img(), int(sys.argv[1], 16), int(sys.argv[2]) if len(sys.argv) > 2 else 40)))
