#!/usr/bin/env python3
"""Consistency checks that need no game files (CI runs this).

  * the prebuilt feature loads and stays inside the injected section
  * every hook trampoline fits and the patched sites are branches into it
  * the committed riivolution/ files are exactly what build.py generates

    python3 tools/check.py
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build
import features
from layout import CAVE_BASE, CAVE_LIMIT
from ops import Hook
from regions import REGIONS

fail = []


def check(cond, msg):
    if not cond:
        fail.append(msg)
        print('  FAIL', msg)


def main():
    for region in REGIONS:
        check(features.available('pad', region), 'missing prebuilt pad_%s.json' % region)
        if not features.available('pad', region):
            continue
        f = features.load('pad', region)
        hooks = [o for o in f.ops if isinstance(o, Hook)]
        check(len(hooks) == 8, '%s: expected 8 hooks, found %d' % (region, len(hooks)))
        spans = []
        for h in hooks:
            end = h.tramp + 4 * len(h.payload)
            check(CAVE_BASE <= h.tramp and end <= CAVE_LIMIT, '%s: hook 0x%08X outside the section' % (region, h.site))
            check(h.payload[-1] == 0, '%s: hook 0x%08X has no return slot' % (region, h.site))
            spans.append((h.tramp, end))
        spans.sort()
        for (a0, a1), (b0, b1) in zip(spans, spans[1:]):
            check(a1 <= b0, '%s: trampolines overlap at 0x%08X' % (region, b0))
        for addr, data in f.writes():
            check(len(data) % 4 == 0, '%s: unaligned write at 0x%08X' % (region, addr))
        path = os.path.join(build.ROOT, 'riivolution', region + '.xml')
        check(os.path.exists(path) and open(path).read() == build.riivolution_xml(region),
              '%s: riivolution/%s.xml is stale (run tools/build.py)' % (region, region))
        print('%s ok: %d hooks, %d bytes of routines' % (region, len(hooks), sum(b - a for a, b in spans)))
    sys.exit(1 if fail else 0)


if __name__ == '__main__':
    main()
