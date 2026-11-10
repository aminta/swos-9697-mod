/* cstack.h - a C stack of its own for engine code in the exe (4.2 engine P2, motore-sr-stage.md).
 *
 * The game's whole DOS stack is 4043 B (Watcom _STACKLOW obj2+0xC4E55 .. _STACKTOP obj2+0xC5E20, the same in every
 * snapshot) and the game itself goes 2.5 KB deep: sr_group_draw alone needs up to 11.5 KB (64 clubs). cstack_call(fn,
 * arg) runs fn(arg) on a block of CSTACK_SIZE bytes at the symbol CSTACK_SYM, then comes back to the caller's stack.
 *
 * One copy in the exe: swe.c defines the block (SWE_CSTACK, obj4's zero-fill tail, outside SWE_ARENA) and #includes
 * this file with CSTACK_IMPL; any other consumer #includes it for the prototype only and gets cstack_call from swe's
 * symbols (cobj.link externs). swe_init() calls cstack_init() before any cstack_call (DOS/4GW zeroes no tail).
 *
 * The block's own words hold the state:
 *   +0..1023            the guard: 256 dwords CSTACK_GUARD, filled on each outer call and checked after it (one
 *                       word is not enough: a recursion's frames can step over it without writing it)
 *   CSTACK_SIZE - 4     depth (calls in progress)
 *   CSTACK_SIZE - 8     the caller's ESP (outer call)
 *   CSTACK_SIZE - 12    overflows seen (sticky: the guard found broken after an outer call)
 *   below that          the stack, painted CSTACK_PAINT by cstack_init (cstack_high: the deepest use so far)
 * A call made while one is in progress (fn calling cstack_call again) stays on the block; one made from outside the
 * block while the depth is not 0 (a broken depth, or a call from an interrupt) is refused: fn is not run, -4.
 * Interrupts stay enabled: ESP stays in the same flat segment. fn is cdecl; cstack_call returns its value (an overflow
 * is not in it: read cstack_overflows()).
 * Stack probes: the game is asm (no Watcom __STK / __CHK on the paths the engine calls). Were a probe ever run on the
 * block, it compares ESP with _STACKLOW, and the block is above it (RC3: obj4 at linear 0x61A000, _STACKLOW 0x42BE55 -
 * DOS/4GW loads obj4 after obj2), so it passes. */
#ifndef CSTACK_H
#define CSTACK_H

#define CSTACK_SIZE 16384
#define CSTACK_GUARD 0x4B435453                 /* 'STCK' */
#define CSTACK_GUARDW 256                       /* guard dwords (1 KB) */
#define CSTACK_PAINT 0xA5
#define CSTACK_REFUSED (-4)
#ifndef CSTACK_SYM
#define CSTACK_SYM CSTACK
#endif

int cstack_call(int (*fn)(void *), void *arg);
void cstack_init(void);
int cstack_high(void);
int cstack_overflows(void);

#ifdef CSTACK_IMPL
extern unsigned char CSTACK_SYM[];

void cstack_init(void)
{
    volatile unsigned char *s = CSTACK_SYM;     /* (volatile: no memset call for clang to emit) */
    for (int i = 0; i < CSTACK_SIZE - 12; i++)
        s[i] = CSTACK_PAINT;
    for (int i = CSTACK_SIZE - 12; i < CSTACK_SIZE; i++)
        s[i] = 0;
}

int cstack_high(void)                           /* the deepest use since cstack_init, in bytes (the guard not counted) */
{
    const volatile unsigned char *s = CSTACK_SYM;
    int i = 4 * CSTACK_GUARDW;
    while (i < CSTACK_SIZE - 12 && s[i] == CSTACK_PAINT)
        i++;
    return CSTACK_SIZE - 12 - i;
}

int cstack_overflows(void)                      /* the outer calls that found the guard broken, since cstack_init */
{
    return *(const volatile int *)(CSTACK_SYM + CSTACK_SIZE - 12);
}

#define CSTACK_S_(x) #x
#define CSTACK_S(x) CSTACK_S_(x)
#define CSTACK_B CSTACK_S(CSTACK_SYM)
#define CSTACK_T(off) CSTACK_B "+" CSTACK_S(CSTACK_SIZE) off
__asm__(
    ".globl cstack_call\n"
    "cstack_call:\n"
    "\tmovl 4(%esp), %eax\n"
    "\tmovl 8(%esp), %edx\n"
    "\tcmpl $0, " CSTACK_T("-4") "\n"
    "\tjne 1f\n"
    "\tmovl %esp, " CSTACK_T("-8") "\n"
    "\tmovl $" CSTACK_T("-12") ", %esp\n"
    "\tpushl %edi\n"
    "\tpushl %eax\n"
    "\tmovl $" CSTACK_B ", %edi\n"              /* arm the guard */
    "\tmovl $" CSTACK_S(CSTACK_GUARDW) ", %ecx\n"
    "\tmovl $" CSTACK_S(CSTACK_GUARD) ", %eax\n"
    "\tcld\n"
    "\trep stosl\n"
    "\tpopl %eax\n"
    "\tincl " CSTACK_T("-4") "\n"
    "\tpushl %edx\n"
    "\tcall *%eax\n"
    "\taddl $4, %esp\n"
    "\tdecl " CSTACK_T("-4") "\n"
    "\tmovl %eax, %edx\n"
    "\tmovl $" CSTACK_B ", %edi\n"              /* check it */
    "\tmovl $" CSTACK_S(CSTACK_GUARDW) ", %ecx\n"
    "\tmovl $" CSTACK_S(CSTACK_GUARD) ", %eax\n"
    "\trepe scasl\n"
    "\tje 2f\n"
    "\tincl " CSTACK_T("-12") "\n"
    "2:\tmovl %edx, %eax\n"
    "\tpopl %edi\n"
    "\tmovl " CSTACK_T("-8") ", %esp\n"
    "\tret\n"
    "1:\tcmpl $" CSTACK_B ", %esp\n"            /* nested: only from inside the block */
    "\tjb 3f\n"
    "\tcmpl $" CSTACK_T("-12") ", %esp\n"
    "\tjae 3f\n"
    "\tincl " CSTACK_T("-4") "\n"
    "\tpushl %edx\n"
    "\tcall *%eax\n"
    "\taddl $4, %esp\n"
    "\tdecl " CSTACK_T("-4") "\n"
    "\tret\n"
    "3:\tmovl $" CSTACK_S(CSTACK_REFUSED) ", %eax\n"
    "\tret\n");
#endif

#endif
