
import shlex
import math
from tkinter import messagebox

TOKENS = {
    # Spectrum Next new tokens
    'PEEK$': 0x87,
    'REG': 0x88,
    'DPOKE': 0x89,
    'DPEEK': 0x8a,
    'MOD': 0x8b,
    '<<': 0x8c,
    '>>': 0x8d,
    'UNTIL': 0x8e,
    'ERROR': 0x8f,
    'ON': 0x90,
    'DEFPROC': 0x91,
    'ENDPROC': 0x92,
    'PROC': 0x93,
    'LOCAL': 0x94,
    'DRIVER': 0x95,
    'WHILE': 0x96,
    'REPEAT': 0x97,
    'ELSE': 0x98,
    'REMOUNT': 0x99,
    'BANK': 0x9a,
    'TILE': 0x9b,
    'LAYER': 0x9c,
    'PALETTE': 0x9d,
    'SPRITE': 0x9e,
    'PWD': 0x9f,
    'CD': 0xa0,
    'MKDIR': 0xa1,
    'RMDIR': 0xa2,

    'SPECTRUM': 0xa3,
    'PLAY1': 0xa4,
    'RND': 0xa5,
    'INKEY$': 0xa6,
    'PI': 0xa7,
    'FN': 0xa8,
    'POINT': 0xa9,
    'SCREEN$': 0xaa,
    'ATTR': 0xab,
    'AT': 0xac,
    'TAB': 0xad,
    'VAL$': 0xae,
    'CODE': 0xaf,
    'VAL': 0xb0,
    'LEN': 0xb1,
    'SIN': 0xb2,
    'COS': 0xb3,
    'TAN': 0xb4,
    'ASN': 0xb5,
    'ACS': 0xb6,
    'ATN': 0xb7,
    'LN': 0xb8,
    'EXP': 0xb9,
    'INT': 0xba,
    'SQR': 0xbb,
    'SGN': 0xbc,
    'ABS': 0xbd,
    'PEEK': 0xbe,
    'IN': 0xbf,
    'USR': 0xc0,
    'STR$': 0xc1,
    'CHR$': 0xc2,
    'NOT': 0xc3,
    'BIN': 0xc4,
    'OR': 0xc5,
    'AND': 0xc6,
    '<=': 0xc7,
    '>=': 0xc8,
    '<>': 0xc9,
    'LINE': 0xca,
    'THEN': 0xcb,
    'TO': 0xcc,
    'STEP': 0xcd,
    'DEF FN': 0xce,
    'CAT': 0xcf,
    'FORMAT': 0xd0,
    'MOVE': 0xd1,
    'ERASE': 0xd2,
    'OPEN #': 0xd3,
    'CLOSE #': 0xd4,
    'MERGE': 0xd5,
    'VERIFY': 0xd6,
    'BEEP': 0xd7,
    'CIRCLE': 0xd8,
    'INK': 0xd9,
    'PAPER': 0xda,
    'FLASH': 0xdb,
    'BRIGHT': 0xdc,
    'INVERSE': 0xdd,
    'OVER': 0xde,
    'OUT': 0xdf,
    'LPRINT': 0xe0,
    'LLIST': 0xe1,
    'STOP': 0xe2,
    'READ': 0xe3,
    'DATA': 0xe4,
    'RESTORE': 0xe5,
    'NEW': 0xe6,
    'BORDER': 0xe7,
    'CONTINUE': 0xe8,
    'DIM': 0xe9,
    'REM': 0xea,
    'FOR': 0xeb,
    'GOTO': 0xec,
    'GOSUB': 0xed,
    'INPUT': 0xee,
    'LOAD': 0xef,
    'LIST': 0xf0,
    'LET': 0xf1,
    'PAUSE': 0xf2,
    'NEXT': 0xf3,
    'POKE': 0xf4,
    'PRINT': 0xf5,
    'PLOT': 0xf6,
    'RUN': 0xf7,
    'SAVE': 0xf8,
    'RANDOMIZE': 0xf9,
    'IF': 0xfa,
    'CLS': 0xfb,
    'DRAW': 0xfc,
    'CLEAR': 0xfd,
    'RETURN': 0xfe,
    'COPY': 0xff,
}

