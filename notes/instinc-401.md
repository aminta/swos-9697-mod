# Install incomplete: a message instead of DOS (4.0.1, session 'Motore') — Gianmarco's case

## What changes
- **Before:** when a world's DATA files are missing (an old or interrupted patcher run), the team pick exits to
  DOS. LoadFile prints the file name and quits.
- **Now:** before SelectTeamsFinalMenu lists a world of CLASSIC CAREERS (list id WMENU + n), every file of that world
  is opened (DOS 3Dh) and closed. This covers CARR. STORICHE > MONDO 2026-27 / EUROPA 1984-85 and the main menu's
  CARRIERA 2026-27 button.
  - The world's files are its team files (TMW5.nnn / TEAM.nnn), WORLDnn.TMD, POOLnn.DAT, XTWn.nnn and RSnnnn.DAT.
- **If one is missing:**
  - the game's error box shows the message below in the exe's language;
  - the text uses the small font: the big font fits only about 27 characters in the box's 300 px;
  - then the team choice ends as when CUSTOMS.EDT is missing (SelectTeamsFinalMenu's err_out), and CONTINUE goes
    back to the main menu.
- **Code:** `tools/instcheck.py`.
  - mkseason's cont_check calls a stub, which instcheck.place points at the check in the career cave (704 B).
  - The file names are stored as prefix + one-byte numbers.

| exe | message (small font, px) |
|---|---|
| it | INSTALLAZIONE INCOMPLETA: RILANCIA IL PATCHER (230) |
| en | INCOMPLETE INSTALL: RUN THE PATCHER AGAIN (215) |
| fr | INSTALLATION INCOMPLETE: RELANCEZ LE PATCHER (236) |
| de | INSTALLATION UNVOLLSTAENDIG: PATCHER NEU STARTEN (260) |

## Tests (release recipe, data world5tm-401nats; builds/instinc_{it,en,fr,de})
- `world_instinc`, PASS in all 4 exes:
  - without DATA\TMW5.150, both ways in show the box, and CONTINUE leads back to the main menu;
  - the complete build lists the world's continents.
- The complete build also opens EUROPA 1984-85 > INGHILTERRA (its files are checked too).

## Release notes (draft)
EN — If the World 2026-27 files are missing (an interrupted or old patcher run), choosing the world no longer quits to
DOS: the game says "INCOMPLETE INSTALL: RUN THE PATCHER AGAIN" and goes back to the menu.

IT — Se mancano i file del Mondo 2026-27 (patcher interrotto o vecchio), scegliere il mondo non fa più uscire a DOS: il
gioco dice "INSTALLAZIONE INCOMPLETA: RILANCIA IL PATCHER" e torna al menu.
