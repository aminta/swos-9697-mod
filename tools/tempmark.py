"""TEMP markers (MC 17/11): a RELEASE build refuses to link while a temporary patch is in it.

A temporary patch is a block of the Mod's source that stands in for somebody else's real commit (an engine sha, the
final band registration ...). Its lines carry the literal TEMP-<NAME> in the source, and the module that puts the
block into a build declares it AT BUILD TIME, when (and only when) the block really goes into the exe being linked:

    tempmark.temp_marker('G1', 'tools/swce/sr_port.c: SR_PORT_LV_NONE until Convergence\'s sha')   # e.g. in fpad.patch

patch.py calls reset() at the start of every exe and check() after the last module has linked, before the save:
- a release build (is_release) with any marker registered: REFUSED (SystemExit, no exe written);
- any other build: one 'exe: TEMP markers: ...' line, so every build log names what is temporary in it.

A release build = the real thing or its candidate: no test switch (modver.is_test), no HOSTTEST_SYMS (the harness's
scenario builds and the host tests always set it), and MODVER_TAG empty (buildrel.sh's FINAL build) or an RC tag (a
release candidate is the release's bytes but for the version line). A beta tag (B11 ...) is not a release.

KNOWN is the registry's table: every TEMP-<NAME> literal in tools/ must be a name here and every name here must still
have its literal in the file it names (hosttest test_tempmark) - a marker cannot be written in a source without being
declared, nor stay declared after its block is gone. Removing a temporary patch = its real commit deletes the block's
TEMP- lines, its temp_marker call and its KNOWN line together.
"""
import os

# name -> (the file that holds the TEMP-<NAME> block, what replaces it)
KNOWN = {
    'G1': ('swce/sr_port.c', 'engine: SR_PORT_LV_NONE (legs 1), sr_port_winner 2 on a level score, SR_PORT_VERSION 1 - '
                             'Convergence\'s sha (SWCE_SHA) replaces the hand patch'),
    'G5': ('swce/sr_port.c', 'engine: sr_port rule 5 < -> <= - Convergence\'s sha'),
    'MINILG': ('swce/sr_stage.c', 'engine: minilg 19ee37a\'s sr_mini_sched / SR_SCHED_* hand-applied on 52301fb - the '
                                  'engine\'s real sha (test_fpad_vendor FAILs until then)'),
    'BANDS': ('swreg.py', 'obj4 bands FPORT / FPORT2 / FPML - Shaved\'s BSS_AT fold registers the final ones'),
}
MARKS = {}              # name -> where / why, for the exe being built


def reset():
    """patch.py, at the start of every exe."""
    MARKS.clear()


def temp_marker(name, why=''):
    """A module declares that the TEMP-<name> block is in the exe being built."""
    assert name in KNOWN, ('tempmark: TEMP-%s is not in tempmark.KNOWN (declare it there)' % name)
    MARKS[name] = why or KNOWN[name][1]


def is_release(env=None):
    env = os.environ if env is None else env
    if env.get('HOSTTEST_SYMS'):
        return False
    tag = (env.get('MODVER_TAG') or '').upper()
    if tag and not tag.startswith('RC'):
        return False
    import modver
    test = any(env.get(v) for v in modver.TEST_VARS) or any(k.endswith('_FORCE') and v for k, v in env.items())
    return not test


def check(env=None, log=print):
    """patch.py, after the last link step and before the exe is saved. Returns the sorted marker names."""
    names = sorted(MARKS)
    if not names:
        return names
    text = ', '.join(f'TEMP-{n}' for n in names)
    if is_release(env):
        raise SystemExit(f'REFUSED: a release build with temporary patches linked: {text}\n' +
                         '\n'.join(f'  TEMP-{n} ({KNOWN[n][0]}): {MARKS[n]}' for n in names) +
                         '\n  (a release / RC build: no test switch, no HOSTTEST_SYMS, MODVER_TAG empty or RC*; tools/tempmark.py)')
    log(f'exe: TEMP markers: {text} - NOT a release build (a release refuses them; tools/tempmark.py)')
    return names