UDG = {
    "  ": 128, " '": 129, "' ": 130, "''": 131, " .": 132, " :": 133, "'.": 134, "':": 135,
    ". ": 136, ".'": 137, ": ": 138, ":'": 139, "..": 140, ".:": 141, ":.": 142, "::": 143
}
#
# partial code porting from Russell Marks zmakebas.c  https://github.com/z00m128/zmakebas
#
# http://fileformats.archiveteam.org/wiki/Sinclair_BASIC_tokenized_file
#

# SPYCCY BASIC to TAP options syntax:
#!option = value
#
# options:
#  prog_name = max 10 char (default: "SPYCCY B2T")
#  use_labels = 0, 1  	(default: 1)
#  auto_start_line = n 	(run line number. default: 0x8000 no auto run)
#  auto_inc = n			(line number increment when use_labels = 1. default: 2)
#  first_line = n		(first line number when use_labels = 1. default: 2)
#
# example:
#!prog_name = "ZMAKEBAS"
#!use_labels = 1
#!auto_start_line = 1

def zmakebas(input, output, stdout=None):

    prog_name = "SPYCCY B2T"
    # basic text
    text_lines = []
    text_line = 0

    def get_text_line():
        nonlocal text_lines, text_line
        text_line += 1
        if text_line > len(text_lines):
            return None
        return text_lines[text_line-1].strip()

    def unget_text_line():
        nonlocal text_line
        text_line -= 1

    # output
    out_line = bytearray([0] * (1024 * 4))
    out_line_ptr = 0
    out_prog = bytearray([0] * (1024 * 48))
    out_prog_ptr = 0
    out_tape = bytearray([0] * 17)
    out_tape_ptr = 0

    def write_bytes(source, soff, len, dest, doff):
        for i in range(soff, len):
            dest[doff] = source[i]
            doff += 1
        return doff

    def write_line(bytes):
        nonlocal out_line, out_line_ptr
        for i in range(0, len(bytes)):
            out_line[out_line_ptr] = bytes[i]
            out_line_ptr += 1
        return out_line_ptr

    def write_line_byte(byte):
        nonlocal out_line, out_line_ptr
        out_line[out_line_ptr] = byte
        out_line_ptr += 1
        return out_line_ptr

    def write_number(num, exp, man):
        if num:
            write_line(bytes(num, "cp850"))
        write_line_byte(0x0e)
        write_line_byte(exp)
        write_line_byte((man >> 24) & 0xff)
        write_line_byte((man >> 16) & 0xff)
        write_line_byte((man >> 8) & 0xff)
        write_line_byte(man & 0xff)

    def write_prog(bas_line):
        nonlocal out_line, out_line_ptr, out_prog, out_prog_ptr
        out_prog[out_prog_ptr] = (bas_line >> 8) & 0xff
        out_prog[out_prog_ptr+1] = bas_line & 0xff
        out_prog[out_prog_ptr+2] = out_line_ptr & 0xff
        out_prog[out_prog_ptr+3] = (out_line_ptr >> 8) & 0xff
        out_prog_ptr += 4
        out_prog_ptr = write_bytes(out_line, 0, out_line_ptr, out_prog, out_prog_ptr)
        out_line_ptr = 0

    def write_tape():
        nonlocal out_line, out_line_ptr, out_prog, out_prog_ptr, out_tape, out_tape_ptr, target
        nonlocal auto_start_line
        out_tape[out_tape_ptr] = 0; out_tape_ptr += 1 # block type: program
        out_tape_ptr = write_bytes(bytes(prog_name, "cp850"), 0, 10, out_tape, out_tape_ptr)
        out_tape[out_tape_ptr] = out_prog_ptr & 0xff
        out_tape[out_tape_ptr+1] = (out_prog_ptr >> 8) & 0xff
        out_tape[out_tape_ptr+2] = auto_start_line & 0xff
        out_tape[out_tape_ptr+3] = (auto_start_line >> 8) & 0xff
        out_tape[out_tape_ptr+4] = out_prog_ptr & 0xff
        out_tape[out_tape_ptr+5] = (out_prog_ptr >> 8) & 0xff
        out_tape_ptr += 6

        target.write(bytes([19, 0, 0])) # header len + 1 flag byte
        chk = 0
        for i in range(0, 17):
            chk ^= out_tape[i]
        target.write(out_tape)
        target.write(bytes([chk]))

        size = out_prog_ptr + 2
        target.write(bytes([size & 0xff, (size >> 8) & 0xff, 0xff]))
        chk = 0xff
        for i in range(0, out_prog_ptr):
            chk ^= out_prog[i]

        target.write(out_prog[0:out_prog_ptr])
        target.write(bytes([chk]))

    # parsing
    use_labels = 0
    pass_num = 1
    pass_max = 2 if use_labels else 1
    auto_start_line = 0x8000 # no autorun
    auto_start_label = ""
    auto_incr = 2
    first_line = 2
    bas_line = 0
    bas_line_last = -1

    tokens = []
    tokens_len = 0
    tokens_index = 0
    token = ""
    token_code = 0
    token_delimiters = "</>=+-*;,'(:)#"

    labels = {}
    error_log = 0
    error_show = 1
    debug_delimiters = ""

    def is_number(s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    def parse(text):
        nonlocal tokens_len, tokens_index
        s = shlex.shlex(text, posix=False, punctuation_chars=token_delimiters)
        s.whitespace_split = True
        s.quotes = '"'
        s.commenters = ''
        _tks_ = list(s)
        tks = []

        for t in _tks_:     # fix potential joined delimiters
            if t[0:1] in token_delimiters:
                for c in t:
                    if c in token_delimiters:
                        tks.append(c)
            else:
                tks.append(t)

        tokens.clear()
        i = 0
        while i < len(tks):
            t = tks[i]
            if use_labels and i == 0 and t.startswith("@"):
                if tks[i+1] == ':':
                    tokens.append(t)
                    i += 1
                else:
                    error(f"line {text_line}: incomplete token definition\n")
                    return False

            elif t.upper() == 'GO':
                if tks[i+1].upper() == 'TO':
                    tokens.append(t+tks[i+1])
                    i += 1
                elif tks[i+1].upper() == 'SUB':
                    tokens.append(t+tks[i+1])
                    i += 1

            elif t.upper() == 'OPEN' or t.upper() == 'CLOSE':
                if tks[i+1] == '#':
                    tokens.append(t+" #")
                    i += 1

            elif t.upper() == 'DEF':
                if tks[i+1].upper() == 'FN':
                    tokens.append(t+" "+tks[i+1])
                    i += 1

            elif t == '<':
                if tks[i+1] == '=':
                    tokens.append("<=")
                    i += 1
                elif  tks[i+1] == '>':
                    tokens.append("<>")
                    i += 1
                else:
                    tokens.append(t)
            elif t == '>':
                if tks[i+1] == '=':
                    tokens.append(">=")
                    i += 1
                else:
                    tokens.append(t)

            else:
                tokens.append(t)

            i += 1

        tokens_len = len(tokens)
        tokens_index = 0

        return tokens

    def get_token():
        nonlocal tokens, tokens_index
        t = ""
        if tokens_index >= 0 and tokens_index < len(tokens):
            t = tokens[tokens_index]
            tokens_index += 1
        return t

    def peek_token(index):
        nonlocal tokens, tokens_index
        t = ""
        index = tokens_index + index
        if index >= 0 and index < len(tokens):
            t = tokens[index]
        return t

    def parse_string(t):
        ti = bytearray(t, encoding='cp850')
        to = bytearray([0] * len(ti))
        i = o = 0
        while i < len(ti):
            cb = ti[i]
            cc = chr(cb)
            if cc == '\\':
                i += 1
                cb = ti[i]
                cc = chr(cb)
                if cb | 0x20 >= ord('a') and cb |0x20 <= ord('u'):
                    to[o] = 144 + (cb|0x20) - ord('a')
                    o += 1; i += 1
                elif cc == '\\' or cc == '@':
                    to[o] = cb
                    o += 1; i += 1
                elif cc == '*':
                    to[o] = 127
                    o += 1; i += 1
                elif cc == '\'' or cc == '.' or cc == ':' or cc == ' ':
                    cc2 = cc + chr(ti[i+1])
                    if cc2 in UDG:
                        to[o] = UDG[cc2]
                    o += 1; i += 2
                elif cc == '{': # handled optional prefix: 0b, 0o, 0x or 0B, 0O, 0X.
                    i += 1
                    num = ""
                    while ti[i] != 125:  # { 123, } 125
                        num += chr(ti[i])
                        i += 1
                    to[o] = int(num, 0) & 0xff
                    o += 1; i += 1
                else:
                    error(f"line {text_line}: warning: unknown escape {cc}, inserting literally\n")
                    to[o] = ord('\\'); o += 1
                    to[o] = cb
                    o += 1; i += 1

            else:
                to[o] = ti[i]
                i += 1; o += 1

        return to[0:o]

    # dbl2spec() converts a double to an inline-basic-style speccy FP number.
    #
    # usage: dbl2spec(num)
    #
    # num is double to convert.
    #
    # returns 1 if ok, 0 if exponent too big.
    #         man: an unsigned long * to where to return the 4 mantissa bytes
    #         exp: exponent byte
    #
    # bit 31 is bit 7 of the 0th (first) mantissa byte, bit 0 is bit 0 of
    # the 3rd (last). As such, unsigned long returned *must* be written
    # to whatever file in big-endian format to make any sense to a speccy.
    def dbl2spec(num):
        man = 0
        exp = 0

        # check for small integers
        if num.is_integer() and num >= -65535 and num <= 65535:        # ignores sign - see below, applies to ints too.
            tmp = int(math.fabs(num))
            exp = 0
            man = ((tmp & 0xff) << 16) | ((tmp >> 8) << 8)
        else:
            # It appears that the sign bit is always left as 0 when floating-point
            # numbers are embedded in programs, the speccy appears to use the
            # '-' character to determine negativity - tests confirm self.
            # As such, *completely ignore* the sign of the number.
            # exp is 0x80+exponent.
            num = math.fabs(num)

            # binary standard form goes from 0.50000... to 0.9999...(dec), like
            # decimal which goes from        0.10000... to 0.9999....
            # as such, the number is >=1, gets divided by 2, exp++.
            # And if the number is <0.5, gets multiplied by 2, exp--.
            exp = 0
            while num >= 1.0:
                num /= 2.0
                exp += 1

            while num != 0 and num < 0.5:
                num *= 2.0
                exp -= 1

            # so now the number is in binary standard form in exp and num.
            # we check the range of exp... -128 <= exp <= 127.
            # (if outside, return error (i.e. 0))
            if exp < -128 or exp > 127:
                return 0, num, exp

            if num != 0:
                exp = 128 + exp

            # so now all we need to do is roll the bits off the mantissa in `num'.
            # we start at the 0.5ths bit at bit 0, shift left 1 each time
            # round the loop.
            num *= 2.0; # make it so that the 0.5ths bit is the integer part,
                        # and the rest is the fractional (0.xxx) part.

            man = 0
            for _ in range(0, 32):
                man <<= 1
                man |= int(num)
                num -= int(num)
                num *= 2.0

            # Now, if (int)num is non-zero (well, 1) then we should generally
            # round up 1. We don't do self if it would cause an overflow in the
            # mantissa, though.
            if (int(num) and man != 0xFFFFFFFF):
                man += 1

            # finally, out the top bit
            man &= 0x7FFFFFFF

        return 1, man, exp

    def error(text):
        nonlocal error_log, error_show
        if error_log and stdout:
            stdout.write(text)
        if error_show:
            messagebox.showerror("BASIC to tape", text)

    #try:
    source = open(input, "r", encoding="utf-8")
    target = open(output, "wb")
    if stdout:
        stdout = open(stdout, "+a")

    text_lines = source.readlines()

    while True:

        text_line = 0
        bas_line = first_line - auto_incr
        while True:
            line = get_text_line()
            if line is None:
                break

            if len(line) == 0:
                continue

            if line.startswith("#!"):
                if pass_num == 1:
                    #code = line[2:].strip()
                    #exec(code)
                    s = shlex.shlex(line[2:],posix=True)
                    var = s.get_token()
                    s.get_token() # =
                    if var == 'use_labels':
                        use_labels = int(s.get_token())
                        pass_max = 2 if use_labels else 1
                    elif var == 'auto_start_line':
                        auto_start_line = int(s.get_token())
                    elif var == 'auto_incr':
                        auto_incr = int(s.get_token())
                    elif var == 'first_line':
                        first_line = int(s.get_token())
                    elif var == 'prog_name':
                        prog_name = s.get_token()
                        l = len(prog_name)
                        if l > 10:
                            prog_name = prog_name[0:10]
                        elif l < 10:
                            prog_name = prog_name.ljust(10)
                continue

            if line.startswith("#"):
                continue

            while line.endswith("\\"):
                line = line[0:-1] + get_text_line()

            bas_line_last = bas_line
            tokens = parse(line)

            # line number
            if use_labels:
                token = peek_token(0)
                if token.isnumeric():
                    token = get_token()
                    ln = int(token)
                    if ln > bas_line:
                        bas_line = ln
                    else:
                        error(f"line {text_line}: line number ignored\n")
                else:
                    bas_line += auto_incr
                    if bas_line > 9999:
                        error("generated line number is > 9999\n")
                        return False
            else:
                token = get_token()
                if token.isnumeric():
                    bas_line = int(token)
                    if bas_line <= bas_line_last:
                        error(f"line {text_line}: line number not greater than previous one\n")
                        return False
                else:
                    error(f"line {text_line}: missing line number\n")
                    return False

            # labels
            if use_labels and peek_token(0).startswith("@"):
                if pass_num == 1:
                    label = get_token()
                    if not label in labels:
                        labels[label] = bas_line
                    else:
                        error(f"line {text_line}: attempt to redefine a label {label}\n")
                        return False

                if tokens_len == 1:
                    bas_line -= auto_incr
                    continue

            if use_labels and pass_num == 1:
                continue

            # statements
            while tokens_index < tokens_len:

                token_code = 0
                token = get_token()

                if use_labels and token.startswith("@"):
                    if token in labels:
                        label_line = labels[token]
                        tokens[tokens_index-1] = str(label_line)
                        ret, man, exp = dbl2spec(float(label_line))
                        if not ret:
                            error(f"line {text_line}: exponent out of range (number too big)\n")
                            return False
                        write_number(str(label_line), exp, man)
                    else:
                        error(f"line {text_line}: '{label}' undefined\n")
                        return False

                elif token.upper() in TOKENS:
                    token_code = TOKENS[token.upper()]
                    tokens[tokens_index-1] = f"{token} [{hex(token_code)}]"
                    write_line_byte(token_code)
                    if token_code == 0xea: # REM
                        not_first = 0
                        while tokens_index < tokens_len:
                            token = get_token()
                            if not_first:
                                write_line_byte(32) # blank
                            else:
                                not_first = 1
                            write_line(bytes(token, "cp850"))
                            if token == ":":
                                break

                    elif token_code == 0xce: # DEF FN
                        while tokens_index < tokens_len:
                            token = get_token()
                            if token == '=':
                                write_line(bytes(token, "cp850"))
                                break
                            elif peek_token(0) == ',' or (peek_token(0) == ')' and token != '('):
                                write_line(bytes(token, "cp850"))
                                write_number(None, 0, 0)
                            else:
                                write_line(bytes(token, "cp850"))

                elif token in token_delimiters:
                    write_line_byte(ord(token))
                    if stdout:
                        debug_delimiters += token + " "

                elif token.startswith('"'):
                    if token.find('\\') >= 0:
                        token = parse_string(token)
                    else:
                        token = bytes(token, "cp850")
                    write_line(token)
                    pass

                elif is_number(token):
                    if peek_token(-1) == "BIN":
                        num = float(int(token, 2))
                    else:
                        num = float(token)

                    ret, man, exp = dbl2spec(num)
                    if not ret:
                        error(f"line {text_line}: exponent out of range (number too big)\n")

                    tokens[tokens_index-1] = f"{token} [{hex(exp & 0xff)} e {hex((man >> 24) & 0xff)} {hex((man >> 16) & 0xff)} {hex((man >> 8) & 0xff)} {hex(man & 0xff)}]"
                    write_number(token, exp, man)

                else:
                    write_line(bytes(token, "cp850"))

            write_line_byte(0x0d) # add terminating CR
            if out_prog_ptr + out_line_ptr > len(out_prog):
                error("program too big!\n")
                return False
            write_prog(bas_line)

            if stdout:
                stdout.write(f"\n{debug_delimiters}"); debug_delimiters = ""
                stdout.write(f"\n{bas_line} {' '.join(tokens)}")
            #line_tokens[tokens_index-1] = f"{t} [{hex(exp & 0xff)} e {hex((man >> 24) & 0xff)} {hex((man >> 16) & 0xff)} {hex((man >> 8) & 0xff)} {hex(man & 0xff)}]"

        pass_num += 1
        if pass_num > pass_max:
            break

    if use_labels and auto_start_label != "":
        if token in labels:
            auto_start_line = labels[token]
        else:
            error(f"auto-start label {auto_start_label} is undefined\n")
            return False

    write_tape()

    #except Exception as e:
    #    print(e)

    #finally:
    source.close()
    target.close()
    if stdout:
        stdout.close()

    return True


"""
Call ZXBASIC Compiler
default options: "--tap --BASIC --autorun"
to override them insert before the first line of code:

'!args=options'

example:

'!args=--tzx --BASIC --autorun
10 PRINT "HELLO FROM SPYCCY!"

https://zxbasic.readthedocs.io/en/docs/zxb/#Command_Line_Options

"""

from io import StringIO
import sys

try:
    from src.zxbc import zxbc
    zxbc.OPTIONS._options['max_syntax_errors'] = 9999 # to avoid sys.exit(1) with more than 20 errors
    zx_basic_compiler = True
except:
    zx_basic_compiler = False

def zxbasic(input, output=None, stdout=None):

    if not zx_basic_compiler:
        return 99, None, "ZXBASIC not installed"

    # options
    args = get_options(input)
    if not args:
        args = ["--tzx", "--BASIC", "--autorun"]

    # output
    out_format = ".tzx"
    if "-t" in args or "--tap" in args:
        out_format = "tap"
    elif  "-T" in args or "--tzx" in args:
        out_format = "tzx"
    elif  "-A" in args:
        out_format = "asm"

    if not output:
        output = f"{input}.{out_format}"

    if "-o" not in args and "--output" not in args:
        args.append("-o")
        args.append(output)

    # stdout
    #if not stdout:
    #    stdout = input + ".log"
    #if "-e" not in args and "--errmsg" not in args:
    #    args.append("-e")
    #    args.append(stdout)
    #errors = ""

    old_stderr = sys.stderr
    sys.stderr = mystderr = StringIO()

    # input
    args.append(input)

    ret = zxbc.main(args)

    sys.stderr = old_stderr

    #if ret:
    #    with open(stdout, 'r') as f:
    #        errors = f.read()

    return ret, out_format, mystderr.getvalue()

def zxasm(input, output=None, stdout=None):

    if not zx_basic_compiler:
        return 99, None, "ZXBASIC not installed"

    # options
    args = get_options(input)
    if not args:
        args = ["-A"]
    else:
        args.append("-A")

    #output
    args.append("-o")
    args.append(output)

    old_stderr = sys.stderr
    sys.stderr = mystderr = StringIO()

    # input
    args.append(input)

    ret = zxbc.main(args)

    sys.stderr = old_stderr

    return ret, "asm", mystderr.getvalue()

def get_options(input):
    args = None
    source = open(input, "r", encoding="utf-8")
    lines = source.readlines()
    i = 0
    while True:
        line = lines[i]
        i += 1
        if line is None:
            break
        if len(line) == 0:
            continue
        if line.startswith('\'!args='):
            args = line[7:].split()
        elif line.startswith('\''):
            continue
        else:
            break
    source.close()

    return args
