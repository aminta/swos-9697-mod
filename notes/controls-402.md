# In-game CONTROLS menu (4.0.2/4.0.3, session Motore)

Approved texts (Davide via Regia, 26/10). FR device row = PERIPHERIQUES, DE device row = GERAETE. German is written
AE / OE / UE (Davide 26/10): the exe's umlaut bytes exist but the menus' small font draws them without dots (as the
game's own ZURÜCK ZU DOS reads ZURUCK), and DRUCKEN would read 'print'.

| # | IT | EN | FR | DE |
|---|---|---|---|---|
| button + title | COMANDI | CONTROLS | COMMANDES | STEUERUNG |
| device row | CONTROLLI | INPUT | PERIPHERIQUES | GERAETE |
| device values | SOLO TASTIERA / G1 JOYPAD, G2 TASTIERA / G1 TASTIERA, G2 JOYPAD / DUE JOYPAD | KEYBOARD ONLY / P1 JOYPAD, P2 KEYBOARD / P1 KEYBOARD, P2 JOYPAD / TWO JOYPADS | CLAVIER SEUL / J1 MANETTE, J2 CLAVIER / J1 CLAVIER, J2 MANETTE / DEUX MANETTES | NUR TASTATUR / S1 JOYPAD, S2 TASTATUR / S1 TASTATUR, S2 JOYPAD / ZWEI JOYPADS |
| keys | SU, GIU', SINISTRA, DESTRA, FUOCO | UP, DOWN, LEFT, RIGHT, FIRE | HAUT, BAS, GAUCHE, DROITE, TIR | OBEN, UNTEN, LINKS, RECHTS, FEUER |
| wait key | PREMI UN TASTO (ESC: LASCIA) | PRESS A KEY (ESC: KEEP) | APPUYEZ SUR UNE TOUCHE (ESC: GARDER) | TASTE DRUECKEN (ESC: BEHALTEN) |
| duplicate | TASTO GIA' USATO | KEY ALREADY USED | TOUCHE DEJA UTILISEE | TASTE SCHON BELEGT |
| calibrate | CALIBRA JOYPAD 1/2 | CALIBRATE JOYPAD 1/2 | CALIBRER MANETTE 1/2 | JOYPAD 1/2 KALIBRIEREN |
| step 1 | LEVA AL CENTRO, PREMI FUOCO | STICK CENTRED, PRESS FIRE | MANCHE AU CENTRE, APPUYEZ SUR TIR | STICK IN DIE MITTE, FEUER DRUECKEN |
| step 2 | MUOVI LA LEVA IN TUTTI GLI ANGOLI, POI FUOCO | MOVE THE STICK TO EVERY CORNER, THEN FIRE | BOUGEZ LE MANCHE DANS CHAQUE COIN, PUIS TIR | STICK IN ALLE ECKEN, DANN FEUER |
| no pad | NESSUN JOYPAD 1 COLLEGATO | NO JOYPAD 1 CONNECTED | AUCUNE MANETTE 1 BRANCHEE | KEIN JOYPAD 1 ANGESCHLOSSEN |
| test prefix | PROVA: | TEST: | TEST : | TEST: |
| save / cancel | SALVA / ANNULLA | SAVE / CANCEL | ENREGISTRER / ANNULER | SPEICHERN / ABBRECHEN |
| hint | CON LA MODALITA' TASTIERA DEL PATCHER TIENI FRECCE E CTRL | WITH THE PATCHER'S KEYBOARD MODE KEEP ARROWS AND CTRL | AVEC LE MODE CLAVIER DU PATCHER GARDEZ FLECHES ET CTRL | IM TASTATURMODUS DES PATCHERS PFEILE UND STRG LASSEN |

Key names: letters/digits as is; FRECCIA SU/GIU'/SINISTRA/DESTRA - UP/DOWN/LEFT/RIGHT ARROW - FLECHE HAUT/BAS/GAUCHE/DROITE -
PFEIL OBEN/UNTEN/LINKS/RECHTS; CTRL (DE STRG); ALT; SHIFT SX/DX - L. SHIFT/R. SHIFT - MAJ G/MAJ D - UMSCH. L/R;
SPAZIO/SPACE/ESPACE/LEERTASTE; INVIO/ENTER/ENTREE/EINGABE; TAB; keypad TN n/KP n/PN n/ZB n; else TASTO nn/KEY nn/TOUCHE nn/TASTE nn.

Decisions: no mouse mode; SALVA creates SETUP.DAT if missing; button hidden under SWOS++.

## Implementation (tools/controls.py, branch 4.0.2-controls)
- OPZIONI entry 19 (PRE-RELEASE VERSION) becomes COMANDI at y 169 between ESCI A DOS and ESCI (OptionsMenu init +
  onReturn hooks); hidden under SWOS++ (menunum's tactics-pitch byte).
- The page edits a copy of setupDatBuffer; SALVA re-reads SETUP.DAT (none: the game's buffer), replaces only device,
  calibration (both sticks), loops and keys, writes it (DOS create) and applies them; no stick = keyboard in memory
  (file keeps the choice; joyfix does the same at the next start). ANNULLA drops the copy.
- Key capture: lastKey after the selecting key's release, menu input held by player1/2ClearFlag + g_inputtingText.
  Duplicates refused, ESC keeps. Key names by the exe language's keyboard (QWERTY / AZERTY / QWERTZ).
- Calibration: ReadGamePort with two sticks and loops 0FFFFh; centre + fire, corners + fire (>= 8 counts each way),
  live TEST line; divisors = distances (as INSTALL.EXE), loops = largest value + 1/8.
- German: AE / OE / UE spelling (GERAETE, DRUECKEN); the umlaut bytes 8Eh / 9Ah drew without dots in the small font.
- Scenarios: controls_menu, controls_calib (SWOSTEST_UI=it/en/fr/de), controls_swospp (en).
