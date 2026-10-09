## English

**SWOS 96/97 Mod 2.7.0: SWOS++ compatibility**

The game content is the same as 2.6.1. This release makes the mod work with [SWOS++](https://github.com/zlatkok/swospp) by Zlatko Karakas (network play, full match replays, DIY competition editor, shirt numbers up to 255, joystick calibration). Thanks to Zlatko for asking for it (via Playaveli) and for SWOS++ itself.

- **English executable only** (original CD or GOG): SWOS++ exists for ENGLISH.EXE only.
- The patcher now gives an extra **`ENGLISH.EXE + SWOS++`** row. You can drop:
  - the original ENGLISH.EXE;
  - an ENGLISH.EXE modified by any earlier release of the mod (1.0 to 2.6.1);
  - an original ENGLISH.EXE that already has SWOS++ installed.
- Then copy **`loader.bin`** and **`swospp.bin`** from the [SWOS++ release page](https://github.com/zlatkok/swospp/releases/latest) into the game folder, next to the executable. `patchit.com` is not needed (and would refuse a modded exe). If you start the game under another name (for example `SWS.EXE`), rename the downloaded file.
- Tested with SWOS++ 1.9.2.2 in DOSBox-X: main menu, the mod's menus, matches (shirt numbers, substitutions, bookings, replays and highlights), career with the mod's cups plus saving and loading, and the DIY editor. Network play has not been tested yet: both players need the same files.
- How it works (for developers): chapter 24 of the technical manual, `tools/swospp.py`, `notes/swospp.md`.
- The other executables and the TEAM files are the same as in 2.6.1.

## Italiano

**SWOS 96/97 Mod 2.7.0: compatibilità con SWOS++**

Il contenuto del gioco è quello della 2.6.1. Questa release fa funzionare la mod con [SWOS++](https://github.com/zlatkok/swospp) di Zlatko Karakas (partite in rete, replay completi, editor delle competizioni DIY, numeri di maglia fino a 255, calibrazione del joystick). Grazie a Zlatko per averla chiesta (tramite Playaveli) e per SWOS++.

- **Solo eseguibile inglese** (CD originale o GOG): SWOS++ esiste solo per ENGLISH.EXE.
- Il patcher ora dà in più la riga **`ENGLISH.EXE + SWOS++`**. Puoi trascinare:
  - l'ENGLISH.EXE originale;
  - un ENGLISH.EXE modificato da una qualsiasi versione precedente della mod (dalla 1.0 alla 2.6.1);
  - un ENGLISH.EXE originale con SWOS++ già installato.
- Poi copia **`loader.bin`** e **`swospp.bin`** dalla [pagina delle release di SWOS++](https://github.com/zlatkok/swospp/releases/latest) nella cartella del gioco, accanto all'eseguibile. `patchit.com` non serve (e su un exe modificato si rifiuterebbe). Se avvii il gioco con un altro nome (per esempio `SWS.EXE`), rinomina il file scaricato.
- Provato con SWOS++ 1.9.2.2 in DOSBox-X: menu principale, menu della mod, partite (numeri di maglia, sostituzioni, ammonizioni, replay e highlights), carriera con le coppe della mod con salvataggio e caricamento, editor DIY. Le partite in rete non sono ancora state provate: i due giocatori devono avere gli stessi file.
- Come funziona (per sviluppatori): capitolo 24 del manuale tecnico, `tools/swospp.py`, `notes/swospp.md`.
- Gli altri eseguibili e i file TEAM sono gli stessi della 2.6.1.
