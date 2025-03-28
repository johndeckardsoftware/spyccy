#!/usr/bin/env python3
#
# tzxtools - a collection for processing tzx files
#
# Copyright (C) 2016 Richard "Shred" Körber
#   https://github.com/shred/tzxtools
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import argparse
import io
import sys
import textwrap

from tzxtools.tzxlib.tapfile import TapHeader
from tzxtools.tzxlib.tzxfile import TzxFile
from io import StringIO

def main(args):

    old_stdout = sys.stdout
    sys.stdout = mystdout = StringIO()

    files = list(args.file)
    if not sys.stdin.isatty() and len(files) == 0:
        files.append(sys.stdin.buffer)

    for f in files:
        if len(files) > 1:
            name = f.name if hasattr(f, 'name') else f
            print('\n%s:' % (name))
        tzx = TzxFile()
        tzx.read(f)

        cnt = 0
        for b in tzx.blocks:
            if args.short:
                if hasattr(b, 'tap') and isinstance(b.tap, TapHeader):
                    print('%s: %s' % (b.tap.type(), b.tap.name()))
            else:
                print('%3d  %-27s %s' % (cnt, b.type, str(b)))
            if args.verbose:
                info = b.info()
                if info is not None:
                    print(textwrap.indent(info.strip(), '\t'))
            cnt += 1
    print(f"Total blocks: {len(tzx.blocks)}\n")    
    sys.stdout = old_stdout
    return mystdout.getvalue(), len(tzx.blocks)
