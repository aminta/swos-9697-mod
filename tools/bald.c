/* 4.0.5 bald heads. The look of each variant is data (blond.LOOKS -> look_flags' SHk / SKk / EGk macros below; look
   0 receding light, 1 receding dark, 2 shaved light, 3 shaved dark):
   - shape 0 = 'E' receding (Davide 30/10, internal/design/bald-mock/variants-20261030 V_E): the hair's top row turns
     skin, and so do the second row's hair pixels with a pixel on both sides; the rest keeps the player's hair colour;
   - shape 1 = 'oval' (round7 row 4, Marco + Davide 30/10): an egg over the head's rows (as wide as the head's widest row,
     20 % narrower below its middle) in ONE colour, the face included (the eyes, raw 1 / 2, kept); outside it the head's
     hair / skin / black pixels go transparent.
   bald_c reshapes one copied RAW player sprite (1 quad = 16 pixels wide, 8 bytes per line, 4-bit pixels, high nibble
   first) in place, before the team's colour conversion: raw hair 13 / 9 / 12, raw skin 6 / 5 / 4. A skull colour 7 is
   the NEW skin tone: bald_c paints it in raw 13 (other hair 13 -> 9), the variant's own conversion table (blond.py:
   face 0 / 2 with 13 -> 7) makes it nibble 7 - raw 7 is a kit colour, but no conversion outputs 7 otherwise - and
   DrawSprite16Pixels draws nibble 7 of these sets as the variant's palette index (pal_init's table, blond pal_setup).
   In the half / EGA mode (planar sprites, no table) no tone: the variant's EGA colour instead.
   bald_icon: the face icons 1910 / 1911 (converted menu colours: hair 3) with the same shape, in the icon's own skin
   (the menus keep two tones). pal_init: the remap table of DrawSprite16Pixels (see LUTP). */
typedef unsigned char u8;

/* the four looks (blond.look_flags): 0 receding light, 1 receding dark, 2 shaved light, 3 shaved dark - shape (0 E,
   1 oval), skull raw colour (7 = the new tone), the half / EGA mode's colour for a 7 */
#ifndef SH0
#define SH0 0
#define SK0 6
#define EG0 6
#define SH1 0
#define SK1 6
#define EG1 6
#define SH2 1
#define SK2 7
#define EG2 6
#define SH3 1
#define SK3 3
#define EG3 3
#endif
#ifndef TONE_L
#define TONE_L 84
#define TONE_D 85
#endif
static const unsigned char SHAPE[4] = {SH0, SH1, SH2, SH3}, SKULL[4] = {SK0, SK1, SK2, SK3}, EGA[4] = {EG0, EG1, EG2, EG3};

enum { W = 16, HMAX = 24 };

static u8 px[HMAX][W], hm[3][W];
static int nl;

static int is_hair(int c) { return c == 13 || c == 9 || c == 12; }

static int tr(int y, int x) { return y < 0 || y >= nl || x < 0 || x >= W || !px[y][x]; }

static void unpack(const u8 *pix) {
    for (int y = 0; y < nl; y++)
        for (int x = 0; x < W; x++) { u8 b = pix[y * 8 + x / 2]; px[y][x] = x & 1 ? b & 15 : b >> 4; }
}

static void pack(u8 *pix) {
    for (int y = 0; y < nl; y++)
        for (int x = 0; x < W; x += 2) pix[y * 8 + x / 2] = (u8)(px[y][x] << 4 | px[y][x + 1]);
}

static double root(double v) {                     /* (no libm: Newton) */
    double r = v > 1 ? v : 1;
    if (v <= 0) return 0;
    for (int i = 0; i < 20; i++) r = (r + v / r) / 2;
    return r;
}

/* The egg over rows y0..top-1 of px (columns from the head's widest span); inside: col (keep 1 / 2), outside: the
   head's pixels in `head` cleared. */
static void egg(int y0, int top, u8 col, int (*head)(int)) {
    int L = W, R = -1;
    for (int y = y0; y < top; y++)
        for (int x = 0; x < W; x++) if (px[y][x]) { if (x < L) L = x; if (x > R) R = x; }
    if (R < 0) return;
    double cx = (L + R) / 2.0, a = (R - L + 1) / 2.0, hgt = top - y0, cy = y0 + hgt / 2 - 0.5;
    for (int y = y0; y < top; y++) {
        double t = (y - cy) / (hgt / 2), aa = t <= 0 ? a : a * 0.8, w = aa * root(1 - t * t);
        for (int x = 0; x < W; x++) {
            int c = px[y][x];
            double d = x - cx;
            if ((d < 0 ? -d : d) <= w + 0.15) px[y][x] = c == 1 || c == 2 ? (u8)c : col;
            else if (head(c)) px[y][x] = 0;
        }
    }
}

static int head_raw(int c) { return is_hair(c) || c == 3 || c == 4 || c == 5 || c == 6; }

