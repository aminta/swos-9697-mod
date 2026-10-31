"""Host tests, tier B: the real exe code run in an x86 emulator (Unicorn) from a real memory snapshot.

A snapshot (tools/hosttest/snapshot.py) is the game's whole linear memory (32 MB, the harness's MEMDUMP) at a routine's
entry, plus the obj bases; the build's ITALIAN.syms.json (HOSTTEST_SYMS=1) names the routines and variables. A test:

    m = Machine(snapshot_dir, k)                # snapshot k of that dir (k.bin + k.json), the build from its json
    m.call('conti.ct_prep')                     # run it to its return (a sentinel return address), milliseconds
    m.u8('uefaq.SYMS.CAL_CUR') ...              # read / write memory by symbol or linear address

Flat 32-bit protected mode: a GDT with the game's flat selectors (code 160h, data 168h) so segment loads work; INT
instructions stop the run (InterruptError with EIP) unless a handler is registered (m.on_int[n] = fn(m) -> True).
Run with the venv: internal/hosttest/.venv/bin/python (Unicorn)."""
import json
import os
import struct

from unicorn import Uc, UcError, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_INTR, UC_HOOK_MEM_WRITE, \
    UC_HOOK_MEM_INVALID
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_ESI,
                               UC_X86_REG_EDI, UC_X86_REG_EBP, UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_CS,
                               UC_X86_REG_DS, UC_X86_REG_ES, UC_X86_REG_SS, UC_X86_REG_FS, UC_X86_REG_GS,
                               UC_X86_REG_GDTR, UC_X86_REG_EFLAGS)

MEMSIZE = 0x2000000                     # the snapshot: linear 0..32 MB
EXTRA = 0x2000000                       # ours above it: GDT, stack, the sentinel
GDT_AT, STACK_TOP, SENTINEL = EXTRA, EXTRA + 0xF0000, EXTRA + 0xFF000
CODE_SEL, DATA_SEL = 0x160, 0x168
REGS = dict(eax=UC_X86_REG_EAX, ebx=UC_X86_REG_EBX, ecx=UC_X86_REG_ECX, edx=UC_X86_REG_EDX, esi=UC_X86_REG_ESI,
            edi=UC_X86_REG_EDI, ebp=UC_X86_REG_EBP, esp=UC_X86_REG_ESP, eip=UC_X86_REG_EIP, eflags=UC_X86_REG_EFLAGS)


class InterruptError(Exception):
    pass


class StrayWrite(Exception):
    pass


def _desc(base, limit, access, flags=0xC):
    return struct.pack('<HHBBBB', limit & 0xFFFF, base & 0xFFFF, (base >> 16) & 0xFF, access,
                       (flags << 4) | ((limit >> 16) & 0xF), (base >> 24) & 0xFF)


