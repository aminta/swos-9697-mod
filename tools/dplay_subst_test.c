#include <stdio.h>
#include <stdlib.h>
#include "dplay.c"
static void table(int d, int n) {
    int pts[24];
    for (int k = 0; k < n; k++) pts[k] = 20 + rand() % 60;
    for (int i = 0; i < n; i++) for (int j = i + 1; j < n; j++) if (pts[j] > pts[i]) { int x = pts[i]; pts[i] = pts[j]; pts[j] = x; }
    DP_IN.n[d] = n;
    for (int k = 0; k < n; k++) { struct dp_row *r = &DP_IN.t[d][k];
        r->team = d * 256 + k + 1; r->glob = d * 100 + k; r->pts = pts[k]; r->won = pts[k] / 3; r->gf = 30 + rand() % 30; r->ga = 40; }
}
int main(int argc, char **argv) {
    int N = atoi(argv[1]), bad = 0, mode = argc > 2 ? atoi(argv[2]) : 0;
    for (int it = 0; it < N; it++) {
        srand(it); DP_IN.ng = 3;
        table(0, 20); for (int g = 1; g <= 3; g++) table(g, 20);
        DP_IN.cpo_win = 0; DP_ST.kind = 0;
        if (mode) { /* real contest: winner = a direct winner (mode 1), final record present */
            memset(&DP_ST, 0, sizeof DP_ST); DP_ST.kind = 3; DP_ST.n = 28;
            for (int i = 0; i < 28; i++) { int g = 1 + i % 3, k = 1 + i % 9; DP_ST.team[i] = DP_IN.t[g][k].team; }
            int g0 = 1 + it % 3;
            DP_IN.cpo_win = DP_IN.t[g0][mode >= 1 ? 0 : 1 + it % 9].team;   /* winner 1st of its group */
            int wi = -1; for (int i = 0; i < 28; i++) if (DP_ST.team[i] == DP_IN.cpo_win) wi = i;
            if (wi < 0) { wi = 0; DP_ST.team[0] = DP_IN.cpo_win; }
            int l = (wi + 1) % 28, s1 = (wi + 2) % 28, s2 = (wi + 3) % 28, o = (wi + 4) % 28;
            if (mode >= 2 && mode != 5) { DP_ST.team[l] = DP_IN.t[1 + (it + 1) % 3][0].team; }
            if (mode == 3) { DP_ST.team[s1] = DP_IN.t[1 + (it + 2) % 3][0].team; DP_ST.team[s2] = DP_IN.t[1 + (it + 2) % 3][0].team; }   /* final loser also a direct winner */
            if (mode == 5) { u8 e[4] = { s1, wi, s2, l }; frec_set(&DP_ST, e); DP_ST.cup |= 48; } else if (mode != 4) { u8 e[4] = { wi, s1, l, s2 }; frec_set(&DP_ST, e); } (void)o;
        }
        if (mode == 6) for (int i = 0; i < 28; i++) DP_ST.team[i] = i < 3 ? DP_IN.t[1 + i][0].team : 0xFFFF;   /* all ineligible */
        dp_season();
        /* SIMASSERT: the simulated play-off never contains a group winner */
        if (mode == 0) for (int i = 0; i < DP_OUT.ntie; i++) { struct dp_tie *t = &DP_OUT.tie[i]; if (t->kind >= K_GR1 && (t->a % 24 == 0 || t->b % 24 == 0)) bad++; }
        int up = 0; for (int i = 0; i < DP_OUT.nmv; i++) if (DP_OUT.mv[i].delta == -1 && DP_OUT.mv[i].club / 24 >= 1) up++;
        if (mode == 6) { if (up != 0 || !DP_SUBF || DP_SUBN[3] == 0) bad++; } else if (DP_OUT.nmv < 1 || up != 1) bad++;
        if (DP_SUBF && mode == 0) bad++;
    }
    printf("bad %d of %d; subs: loser %u semi %u state %u none %u\n", bad, N, DP_SUBN[0], DP_SUBN[1], DP_SUBN[2], DP_SUBN[3]);
    return bad != 0;
}
