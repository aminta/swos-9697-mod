/* 4.0.5 bald heads, look E 'receding' (Davide 30/10, internal/design/bald-mock/variants-20261030 mkvariants.py V_E /
   icon_var 'E'; the earlier oval / domed back / look A are gone): a bald crown, the hair kept at the sides and the back
   in the player's own hair colour, the same rule for bald light and bald dark (the team's face conversion makes the
   crown light or dark skin). bald_c reshapes the hair of one copied RAW player sprite (1 quad = 16 pixels wide,
   8 bytes per line, 4-bit pixels, high nibble first) in place, before the team's colour conversion: raw hair = 13 / 9
   / 12, raw skin 6. The hair's top row turns skin, and so do the second row's hair pixels with a pixel on both sides
   (all views, the back ones too). bald_icon: the face icons 1910 / 1911 the same way. */
typedef unsigned char u8;

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

void bald_c(u8 *pix, int lines, int dark) {
    (void)dark;
    if (lines < 2 || lines > HMAX) return;
    nl = lines;
    unpack(pix);
    int y0 = -1;
    for (int y = 0; y < nl && y0 < 0; y++)
        for (int x = 0; x < W; x++) if (is_hair(px[y][x])) { y0 = y; break; }
    if (y0 < 0) return;
    for (int y = y0; y <= y0 + 1 && y < nl; y++)     /* (turning hair into skin keeps tr() as it was) */
        for (int x = 0; x < W; x++)
            if (is_hair(px[y][x]) && (y == y0 || !(tr(y, x - 1) || tr(y, x + 1)))) px[y][x] = 6;
    pack(pix);
}

static int rowlen(int y) { int n = 0; for (int x = 0; x < W; x++) n += px[y][x] != 0; return n; }

/* A face icon (converted colours, hair 3 in its top three rows): the hair in the face's skin colour (the first pixel
   of rows 3.. neither 0 nor 3), the top row's two end pixels off (a round head) and, when that leaves the top row a
   spike (fewer pixels than the next row less 3), the whole top row off; then the two lowest rows of the former hair
   get their end pixels back in hair colour 3 (the hair at the sides). */
void bald_icon(u8 *pix, int lines, int dark) {
    (void)dark;
    if (lines < 4 || lines > HMAX) return;
    nl = lines;
    unpack(pix);
    int skin = 0;
    for (int y = 3; y < nl && !skin; y++)
        for (int x = 0; x < W; x++) if (px[y][x] && px[y][x] != 3) { skin = px[y][x]; break; }
    if (!skin) return;
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