void bald_c(u8 *pix, int lines, int look, int ega) {
    if (lines < 2 || lines > HMAX) return;
    nl = lines;
    unpack(pix);
    int y0 = -1;
    for (int y = 0; y < nl && y0 < 0; y++)
        for (int x = 0; x < W; x++) if (is_hair(px[y][x])) { y0 = y; break; }
    if (y0 < 0) return;
    look &= 3;
    int shape = SHAPE[look], skull = SKULL[look];
    if (skull == 7) {                               /* a new tone: the variant's conversion table makes raw 13 -> 7, */
        for (int y = 0; y < nl; y++)                /* so any hair kept stays hair (13 -> 9, black too) and the skull */
            for (int x = 0; x < W; x++) if (px[y][x] == 13) px[y][x] = 9;   /* is painted 13 (the EGA colour in the */
        skull = ega ? EGA[look] : 13;               /* half mode: no table there) */
    }
    if (shape == 1) {
        int top = y0;                               /* the head's rows: down to the first kit row */
        for (; top < nl; top++) {
            int kit = 0;
            for (int x = 0; x < W; x++) { int c = px[top][x]; if (c && c != 1 && c != 2 && !head_raw(c)) kit = 1; }
            if (kit) break;
        }
        int L = W, R = -1;                          /* (the head's span, for the chin below) */
        for (int y = y0; y < top; y++)
            for (int x = 0; x < W; x++) if (px[y][x]) { if (x < L) L = x; if (x > R) R = x; }
        egg(y0, top, (u8)skull, head_raw);
        if (top < nl)                               /* the chin in the collar's row: the same colour as the face */
            for (int x = L; x <= R && x >= 0; x++)
                if (px[top][x] == 4 || px[top][x] == 5 || px[top][x] == 6 || px[top][x] == 3) px[top][x] = (u8)skull;
    } else {
        for (int y = y0; y <= y0 + 1 && y < nl; y++)  /* (turning hair into skin keeps tr() as it was) */
            for (int x = 0; x < W; x++)
                if (is_hair(px[y][x]) && (y == y0 || !(tr(y, x - 1) || tr(y, x + 1)))) px[y][x] = 6;
    }
    pack(pix);
}

static int rowlen(int y) { int n = 0; for (int x = 0; x < W; x++) n += px[y][x] != 0; return n; }

static int head_menu(int c) { return c == 3 || c == 4 || c == 5 || c == 6; }

/* A face icon (converted colours, hair 3 in its top three rows). Shape 0 (E): the hair in the face's skin colour (the
   first pixel of rows 3.. neither 0 nor 3), the top row's two end pixels off (a round head) and, when that leaves the
   top row a spike (fewer pixels than the next row less 3), the whole top row off; then the two lowest rows of the
   former hair get their end pixels back in hair colour 3. Shape 1 (oval): the egg over the head's rows in that skin. */
void bald_icon(u8 *pix, int lines, int look) {
    if (lines < 4 || lines > HMAX) return;
    nl = lines;
    unpack(pix);
    int skin = 0;
    for (int y = 3; y < nl && !skin; y++)
        for (int x = 0; x < W; x++) if (px[y][x] && px[y][x] != 3) { skin = px[y][x]; break; }
    if (!skin) return;
    look &= 3;
    if (SHAPE[look] == 1) {
        int y0 = 0, top;
        while (y0 < nl && !rowlen(y0)) y0++;
        for (top = y0; top < nl; top++) {           /* the head's rows: those with a hair / skin pixel */
            int h = 0;
            for (int x = 0; x < W; x++) h |= head_menu(px[top][x]);
            if (!h) break;
        }
        egg(y0, top, (u8)(SKULL[look] == 3 ? 3 : skin), head_menu);   /* (black stays black) */
        pack(pix);
        return;
    }
    int y0 = -1;
    for (int y = 0; y < 3; y++)
        for (int x = 0; x < W; x++) {
            hm[y][x] = px[y][x] == 3;
            if (hm[y][x]) { px[y][x] = (u8)skin; if (y0 < 0) y0 = y; }
        }
    if (y0 < 0) return;
    int lo = 0, hi = W - 1;
    while (!px[y0][lo]) lo++;
    while (!px[y0][hi]) hi--;
    px[y0][lo] = px[y0][hi] = 0;
    if (rowlen(y0) < rowlen(y0 + 1) - 3)
        for (int x = 0; x < W; x++) px[y0][x] = 0;
    for (int y = 2, n = 0; y >= 0 && n < 2; y--) {
        int a = -1, b = -1;
        for (int x = 0; x < W; x++) if (hm[y][x] && px[y][x]) { if (a < 0) a = x; b = x; }
        if (a < 0) continue;
        px[y][a] = px[y][b] = 3;
        n++;
    }
    pack(pix);
}

/* DrawSprite16Pixels' table (blond.PAL_ASM's pal_setup: ebx = LUTP + slot * 256, each `or bl, bh` became
   `mov bl, [ebx]`): slot 0 delta 0, 1 delta 10h (the bench), 2 delta 70h (the replay icons), 3 bald light, 4 bald dark
   (as slot 0, nibble 7 -> the light / dark tone; blond LUTSL picks them per flag), 5 any other delta (filled by
   pal_setup). 256-aligned at run time. */
static u8 lut[7 * 256];
u8 *LUTP;

void pal_init(void) {
    u8 *t = (u8 *)(((unsigned)lut + 255) & ~255u);
    for (int n = 0; n < 16; n++) {
        t[n] = (u8)n;
        t[256 + n] = (u8)(0x10 | n);
        t[512 + n] = (u8)(0x70 | n);
        t[768 + n] = (u8)(n == 7 ? TONE_L : n);
        t[1024 + n] = (u8)(n == 7 ? TONE_D : n);
    }
    LUTP = t;
}
