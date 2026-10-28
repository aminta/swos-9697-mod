/* 4.0.5 bald heads (Davide 28/10, internal/design/bald-mock/bald_light_final.png row 3; mock3.py's oval / backtop):
   bald_c reshapes the hair of one copied RAW player sprite (1 quad = 16 pixels wide, 8 bytes per line, 4-bit pixels,
   high nibble first) in place, before the team's colour conversion. Raw hair = 13 / 9 / 12, raw skin = 6 / 5 / 4
   (face 0 keeps them, face 2 makes them dark skin). Back views (no face pixel in the hair's rows): a full head from
   the hair's top row down, as wide as its widest row (the spikes off), the top row's corners off (a dome), its last
   row a 2-pixel neck; skin 6, side edges 5. Other views: bald light (dark = 0) an oval skull (super-ellipse,
   exponent 3, one row lower than the hair, as wide as the head's widest row less one pixel each side), skin 6 with 5
   side edges, the hair outside it transparent; bald dark (dark = 1) look A as before (the hair's outer ring
   transparent, the rest 6 on top, 4 at the sides, 5 inside). */
typedef unsigned char u8;

enum { W = 16, HMAX = 24 };

static int is_hair(int c) { return c == 13 || c == 9 || c == 12; }

static u8 px[HMAX][W], hr[HMAX][W], hd[HMAX][W];
static int nl;

static int tr(int y, int x) { return y < 0 || y >= nl || x < 0 || x >= W || !px[y][x]; }

static void look_a(void) {
    static u8 drop[HMAX][W];
    for (int y = 0; y < nl; y++)
        for (int x = 0; x < W; x++)
            drop[y][x] = hr[y][x] && (tr(y - 1, x) || tr(y + 1, x) || tr(y, x - 1) || tr(y, x + 1));
    for (int y = 0; y < nl; y++)
        for (int x = 0; x < W; x++)
            if (drop[y][x]) { px[y][x] = 0; hr[y][x] = 0; }
    for (int y = 0; y < nl; y++)
        for (int x = 0; x < W; x++)
            if (hr[y][x]) px[y][x] = tr(y - 1, x) ? 6 : (tr(y, x - 1) || tr(y, x + 1)) ? 4 : 5;
}

static void oval(int y0, int y1) {
    int wy = -1, wmin = 0, wmax = -1;
    for (int y = y0; y <= y1; y++) {               /* the head's widest row (hair and face), the first of them */
        int lo = W, hi = -1;
        for (int x = 0; x < W; x++) if (px[y][x]) { if (x < lo) lo = x; if (x > hi) hi = x; }
        if (hi >= 0 && (wy < 0 || hi - lo > wmax - wmin)) { wy = y; wmin = lo; wmax = hi; }
    }
    if (wy < 0) return;
    double cx = (wmin + wmax) / 2.0, a = (wmax - wmin + 1) / 2.0 - 0.5;
    if (a < 1) a = 1;
    int yb = (wy > y1 ? wy : y1) + 1, h = yb - y0 - 1;
    if (h < 1) h = 1;
    for (int y = y0; y <= y1; y++)
        for (int x = 0; x < W; x++) {
            if (!hr[y][x]) continue;
            double t = (yb - y) / (h + 0.5), d = (x > cx ? x - cx : cx - x) - 0.25;
            int in = y > y0 && t < 1 && (d <= 0 || d * d * d <= a * a * a * (1 - t * t * t));
            px[y][x] = in ? 6 : 0;
        }
    for (int y = y0; y <= y1; y++)
        for (int x = 0; x < W; x++)
            if (hr[y][x] && px[y][x] && (tr(y, x - 1) || tr(y, x + 1))) px[y][x] = 5;
}

static void back(int y0, int y1) {
    int wy = -1, L = 0, R = -1;
    for (int y = y0; y <= y1; y++) {               /* the hair's widest row, the first of them */
        int lo = W, hi = -1;
        for (int x = 0; x < W; x++) if (hr[y][x]) { if (x < lo) lo = x; if (x > hi) hi = x; }
        if (hi >= 0 && (wy < 0 || hi - lo > R - L)) { wy = y; L = lo; R = hi; }
    }
    if (wy < 0) return;
    for (int y = 0; y < nl; y++)
        for (int x = 0; x < W; x++) { if (hr[y][x]) px[y][x] = 0; hd[y][x] = 0; }
    for (int y = y0; y < y1; y++) {                /* (row y1: the neck) */
        int lo = y == y0 ? L + 1 : L, hi = y == y0 ? R - 1 : R;
        for (int x = lo; x <= hi; x++) if (x >= 0 && x < W) hd[y][x] = 1;
    }
    if (y0 > 0)                                    /* one more row above the top, when the sprite has it */
        for (int x = L + 2; x <= R - 2; x++) if (x >= 0 && x < W) hd[y0 - 1][x] = 1;
    for (int y = 0; y < nl; y++)
        for (int x = 0; x < W; x++)
            if (hd[y][x]) px[y][x] = (x == 0 || !hd[y][x - 1] || x == W - 1 || !hd[y][x + 1]) ? 5 : 6;
    int c2 = L + R;                                /* the neck: the 1 or 2 centre pixels, skin 5 */
    if (R - L >= 3) { px[y1][(c2 - 1) / 2] = 5; px[y1][(c2 + 1) / 2] = 5; }
    else px[y1][c2 / 2] = 5;
}

void bald_c(u8 *pix, int lines, int dark) {
    if (lines < 1 || lines > HMAX) return;
    nl = lines;
    int y0 = -1, y1 = -1;
    for (int y = 0; y < nl; y++)
        for (int x = 0; x < W; x++) {
            u8 b = pix[y * 8 + x / 2];
            px[y][x] = x & 1 ? b & 15 : b >> 4;
            hr[y][x] = is_hair(px[y][x]);
            if (hr[y][x]) { if (y0 < 0) y0 = y; y1 = y; }
        }
    if (y0 < 0) return;
    int face = 0;
    for (int y = y0; y <= y1; y++)
        for (int x = 0; x < W; x++) if (px[y][x] && !hr[y][x]) face = 1;
    if (!face) back(y0, y1);
    else if (dark) look_a();
    else oval(y0, y1);
    for (int y = 0; y < nl; y++)
        for (int x = 0; x < W; x += 2) pix[y * 8 + x / 2] = (u8)(px[y][x] << 4 | px[y][x + 1]);
}