class Machine:
    def __init__(self, snap_dir, k=0, syms=None):
        meta = json.load(open(os.path.join(snap_dir, f'{k}.json')))
        self.meta, self.base1, self.base2 = meta, meta['base1'], meta['base2']
        self.syms = syms or json.load(open(os.path.join(meta['build'], 'ITALIAN.syms.json')))
        self.uc = uc = Uc(UC_ARCH_X86, UC_MODE_32)
        uc.mem_map(0, MEMSIZE)
        uc.mem_write(0, open(os.path.join(snap_dir, f'{k}.bin'), 'rb').read()[:MEMSIZE])
        uc.mem_map(EXTRA, 0x100000)
        gdt = bytearray(8 * 64)                       # flat selectors at the game's numbers
        gdt[CODE_SEL:CODE_SEL + 8] = _desc(0, 0xFFFFF, 0x9A)
        gdt[DATA_SEL:DATA_SEL + 8] = _desc(0, 0xFFFFF, 0x92)
        uc.mem_write(GDT_AT, bytes(gdt))
        uc.reg_write(UC_X86_REG_GDTR, (0, GDT_AT, len(gdt) - 1, 0))
        for r in (UC_X86_REG_SS, UC_X86_REG_DS, UC_X86_REG_ES):
            uc.reg_write(r, DATA_SEL)
        uc.reg_write(UC_X86_REG_CS, CODE_SEL)
        uc.mem_write(SENTINEL, b'\xF4')               # (hlt: never reached, the code hook stops first)
        self.on_int = {}
        self.writes = []                              # (eip, address, size) of watched writes
        self.watch = []                               # [(lo, hi)]: writes there raise StrayWrite
        self.steps = 0
        uc.hook_add(UC_HOOK_INTR, self._intr)
        uc.hook_add(UC_HOOK_CODE, self._code, begin=SENTINEL, end=SENTINEL)
        uc.hook_add(UC_HOOK_MEM_WRITE, self._write)

    # --- symbols --------------------------------------------------------------------------------------------------
    def lin(self, name_or_lin):
        if isinstance(name_or_lin, int):
            return name_or_lin
        mod, lab = name_or_lin.split('.', 1)
        obj, off = self.syms[mod][lab]
        return (self.base2 if obj == 2 else self.base1) + off

    # --- memory ---------------------------------------------------------------------------------------------------
    def read(self, where, n, off=0):
        return bytes(self.uc.mem_read(self.lin(where) + off, n))

    def write(self, where, data, off=0):
        self.uc.mem_write(self.lin(where) + off, bytes(data))

    def u8(self, where, off=0):
        return self.read(where, 1, off)[0]

    def u16(self, where, off=0):
        return struct.unpack('<H', self.read(where, 2, off))[0]

    def u32(self, where, off=0):
        return struct.unpack('<I', self.read(where, 4, off))[0]

    def reg(self, name, value=None):
        if value is None:
            return self.uc.reg_read(REGS[name])
        self.uc.reg_write(REGS[name], value)

    # --- running --------------------------------------------------------------------------------------------------
    def call(self, where, *args, regs=None, max_insn=50_000_000):
        """cdecl call of a routine (asm labels take no arguments: their inputs are memory / registers); returns EAX"""
        esp = STACK_TOP
        for a in reversed(args):
            esp -= 4
            self.uc.mem_write(esp, struct.pack('<I', a & 0xFFFFFFFF))
        esp -= 4
        self.uc.mem_write(esp, struct.pack('<I', SENTINEL))
        self.uc.reg_write(UC_X86_REG_ESP, esp)
        for k, v in (regs or {}).items():
            self.reg(k, v)
        self._err = None
        try:
            self.uc.emu_start(self.lin(where), SENTINEL, count=max_insn)
        except UcError as e:
            raise RuntimeError(f'{e} at EIP {self.reg("eip"):#x} ({self.where(self.reg("eip"))})') from None
        if self._err:
            raise self._err
        if self.reg('eip') != SENTINEL:
            raise RuntimeError(f'did not return within {max_insn} instructions (EIP {self.reg("eip"):#x})')
        return self.reg('eax')

    def where(self, lin):
        """obj1+offset (and the nearest symbol below it) of a linear address"""
        if not self.base1 <= lin < self.base2:
            return f'lin {lin:#x}'
        off = lin - self.base1
        best = max(((v[1], f'{m}.{k}') for m, d in self.syms.items() for k, v in d.items()
                    if v[0] in (0, 1) and v[1] <= off), default=(0, '?'))
        return f'obj1+{off:#x} {best[1]}+{off - best[0]:#x}'

    def _code(self, uc, addr, size, data):
        uc.emu_stop()

    def _intr(self, uc, intno, data):
        eip = uc.reg_read(UC_X86_REG_EIP)
        fn = self.on_int.get(intno)
        if fn and fn(self):
            return
        self._err = InterruptError(f'INT {intno:#x} at {self.where(eip)}')
        uc.emu_stop()

    def _write(self, uc, access, addr, size, value, data):
        for lo, hi in self.watch:
            if lo <= addr < hi:
                eip = uc.reg_read(UC_X86_REG_EIP)
                self.writes.append((eip, addr, size))
                self._err = StrayWrite(f'write {size} B at {addr:#x} from {self.where(eip)}')
                uc.emu_stop()
