#!/usr/bin/env python3
"""Emit the Riivolution XML from the prebuilt feature.

    python3 tools/build.py            # writes riivolution/<ID>.xml

The patched-DOL path (tools/patcher.py, the GUI) uses the very same ops, so the
two install methods cannot disagree.  There is no Gecko code list: the routines
come to about 440 lines, and Dolphin's code handler has room for about 230.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import features
from regions import REGIONS

ROOT = os.path.join(HERE, '..')


def riivolution_xml(region):
    r = REGIONS[region]
    f = features.load('pad', region)
    out = ['<!-- %s: controller patch by quatric -->' % r['label'],
           '<wiidisc version="1" root="/">',
           '  <id game="%s" version="%d" />' % (region, r['version']),
           '  <options>',
           '    <section name="%s">' % r['label'],
           '      <option name="Controller" default="1">',
           '        <choice name="%s"><patch id="pad" /></choice>' % features.TITLES['pad'],
           '      </option>',
           '    </section>',
           '  </options>',
           '  <patch id="pad">']
    out += ['    ' + e for e in f.memory_elements()]
    out += ['  </patch>', '</wiidisc>']
    return '\n'.join(out) + '\n'


def main():
    os.makedirs(os.path.join(ROOT, 'riivolution'), exist_ok=True)
    for region in REGIONS:
        with open(os.path.join(ROOT, 'riivolution', region + '.xml'), 'w') as fh:
            fh.write(riivolution_xml(region))
        print(region, REGIONS[region]['label'])


if __name__ == '__main__':
    main()
