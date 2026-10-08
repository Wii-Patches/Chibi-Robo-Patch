"""Build the controller feature for Wii de Asobu: Chibi-Robo! (R24J01) from src/*.s."""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
import asm
from layout import PAD_BASE, PAD_END
from ops import Feature, Hook

KBASE = 0x8052B8E8            # KPAD channel 0 state (stride 0x5C0)
FACA0 = 0x801FACA0            # KPAD: raw buttons -> hold / trig / release
DECODE = 0x801FC9C0           # KPAD: decode a sample's extension data (Nunchuk / Classic stick)
PROBE = 0x801EA544            # WPAD: probe a channel (status; extension type through r4)
IRPROC = 0x801FC208           # KPAD: process a sample's pointer (IR) data
DEAD, KMUL = 10, 205          # pointer stick: dead zone, 256 * 64 / 80

SITES = [   # (source file, addresses of the `bl` it replaces)
    ('buttons.s', (0x801FD810, 0x801FD96C)),
    ('stick.s', (0x801FD838, 0x801FD9B4)),
    ('pointer.s', (0x801FD850, 0x801FD9CC)),
    ('probe.s', (0x802B1DF4, 0x800AB504)),
]
NOTES = {
    'buttons.s': 'KPADRead: pad / Classic Controller buttons -> Wii Remote and Nunchuk bits',
    'stick.s': 'KPADRead: pad / Classic Controller left stick -> Nunchuk stick',
    'pointer.s': 'KPADRead: no real pointer -> steer one with the right stick / C-stick',
    'probe.s': 'game: report a Classic Controller or pad as a Nunchuk',
}


def _read(name):
    return open(os.path.join(ROOT, 'src', 'common.inc')).read() + '\n' + open(os.path.join(ROOT, 'src', name)).read()


def build(dol, consts=None):
    syms = {'KBASE': KBASE, 'FACA0': FACA0, 'DECODE': DECODE, 'PROBE': PROBE, 'IRPROC': IRPROC}
    consts = dict(consts or {}, DEAD=DEAD, KMUL=KMUL)
    ops, cur = [], PAD_BASE
    for name, sites in SITES:
        for site in sites:
            orig = struct.unpack('>I', dol.read(site, 4))[0]
            if orig >> 26 != 18 or not orig & 1:
                raise SystemExit('0x%08X is not a bl (0x%08X): wrong game build?' % (site, orig))
            body = asm.words(asm.assemble(_read(name), cur, syms, consts)) + [0]
            ops.append(Hook(site, orig, body, cur, note=NOTES[name]))
            cur += (len(body) * 4 + 15) & ~15
    if cur > PAD_END:
        raise SystemExit('code overflows its window: 0x%X > 0x%X' % (cur, PAD_END))
    return Feature('pad', 'GameCube and Classic Controller', 'R24J01', ops)


def gecko_ini(feature, name='Chibi-Robo controllers'):
    return '[Gecko]\n$%s\n%s\n[Gecko_Enabled]\n$%s\n' % (name, '\n'.join(feature.gecko_lines()), name)


if __name__ == '__main__':
    from dol import Dol
    dol = Dol(sys.argv[1])
    f = build(dol)
    print(gecko_ini(f))
