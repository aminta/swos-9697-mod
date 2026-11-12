/* swefile.h - the engine's file layer v1 (4.2, MC 12/11; internal/handoff/swe-file-layer.md).
 *
 * DOS files from engine code (obj4), straight through int 21h as DOS/4GW extends it (32-bit offsets, counts over
 * 64 KB: the extender splits them through its transfer buffer) - no call into the game's Watcom runtime, so no obj1
 * code and no obj1 fixups. Every function returns a code, never asserts:
 *   >= 0  success (a handle, a byte count, 0)
 *   < 0   -(the DOS error code): -2 file not found, -3 path not found, -4 no handles, -5 access denied, ...
 *         SWEF_ESHORT  a write that wrote fewer bytes than asked (disk full)
 *         SWEF_ENAME   a name too long for swe_save_atomic's temporary name
 * swe_fread returns the bytes read: fewer than asked = the end of the file, not an error.
 *
 * swe_save_atomic(name, buf, len): writes NAME.MK$ (NAME's extension replaced), closes it, renames it NAME.MK! (the
 * mark of a complete file), removes NAME, renames NAME.MK! to NAME. Any error before the remove leaves NAME as it
 * was (and removes the temporary file); a power cut leaves the old NAME, or the new one, or - in the remove..rename
 * window only - no NAME and a complete NAME.MK!. A loader calls swe_recover(name) before swe_fopen_r: it removes a
 * NAME.MK$ (never complete: a cut write) and, when a NAME.MK! is there, makes it NAME (it wins over a NAME still
 * there: the cut fell between the MK! rename and the remove). The 4 cut points (internal/handoff/swe-file-layer.md):
 *   1 in the MK$ write / before MK$ -> MK!:  NAME old (or none), MK$ partial    -> recover: old (or none)
 *   2 after MK$ -> MK!, before remove NAME:  NAME old, MK! complete            -> recover: new
 *   3 after remove NAME, before MK! -> NAME: no NAME, MK! complete             -> recover: new
 *   4 after MK! -> NAME:                     NAME new                          -> recover: new (nothing to do)
 * (MC's v1 sequence had no MK! step: a first save cut in its write left a partial MK$ that a recover could not
 * tell from a complete one.)
 *
 * One copy in the exe: tools/swefile.c (SWEFILE_IMPL), linked by swefile.py at obj4+swreg.SWEFILE_AT..SWEFILE_END
 * (page 18, MC 12/11) when a consumer sets swe.SWEFILE (or in SWEFILE_TEST=1 builds); a consumer #includes this file
 * for the prototypes and links to swefile's symbols (cobj.link externs, swefile.LABELS), as cstack.h. */
#ifndef SWEFILE_H
#define SWEFILE_H

#define SWEF_ESHORT (-0x101)
#define SWEF_ENAME (-0x102)
#define SWEF_NAMEMAX 80                         /* the temporary name's buffer (with the 0) */

int swe_fopen_r(const char *name);
int swe_fopen_w(const char *name);              /* create, or truncate an existing file */
int swe_fread(int h, void *buf, unsigned int n);
int swe_fwrite(int h, const void *buf, unsigned int n);
int swe_fclose(int h);
int swe_fremove(const char *name);
int swe_frename(const char *from, const char *to);  /* removes `to` first (DOS renames onto no existing file) */
int swe_tmpname(const char *name, char *out, char last);   /* NAME.EXT -> NAME.MK<last> in out (SWEF_NAMEMAX), 0 /
                                                               SWEF_ENAME */
int swe_save_atomic(const char *name, const void *buf, unsigned int len);
int swe_recover(const char *name);              /* MK$ removed; MK! -> NAME: 1, nothing to do: 0, an error: < 0 */

