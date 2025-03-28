#!/usr/bin/env python3
#
# tzxtools - a collection for processing tzx files
#
# Copyright (C) 2018 Richard "Shred" Körber
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

import io
import sys, os

from tzxtools.tzxlib.tzxfile import TzxFile
from tzxtools.tzxlib.tapfile import TapHeader
from tzxtools.tzxlib.convert import convertToText
from tzxtools.tzxlib.convert import convertToBasic
from tzxtools.tzxlib.convert import convertToDump
from tzxtools.tzxlib.convert import convertToAssembler
from tzxtools.tzxlib.convert import convertToScreen

out = None

def writeBlock(out, dump, converter, skip, length, org):
    if skip:
        if 0 <= skip < len(dump):
            dump = dump[skip:]
        else:
            dump = []
    if length:
        if 0 <= length < len(dump):
            dump = dump[:length]
    if converter:
        dump = converter(dump, out, org)
    return dump

def writeSingleBlock(tzx, out, index, writer, skipNotDumpable=False):
    if index < 0 or index >= len(tzx.blocks):
        out.write(f'Error: Block {index} out of range'.encode("utf-8"))
        return(1)
    b = tzx.blocks[index]
    out.write(f'Block: {index} {str(b)}\n'.encode("utf-8"))
    d = b.dump()
    if d is None:
        if skipNotDumpable:
            return
        else:
            out.write(f'Error: Block {index} has no data content'.encode('utf-8'))
            return(1)
    if hasattr(b, 'tap') and not b.tap.valid():
        out.write(f'Warning: Block {index} has bad CRC'.encode('utf-8'))

    writer(out, d, findOrg(tzx, index))

def writeAllBlocks(tzx, out, writer):
    for i in range(len(tzx.blocks)):
        #out.write(f'block: {i}\n'.encode("utf-8"))
        writeSingleBlock(tzx, out, i, writer, True)

def findOrg(tzx, index):
    if index > 1:
        b = tzx.blocks[index - 1]
        if hasattr(b, 'tap'):
            if isinstance(b.tap, TapHeader) and b.tap.typeId() == 3:
                return b.tap.param1()
    return None

def main(args):
    global out

    file = TzxFile()
    file.read(args.file)

    converter = lambda data, out, org: out.write(data)  # default binary output
    if args.basic:
        converter = convertToBasic
    elif args.assembler:
        converter = convertToAssembler
    elif args.screen:
        converter = convertToScreen
    elif args.text:
        converter = convertToText
    elif args.dump:
        converter = convertToDump

    writer = lambda out, dump, org : writeBlock(out, dump, converter, args.skip, args.length, args.org or org or 0)

    outf = args.to if args.to != '-' else sys.stdout.buffer
    with outf if isinstance(outf, io.IOBase) else open(outf, 'wb') as out:
        if args.block != None:
            writeSingleBlock(file, out, args.block, writer)
        else:
            writeAllBlocks(file, out, writer)

    file = open(args.to,"r", encoding="utf-8")
    info = file.read()
    file.close()
    os.remove(args.to) 
    return info