#ifdef SWEFILE_IMPL
__attribute__((noinline)) static int swef_dos(unsigned int ax, unsigned int bx, unsigned int cx, unsigned int dx, unsigned int di)
{
    unsigned int cf, wide = ax - 0x3F00 < 0x200;   /* (3Fh / 40h: a 32-bit count; the rest: AX alone) */
    __asm__ volatile("int $0x21\n\tsbbl %%esi, %%esi"       /* (flat model: ES = DS, 56h's ES:EDI as is) */
                     : "+a"(ax), "+b"(bx), "+c"(cx), "+d"(dx), "+D"(di), "=S"(cf) : : "cc", "memory");
    if (cf)
        return (ax & 0xFFFF) ? -(int)(ax & 0xFFFF) : -1;
    return (int)(wide ? ax : ax & 0xFFFF);
}

int swe_fopen_r(const char *name)
{
    return swef_dos(0x3D00, 0, 0, (unsigned int)name, 0);
}

int swe_fopen_w(const char *name)
{
    return swef_dos(0x3C00, 0, 0, (unsigned int)name, 0);
}

int swe_fread(int h, void *buf, unsigned int n)
{
    return n ? swef_dos(0x3F00, h, n, (unsigned int)buf, 0) : 0;
}

int swe_fwrite(int h, const void *buf, unsigned int n)
{
    if (!n)
        return 0;                               /* (a 0-byte write would truncate the file there) */
    int r = swef_dos(0x4000, h, n, (unsigned int)buf, 0);
    return r < 0 ? r : (unsigned int)r != n ? SWEF_ESHORT : r;
}

int swe_fclose(int h)
{
    int r = swef_dos(0x3E00, h, 0, 0, 0);
    return r < 0 ? r : 0;
}

int swe_fremove(const char *name)
{
    int r = swef_dos(0x4100, 0, 0, (unsigned int)name, 0);
    return r < 0 ? r : 0;
}

int swe_frename(const char *from, const char *to)
{
    int r = swe_fremove(to);
    if (r < 0 && r != -2)                       /* (-2: no such file, nothing to remove) */
        return r;
    r = swef_dos(0x5600, 0, 0, (unsigned int)from, (unsigned int)to);
    return r < 0 ? r : 0;
}

int swe_tmpname(const char *name, char *out, char last)
{
    int n = 0, dot = -1;
    for (; name[n]; n++) {
        if (n >= SWEF_NAMEMAX - 5)
            return SWEF_ENAME;
        out[n] = name[n];
        if (name[n] == '.')
            dot = n;
        else if (name[n] == '\\' || name[n] == '/' || name[n] == ':')
            dot = -1;
    }
    if (dot >= 0)
        n = dot;
    out[n] = '.', out[n + 1] = 'M', out[n + 2] = 'K', out[n + 3] = last, out[n + 4] = 0;
    return 0;
}

int swe_save_atomic(const char *name, const void *buf, unsigned int len)
{
    char tmp[SWEF_NAMEMAX], done[SWEF_NAMEMAX];
    int r = swe_tmpname(name, tmp, '$');
    if (r < 0)
        return r;
    swe_tmpname(name, done, '!');
    int h = swe_fopen_w(tmp);
    if (h < 0)
        return h;
    r = swe_fwrite(h, buf, len);
    int c = swe_fclose(h);
    if (r >= 0 && c < 0)
        r = c;
    if (r < 0) {
        swe_fremove(tmp);                       /* (NAME untouched) */
        return r;
    }
    r = swe_frename(tmp, done);
    if (r < 0) {
        swe_fremove(tmp);
        return r;
    }
    return swe_frename(done, name);
}

int swe_recover(const char *name)
{
    char tmp[SWEF_NAMEMAX];
    int r = swe_tmpname(name, tmp, '$');
    if (r < 0)
        return r;
    swe_fremove(tmp);                           /* (a MK$ is never complete: a cut write) */
    swe_tmpname(name, tmp, '!');
    int h = swe_fopen_r(tmp);
    if (h < 0)
        return h == -2 ? 0 : h;
    swe_fclose(h);
    r = swe_frename(tmp, name);                 /* (MK! complete: it wins over a NAME still there - MC 12/11) */
    return r < 0 ? r : 1;
}
#endif
#endif
