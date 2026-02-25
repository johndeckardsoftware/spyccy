#
# Adapted from  Fuse - the Free Unix Spectrum Emulator  https://fuse-emulator.sourceforge.net/
#
# https://github.com/floooh/emu-info/tree/master/z80
#
from typing import Tuple, Callable, List
import app_globals
import z80profile2
import dis

# extend sign
def u8(val:int): return val & 0xff
def u1(val:int): return 1 if val else 0
def i8(val:int): return  ((val + 0x80) & 0xff) - 0x80
def i16(val:int): return ((val + 0x8000) & 0xffff) - 0x8000
def i32(val:int): return ((val + 0x80000000) & 0xffffffff) - 0x80000000
def unpack(rr): return rr >> 8, rr & 0xff
def pack(r1, r2): return (r1 << 8) | r2

def log(text : str) -> None:
  fh = open("./tmp/z80a.log", 'a')
  fh.write(text)
  fh.write("\n")
  fh.close()

# registers (af, bc, de, hl, ir pairs are created when needed)
a = 0
f = 0
b = 0
c = 0
d = 0
e = 0
h = 0
l = 0
i = 0
r = 0
ix = 0
iy = 0
af_ = 0
bc_ = 0
de_ = 0
hl_ = 0
sp = 0
pc = 0
xy_offset = 0
halted = 0
im = 0
iff1 = 0
iff2 = 0
t = 0
memptr: int = 0x0

interruptible = False  #  bool
opcode_prefix = 0  #  u8

app_globals.floating_bus_value = 0xff  #  u8
frame_cycle_count = 0  #  u32

def set_t_state(val):
  global t
  t = val

def get_t_state():
  global t
  return t

def inc_t_state():
  global t
  t += 1

def add_t_state(val):
  global t
  t += val

def set_pc(val):
  global pc
  pc = val

def get_pc():
  global pc
  return pc

def set_sp(val):
  global sp
  sp = val

def get_sp():
  global sp
  return sp

# used by tapedeck.basic_load
def get_af_():
  global af_
  return af_
def get_af():
  global a, f
  return pack(a, f)
def set_af(val):
  global a, f
  a, f = unpack(val)
def get_de():
  global d, e
  return pack(d, e)
def set_de(val):
  global d, e
  d, e = unpack(val)
def get_ix():
  global ix
  return ix
def set_ix(val):
  global ix
  ix = val

def set_registers(AF, BC, DE, HL, AF_, BC_, DE_, HL_, IX, IY, SP, IR):
  global a, f, b, c, d, e, h, l, i, r, ix, iy
  global af_, bc_, de_, hl_, sp, pc
  global xy_offset, halted, im, iff1, iff2

  a, f = unpack(AF)
  b, c = unpack(BC)
  d, e = unpack(DE)
  h, l = unpack(HL)
  af_ = AF_
  bc_ = BC_
  de_ = DE_
  hl_ = HL_
  ix = IX
  iy = IY
  sp = SP
  i, r = unpack(IR)

def get_registers():
  global a, f, b, c, d, e, h, l, i, r, ix, iy
  global af_, bc_, de_, hl_, sp, pc
  global xy_offset, halted, im, iff1, iff2

  dic = {}
  dic['A'] = a
  dic['F'] = f
  dic['AF'] = pack(a, f)
  dic['B'] = b
  dic['C'] = c
  dic['BC'] = pack(b, c)
  dic['D'] = d
  dic['E'] = e
  dic['DE'] = pack(d, e)
  dic['H'] = h
  dic['L'] = l
  dic['HL'] = pack(h, l)

  dic['A_'], dic['F_'] = unpack(af_)
  dic['AF_'] = af_
  dic['B_'], dic['C_'] = unpack(bc_)
  dic['BC_'] = bc_
  dic['D_'], dic['E_'] = unpack(de_)
  dic['DE_'] = de_
  dic['H_'], dic['L_'] = unpack(hl_)
  dic['HL_'] = hl_

  dic['Ix'], dic['X'] = unpack(ix)
  dic['IX'] = ix
  dic['Iy'], dic['Y'] = unpack(iy)
  dic['IY'] = iy

  dic['S'], dic['P'] = unpack(sp)
  dic['SP'] = sp

  dic['I'] = i
  dic['R'] = r
  dic['IR'] = pack(i, r)

  return dic

def get_cpu_state():
  global iff1, iff2, im, pc, t, memptr
  cpu_state = get_registers()
  cpu_state['iff1'] = iff1
  cpu_state['iff2'] = iff2
  cpu_state['im'] = im
  cpu_state['pc'] = pc
  cpu_state['t'] = t
  cpu_state['memptr'] = memptr
  return cpu_state

def set_cpu_state(snapshot):
  global a, f, b, c, d, e, h, l, i, r, ix, iy
  global af_, bc_, de_, hl_, sp, pc
  global xy_offset, halted, im, iff1, iff2, memptr

  a, f = unpack(snapshot['registers']['AF'])
  b, c = unpack(snapshot['registers']['BC'])
  d, e = unpack(snapshot['registers']['DE'])
  h, l = unpack(snapshot['registers']['HL'])
  af_ = snapshot['registers']['AF_']
  bc_ = snapshot['registers']['BC_']
  de_ = snapshot['registers']['DE_']
  hl_ = snapshot['registers']['HL_']
  ix = snapshot['registers']['IX']
  iy = snapshot['registers']['IY']
  sp = snapshot['registers']['SP']
  i, r = unpack(snapshot['registers']['IR'])
  pc = snapshot['registers']['PC']
  iff1 = snapshot['registers']['iff1']
  iff2 = snapshot['registers']['iff2']
  im = snapshot['registers']['im']
  #memptr = snapshot['registers']['memptr']

  if 'halted' in snapshot:
      halted = not not snapshot['halted']

#z80profile2.init_trace(log='./tmp/z80a5.log', profile=False, pcr_enabled=True, pcr_start=0x8000, ops_list=[0x37])
#z80profile2.init_trace(log='./tmp/z80a5.log', profile=False, pcr_enabled=True, pcr_start=0x8000)
#z80profile2.enable_log()
#z80profile2.enable_trace()

FLAG_C = 0x01
FLAG_N = 0x02
FLAG_P = 0x04
FLAG_V = 0x04
FLAG_3 = 0x08
FLAG_H = 0x10
FLAG_5 = 0x20
FLAG_Z = 0x40
FLAG_S = 0x80

halfcarryAddTable = bytearray([0, FLAG_H, FLAG_H, FLAG_H, 0, 0, 0, FLAG_H])
halfcarrySubTable = bytearray([0, 0, FLAG_H, 0, FLAG_H, 0, FLAG_H, FLAG_H])
overflowAddTable = bytearray([0, 0, 0, FLAG_V, FLAG_V, 0, 0, 0])
overflowSubTable = bytearray([0, FLAG_V, 0, 0, 0, 0, FLAG_V, 0])

def setup_parity_tables():
  i = 0
  while True:
    sz53Table[i] = (i & (FLAG_3 | FLAG_5 | FLAG_S))
    j = i
    parity = 0

    for k in range(0, 8):
      parity ^= (j & 1)
      j >>= 1

    parityTable[i] = 0 if parity else FLAG_P
    sz53pTable[i] = (sz53Table[i] | parityTable[i])
    sz53Table[0] |= FLAG_Z
    sz53pTable[0] |= FLAG_Z

    i += 1
    if (u8(i) == 0):
      break
sz53Table = bytearray(256)
parityTable = bytearray(256)
sz53pTable = bytearray(256)
setup_parity_tables()

opcodes: List[Callable] = [ None ] * 256
opcodes_cb: List[Callable] = [ None ] * 256
opcodes_dd: List[Callable] = [ None ] * 256
opcodes_ddcb: List[Callable] = [ None ] * 256
opcodes_ed: List[Callable] = [ None ] * 256
opcodes_fd: List[Callable] = [ None ] * 256
opcodes_fdcb: List[Callable] = [ None ] * 256

# memory manager
mmu = None
# in/out port manager
ports = None

# traps, rom switch and other tricks
# tape
tape_traps_enabled = True
will_trap = True  #  whether a trap on the next instruction will be honoured
# uSource
uSource = False
# TR-DOS beta disk 128
betadisk = False
betadisk_active = False
# machine configuration
machine = None

def reset(start_pc=0):
  global t, pc, sp, iff1, iff2, im, interruptible, halted, opcode_prefix, memptr
  t = 0
  pc = start_pc
  iff1 = iff2 = 0
  im = 0
  interruptible = False
  halted = False
  opcode_prefix = 0
  memptr = 0
  #set_registers(0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0x0000)
  set_registers(0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0)
  sp = 0x0

### status codes returned from runFrame / resumeFrame:
# 0 = OK (end of frame)
# 1 = unrecognised opcode (should never happen...)
###
def runFrame():
  return resumeFrame()

def resumeFrame():
  global will_trap
  status = runUntil(frame_cycle_count)
  if status:
    #  a non-zero status indicates we've broken out of the frame prematurely
    #  and will need to resume it with resumeFrame.
    #  When we do, a trap on the next instruction back will not be honoured
    #  (so that it's possible for the trap to leave pc unchanged without putting us
    #  in an infinite loop).
    will_trap = False
    return status
  return 0

def runUntil(max_t_state):
  global t, i, r, pc, sp, iff1, iff2, im, interruptible, halted, opcode_prefix
  global tape_traps_enabled, uSource, betadisk, betadisk_active, will_trap

  #will_trap = 0
  intVector = 0

  while ((t < max_t_state)):

    #if (((t < 36) and iff1) and interruptible):
    if (((t < 36) and iff1)):

      #mmu.uSource_paged = 0

      #  process interrupt
      if halted:
        #  move pc on from the HALT opcode
        pc = (pc + 1) & 0xffff
        halted = 0

      iff1 = iff2 = 0

      #  push current pc in readiness for call to interrupt handler
      sp = (sp - 1) & 0xffff
      mmu.write(sp, (pc >> 8))
      sp = (sp - 1) & 0xffff
      mmu.write(sp, (pc & 0xff))

      if (im == 1):
        pc = 0x0038
        t += 7
      elif (im == 2):
        intVector = (i << 8) | 0xff
        lo = mmu.read(intVector)
        hi = mmu.read(intVector + 1)
        pc = (lo | (hi << 8))
        t += 7
      else:  #  im == 0
        pc = 0x0038
        t += 6

    #if (pc == 0x056b) and tape_traps_enabled and will_trap:
    #  return 2  #  tape loading trap

    #if (pc == 0x04c2) and tape_traps_enabled and will_trap:
    #  machine.tapedeck.basic_save()  #  tape save trap

    if uSource and pc == 0x2bae:
      mmu.uSource_paged = not mmu.uSource_paged

    if betadisk:
      if pc >= 0x4000 and betadisk_active:
        mmu.switch_out_trdos()
        betadisk_active = False
      elif  ((pc & 0xff00) == 0x3d00) and not betadisk_active:
        mmu.switch_in_trdos()
        betadisk_active = True

    #will_trap = True

    op = mmu.peek(pc)  #  u8

    #z80profile2.add_opcode(op, pc, t)

    pc = (pc + 1) & 0xffff
    r = (r & 0x80) | ((r + 1) & 0x7f)
    opcodes[op]()
    t += 4

    #z80profile2.trace_step(get_cpu_state())

  return 0

def opcode_ed_cd():  #  basic_load
  global machine
  machine.tapedeck.basic_load()

def opcode_ed_2():  #  basic_save
  global pc, l, h, machine
  machine.tapedeck.basic_save()
  l = 0x3f    # exec original opcode 21 3f 05 (ld hl,0x053f)
  h = 0x05
  pc = pc + 1

def opcode_nop():    #  NOP
  pass

def opcode_cb():    #  CB prefix
  global t, pc, r
  t += 4
  op = mmu.peek(pc)  #  u8
  #z80profile2.add_opcode(op)
  pc = (pc + 1) & 0xffff
  r = (r & 0x80) | ((r + 1) & 0x7f)
  return opcodes_cb[op]()

def opcode_dd():    #  DD prefix
  global t, pc, r
  t += 4
  op = mmu.peek(pc)  #  u8
  #z80profile2.add_opcode(op)
  pc = (pc + 1) & 0xffff
  r = (r & 0x80) | ((r + 1) & 0x7f)
  return opcodes_dd[op]()

def opcode_ddcb():    #  DDCB prefix
  global t, xy_offset, pc, ix, memptr
  t += 4
  xy_offset = i8(mmu.peek(pc))
  memptr = (ix + xy_offset) & 0xffff
  #z80profile2.add_opcode(0)
  pc = (pc + 1) & 0xffff
  op = mmu.peek(pc)  #  u8
  #z80profile2.add_opcode(op)
  pc = (pc + 1) & 0xffff
  return opcodes_ddcb[op]()

def opcode_ed():    #  ED prefix
  global t, pc, r
  t += 4
  op = mmu.peek(pc)  #  u8
  #z80profile2.add_opcode(op)
  pc = (pc + 1) & 0xffff
  r = (r & 0x80) | ((r + 1) & 0x7f)
  return opcodes_ed[op]()

def opcode_fd():    #  FD prefix
  global t, pc, r
  t += 4
  op = mmu.peek(pc)  #  u8
  #z80profile2.add_opcode(op)
  pc = (pc + 1) & 0xffff
  r = (r & 0x80) | ((r + 1) & 0x7f)
  return opcodes_fd[op]()

def opcode_fdcb():    #  FDCB prefix
  global t, xy_offset, pc, iy, memptr
  t += 4
  xy_offset = i8(mmu.peek(pc))
  memptr = (iy + xy_offset) & 0xffff
  #z80profile2.add_opcode(0)
  pc = (pc + 1) & 0xffff
  op = mmu.peek(pc)  #  u8
  #z80profile2.add_opcode(op)
  pc = (pc + 1) & 0xffff
  return opcodes_fdcb[op]()

def opcode_1():    #  LD BC,nn
  global pc, b, c
  c = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  b = mmu.read(pc)
  pc = (pc + 1) & 0xffff

def opcode_2():    #  LD (BC),A
  global b, c, a, memptr
  bc = (b << 8) | c

  mmu.write(bc, a)
  memptr = (a << 8) | ((bc + 1) & 0xff)

def opcode_3():    #  INC BC
  global b, c, t
  bc = (b << 8) | c

  bc = (bc + 1)
  t += 2

  b = (bc >> 8) & 0xff; c = bc & 0xff

def opcode_4():    #  INC B
  global b, f
  b = (b + 1) & 0xff  #  u8
  f = (f & FLAG_C) | (FLAG_V if (b == 0x80) else 0) | (0 if (b & 0x0f) else FLAG_H) | sz53Table[b]

def opcode_5():    #  DEC B
  global b, f
  tempF = (f & FLAG_C) | (0 if (b & 0x0f) else FLAG_H) | FLAG_N  #  u8
  b = (b - 1) & 0xff  #  u8
  f = (tempF | (FLAG_V if (b == 0x7f) else 0) | sz53Table[b])

def opcode_6():    #  LD B,n
  global pc, b
  b = mmu.read(pc)
  pc = (pc + 1) & 0xffff

def opcode_7():    #  RLCA
  global a, f
  a = ((a << 1) | (a >> 7))
  f = ((f & (FLAG_P | FLAG_Z | FLAG_S)) | (a & (FLAG_C | FLAG_3 | FLAG_5)))

  a = a & 0xff

def opcode_8():    #  EX AF,AF'
  global a, f, af_
  af = (a << 8) | f

  tmp = af  #  u16
  af = af_
  af_ = tmp

  a = (af >> 8) & 0xff; f = af & 0xff

def opcode_9():    #  ADD HL,BC
  global h, l, b, c, f, i, r, t, memptr
  hl = (h << 8) | l
  bc = (b << 8) | c

  memptr = (hl + 1) & 0xffff
  #memptr = hl
  add16temp = (hl + bc)  #  u32
  lookup = ((hl & 0x0800) >> 11) | ((bc & 0x0800) >> 10) | ((add16temp & 0x0800) >> 9)  #  u32
  hl = add16temp
  f = (f & (FLAG_V | FLAG_Z | FLAG_S)) | (FLAG_C if (add16temp & 0x10000) else 0) | ((add16temp >> 8) & (FLAG_3 | FLAG_5)) | halfcarryAddTable[lookup]
  t += 7

  h = (hl >> 8) & 0xff; l = hl & 0xff

def opcode_a():    #  LD A,(BC)
  global a, b, c, memptr
  bc = (b << 8) | c

  a = mmu.read(bc)
  memptr = (bc + 1) & 0xffff

def opcode_b():    #  DEC BC
  global b, c, i, r, t
  bc = (b << 8) | c

  bc = (bc - 1)
  t += 2

  b = (bc >> 8) & 0xff; c = bc & 0xff

def opcode_c():    #  INC C
  global c, f
  c = (c + 1) & 0xff  #  u8
  f = (f & FLAG_C) | (FLAG_V if (c == 0x80) else 0) | (0 if (c & 0x0f) else FLAG_H) | sz53Table[c]

def opcode_d():    #  DEC C
  global c, f
  tempF = (f & FLAG_C) | (0 if (c & 0x0f) else FLAG_H) | FLAG_N  #  u8
  c = (c - 1) & 0xff  #  u8
  f = (tempF | (FLAG_V if (c == 0x7f) else 0) | sz53Table[c])

def opcode_e():    #  LD C,n
  global pc, c
  c = mmu.read(pc)
  pc = (pc + 1) & 0xffff

def opcode_f():    #  RRCA
  global a, f
  F = (f & (FLAG_P | FLAG_Z | FLAG_S)) | (a & FLAG_C)  #  u8
  a = ((a >> 1) | (a << 7))
  f = (F | (a & (FLAG_3 | FLAG_5)))

  a = a & 0xff

def opcode_10():    #  DJNZ n
  global t, b, pc, memptr
  t += 1
  b = (b - 1)  #  u8
  if b:
    #  take branch
    offset = mmu.read(pc)
    t += 5
    pc = (pc + i8(offset) + 1) & 0xffff
    memptr = pc
  else:
    #  do not take branch
    pc = (pc + 1) & 0xffff
    t += 3

  b = b & 0xff

def opcode_11():    #  LD DE,nn
  global pc, d, e

  e = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  d = mmu.read(pc)
  pc = (pc + 1) & 0xffff

def opcode_12():    #  LD (DE),A
  global d, e, a, memptr
  de = (d << 8) | e

  mmu.write(de, a)
  memptr = (a << 8) | ((de + 1) & 0xff)

def opcode_13():    #  INC DE
  global d, e, i, r, t
  de = (d << 8) | e

  de = (de + 1)
  t += 2

  d = (de >> 8) & 0xff; e = de & 0xff

def opcode_14():    #  INC D
  global d, f
  d = (d + 1) & 0xff  #  u8
  f = (f & FLAG_C) | (FLAG_V if (d == 0x80) else 0) | (0 if (d & 0x0f) else FLAG_H) | sz53Table[d]

def opcode_15():    #  DEC D
  global d, f
  tempF = (f & FLAG_C) | (0 if (d & 0x0f) else FLAG_H) | FLAG_N  #  u8
  d = (d - 1) & 0xff  #  u8
  f = (tempF | (FLAG_V if (d == 0x7f) else 0) | sz53Table[d])

def opcode_16():    #  LD D,n
  global pc, d
  d = mmu.read(pc)
  pc = (pc + 1) & 0xffff

def opcode_17():    #  RLA
  global a, f
  carry = a >> 7 #  u8
  a = ((a << 1) | (f & FLAG_C))  #  u8
  f = ((f & (FLAG_P | FLAG_Z | FLAG_S)) | (a & (FLAG_3 | FLAG_5)) | carry)

  a = a & 0xff

def opcode_18():    #  JR n
  global pc, t, memptr
  offset = mmu.read(pc)
  t += 5
  pc = (pc + i8(offset) + 1) & 0xffff
  memptr = pc

def opcode_19():    #  ADD HL,DE
  global h, l, d, e, f, i, r, t, memptr
  hl = (h << 8) | l
  de = (d << 8) | e

  memptr = (hl + 1) & 0xffff
  #memptr = hl
  add16temp = (hl + de)  #  u32
  lookup = ((hl & 0x0800) >> 11) | ((de & 0x0800) >> 10) | ((add16temp & 0x0800) >> 9)  #  u32
  hl = add16temp
  f = (f & (FLAG_V | FLAG_Z | FLAG_S)) | (FLAG_C if (add16temp & 0x10000) else 0) | ((add16temp >> 8) & (FLAG_3 | FLAG_5)) | halfcarryAddTable[lookup]
  t += 7

  h = (hl >> 8) & 0xff; l = hl & 0xff

def opcode_1a():    #  LD A,(DE)
  global a, d, e, memptr
  de = (d << 8) | e

  a = mmu.read(de)
  memptr = (de + 1) & 0xffff

def opcode_1b():    #  DEC DE
  global d, e, i, r, t
  de = (d << 8) | e

  de = (de - 1)
  t += 2

  d = (de >> 8) & 0xff; e = de & 0xff

def opcode_1c():    #  INC E
  global e, f

  e = (e + 1) & 0xff  #  u8
  f = (f & FLAG_C) | (FLAG_V if (e == 0x80) else 0) | (0 if (e & 0x0f) else FLAG_H) | sz53Table[e]

def opcode_1d():    #  DEC E
  global e, f
  tempF = (f & FLAG_C) | (0 if (e & 0x0f) else FLAG_H) | FLAG_N  #  u8
  e = (e - 1) & 0xff  #  u8
  f = (tempF | (FLAG_V if (e == 0x7f) else 0) | sz53Table[e])

def opcode_1e():    #  LD E,n
  global pc, e
  e = mmu.read(pc)
  pc = (pc + 1) & 0xffff

def opcode_1f():    #  RRA
  global a, f
  carry = a & FLAG_C  #  u8
  a = ((a >> 1) | (f << 7))
  f = ((f & (FLAG_P | FLAG_Z | FLAG_S)) | (a & (FLAG_3 | FLAG_5)) | carry)

  a = a & 0xff

def opcode_20():    #  JR NZ,n
  global f, pc, t, memptr
  if (not (f & FLAG_Z)):
    offset = mmu.read(pc)
    t += 5
    pc = (pc + i8(offset) + 1) & 0xffff
    memptr = pc
  else:
    pc = (pc + 1) & 0xffff
    t += 3

def opcode_21():    #  LD HL,nn
  global pc, h, l

  l = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  h = mmu.read(pc)
  pc = (pc + 1) & 0xffff

def opcode_22():    #  LD (nn),HL
  global pc, h, l, memptr

  lo = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  hi = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  addr = (lo | (hi << 8))
  mmu.write(addr, l)
  addr = (addr + 1) & 0xffff
  mmu.write(addr, h)
  #memptr = (mmu.peek16(pc - 3) + 1) & 0xffff  # pc - 3 = opcode
  memptr = addr

def opcode_23():    #  INC HL
  global h, l, t
  hl = (h << 8) | l

  hl = hl + 1
  t += 2

  h = (hl >> 8) & 0xff; l = hl & 0xff

def opcode_24():    #  INC H
  global h, f
  h = (h + 1) & 0xff  #  u8
  f = (f & FLAG_C) | (FLAG_V if (h == 0x80) else 0) | (0 if (h & 0x0f) else FLAG_H) | sz53Table[h]

def opcode_25():    #  DEC H
  global h, f
  tempF = (f & FLAG_C) | (0 if (h & 0x0f) else FLAG_H) | FLAG_N  #  u8
  h = (h - 1) & 0xff  #  u8
  f = (tempF | (FLAG_V if (h == 0x7f) else 0) | sz53Table[h])

def opcode_26():    #  LD H,n
  global pc, h
  h = mmu.read(pc)
  pc = (pc + 1) & 0xffff

def opcode_27():    #  DAA
  global a, f
  add = 0  #  u32
  A = a  #  u8
  F = f  #  u8
  carry = (F & FLAG_C)  #  u8
  if ((F & FLAG_H) or ((A & 0x0f) > 9)):
    add = 6
  if (carry or (A > 0x99)):
    add |= 0x60
  if (A > 0x99):
    carry = FLAG_C
  if (F & FLAG_N):
    result = (A - add)
    lookup = ((A & 0x88) >> 3) | ((add & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
    a = result & 0xff
    F = (FLAG_C if (result & 0x100) else 0) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | sz53Table[a]
  else:
    result = (A + add)
    lookup = ((A & 0x88) >> 3) | ((add & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
    a = result & 0xff
    F = (FLAG_C if (result & 0x100) else 0) | halfcarryAddTable[(lookup & 0x07)] | overflowAddTable[(lookup >> 4)] | sz53Table[a]
  f = ((F & (~(FLAG_C | FLAG_P))) | carry | parityTable[result & 0xff])

def opcode_28():    #  JR Z,n
  global f, pc, t, memptr
  if (f & FLAG_Z):
    offset = mmu.read(pc)
    t += 5
    pc = (pc + i8(offset) + 1) & 0xffff
    memptr = pc
  else:
    pc = (pc + 1) & 0xffff
    t += 3

def opcode_29():    #  ADD HL,HL
  global h, l, f, i, r, t, memptr
  hl = (h << 8) | l

  memptr = (hl + 1) & 0xffff
  #memptr = hl
  add16temp = (hl + hl)  #  u32
  lookup = ((hl & 0x0800) >> 11) | ((hl & 0x0800) >> 10) | ((add16temp & 0x0800) >> 9)  #  u32
  hl = add16temp
  f = (f & (FLAG_V | FLAG_Z | FLAG_S)) | (FLAG_C if (add16temp & 0x10000) else 0) | ((add16temp >> 8) & (FLAG_3 | FLAG_5)) | halfcarryAddTable[lookup]
  t += 7

  h = (hl >> 8) & 0xff; l = hl & 0xff

def opcode_2a():    #  LD HL,(nn)
  global pc, h, l, memptr

  lo = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  hi = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  addr = (lo | (hi << 8))
  l = mmu.read(addr)
  h = mmu.read((addr + 1))
  memptr = addr

def opcode_2b():    #  DEC HL
  global h, l, i, r, t
  hl = (h << 8) | l

  hl = (hl - 1)
  t += 2

  h = (hl >> 8) & 0xff; l = hl & 0xff

def opcode_2c():    #  INC L
  global l, f
  l = (l + 1) & 0xff  #  u8
  f = (f & FLAG_C) | (FLAG_V if (l == 0x80) else 0) | (0 if (l & 0x0f) else FLAG_H) | sz53Table[l]

def opcode_2d():    #  DEC L
  global l, f
  tempF = (f & FLAG_C) | (0 if (l & 0x0f) else FLAG_H) | FLAG_N  #  u8
  l = (l - 1) & 0xff  #  u8
  f = (tempF | (FLAG_V if (l == 0x7f) else 0) | sz53Table[l])

  l = l & 0xff

def opcode_2e():    #  LD L,n
  global pc, l
  l = mmu.read(pc)
  pc = (pc + 1) & 0xffff

def opcode_2f():    #  CPL
  global a, f
  a = (a ^ 0xff)  #  u8
  f = (f & (FLAG_C | FLAG_P | FLAG_Z | FLAG_S)) | ((a & (FLAG_3 | FLAG_5)) | FLAG_N | FLAG_H)

def opcode_30():    #  JR NC,n
  global f, pc, t, memptr
  if (not (f & FLAG_C)):
    offset = mmu.read(pc)
    t += 5
    pc = (pc + i8(offset) + 1) & 0xffff
    memptr = pc
  else:
    pc = (pc + 1) & 0xffff
    t += 3

def opcode_31():    #  LD SP,nn
  global pc, sp
  lo = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  hi = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  sp = (lo | (hi << 8))

def opcode_32():    #  LD (nn),A
  global pc, a, memptr
  lo = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  hi = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  addr = (lo | (hi << 8))
  mmu.write(addr, a)
  #memptr = (a << 8) | ((mmu.peek16(pc - 3) + 1) & 0xff)
  memptr = (a << 8) | ((addr + 1) & 0xff)

def opcode_33():    #  INC SP
  global sp, i, r, t
  sp = (sp + 1) & 0xffff
  t += 2

def opcode_34():    #  INC (HL)
  global h, l, t, f
  hl = (h << 8) | l

  val = mmu.read(hl)
  result = (val + 1) & 0xff  #  u8
  t += 1
  mmu.write(hl, result)
  f = (f & FLAG_C) | (FLAG_V if (result == 0x80) else 0) | (0 if (result & 0x0f) else FLAG_H) | sz53Table[result]

def opcode_35():    #  DEC (HL)
  global h, l, f, t
  hl = (h << 8) | l

  val = mmu.read(hl)
  tempF = (f & FLAG_C) | (0 if (val & 0x0f) else FLAG_H) | FLAG_N  #  u8
  result = (val - 1) & 0xff  #  u8
  t += 1
  mmu.write(hl, result)
  f = (tempF | (FLAG_V if (result == 0x7f) else 0) | sz53Table[result])

def opcode_36():    #  LD (HL),n
  global h, l, pc
  hl = (h << 8) | l

  mmu.write(hl, mmu.read(pc))
  pc = (pc + 1) & 0xffff

def opcode_37():    #  SCF
  global f, a, pc
  f = ((f & (FLAG_P | FLAG_Z | FLAG_S | FLAG_3 | FLAG_5)) | (a & (FLAG_3 | FLAG_5)) | FLAG_C)

def opcode_38():    #  JR C,n
  global f, pc, t, memptr
  if (f & FLAG_C):
    offset = mmu.read(pc)
    t += 5
    pc = (pc + i8(offset) + 1) & 0xffff
    memptr = pc
  else:
    pc = (pc + 1) & 0xffff
    t += 3

def opcode_39():    #  ADD HL,SP
  global h, l, sp, f, i, r, t, memptr
  hl = (h << 8) | l

  memptr = (hl + 1) & 0xffff
  #memptr = hl
  add16temp = (hl + sp)  #  u32
  lookup = ((hl & 0x0800) >> 11) | ((sp & 0x0800) >> 10) | ((add16temp & 0x0800) >> 9)  #  u32
  hl = add16temp
  f = (f & (FLAG_V | FLAG_Z | FLAG_S)) | (FLAG_C if (add16temp & 0x10000) else 0) | ((add16temp >> 8) & (FLAG_3 | FLAG_5)) | halfcarryAddTable[lookup]
  t += 7

  h = (hl >> 8) & 0xff; l = hl & 0xff

def opcode_3a():    #  LD A,(nn)
  global pc, a, memptr
  lo = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  hi = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  addr = (lo | (hi << 8))
  a = mmu.read(addr)
  #memptr = (mmu.peek16(pc - 3) + 1) & 0xffff  # pc - 3 = opcode
  memptr = (addr + 1) & 0xffff

def opcode_3b():    #  DEC SP
  global sp, i, r, t

  sp = (sp - 1)
  t += 2

def opcode_3c():    #  INC A
  global a, f
  a = (a + 1) & 0xff  #  u8
  f = (f & FLAG_C) | (FLAG_V if (a == 0x80) else 0) | (0 if (a & 0x0f) else FLAG_H) | sz53Table[a]

def opcode_3d():    #  DEC A
  global a, f
  tempF = (f & FLAG_C) | (0 if (a & 0x0f) else FLAG_H) | FLAG_N  #  u8
  a = (a - 1) & 0xff  #  u8
  f = (tempF | (FLAG_V if (a == 0x7f) else 0) | sz53Table[a])

def opcode_3e():    #  LD A,n
  global a, pc
  a = mmu.read(pc)
  pc = (pc + 1) & 0xffff

def opcode_3f():    #  CCF
  global f, a
  f = ((f & (FLAG_P | FLAG_Z | FLAG_S)) | (FLAG_H if (f & FLAG_C) else FLAG_C) | ((f | a) & (FLAG_3 | FLAG_5)))

def opcode_40():    #  LD B,B
  pass

def opcode_41():    #  LD B,C
  global b, c
  b = c

def opcode_42():    #  LD B,D
  global b, d
  b = d

def opcode_43():    #  LD B,E
  global b, e
  b = e

def opcode_44():    #  LD B,H
  global b, h
  b = h

def opcode_45():    #  LD B,L
  global l, b
  b = l

def opcode_46():    #  LD B,(HL)
  global b, h, l
  hl = (h << 8) | l

  b = mmu.read(hl)

def opcode_47():    #  LD B,A
  global b, a
  b = a

def opcode_48():    #  LD C,B
  global b, c
  c = b

def opcode_49():    #  LD C,C
  pass

def opcode_4a():    #  LD C,D
  global d, c
  c = d

def opcode_4b():    #  LD C,E
  global e, c
  c = e

def opcode_4c():    #  LD C,H
  global h, c
  c = h

def opcode_4d():    #  LD C,L
  global l, c
  c = l

def opcode_4e():    #  LD C,(HL)
  global h, l, c
  hl = (h << 8) | l

  c = mmu.read(hl)

def opcode_4f():    #  LD C,A
  global a, c
  c = a

def opcode_50():    #  LD D,B
  global b, d
  d = b

def opcode_51():    #  LD D,C
  global c, d
  d = c

def opcode_52():    #  LD D,D
  pass

def opcode_53():    #  LD D,E
  global e, d
  d = e

def opcode_54():    #  LD D,H
  global h, d
  d = h

def opcode_55():    #  LD D,L
  global l, d
  d = l

def opcode_56():    #  LD D,(HL)
  global h, l, d
  hl = (h << 8) | l

  d = mmu.read(hl)

def opcode_57():    #  LD D,A
  global a, d
  d = a

def opcode_58():    #  LD E,B
  global b, e
  e = b

def opcode_59():    #  LD E,C
  global c, e
  e = c

def opcode_5a():    #  LD E,D
  global d, e
  e = d

def opcode_5b():    #  LD E,E
  pass

def opcode_5c():    #  LD E,H
  global h, e
  e = h

def opcode_5d():    #  LD E,L
  global l, e
  e = l

def opcode_5e():    #  LD E,(HL)
  global h, l, e
  hl = (h << 8) | l

  e = mmu.read(hl)

def opcode_5f():    #  LD E,A
  global a, e
  e = a

def opcode_60():    #  LD H,B
  global b, h
  h = b

def opcode_61():    #  LD H,C
  global c, h
  h = c

def opcode_62():    #  LD H,D
  global d, h
  h = d

def opcode_63():    #  LD H,E
  global e, h
  h = e

def opcode_64():    #  LD H,H
  pass

def opcode_65():    #  LD H,L
  global l, h
  h = l

def opcode_66():    #  LD H,(HL)
  global h, l
  hl = (h << 8) | l

  h = mmu.read(hl)

def opcode_67():    #  LD H,A
  global a, h
  h = a

def opcode_68():    #  LD L,B
  global b, l
  l = b

def opcode_69():    #  LD L,C
  global c, l
  l = c

def opcode_6a():    #  LD L,D
  global d, l
  l = d

def opcode_6b():    #  LD L,E
  global e, l
  l = e

def opcode_6c():    #  LD L,H
  global h, l
  l = h

def opcode_6d():    #  LD L,L
  pass

def opcode_6e():    #  LD L,(HL)
  global h, l
  hl = (h << 8) | l

  l = mmu.read(hl)

def opcode_6f():    #  LD L,A
  global a, l
  l = a

def opcode_70():    #  LD (HL),B
  global h, l, b
  hl = (h << 8) | l

  mmu.write(hl, b)

def opcode_71():    #  LD (HL),C
  global h, l, c
  hl = (h << 8) | l

  mmu.write(hl, c)

def opcode_72():    #  LD (HL),D
  global h, l, d
  hl = (h << 8) | l

  mmu.write(hl, d)

def opcode_73():    #  LD (HL),E
  global h, l, e
  hl = (h << 8) | l

  mmu.write(hl, e)

def opcode_74():    #  LD (HL),H
  global h, l
  hl = (h << 8) | l

  mmu.write(hl, h)

def opcode_75():    #  LD (HL),L
  global h, l
  hl = (h << 8) | l

  mmu.write(hl, l)

def opcode_76():    #  HALT
  global halted, pc
  halted = 1
  pc = (pc - 1) & 0xffff

def opcode_77():    #  LD (HL),A
  global h, l, a
  hl = (h << 8) | l

  mmu.write(hl, a)

def opcode_78():    #  LD A,B
  global b, a
  a = b

def opcode_79():    #  LD A,C
  global c, a
  a = c

def opcode_7a():    #  LD A,D
  global d, a
  a = d

def opcode_7b():    #  LD A,E
  global e, a
  a = e

def opcode_7c():    #  LD A,H
  global h, a
  a = h

def opcode_7d():    #  LD A,L
  global l, a
  a = l

def opcode_7e():    #  LD A,(HL)
  global a, h, l
  hl = (h << 8) | l

  a = mmu.read(hl)

def opcode_7f():    #  LD A,A
  pass

def opcode_80():    #  ADD A,B
  global b, a, f
  result = (b + a)  #  u32
  lookup = ((a & 0x88) >> 3) | ((b & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | halfcarryAddTable[(lookup & 0x07)] | overflowAddTable[(lookup >> 4)] | sz53Table[a]

def opcode_81():    #  ADD A,C
  global c, a, f
  result = (c + a)  #  u32
  lookup = ((a & 0x88) >> 3) | ((c & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | halfcarryAddTable[(lookup & 0x07)] | overflowAddTable[(lookup >> 4)] | sz53Table[a]

def opcode_82():    #  ADD A,D
  global d, a, f
  result = (d + a)  #  u32
  lookup = ((a & 0x88) >> 3) | ((d & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | halfcarryAddTable[(lookup & 0x07)] | overflowAddTable[(lookup >> 4)] | sz53Table[a]

def opcode_83():    #  ADD A,E
  global e, a, f
  result = (e + a)  #  u32
  lookup = ((a & 0x88) >> 3) | ((e & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | halfcarryAddTable[(lookup & 0x07)] | overflowAddTable[(lookup >> 4)] | sz53Table[a]

def opcode_84():    #  ADD A,H
  global h, a, f
  result = (h + a)  #  u32
  lookup = ((a & 0x88) >> 3) | ((h & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | halfcarryAddTable[(lookup & 0x07)] | overflowAddTable[(lookup >> 4)] | sz53Table[a]

def opcode_85():    #  ADD A,L
  global l, a, f
  result = (l + a)  #  u32
  lookup = ((a & 0x88) >> 3) | ((l & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | halfcarryAddTable[(lookup & 0x07)] | overflowAddTable[(lookup >> 4)] | sz53Table[a]

def opcode_86():    #  ADD A,(HL)
  global h, l, a, f
  hl = (h << 8) | l

  val = mmu.read(hl)
  result = (val + a)  #  u32
  lookup = ((a & 0x88) >> 3) | ((val & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | halfcarryAddTable[(lookup & 0x07)] | overflowAddTable[(lookup >> 4)] | sz53Table[a]

def opcode_87():    #  ADD A,A
  global a, f
  result = (a + a)  #  u32
  lookup = ((a & 0x88) >> 3) | ((a & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | halfcarryAddTable[(lookup & 0x07)] | overflowAddTable[(lookup >> 4)] | sz53Table[a]

def opcode_88():    #  ADC A,B
  global b, a, f
  result = ((a + b) + (f & FLAG_C))  #  u32
  lookup = ((a & 0x88) >> 3) | ((b & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | halfcarryAddTable[(lookup & 0x07)] | overflowAddTable[(lookup >> 4)] | sz53Table[a]

  b = b & 0xff
  a = a & 0xff

def opcode_89():    #  ADC A,C
  global c, a, f
  result = ((a + c) + (f & FLAG_C))  #  u32
  lookup = ((a & 0x88) >> 3) | ((c & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | halfcarryAddTable[(lookup & 0x07)] | overflowAddTable[(lookup >> 4)] | sz53Table[a]

def opcode_8a():    #  ADC A,D
  global d, a, f
  result = ((a + d) + (f & FLAG_C))  #  u32
  lookup = ((a & 0x88) >> 3) | ((d & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | halfcarryAddTable[(lookup & 0x07)] | overflowAddTable[(lookup >> 4)] | sz53Table[a]

def opcode_8b():    #  ADC A,E
  global e, a, f
  result = ((a + e) + (f & FLAG_C))  #  u32
  lookup = ((a & 0x88) >> 3) | ((e & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | halfcarryAddTable[(lookup & 0x07)] | overflowAddTable[(lookup >> 4)] | sz53Table[a]

def opcode_8c():    #  ADC A,H
  global h, a, f
  result = ((a + h) + (f & FLAG_C))  #  u32
  lookup = ((a & 0x88) >> 3) | ((h & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | halfcarryAddTable[(lookup & 0x07)] | overflowAddTable[(lookup >> 4)] | sz53Table[a]

def opcode_8d():    #  ADC A,L
  global l, a, f
  result = ((a + l) + (f & FLAG_C))  #  u32
  lookup = ((a & 0x88) >> 3) | ((l & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | halfcarryAddTable[(lookup & 0x07)] | overflowAddTable[(lookup >> 4)] | sz53Table[a]

def opcode_8e():    #  ADC A,(HL)
  global h, l, a, f
  hl = (h << 8) | l

  val = mmu.read(hl)
  result = ((a + val) + (f & FLAG_C))  #  u32
  lookup = ((a & 0x88) >> 3) | ((val & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | halfcarryAddTable[(lookup & 0x07)] | overflowAddTable[(lookup >> 4)] | sz53Table[a]

def opcode_8f():    #  ADC A,A
  global a, f
  result = ((a + a) + (f & FLAG_C))  #  u32
  lookup = ((a & 0x88) >> 3) | ((a & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | halfcarryAddTable[(lookup & 0x07)] | overflowAddTable[(lookup >> 4)] | sz53Table[a]

def opcode_90():    #  SUB B
  global b, a, f
  result = (a - b)  #  u32
  lookup = ((a & 0x88) >> 3) | ((b & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | sz53Table[a]

def opcode_91():    #  SUB C
  global c, a, f
  result = (a - c)  #  u32
  lookup = ((a & 0x88) >> 3) | ((c & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | sz53Table[a]

def opcode_92():    #  SUB D
  global d, a, f
  result = (a - d)  #  u32
  lookup = ((a & 0x88) >> 3) | ((d & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | sz53Table[a]

def opcode_93():    #  SUB E
  global e, a, f
  result = (a - e)  #  u32
  lookup = ((a & 0x88) >> 3) | ((e & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | sz53Table[a]

def opcode_94():    #  SUB H
  global h, a, f
  result = (a - h)  #  u32
  lookup = ((a & 0x88) >> 3) | ((h & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | sz53Table[a]

def opcode_95():    #  SUB L
  global l, a, f
  result = (a - l)  #  u32
  lookup = ((a & 0x88) >> 3) | ((l & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | sz53Table[a]

def opcode_96():    #  SUB (HL)
  global h, l, a, f
  hl = (h << 8) | l

  val = mmu.read(hl)
  result = (a - val)  #  u32
  lookup = ((a & 0x88) >> 3) | ((val & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | sz53Table[a]

def opcode_97():    #  SUB A
  global a, f
  result = (a - a)  #  u32
  lookup = ((a & 0x88) >> 3) | ((a & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | sz53Table[a]

def opcode_98():    #  SBC A,B
  global b, a, f
  result = ((a - b) - (f & FLAG_C))  #  u32
  lookup = ((a & 0x88) >> 3) | ((b & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | sz53Table[a]

def opcode_99():    #  SBC A,C
  global c, a, f
  result = ((a - c) - (f & FLAG_C))  #  u32
  lookup = ((a & 0x88) >> 3) | ((c & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | sz53Table[a]

def opcode_9a():    #  SBC A,D
  global d, a, f
  result = ((a - d) - (f & FLAG_C))  #  u32
  lookup = ((a & 0x88) >> 3) | ((d & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | sz53Table[a]

def opcode_9b():    #  SBC A,E
  global e, a, f
  result = ((a - e) - (f & FLAG_C))  #  u32
  lookup = ((a & 0x88) >> 3) | ((e & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | sz53Table[a]

def opcode_9c():    #  SBC A,H
  global h, a, f
  result = ((a - h) - (f & FLAG_C))  #  u32
  lookup = ((a & 0x88) >> 3) | ((h & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | sz53Table[a]

def opcode_9d():    #  SBC A,L
  global l, a, f
  result = ((a - l) - (f & FLAG_C))  #  u32
  lookup = ((a & 0x88) >> 3) | ((l & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | sz53Table[a]

def opcode_9e():    #  SBC A,(HL)
  global h, l, a, f
  hl = (h << 8) | l

  val = mmu.read(hl)
  result = ((a - val) - (f & FLAG_C))  #  u32
  lookup = ((a & 0x88) >> 3) | ((val & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | sz53Table[a]

def opcode_9f():    #  SBC A,A
  global a, f
  result = ((a - a) - (f & FLAG_C))  #  u32
  lookup = ((a & 0x88) >> 3) | ((a & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | sz53Table[a]

def opcode_a0():    #  AND B
  global b, a, f
  a = (a & b)  #  u8
  f = (FLAG_H | sz53pTable[a])

def opcode_a1():    #  AND C
  global c, a, f
  a = (a & c)  #  u8
  f = (FLAG_H | sz53pTable[a])

def opcode_a2():    #  AND D
  global d, a, f
  a = (a & d)  #  u8
  f = (FLAG_H | sz53pTable[a])

def opcode_a3():    #  AND E
  global e, a, f
  a = (a & e)  #  u8
  f = (FLAG_H | sz53pTable[a])

def opcode_a4():    #  AND H
  global h, a, f
  a = (a & h)  #  u8
  f = (FLAG_H | sz53pTable[a])

def opcode_a5():    #  AND L
  global l, a, f
  a = (a & l)  #  u8
  f = (FLAG_H | sz53pTable[a])

def opcode_a6():    #  AND (HL)
  global h, l, a, f
  hl = (h << 8) | l

  val = mmu.read(hl)
  a = (a & val)  #  u8
  f = (FLAG_H | sz53pTable[a])

def opcode_a7():    #  AND A
  global f, a
  f = (FLAG_H | sz53pTable[a])

def opcode_a8():    #  XOR B
  global b, a, f
  a = (a ^ b)  #  u8
  f = sz53pTable[a]

def opcode_a9():    #  XOR C
  global c, a, f
  a = (a ^ c)  #  u8
  f = sz53pTable[a]

def opcode_aa():    #  XOR D
  global d, a, f
  a = (a ^ d)  #  u8
  f = sz53pTable[a]

def opcode_ab():    #  XOR E
  global e, a, f
  a = (a ^ e)  #  u8
  f = sz53pTable[a]

def opcode_ac():    #  XOR H
  global h, a, f
  a = (a ^ h)  #  u8
  f = sz53pTable[a]

def opcode_ad():    #  XOR L
  global l, a, f
  a = (a ^ l)  #  u8
  f = sz53pTable[a]

def opcode_ae():    #  XOR (HL)
  global h, l, a, f
  hl = (h << 8) | l

  val = mmu.read(hl)
  a = (a ^ val)  #  u8
  f = sz53pTable[a]

def opcode_af():    #  XOR A
  global a, f
  a = 0
  f = sz53pTable[0]

def opcode_b0():    #  OR B
  global b, a, f
  a = (a | b)  #  u8
  f = sz53pTable[a]

def opcode_b1():    #  OR C
  global c, a, f
  a = (a | c)  #  u8
  f = sz53pTable[a]

def opcode_b2():    #  OR D
  global d, a, f
  a = (a | d)  #  u8
  f = sz53pTable[a]

def opcode_b3():    #  OR E
  global e, a, f
  a = (a | e)  #  u8
  f = sz53pTable[a]

def opcode_b4():    #  OR H
  global h, a, f
  a = (a | h)  #  u8
  f = sz53pTable[a]

def opcode_b5():    #  OR L
  global l, a, f
  a = (a | l)  #  u8
  f = sz53pTable[a]

def opcode_b6():    #  OR (HL)
  global h, l, a, f
  hl = (h << 8) | l

  val = mmu.read(hl)
  a = (a | val)  #  u8
  f = sz53pTable[a]

def opcode_b7():    #  OR A
  global f, a
  f = sz53pTable[a]

def opcode_b8():    #  CP B
  global b, a, f
  val = b
  cptemp = (a - val)  #  u32
  lookup = ((a & 0x88) >> 3) | ((val & 0x88) >> 2) | ((cptemp & 0x88) >> 1)  #  u32
  f = (FLAG_C if (cptemp & 0x100) else (0 if cptemp else FLAG_Z)) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | (val & (FLAG_3 | FLAG_5)) | (cptemp & FLAG_S)

def opcode_b9():    #  CP C
  global c, a, f
  val = c
  cptemp = (a - val)  #  u32
  lookup = ((a & 0x88) >> 3) | ((val & 0x88) >> 2) | ((cptemp & 0x88) >> 1)  #  u32
  f = (FLAG_C if (cptemp & 0x100) else (0 if cptemp else FLAG_Z)) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | (val & (FLAG_3 | FLAG_5)) | (cptemp & FLAG_S)

def opcode_ba():    #  CP D
  global d, a, f
  val = d
  cptemp = (a - val)  #  u32
  lookup = ((a & 0x88) >> 3) | ((val & 0x88) >> 2) | ((cptemp & 0x88) >> 1)  #  u32
  f = (FLAG_C if (cptemp & 0x100) else (0 if cptemp else FLAG_Z)) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | (val & (FLAG_3 | FLAG_5)) | (cptemp & FLAG_S)

def opcode_bb():    #  CP E
  global e, a, f
  val = e
  cptemp = (a - val)  #  u32
  lookup = ((a & 0x88) >> 3) | ((val & 0x88) >> 2) | ((cptemp & 0x88) >> 1)  #  u32
  f = (FLAG_C if (cptemp & 0x100) else (0 if cptemp else FLAG_Z)) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | (val & (FLAG_3 | FLAG_5)) | (cptemp & FLAG_S)

def opcode_bc():    #  CP H
  global h, a, f
  val = h
  cptemp = (a - val)  #  u32
  lookup = ((a & 0x88) >> 3) | ((val & 0x88) >> 2) | ((cptemp & 0x88) >> 1)  #  u32
  f = (FLAG_C if (cptemp & 0x100) else (0 if cptemp else FLAG_Z)) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | (val & (FLAG_3 | FLAG_5)) | (cptemp & FLAG_S)

def opcode_bd():    #  CP L
  global l, a, f
  val = l
  cptemp = (a - val)  #  u32
  lookup = ((a & 0x88) >> 3) | ((val & 0x88) >> 2) | ((cptemp & 0x88) >> 1)  #  u32
  f = (FLAG_C if (cptemp & 0x100) else (0 if cptemp else FLAG_Z)) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | (val & (FLAG_3 | FLAG_5)) | (cptemp & FLAG_S)

def opcode_be():    #  CP (HL)
  global h, l, a, f
  hl = (h << 8) | l

  val = mmu.read(hl)
  cptemp = (a - val)  #  u32
  lookup = ((a & 0x88) >> 3) | ((val & 0x88) >> 2) | ((cptemp & 0x88) >> 1)  #  u32
  f = (FLAG_C if (cptemp & 0x100) else (0 if cptemp else FLAG_Z)) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | (val & (FLAG_3 | FLAG_5)) | (cptemp & FLAG_S)

def opcode_bf():    #  CP A
  global a, f
  val = a
  cptemp = (val - val)  #  u32
  lookup = ((val & 0x88) >> 3) | ((val & 0x88) >> 2) | ((cptemp & 0x88) >> 1)  #  u32
  f = (FLAG_C if (cptemp & 0x100) else (0 if cptemp else FLAG_Z)) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | (val & (FLAG_3 | FLAG_5)) | (cptemp & FLAG_S)

def opcode_c0():    #  RET NZ
  global t, f, sp, pc, memptr
  t += 1
  if (not (f & FLAG_Z)):
    #lo = mmu.read(sp)
    #sp = (sp + 1) & 0xffff
    #hi = mmu.read(sp)
    #sp = (sp + 1) & 0xffff
    #pc = (lo | (hi << 8))
    pc, sp = mmu.ret(sp)
    memptr = pc

def opcode_c1():    #  POP BC
  global sp, b, c
  #c = mmu.read(sp)
  #sp = (sp + 1) & 0xffff
  #b = mmu.read(sp)
  #sp = (sp + 1) & 0xffff
  sp, b, c = mmu.pop(sp)

def opcode_c2():    #  JP NZ,nn
  global pc, t, memptr
  pc, memptr = mmu.read_nn(pc)
  if (not (f & FLAG_Z)):
    #lo = mmu.read(pc)
    #pc = (pc + 1) & 0xffff
    #hi = mmu.read(pc)
    #pc = (pc + 1) & 0xffff
    #pc = (lo + (hi << 8))
    pc = memptr
  #else:
    #pc = (pc + 2) & 0xffff
    #t += 6

def opcode_c3():    #  JP nn
  global pc, memptr
  #lo = mmu.read(pc)
  #pc = (pc + 1) & 0xffff
  #hi = mmu.read(pc)
  #pc = (pc + 1) & 0xffff
  #pc = (lo + (hi << 8))
  pc, memptr = mmu.read_nn(pc)
  pc = memptr

def opcode_c4():    #  CALL NZ,nn
  global f, pc, t, sp, memptr
  pc, memptr = mmu.read_nn(pc)
  if (not (f & FLAG_Z)):
    #lo = mmu.read(pc)
    #pc = (pc + 1) & 0xffff
    #hi = mmu.read(pc)
    #t += 1
    #pc = (pc + 1) & 0xffff
    #sp = (sp - 1) & 0xffff
    #mmu.write(sp, (pc >> 8))
    #sp = (sp - 1) & 0xffff
    #mmu.write(sp, (pc & 0xff))
    #pc = (lo + (hi << 8))
    sp = mmu.push16(sp, pc)
    pc = memptr
  #else:
  #  pc = (pc + 2) & 0xffff
  #  t += 6

def opcode_c5():    #  PUSH BC
  global t, b, c, sp
  #t += 1
  #sp = (sp - 1) & 0xffff
  #mmu.write(sp, b)
  #sp = (sp - 1) & 0xffff
  #mmu.write(sp, c)
  sp = mmu.push(sp, b, c)

def opcode_c6():    #  ADD A,n
  global pc, a, f
  val = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  result = (val + a)  #  u32
  lookup = ((a & 0x88) >> 3) | ((val & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | halfcarryAddTable[(lookup & 0x07)] | overflowAddTable[(lookup >> 4)] | sz53Table[a]

def opcode_c7():    #  RST 0x00
  global t, sp, pc, memptr
  t += 1
  sp = (sp - 1) & 0xffff
  mmu.write(sp, (pc >> 8))
  sp = (sp - 1) & 0xffff
  mmu.write(sp, (pc & 0xff))
  pc = 0
  memptr = pc

def opcode_c8():    #  RET Z
  global t, f, sp, pc, memptr
  t += 1
  if (f & FLAG_Z):
    #lo = mmu.read(sp)
    #sp = (sp + 1) & 0xffff
    #hi = mmu.read(sp)
    #sp = (sp + 1) & 0xffff
    #pc = (lo | (hi << 8))
    pc, sp = mmu.ret(sp)
    memptr = pc

def opcode_c9():    #  RET
  global sp, pc, memptr
  #lo = mmu.read(sp)
  #sp = (sp + 1) & 0xffff
  #hi = mmu.read(sp)
  #sp = (sp + 1) & 0xffff
  #pc = (lo | (hi << 8))
  pc, sp = mmu.ret(sp)
  memptr = pc

def opcode_ca():    #  JP Z,nn
  global f, pc, t, memptr
  pc, memptr = mmu.read_nn(pc)
  if (f & FLAG_Z):
    #lo = mmu.read(pc)
    #pc = (pc + 1) & 0xffff
    #hi = mmu.read(pc)
    #pc = (pc + 1) & 0xffff
    #pc = (lo + (hi << 8))
    pc = memptr
  #else:
  #  pc = (pc + 2) & 0xffff
  #  t += 6

def opcode_cc():    #  CALL Z,nn
  global f, pc, t, sp, memptr
  pc, memptr = mmu.read_nn(pc)
  if (f & FLAG_Z):
    #lo = mmu.read(pc)
    #pc = (pc + 1) & 0xffff
    #hi = mmu.read(pc)
    #t += 1
    #pc = (pc + 1) & 0xffff
    #sp = (sp - 1) & 0xffff
    #mmu.write(sp, (pc >> 8))
    #sp = (sp - 1) & 0xffff
    #mmu.write(sp, (pc & 0xff))
    #pc = (lo + (hi << 8))
    sp = mmu.push16(sp, pc)
    pc = memptr
  #else:
  #  pc = (pc + 2) & 0xffff
  #  t += 6

def opcode_cd():    #  CALL nn
  global pc, t, sp, memptr
  pc, memptr = mmu.read_nn(pc)
  #lo = mmu.read(pc)
  #pc = (pc + 1) & 0xffff
  #hi = mmu.read(pc)
  #pc = (pc + 1) & 0xffff
  #t += 1
  #sp = (sp - 1) & 0xffff
  #mmu.write(sp, (pc >> 8))
  #sp = (sp - 1) & 0xffff
  #mmu.write(sp, (pc & 0xff))
  #pc = (lo + (hi << 8))
  sp = mmu.push16(sp, pc)
  pc = memptr

def opcode_ce():    #  ADC A,n
  global pc, a, f
  val = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  result = ((a + val) + (f & FLAG_C))  #  u32
  lookup = ((a & 0x88) >> 3) | ((val & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | halfcarryAddTable[(lookup & 0x07)] | overflowAddTable[(lookup >> 4)] | sz53Table[a]

def opcode_cf():    #  RST 0x08
  global t, sp, pc, memptr
  t += 1
  sp = (sp - 1) & 0xffff
  mmu.write(sp, (pc >> 8))
  sp = (sp - 1) & 0xffff
  mmu.write(sp, (pc & 0xff))
  pc = 8
  memptr = pc

def opcode_d0():    #  RET NC
  global t, f, sp, pc, memptr
  t += 1
  if (not (f & FLAG_C)):
    #lo = mmu.read(sp)
    #sp = (sp + 1) & 0xffff
    #hi = mmu.read(sp)
    #sp = (sp + 1) & 0xffff
    #pc = (lo | (hi << 8))
    pc, sp = mmu.ret(sp)
    memptr = pc

def opcode_d1():    #  POP DE
  global sp, d, e
  #e = mmu.read(sp)
  #sp = (sp + 1) & 0xffff
  #d = mmu.read(sp)
  #sp = (sp + 1) & 0xffff
  sp, d, e = mmu.pop(sp)

def opcode_d2():    #  JP NC,nn
  global f, pc, t, memptr
  pc, memptr = mmu.read_nn(pc)
  if (not (f & FLAG_C)):
    #lo = mmu.read(pc)
    #pc = (pc + 1) & 0xffff
    #hi = mmu.read(pc)
    #pc = (pc + 1) & 0xffff
    #pc = (lo + (hi << 8))
    pc = memptr
  #else:
  #  pc = (pc + 2) & 0xffff
  #  t += 6

def opcode_d3():    #  OUT (n),A
  global pc, a, memptr
  n = mmu.read(pc)  #  u16
  pc = (pc + 1) & 0xffff
  port = (a << 8) | n
  ports.write(port, a)
  memptr = (a << 8) | ((port + 1) & 0xff)

def opcode_d4():    #  CALL NC,nn
  global f, pc, t, sp, memptr
  pc, memptr = mmu.read_nn(pc)
  if (not (f & FLAG_C)):
    #lo = mmu.read(pc)
    #pc = (pc + 1) & 0xffff
    #hi = mmu.read(pc)
    #t += 1
    #pc = (pc + 1) & 0xffff
    #sp = (sp - 1) & 0xffff
    #mmu.write(sp, (pc >> 8))
    #sp = (sp - 1) & 0xffff
    #mmu.write(sp, (pc & 0xff))
    #pc = (lo + (hi << 8))
    sp = mmu.push16(sp, pc)
    pc = memptr
  #else:
  #  pc = (pc + 2) & 0xffff
  #  t += 6

def opcode_d5():    #  PUSH DE
  global t, d, e, sp
  #t += 1
  #sp = (sp - 1) & 0xffff
  #mmu.write(sp, d)
  #sp = (sp - 1) & 0xffff
  #mmu.write(sp, e)
  sp = mmu.push(sp, d, e)

def opcode_d6():    #  SUB n
  global pc, a, f
  val = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  result = (a - val)  #  u32
  lookup = ((a & 0x88) >> 3) | ((val & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | sz53Table[a]

def opcode_d7():    #  RST 0x10
  global t, sp, pc, memptr
  t += 1
  sp = (sp - 1) & 0xffff
  mmu.write(sp, (pc >> 8))
  sp = (sp - 1) & 0xffff
  mmu.write(sp, (pc & 0xff))
  pc = 16
  memptr = pc

def opcode_d8():    #  RET C
  global t, f, sp, pc, memptr
  t += 1
  if (f & FLAG_C):
    #lo = mmu.read(sp)
    #sp = (sp + 1) & 0xffff
    #hi = mmu.read(sp)
    #sp = (sp + 1) & 0xffff
    #pc = (lo | (hi << 8))
    pc, sp = mmu.ret(sp)
    memptr = pc

def opcode_d9():    #  EXX
  global b, c, bc_, d, e, de_, h, l, hl_
  bc = (b << 8) | c
  de = (d << 8) | e
  hl = (h << 8) | l

  tmp = bc  #  u16
  bc = bc_
  bc_ = tmp
  tmp = de
  de = de_
  de_ = tmp
  tmp = hl
  hl = hl_
  hl_ = tmp

  b = (bc >> 8) & 0xff; c = bc & 0xff
  d = (de >> 8) & 0xff; e = de & 0xff
  h = (hl >> 8) & 0xff; l = hl & 0xff

def opcode_da():    #  JP C,nn
  global f, pc, t, memptr
  pc, memptr = mmu.read_nn(pc)
  if (f & FLAG_C):
    #lo = mmu.read(pc)
    #pc = (pc + 1) & 0xffff
    #hi = mmu.read(pc)
    #pc = (pc + 1) & 0xffff
    #pc = (lo + (hi << 8))
    pc = memptr
  #else:
  #  pc = (pc + 2) & 0xffff
  #  t += 6

def opcode_db():    #  IN A,(n)
  global a, pc, memptr
  n = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  port = (a << 8) | n  #  u16
  memptr = (port + 1) & 0xffff
  a = ports.read(port)

def opcode_dc():    #  CALL C,nn
  global f, pc, t, sp, memptr
  pc, memptr = mmu.read_nn(pc)
  if (f & FLAG_C):
    #lo = mmu.read(pc)
    #pc = (pc + 1) & 0xffff
    #hi = mmu.read(pc)
    #t += 1
    #pc = (pc + 1) & 0xffff
    #sp = (sp - 1) & 0xffff
    #mmu.write(sp, (pc >> 8))
    #sp = (sp - 1) & 0xffff
    #mmu.write(sp, (pc & 0xff))
    #pc = (lo + (hi << 8))
    sp = mmu.push16(sp, pc)
    pc = memptr
  #else:
  #  pc = (pc + 2) & 0xffff
  #  t += 6

def opcode_de():    #  SBC A,n
  global pc, a, f
  val = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  result = ((a - val) - (f & FLAG_C))  #  u32
  lookup = ((a & 0x88) >> 3) | ((val & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | sz53Table[a]

def opcode_df():    #  RST 0x18
  global t, sp, pc, memptr
  t += 1
  sp = (sp - 1) & 0xffff
  mmu.write(sp, (pc >> 8))
  sp = (sp - 1) & 0xffff
  mmu.write(sp, (pc & 0xff))
  pc = 24
  memptr = pc

def opcode_e0():    #  RET PO
  global t, f, sp, pc, memptr
  t += 1
  if (not (f & FLAG_V)):
    #lo = mmu.read(sp)
    #sp = (sp + 1) & 0xffff
    #hi = mmu.read(sp)
    #sp = (sp + 1) & 0xffff
    #pc = (lo | (hi << 8))
    pc, sp = mmu.ret(sp)
    memptr = pc

def opcode_e1():    #  POP HL
  global sp, h, l
  #l = mmu.read(sp)
  #sp = (sp + 1) & 0xffff
  #h = mmu.read(sp)
  #sp = (sp + 1) & 0xffff
  sp, h, l = mmu.pop(sp)

def opcode_e2():    #  JP PO,nn
  global f, pc, t, memptr
  pc, memptr = mmu.read_nn(pc)
  if (not (f & FLAG_V)):
    #lo = mmu.read(pc)
    #pc = (pc + 1) & 0xffff
    #hi = mmu.read(pc)
    #pc = (pc + 1) & 0xffff
    #pc = (lo + (hi << 8))
    pc = memptr
  #else:
  #  pc = (pc + 2) & 0xffff
  #  t += 6

def opcode_e3():    #  EX (SP),HL
  global sp, t, h, l, memptr

  lo = mmu.read(sp)
  hi = mmu.read((sp + 1))
  mmu.write((sp + 1), h)
  mmu.write(sp, l)
  h = hi
  l = lo
  memptr = (h << 8) | l
  t += 3

def opcode_e4():    #  CALL PO,nn
  global f, pc, t, sp, memptr
  pc, memptr = mmu.read_nn(pc)
  if (not (f & FLAG_V)):
    #lo = mmu.read(pc)
    #pc = (pc + 1) & 0xffff
    #hi = mmu.read(pc)
    #t += 1
    #pc = (pc + 1) & 0xffff
    #sp = (sp - 1) & 0xffff
    #mmu.write(sp, (pc >> 8))
    #sp = (sp - 1) & 0xffff
    #mmu.write(sp, (pc & 0xff))
    #pc = (lo + (hi << 8))
    sp = mmu.push16(sp, pc)
    pc = memptr
  #else:
  #  pc = (pc + 2) & 0xffff
  #  t += 6

def opcode_e5():    #  PUSH HL
  global t, h, l, sp
  #t += 1
  #sp = (sp - 1) & 0xffff
  #mmu.write(sp, h)
  #sp = (sp - 1) & 0xffff
  #mmu.write(sp, l)
  sp = mmu.push(sp, h, l)

def opcode_e6():    #  AND n
  global pc, a, f
  val = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  a = (a & val)  #  u8
  f = (FLAG_H | sz53pTable[a])

def opcode_e7():    #  RST 0x20
  global t, sp, pc, memptr
  t += 1
  sp = (sp - 1) & 0xffff
  mmu.write(sp, (pc >> 8))
  sp = (sp - 1) & 0xffff
  mmu.write(sp, (pc & 0xff))
  pc = 32
  memptr = pc

def opcode_e8():    #  RET PE
  global t, f, sp, pc, memptr
  t += 1
  if (f & FLAG_V):
    #lo = mmu.read(sp)
    #sp = (sp + 1) & 0xffff
    #hi = mmu.read(sp)
    #sp = (sp + 1) & 0xffff
    #pc = (lo | (hi << 8))
    pc, sp = mmu.ret(sp)
    memptr = pc

def opcode_e9():    #  JP (HL)
  global pc, h, l
  hl = (h << 8) | l

  pc = hl

def opcode_ea():    #  JP PE,nn
  global f, pc, t, memptr
  pc, memptr = mmu.read_nn(pc)
  if (f & FLAG_V):
    #lo = mmu.read(pc)
    #pc = (pc + 1) & 0xffff
    #hi = mmu.read(pc)
    #pc = (pc + 1) & 0xffff
    #pc = (lo + (hi << 8))
    pc = memptr
  #else:
  #  pc = (pc + 2) & 0xffff
  #  t += 6

def opcode_eb():    #  EX DE,HL
  global d, e, h, l
  tmp = d
  d = h
  h = tmp
  tmp = e
  e = l
  l = tmp

def opcode_ec():    #  CALL PE,nn
  global f, pc, t, sp, memptr
  pc, memptr = mmu.read_nn(pc)
  if (f & FLAG_V):
    #lo = mmu.read(pc)
    #pc = (pc + 1) & 0xffff
    #hi = mmu.read(pc)
    #t += 1
    #pc = (pc + 1) & 0xffff
    #sp = (sp - 1) & 0xffff
    #mmu.write(sp, (pc >> 8))
    #sp = (sp - 1) & 0xffff
    #mmu.write(sp, (pc & 0xff))
    #pc = (lo + (hi << 8))
    sp = mmu.push16(sp, pc)
    pc = memptr
  #else:
  #  pc = (pc + 2) & 0xffff
  #  t += 6

def opcode_ee():    #  XOR n
  global pc, a, f
  val = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  a = (a ^ val)  #  u8
  f = sz53pTable[a]

def opcode_ef():    #  RST 0x28
  global t, sp, pc, memptr
  t += 1
  sp = (sp - 1) & 0xffff
  mmu.write(sp, (pc >> 8))
  sp = (sp - 1) & 0xffff
  mmu.write(sp, (pc & 0xff))
  pc = 40
  memptr = pc

def opcode_f0():    #  RET P
  global t, f, sp, pc, memptr
  t += 1
  if (not (f & FLAG_S)):
    #lo = mmu.read(sp)
    #sp = (sp + 1) & 0xffff
    #hi = mmu.read(sp)
    #sp = (sp + 1) & 0xffff
    #pc = (lo | (hi << 8))
    pc, sp = mmu.ret(sp)
    memptr = pc

def opcode_f1():    #  POP AF
  global sp, a, f
  #f = mmu.read(sp)
  #sp = (sp + 1) & 0xffff
  #a = mmu.read(sp)
  #sp = (sp + 1) & 0xffff
  sp, a, f = mmu.pop(sp)

def opcode_f2():    #  JP P,nn
  global f, pc, t, memptr
  pc, memptr = mmu.read_nn(pc)
  if (not (f & FLAG_S)):
    #lo = mmu.read(pc)
    #pc = (pc + 1) & 0xffff
    #hi = mmu.read(pc)
    #pc = (pc + 1) & 0xffff
    #pc = (lo + (hi << 8))
    pc = memptr
  #else:
  #  pc = (pc + 2) & 0xffff
  #  t += 6

def opcode_f3():    #  DI
  global iff1, iff2
  iff1 = iff2 = 0

def opcode_f4():    #  CALL P,nn
  global f, pc, t, sp, memptr
  pc, memptr = mmu.read_nn(pc)
  if (not (f & FLAG_S)):
    #lo = mmu.read(pc)
    #pc = (pc + 1) & 0xffff
    #hi = mmu.read(pc)
    #t += 1
    #pc = (pc + 1) & 0xffff
    #sp = (sp - 1) & 0xffff
    #mmu.write(sp, (pc >> 8))
    #sp = (sp - 1) & 0xffff
    #mmu.write(sp, (pc & 0xff))
    #pc = (lo + (hi << 8))
    sp = mmu.push16(sp, pc)
    pc = memptr
  #else:
  #  pc = (pc + 2) & 0xffff
  #  t += 6

def opcode_f5():    #  PUSH AF
  global t, a, f, sp
  #t += 1
  #sp = (sp - 1) & 0xffff
  #mmu.write(sp, a)
  #sp = (sp - 1) & 0xffff
  #mmu.write(sp, f)
  sp = mmu.push(sp, a, f)

def opcode_f6():    #  OR n
  global pc, a, f
  val = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  a = (a | val)  #  u8
  f = sz53pTable[a]

def opcode_f7():    #  RST 0x30
  global t, sp, pc, memptr
  t += 1
  sp = (sp - 1) & 0xffff
  mmu.write(sp, (pc >> 8))
  sp = (sp - 1) & 0xffff
  mmu.write(sp, (pc & 0xff))
  pc = 48
  memptr = pc

def opcode_f8():    #  RET M
  global t, f, sp, pc, memptr
  t += 1
  if (f & FLAG_S):
    #lo = mmu.read(sp)
    #sp = (sp + 1) & 0xffff
    #hi = mmu.read(sp)
    #sp = (sp + 1) & 0xffff
    #pc = (lo | (hi << 8))
    pc, sp = mmu.ret(sp)
    memptr = pc

def opcode_f9():    #  LD SP,HL
  global sp, h, l, i, r, t
  hl = (h << 8) | l

  sp = hl
  t += 2

def opcode_fa():    #  JP M,nn
  global f, pc, t, memptr
  pc, memptr = mmu.read_nn(pc)
  if (f & FLAG_S):
    #lo = mmu.read(pc)
    #pc = (pc + 1) & 0xffff
    #hi = mmu.read(pc)
    #pc = (pc + 1) & 0xffff
    #pc = (lo + (hi << 8))
    pc = memptr
  #else:
  #  pc = (pc + 2) & 0xffff
  #  t += 6

def opcode_fb():    #  EI
  global iff1, iff2
  iff1 = iff2 = 1
  #interruptible = False

def opcode_fc():    #  CALL M,nn
  global f, pc, t, sp, memptr
  pc, memptr = mmu.read_nn(pc)
  if (f & FLAG_S):
    #lo = mmu.read(pc)
    #pc = (pc + 1) & 0xffff
    #hi = mmu.read(pc)
    #t += 1
    #pc = (pc + 1) & 0xffff
    #sp = (sp - 1) & 0xffff
    #mmu.write(sp, (pc >> 8))
    #sp = (sp - 1) & 0xffff
    #mmu.write(sp, (pc & 0xff))
    #pc = (lo + (hi << 8))
    sp = mmu.push16(sp, pc)
    pc = memptr
  #else:
  #  pc = (pc + 2) & 0xffff
  #  t += 6

def opcode_fe():    #  CP n
  global pc, a, f
  val = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  cptemp = (a - val)  #  u32
  lookup = ((a & 0x88) >> 3) | ((val & 0x88) >> 2) | ((cptemp & 0x88) >> 1)  #  u32
  f = (FLAG_C if (cptemp & 0x100) else (0 if cptemp else FLAG_Z)) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | (val & (FLAG_3 | FLAG_5)) | (cptemp & FLAG_S)

def opcode_ff():    #  RST 0x38
  global t, sp, pc, memptr
  t += 1
  sp = (sp - 1) & 0xffff
  mmu.write(sp, (pc >> 8))
  sp = (sp - 1) & 0xffff
  mmu.write(sp, (pc & 0xff))
  pc = 56
  memptr = pc

def opcode_cb_0():  #  RLC B
  global b, f
  b = ((b << 1) | (b >> 7)) & 0xff #  u8
  f = ((b & FLAG_C) | sz53pTable[b])

def opcode_cb_1():  #  RLC C
  global c, f
  c = ((c << 1) | (c >> 7)) & 0xff  #  u8
  f = ((c & FLAG_C) | sz53pTable[c])

def opcode_cb_2():  #  RLC D
  global d, f
  d = ((d << 1) | (d >> 7)) & 0xff  #  u8
  f = ((d & FLAG_C) | sz53pTable[d])

def opcode_cb_3():  #  RLC E
  global e, f
  e = ((e << 1) | (e >> 7)) & 0xff  #  u8
  f = ((e & FLAG_C) | sz53pTable[e])

def opcode_cb_4():  #  RLC H
  global h, f
  h = ((h << 1) | (h >> 7)) & 0xff  #  u8
  f = ((h & FLAG_C) | sz53pTable[h])

def opcode_cb_5():  #  RLC L
  global l, f
  l = ((l << 1) | (l >> 7)) & 0xff  #  u8
  f = ((l & FLAG_C) | sz53pTable[l])

def opcode_cb_6():  #  RLC (HL)
  global h, l, f, t
  hl = (h << 8) | l

  val = mmu.read(hl)
  result = ((val << 1) | (val >> 7)) & 0xff  #  u8
  f = ((result & FLAG_C) | sz53pTable[result])
  t += 1
  mmu.write(hl, result)

def opcode_cb_7():  #  RLC A
  global a, f
  a = ((a << 1) | (a >> 7)) & 0xff  #  u8
  f = ((a & FLAG_C) | sz53pTable[a])

def opcode_cb_8():  #  RRC B
  global b, f
  carry = (b & FLAG_C)  #  u8
  b = ((b >> 1) | (b << 7)) & 0xff #  u8
  f = (carry | sz53pTable[b])

def opcode_cb_9():  #  RRC C
  global c, f
  carry = (c & FLAG_C)  #  u8
  c = ((c >> 1) | (c << 7)) & 0xff  #  u8
  f = (carry | sz53pTable[c])

def opcode_cb_a():  #  RRC D
  global d, f
  carry = (d & FLAG_C)  #  u8
  d = ((d >> 1) | (d << 7)) & 0xff  #  u8
  f = (carry | sz53pTable[d])

def opcode_cb_b():  #  RRC E
  global e, f
  carry = (e & FLAG_C)  #  u8
  e = ((e >> 1) | (e << 7)) & 0xff  #  u8
  f = (carry | sz53pTable[e])

def opcode_cb_c():  #  RRC H
  global h, f
  carry = (h & FLAG_C)  #  u8
  h = ((h >> 1) | (h << 7)) & 0xff  #  u8
  f = (carry | sz53pTable[h])

def opcode_cb_d():  #  RRC L
  global l, f
  carry = (l & FLAG_C)  #  u8
  l = ((l >> 1) | (l << 7)) & 0xff  #  u8
  f = (carry | sz53pTable[l])

def opcode_cb_e():  #  RRC (HL)
  global h, l, f, t
  hl = (h << 8) | l

  val = mmu.read(hl)
  carry = (val & FLAG_C)  #  u8
  result = ((val >> 1) | (val << 7)) & 0xff  #  u8
  f = (carry | sz53pTable[result])
  t += 1
  mmu.write(hl, result)

def opcode_cb_f():  #  RRC A
  global a, f
  carry = (a & FLAG_C)  #  u8
  a = ((a >> 1) | (a << 7)) & 0xff  #  u8
  f = (carry | sz53pTable[a])

def opcode_cb_10():  #  RL B
  global b, f
  val = b
  result = ((val << 1) | (f & FLAG_C)) & 0xff  #  u8
  f = ((val >> 7) | sz53pTable[result])
  b = result

def opcode_cb_11():  #  RL C
  global c, f
  val = c
  result = ((val << 1) | (f & FLAG_C)) & 0xff  #  u8
  f = ((val >> 7) | sz53pTable[result])
  c = result

def opcode_cb_12():  #  RL D
  global d, f
  val = d
  result = ((val << 1) | (f & FLAG_C)) & 0xff  #  u8
  f = ((val >> 7) | sz53pTable[result])
  d = result

def opcode_cb_13():  #  RL E
  global e, f
  val = e
  result = ((val << 1) | (f & FLAG_C)) & 0xff  #  u8
  f = ((val >> 7) | sz53pTable[result])
  e = result

def opcode_cb_14():  #  RL H
  global h, f
  val = h
  result = ((val << 1) | (f & FLAG_C)) & 0xff  #  u8
  f = ((val >> 7) | sz53pTable[result])
  h = result

def opcode_cb_15():  #  RL L
  global l, f
  val = l
  result = ((val << 1) | (f & FLAG_C)) & 0xff  #  u8
  f = ((val >> 7) | sz53pTable[result])
  l = result

def opcode_cb_16():  #  RL (HL)
  global h, l, f, t
  hl = (h << 8) | l

  val = mmu.read(hl)
  result = ((val << 1) | (f & FLAG_C)) & 0xff  #  u8
  f = ((val >> 7) | sz53pTable[result])
  t += 1
  mmu.write(hl, result)

def opcode_cb_17():  #  RL A
  global a, f
  val = a
  result = ((val << 1) | (f & FLAG_C)) & 0xff  #  u8
  f = ((val >> 7) | sz53pTable[result])
  a = result

def opcode_cb_18():  #  RR B
  global b, f
  val = b
  result = ((val >> 1) | (f << 7)) & 0xff  #  u8
  f = ((val & FLAG_C) | sz53pTable[result])
  b = result

def opcode_cb_19():  #  RR C
  global c, f
  val = c
  result = ((val >> 1) | (f << 7)) & 0xff  #  u8
  f = ((val & FLAG_C) | sz53pTable[result])
  c = result

def opcode_cb_1a():  #  RR D
  global d, f
  val = d
  result = ((val >> 1) | (f << 7)) & 0xff  #  u8
  f = ((val & FLAG_C) | sz53pTable[result])
  d = result

def opcode_cb_1b():  #  RR E
  global e, f
  val = e
  result = ((val >> 1) | (f << 7)) & 0xff  #  u8
  f = ((val & FLAG_C) | sz53pTable[result])
  e = result

def opcode_cb_1c():  #  RR H
  global h, f
  val = h
  result = ((val >> 1) | (f << 7)) & 0xff  #  u8
  f = ((val & FLAG_C) | sz53pTable[result])
  h = result

def opcode_cb_1d():  #  RR L
  global l, f
  val = l
  result = ((val >> 1) | (f << 7)) & 0xff  #  u8
  f = ((val & FLAG_C) | sz53pTable[result])
  l = result

def opcode_cb_1e():  #  RR (HL)
  global h, l, f, t
  hl = (h << 8) | l

  val = mmu.read(hl)
  result = ((val >> 1) | (f << 7)) & 0xff  #  u8
  f = ((val & FLAG_C) | sz53pTable[result])
  t += 1
  mmu.write(hl, result)

def opcode_cb_1f():  #  RR A
  global a, f
  val = a
  result = ((val >> 1) | (f << 7)) & 0xff  #  u8
  f = ((val & FLAG_C) | sz53pTable[result])
  a = result

def opcode_cb_20():  #  SLA B
  global b, f
  carry = (b >> 7)  #  u8
  b = (b << 1) & 0xff  #  u8
  f = (carry | sz53pTable[b])

def opcode_cb_21():  #  SLA C
  global c, f
  carry = (c >> 7)  #  u8
  c = (c << 1) & 0xff #  u8
  f = (carry | sz53pTable[c])

def opcode_cb_22():  #  SLA D
  global d, f
  carry = (d >> 7)  #  u8
  d = (d << 1) & 0xff  #  u8
  f = (carry | sz53pTable[d])

def opcode_cb_23():  #  SLA E
  global e, f
  carry = (e >> 7)  #  u8
  e = (e << 1) & 0xff  #  u8
  f = (carry | sz53pTable[e])

def opcode_cb_24():  #  SLA H
  global h, f
  carry = (h >> 7)  #  u8
  h = (h << 1) & 0xff  #  u8
  f = (carry | sz53pTable[h])

def opcode_cb_25():  #  SLA L
  global l, f
  carry = (l >> 7)  #  u8
  l = (l << 1) & 0xff  #  u8
  f = (carry | sz53pTable[l])

def opcode_cb_26():  #  SLA (HL)
  global h, l, f, t
  hl = (h << 8) | l

  val = mmu.read(hl)
  carry = (val >> 7)  #  u8
  result = (val << 1) & 0xff  #  u8
  f = (carry | sz53pTable[result])
  t += 1
  mmu.write(hl, result)

def opcode_cb_27():  #  SLA A
  global a, f
  carry = (a >> 7)  #  u8
  a = (a << 1) & 0xff  #  u8
  f = (carry | sz53pTable[a])

def opcode_cb_28():  #  SRA B
  global b, f
  carry = (b & FLAG_C)  #  u8
  b = ((b & 0x80) | (b >> 1))  #  u8
  f = (carry | sz53pTable[b])

def opcode_cb_29():  #  SRA C
  global c, f
  carry = (c & FLAG_C)  #  u8
  c = ((c & 0x80) | (c >> 1))  #  u8
  f = (carry | sz53pTable[c])

def opcode_cb_2a():  #  SRA D
  global d, f
  carry = (d & FLAG_C)  #  u8
  d = ((d & 0x80) | (d >> 1))  #  u8
  f = (carry | sz53pTable[d])

def opcode_cb_2b():  #  SRA E
  global e, f
  carry = (e & FLAG_C)  #  u8
  e = ((e & 0x80) | (e >> 1))  #  u8
  f = (carry | sz53pTable[e])

def opcode_cb_2c():  #  SRA H
  global h, f
  carry = (h & FLAG_C)  #  u8
  h = ((h & 0x80) | (h >> 1))  #  u8
  f = (carry | sz53pTable[h])

def opcode_cb_2d():  #  SRA L
  global l, f
  carry = (l & FLAG_C)  #  u8
  l = ((l & 0x80) | (l >> 1))  #  u8
  f = (carry | sz53pTable[l])

def opcode_cb_2e():  #  SRA (HL)
  global h, l, f, t
  hl = (h << 8) | l

  val = mmu.read(hl)
  carry = (val & FLAG_C)  #  u8
  result = ((val & 0x80) | (val >> 1))  #  u8
  f = (carry | sz53pTable[result])
  t += 1
  mmu.write(hl, result)

def opcode_cb_2f():  #  SRA A
  global a, f
  carry = (a & FLAG_C)  #  u8
  a = ((a & 0x80) | (a >> 1))  #  u8
  f = (carry | sz53pTable[a])

def opcode_cb_30():  #  SLL B
  global b, f
  carry = (b >> 7)  #  u8
  b = ((b << 1) | 0x01) &0xff #  u8
  f = (carry | sz53pTable[b])

def opcode_cb_31():  #  SLL C
  global c, f
  carry = (c >> 7)  #  u8
  c = ((c << 1) | 0x01) &0xff #  u8
  f = (carry | sz53pTable[c])

def opcode_cb_32():  #  SLL D
  global d, f
  val = d
  carry = (d >> 7)  #  u8
  d = ((d << 1) | 0x01) &0xff #  u8
  f = (carry | sz53pTable[d])

def opcode_cb_33():  #  SLL E
  global e, f
  carry = (e >> 7)  #  u8
  e = ((e << 1) | 0x01) &0xff #  u8
  f = (carry | sz53pTable[e])

def opcode_cb_34():  #  SLL H
  global h, f
  carry = (h >> 7)  #  u8
  h = ((h << 1) | 0x01) &0xff #  u8
  f = (carry | sz53pTable[h])

def opcode_cb_35():  #  SLL L
  global l, f
  carry = (l >> 7)  #  u8
  l = ((l << 1) | 0x01) &0xff #  u8
  f = (carry | sz53pTable[l])

def opcode_cb_36():  #  SLL (HL)
  global h, l, f, t
  hl = (h << 8) | l

  val = mmu.read(hl)
  carry = (val >> 7)  #  u8
  result = ((val << 1) | 0x01) &0xff #  u8
  f = (carry | sz53pTable[result])
  t += 1
  mmu.write(hl, result)

def opcode_cb_37():  #  SLL A
  global a, f
  carry = (a >> 7)  #  u8
  a = ((a << 1) | 0x01) &0xff #  u8
  f = (carry | sz53pTable[a])

def opcode_cb_38():  #  SRL B
  global b, f
  carry = (b & FLAG_C)  #  u8
  b = (b >> 1)  #  u8
  f = (carry | sz53pTable[b])

def opcode_cb_39():  #  SRL C
  global c, f
  carry = (c & FLAG_C)  #  u8
  c = (c >> 1)  #  u8
  f = (carry | sz53pTable[c])

def opcode_cb_3a():  #  SRL D
  global d, f
  carry = (d & FLAG_C)  #  u8
  d = (d >> 1)  #  u8
  f = (carry | sz53pTable[d])

def opcode_cb_3b():  #  SRL E
  global e, f
  carry = (e & FLAG_C)  #  u8
  e = (e >> 1)  #  u8
  f = (carry | sz53pTable[e])

def opcode_cb_3c():  #  SRL H
  global h, f
  carry = (h & FLAG_C)  #  u8
  h = (h >> 1)  #  u8
  f = (carry | sz53pTable[h])

def opcode_cb_3d():  #  SRL L
  global l, f
  carry = (l & FLAG_C)  #  u8
  l = (l >> 1)  #  u8
  f = (carry | sz53pTable[l])

def opcode_cb_3e():  #  SRL (HL)
  global h, l, f, t
  hl = (h << 8) | l

  val = mmu.read(hl)
  carry = (val & FLAG_C)  #  u8
  result = (val >> 1)  #  u8
  f = (carry | sz53pTable[result])
  t += 1
  mmu.write(hl, result)

def opcode_cb_3f():  #  SRL A
  global a, f
  carry = (a & FLAG_C)  #  u8
  a = (a >> 1)  #  u8
  f = (carry | sz53pTable[a])

def opcode_cb_40():  #  BIT 0,B
  global b, f
  f = (f & FLAG_C) | FLAG_H | (b & (FLAG_3 | FLAG_5))  #  u8
  if (not (b & 1)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_41():  #  BIT 0,C
  global c, f
  f = (f & FLAG_C) | FLAG_H | (c & (FLAG_3 | FLAG_5))  #  u8
  if (not (c & 1)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_42():  #  BIT 0,D
  global d, f
  f = (f & FLAG_C) | FLAG_H | (d & (FLAG_3 | FLAG_5))  #  u8
  if (not (d & 1)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_43():  #  BIT 0,E
  global e, f
  f = (f & FLAG_C) | FLAG_H | (e & (FLAG_3 | FLAG_5))  #  u8
  if (not (e & 1)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_44():  #  BIT 0,H
  global h, f
  f = (f & FLAG_C) | FLAG_H | (h & (FLAG_3 | FLAG_5))  #  u8
  if (not (h & 1)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_45():  #  BIT 0,L
  global l, f
  f = (f & FLAG_C) | FLAG_H | (l & (FLAG_3 | FLAG_5))  #  u8
  if (not (l & 1)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_46():  #  BIT 0,(HL)
  global h, l, f, t, memptr
  hl = (h << 8) | l

  val = mmu.read(hl)  #  u8
  #f = (f & FLAG_C) | FLAG_H | (val & (FLAG_3 | FLAG_5))  #  u8
  f = (f & FLAG_C) | FLAG_H | (((memptr & 0xff00) >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 1)):
    f |= (FLAG_P | FLAG_Z)
  t += 1

def opcode_cb_47():  #  BIT 0,A
  global a, f
  f = (f & FLAG_C) | FLAG_H | (a & (FLAG_3 | FLAG_5))  #  u8
  if (not (a & 1)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_48():  #  BIT 1,B
  global b, f
  f = (f & FLAG_C) | FLAG_H | (b & (FLAG_3 | FLAG_5))  #  u8
  if (not (b & 2)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_49():  #  BIT 1,C
  global c, f
  f = (f & FLAG_C) | FLAG_H | (c & (FLAG_3 | FLAG_5))  #  u8
  if (not (c & 2)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_4a():  #  BIT 1,D
  global d, f
  f = (f & FLAG_C) | FLAG_H | (d & (FLAG_3 | FLAG_5))  #  u8
  if (not (d & 2)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_4b():  #  BIT 1,E
  global e, f
  f = (f & FLAG_C) | FLAG_H | (e & (FLAG_3 | FLAG_5))  #  u8
  if (not (e & 2)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_4c():  #  BIT 1,H
  global h, f
  f = (f & FLAG_C) | FLAG_H | (h & (FLAG_3 | FLAG_5))  #  u8
  if (not (h & 2)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_4d():  #  BIT 1,L
  global l, f
  f = (f & FLAG_C) | FLAG_H | (l & (FLAG_3 | FLAG_5))  #  u8
  if (not (l & 2)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_4e():  #  BIT 1,(HL)
  global h, l, f, t, memptr
  hl = (h << 8) | l

  val = mmu.read(hl)  #  u8
  f = (f & FLAG_C) | FLAG_H | (((memptr & 0xff00) >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 2)):
    f |= (FLAG_P | FLAG_Z)
  t += 1
def opcode_cb_4f():  #  BIT 1,A
  global a, f
  f = (f & FLAG_C) | FLAG_H | (a & (FLAG_3 | FLAG_5))  #  u8
  if (not (a & 2)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_50():  #  BIT 2,B
  global b, f
  f = (f & FLAG_C) | FLAG_H | (b & (FLAG_3 | FLAG_5))  #  u8
  if (not (b & 4)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_51():  #  BIT 2,C
  global c, f
  f = (f & FLAG_C) | FLAG_H | (c & (FLAG_3 | FLAG_5))  #  u8
  if (not (c & 4)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_52():  #  BIT 2,D
  global d, f
  f = (f & FLAG_C) | FLAG_H | (d & (FLAG_3 | FLAG_5))  #  u8
  if (not (d & 4)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_53():  #  BIT 2,E
  global e, f
  f = (f & FLAG_C) | FLAG_H | (e & (FLAG_3 | FLAG_5))  #  u8
  if (not (e & 4)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_54():  #  BIT 2,H
  global h, f
  f = (f & FLAG_C) | FLAG_H | (h & (FLAG_3 | FLAG_5))  #  u8
  if (not (h & 4)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_55():  #  BIT 2,L
  global l, f
  f = (f & FLAG_C) | FLAG_H | (l & (FLAG_3 | FLAG_5))  #  u8
  if (not (l & 4)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_56():  #  BIT 2,(HL)
  global h, l, f, t, memptr
  hl = (h << 8) | l

  val = mmu.read(hl)  #  u8
  f = (f & FLAG_C) | FLAG_H | (((memptr & 0xff00) >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 4)):
    f |= (FLAG_P | FLAG_Z)
  t += 1
def opcode_cb_57():  #  BIT 2,A
  global a, f
  f = (f & FLAG_C) | FLAG_H | (a & (FLAG_3 | FLAG_5))  #  u8
  if (not (a & 4)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_58():  #  BIT 3,B
  global b, f
  f = (f & FLAG_C) | FLAG_H | (b & (FLAG_3 | FLAG_5))  #  u8
  if (not (b & 8)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_59():  #  BIT 3,C
  global c, f
  f = (f & FLAG_C) | FLAG_H | (c & (FLAG_3 | FLAG_5))  #  u8
  if (not (c & 8)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_5a():  #  BIT 3,D
  global d, f
  f = (f & FLAG_C) | FLAG_H | (d & (FLAG_3 | FLAG_5))  #  u8
  if (not (d & 8)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_5b():  #  BIT 3,E
  global e, f
  f = (f & FLAG_C) | FLAG_H | (e & (FLAG_3 | FLAG_5))  #  u8
  if (not (e & 8)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_5c():  #  BIT 3,H
  global h, f
  f = (f & FLAG_C) | FLAG_H | (h & (FLAG_3 | FLAG_5))  #  u8
  if (not (h & 8)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_5d():  #  BIT 3,L
  global l, f
  f = (f & FLAG_C) | FLAG_H | (l & (FLAG_3 | FLAG_5))  #  u8
  if (not (l & 8)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_5e():  #  BIT 3,(HL)
  global h, l, f, t, memptr
  hl = (h << 8) | l

  val = mmu.read(hl)  #  u8
  f = (f & FLAG_C) | FLAG_H | (((memptr & 0xff00) >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 8)):
    f |= (FLAG_P | FLAG_Z)
  t += 1
def opcode_cb_5f():  #  BIT 3,A
  global a, f
  f = (f & FLAG_C) | FLAG_H | (a & (FLAG_3 | FLAG_5))  #  u8
  if (not (a & 8)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_60():  #  BIT 4,B
  global b, f
  f = (f & FLAG_C) | FLAG_H | (b & (FLAG_3 | FLAG_5))  #  u8
  if (not (b & 16)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_61():  #  BIT 4,C
  global c, f
  f = (f & FLAG_C) | FLAG_H | (c & (FLAG_3 | FLAG_5))  #  u8
  if (not (c & 16)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_62():  #  BIT 4,D
  global d, f
  f = (f & FLAG_C) | FLAG_H | (d & (FLAG_3 | FLAG_5))  #  u8
  if (not (d & 16)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_63():  #  BIT 4,E
  global e, f
  f = (f & FLAG_C) | FLAG_H | (e & (FLAG_3 | FLAG_5))  #  u8
  if (not (e & 16)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_64():  #  BIT 4,H
  global h, f
  f = (f & FLAG_C) | FLAG_H | (h & (FLAG_3 | FLAG_5))  #  u8
  if (not (h & 16)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_65():  #  BIT 4,L
  global l, f
  f = (f & FLAG_C) | FLAG_H | (l & (FLAG_3 | FLAG_5))  #  u8
  if (not (l & 16)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_66():  #  BIT 4,(HL)
  global h, l, f, t,memptr
  hl = (h << 8) | l

  val = mmu.read(hl)  #  u8
  f = (f & FLAG_C) | FLAG_H | (((memptr & 0xff00) >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 16)):
    f |= (FLAG_P | FLAG_Z)
  t += 1
def opcode_cb_67():  #  BIT 4,A
  global a, f
  f = (f & FLAG_C) | FLAG_H | (a & (FLAG_3 | FLAG_5))  #  u8
  if (not (a & 16)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_68():  #  BIT 5,B
  global b, f
  f = (f & FLAG_C) | FLAG_H | (b & (FLAG_3 | FLAG_5))  #  u8
  if (not (b & 32)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_69():  #  BIT 5,C
  global c, f
  f = (f & FLAG_C) | FLAG_H | (c & (FLAG_3 | FLAG_5))  #  u8
  if (not (c & 32)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_6a():  #  BIT 5,D
  global d, f
  f = (f & FLAG_C) | FLAG_H | (d & (FLAG_3 | FLAG_5))  #  u8
  if (not (d & 32)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_6b():  #  BIT 5,E
  global e, f
  f = (f & FLAG_C) | FLAG_H | (e & (FLAG_3 | FLAG_5))  #  u8
  if (not (e & 32)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_6c():  #  BIT 5,H
  global h, f
  f = (f & FLAG_C) | FLAG_H | (h & (FLAG_3 | FLAG_5))  #  u8
  if (not (h & 32)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_6d():  #  BIT 5,L
  global l, f
  f = (f & FLAG_C) | FLAG_H | (l & (FLAG_3 | FLAG_5))  #  u8
  if (not (l & 32)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_6e():  #  BIT 5,(HL)
  global h, l, f, t, memptr
  hl = (h << 8) | l

  val = mmu.read(hl)  #  u8
  f = (f & FLAG_C) | FLAG_H | (((memptr & 0xff00) >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 32)):
    f |= (FLAG_P | FLAG_Z)
  t += 1
def opcode_cb_6f():  #  BIT 5,A
  global a, f
  f = (f & FLAG_C) | FLAG_H | (a & (FLAG_3 | FLAG_5))  #  u8
  if (not (a & 32)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_70():  #  BIT 6,B
  global b, f
  f = (f & FLAG_C) | FLAG_H | (b & (FLAG_3 | FLAG_5))  #  u8
  if (not (b & 64)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_71():  #  BIT 6,C
  global c, f
  f = (f & FLAG_C) | FLAG_H | (c & (FLAG_3 | FLAG_5))  #  u8
  if (not (c & 64)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_72():  #  BIT 6,D
  global d, f
  f = (f & FLAG_C) | FLAG_H | (d & (FLAG_3 | FLAG_5))  #  u8
  if (not (d & 64)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_73():  #  BIT 6,E
  global e, f
  f = (f & FLAG_C) | FLAG_H | (e & (FLAG_3 | FLAG_5))  #  u8
  if (not (e & 64)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_74():  #  BIT 6,H
  global h, f
  f = (f & FLAG_C) | FLAG_H | (h & (FLAG_3 | FLAG_5))  #  u8
  if (not (h & 64)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_75():  #  BIT 6,L
  global l, f
  f = (f & FLAG_C) | FLAG_H | (l & (FLAG_3 | FLAG_5))  #  u8
  if (not (l & 64)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_76():  #  BIT 6,(HL)
  global h, l, f, t, memptr
  hl = (h << 8) | l

  val = mmu.read(hl)  #  u8
  f = (f & FLAG_C) | FLAG_H | (((memptr & 0xff00) >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 64)):
    f |= (FLAG_P | FLAG_Z)
  t += 1
def opcode_cb_77():  #  BIT 6,A
  global a, f
  f = (f & FLAG_C) | FLAG_H | (a & (FLAG_3 | FLAG_5))  #  u8
  if (not (a & 64)):
    f |= (FLAG_P | FLAG_Z)

def opcode_cb_78():  #  BIT 7,B
  global b, f
  f = (f & FLAG_C) | FLAG_H | (b & (FLAG_3 | FLAG_5))  #  u8
  if (not (b & 128)):
    f |= (FLAG_P | FLAG_Z)
  if (b & 0x80):
    f |= FLAG_S

def opcode_cb_79():  #  BIT 7,C
  global c, f
  f = (f & FLAG_C) | FLAG_H | (c & (FLAG_3 | FLAG_5))  #  u8
  if (not (c & 128)):
    f |= (FLAG_P | FLAG_Z)
  if (c & 0x80):
    f |= FLAG_S

def opcode_cb_7a():  #  BIT 7,D
  global d, f
  f = (f & FLAG_C) | FLAG_H | (d & (FLAG_3 | FLAG_5))  #  u8
  if (not (d & 128)):
    f |= (FLAG_P | FLAG_Z)
  if (d & 0x80):
    f |= FLAG_S

def opcode_cb_7b():  #  BIT 7,E
  global e, f
  f = (f & FLAG_C) | FLAG_H | (e & (FLAG_3 | FLAG_5))  #  u8
  if (not (e & 128)):
    f |= (FLAG_P | FLAG_Z)
  if (e & 0x80):
    f |= FLAG_S

def opcode_cb_7c():  #  BIT 7,H
  global h, f
  f = (f & FLAG_C) | FLAG_H | (h & (FLAG_3 | FLAG_5))  #  u8
  if (not (h & 128)):
    f |= (FLAG_P | FLAG_Z)
  if (h & 0x80):
    f |= FLAG_S

def opcode_cb_7d():  #  BIT 7,L
  global l, f
  f = (f & FLAG_C) | FLAG_H | (l & (FLAG_3 | FLAG_5))  #  u8
  if (not (l & 128)):
    f |= (FLAG_P | FLAG_Z)
  if (l & 0x80):
    f |= FLAG_S

def opcode_cb_7e():  #  BIT 7,(HL)
  global h, l, f, t, memptr
  hl = (h << 8) | l

  val = mmu.read(hl)  #  u8
  f = (f & FLAG_C) | FLAG_H | (((memptr & 0xff00) >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 128)):
    f |= (FLAG_P | FLAG_Z)
  if (val & 0x80):
    f |= FLAG_S
  t += 1
def opcode_cb_7f():  #  BIT 7,A
  global a, f
  f = (f & FLAG_C) | FLAG_H | (a & (FLAG_3 | FLAG_5))  #  u8
  if (not (a & 128)):
    f |= (FLAG_P | FLAG_Z)
  if (a & 0x80):
    f |= FLAG_S

def opcode_cb_80():  #  RES 0,B
  global b
  b = (b & 254)  #  u8

def opcode_cb_81():  #  RES 0,C
  global c
  c = (c & 254)  #  u8

def opcode_cb_82():  #  RES 0,D
  global d
  d = (d & 254)  #  u8

def opcode_cb_83():  #  RES 0,E
  global e
  e = (e & 254)  #  u8

def opcode_cb_84():  #  RES 0,H
  global h
  h = (h & 254)  #  u8

def opcode_cb_85():  #  RES 0,L
  global l
  l = (l & 254)  #  u8

def opcode_cb_86():  #  RES 0,(HL)
  global h, l, t
  hl = (h << 8) | l

  val = mmu.read(hl)
  result = (val & 254)  #  u8
  t += 1
  mmu.write(hl, result)
def opcode_cb_87():  #  RES 0,A
  global a
  a = (a & 254)  #  u8

def opcode_cb_88():  #  RES 1,B
  global b
  b = (b & 253)  #  u8

def opcode_cb_89():  #  RES 1,C
  global c
  c = (c & 253)  #  u8

def opcode_cb_8a():  #  RES 1,D
  global d
  d = (d & 253)  #  u8

def opcode_cb_8b():  #  RES 1,E
  global e
  e = (e & 253)  #  u8

def opcode_cb_8c():  #  RES 1,H
  global h
  h = (h & 253)  #  u8

def opcode_cb_8d():  #  RES 1,L
  global l
  l = (l & 253)  #  u8

def opcode_cb_8e():  #  RES 1,(HL)
  global h, l, t
  hl = (h << 8) | l

  val = mmu.read(hl)
  result = (val & 253)  #  u8
  t += 1
  mmu.write(hl, result)
def opcode_cb_8f():  #  RES 1,A
  global a
  a = (a & 253)  #  u8

def opcode_cb_90():  #  RES 2,B
  global b
  b = (b & 251)  #  u8

def opcode_cb_91():  #  RES 2,C
  global c
  c = (c & 251)  #  u8

def opcode_cb_92():  #  RES 2,D
  global d
  d = (d & 251)  #  u8

def opcode_cb_93():  #  RES 2,E
  global e
  e = (e & 251)  #  u8

def opcode_cb_94():  #  RES 2,H
  global h
  h = (h & 251)  #  u8

def opcode_cb_95():  #  RES 2,L
  global l
  l = (l & 251)  #  u8

def opcode_cb_96():  #  RES 2,(HL)
  global h, l, t
  hl = (h << 8) | l

  val = mmu.read(hl)
  result = (val & 251)  #  u8
  t += 1
  mmu.write(hl, result)
def opcode_cb_97():  #  RES 2,A
  global a
  a = (a & 251)  #  u8

def opcode_cb_98():  #  RES 3,B
  global b
  b = (b & 247)  #  u8

def opcode_cb_99():  #  RES 3,C
  global c
  c = (c & 247)  #  u8

def opcode_cb_9a():  #  RES 3,D
  global d
  d = (d & 247)  #  u8

def opcode_cb_9b():  #  RES 3,E
  global e
  e = (e & 247)  #  u8

def opcode_cb_9c():  #  RES 3,H
  global h
  h = (h & 247)  #  u8

def opcode_cb_9d():  #  RES 3,L
  global l
  l = (l & 247)  #  u8

def opcode_cb_9e():  #  RES 3,(HL)
  global h, l, t
  hl = (h << 8) | l

  val = mmu.read(hl)
  result = (val & 247)  #  u8
  t += 1
  mmu.write(hl, result)
def opcode_cb_9f():  #  RES 3,A
  global a
  a = (a & 247)  #  u8

def opcode_cb_a0():  #  RES 4,B
  global b
  b = (b & 239)  #  u8

def opcode_cb_a1():  #  RES 4,C
  global c
  c = (c & 239)  #  u8

def opcode_cb_a2():  #  RES 4,D
  global d
  d = (d & 239)  #  u8

def opcode_cb_a3():  #  RES 4,E
  global e
  e = (e & 239)  #  u8

def opcode_cb_a4():  #  RES 4,H
  global h
  h = (h & 239)  #  u8

def opcode_cb_a5():  #  RES 4,L
  global l
  l = (l & 239)  #  u8

def opcode_cb_a6():  #  RES 4,(HL)
  global h, l, t
  hl = (h << 8) | l

  val = mmu.read(hl)
  result = (val & 239)  #  u8
  t += 1
  mmu.write(hl, result)
def opcode_cb_a7():  #  RES 4,A
  global a
  a = (a & 239)  #  u8

def opcode_cb_a8():  #  RES 5,B
  global b
  b = (b & 223)  #  u8

def opcode_cb_a9():  #  RES 5,C
  global c
  c = (c & 223)  #  u8

def opcode_cb_aa():  #  RES 5,D
  global d
  d = (d & 223)  #  u8

def opcode_cb_ab():  #  RES 5,E
  global e
  e = (e & 223)  #  u8

def opcode_cb_ac():  #  RES 5,H
  global h
  h = (h & 223)  #  u8

def opcode_cb_ad():  #  RES 5,L
  global l
  l = (l & 223)  #  u8

def opcode_cb_ae():  #  RES 5,(HL)
  global h, l, t
  hl = (h << 8) | l

  val = mmu.read(hl)
  result = (val & 223)  #  u8
  t += 1
  mmu.write(hl, result)
def opcode_cb_af():  #  RES 5,A
  global a
  a = (a & 223)  #  u8

def opcode_cb_b0():  #  RES 6,B
  global b
  b = (b & 191)  #  u8

def opcode_cb_b1():  #  RES 6,C
  global c
  c = (c & 191)  #  u8

def opcode_cb_b2():  #  RES 6,D
  global d
  d = (d & 191)  #  u8

def opcode_cb_b3():  #  RES 6,E
  global e
  e = (e & 191)  #  u8

def opcode_cb_b4():  #  RES 6,H
  global h
  h = (h & 191)  #  u8

def opcode_cb_b5():  #  RES 6,L
  global l
  l = (l & 191)  #  u8

def opcode_cb_b6():  #  RES 6,(HL)
  global h, l, t
  hl = (h << 8) | l

  val = mmu.read(hl)
  result = (val & 191)  #  u8
  t += 1
  mmu.write(hl, result)
def opcode_cb_b7():  #  RES 6,A
  global a
  a = (a & 191)  #  u8

def opcode_cb_b8():  #  RES 7,B
  global b
  b = (b & 127)  #  u8

def opcode_cb_b9():  #  RES 7,C
  global c
  c = (c & 127)  #  u8

def opcode_cb_ba():  #  RES 7,D
  global d
  d = (d & 127)  #  u8

def opcode_cb_bb():  #  RES 7,E
  global e
  e = (e & 127)  #  u8

def opcode_cb_bc():  #  RES 7,H
  global h
  h = (h & 127)  #  u8

def opcode_cb_bd():  #  RES 7,L
  global l
  l = (l & 127)  #  u8

def opcode_cb_be():  #  RES 7,(HL)
  global h, l, t
  hl = (h << 8) | l

  val = mmu.read(hl)
  result = (val & 127)  #  u8
  t += 1
  mmu.write(hl, result)
def opcode_cb_bf():  #  RES 7,A
  global a
  a = (a & 127)  #  u8

def opcode_cb_c0():  #  SET 0,B
  global b
  b = (b | 1)  #  u8

def opcode_cb_c1():  #  SET 0,C
  global c
  c = (c | 1)  #  u8

def opcode_cb_c2():  #  SET 0,D
  global d
  d = (d | 1)  #  u8

def opcode_cb_c3():  #  SET 0,E
  global e
  e = (e | 1)  #  u8

def opcode_cb_c4():  #  SET 0,H
  global h
  h = (h | 1)  #  u8

def opcode_cb_c5():  #  SET 0,L
  global l
  l = (l | 1)  #  u8

def opcode_cb_c6():  #  SET 0,(HL)
  global h, l, t
  hl = (h << 8) | l

  val = mmu.read(hl)
  result = (val | 1)  #  u8
  t += 1
  mmu.write(hl, result)
def opcode_cb_c7():  #  SET 0,A
  global a
  a = (a | 1)  #  u8

def opcode_cb_c8():  #  SET 1,B
  global b
  b = (b | 2)  #  u8

def opcode_cb_c9():  #  SET 1,C
  global c
  c = (c | 2)  #  u8

def opcode_cb_ca():  #  SET 1,D
  global d
  d = (d | 2)  #  u8

def opcode_cb_cb():  #  SET 1,E
  global e
  e = (e | 2)  #  u8

def opcode_cb_cc():  #  SET 1,H
  global h
  h = (h | 2)  #  u8

def opcode_cb_cd():  #  SET 1,L
  global l
  l = (l | 2)  #  u8

def opcode_cb_ce():  #  SET 1,(HL)
  global h, l, t
  hl = (h << 8) | l

  val = mmu.read(hl)
  result = (val | 2)  #  u8
  t += 1
  mmu.write(hl, result)
def opcode_cb_cf():  #  SET 1,A
  global a
  a = (a | 2)  #  u8

def opcode_cb_d0():  #  SET 2,B
  global b
  b = (b | 4)  #  u8

def opcode_cb_d1():  #  SET 2,C
  global c
  c = (c | 4)  #  u8

def opcode_cb_d2():  #  SET 2,D
  global d
  d = (d | 4)  #  u8

def opcode_cb_d3():  #  SET 2,E
  global e
  e = (e | 4)  #  u8

def opcode_cb_d4():  #  SET 2,H
  global h
  h = (h | 4)  #  u8

def opcode_cb_d5():  #  SET 2,L
  global l
  l = (l | 4)  #  u8

def opcode_cb_d6():  #  SET 2,(HL)
  global h, l, t
  hl = (h << 8) | l

  val = mmu.read(hl)
  result = (val | 4)  #  u8
  t += 1
  mmu.write(hl, result)
def opcode_cb_d7():  #  SET 2,A
  global a
  a = (a | 4)  #  u8

def opcode_cb_d8():  #  SET 3,B
  global b
  b = (b | 8)  #  u8

def opcode_cb_d9():  #  SET 3,C
  global c
  c = (c | 8)  #  u8

def opcode_cb_da():  #  SET 3,D
  global d
  d = (d | 8)  #  u8

def opcode_cb_db():  #  SET 3,E
  global e
  e = (e | 8)  #  u8

def opcode_cb_dc():  #  SET 3,H
  global h
  h = (h | 8)  #  u8

def opcode_cb_dd():  #  SET 3,L
  global l
  l = (l | 8)  #  u8

def opcode_cb_de():  #  SET 3,(HL)
  global h, l, t
  hl = (h << 8) | l

  val = mmu.read(hl)
  result = (val | 8)  #  u8
  t += 1
  mmu.write(hl, result)
def opcode_cb_df():  #  SET 3,A
  global a
  a = (a | 8)  #  u8

def opcode_cb_e0():  #  SET 4,B
  global b
  b = (b | 16)  #  u8

def opcode_cb_e1():  #  SET 4,C
  global c
  c = (c | 16)  #  u8

def opcode_cb_e2():  #  SET 4,D
  global d
  d = (d | 16)  #  u8

def opcode_cb_e3():  #  SET 4,E
  global e
  e = (e | 16)  #  u8

def opcode_cb_e4():  #  SET 4,H
  global h
  h = (h | 16)  #  u8

def opcode_cb_e5():  #  SET 4,L
  global l
  l = (l | 16)  #  u8

def opcode_cb_e6():  #  SET 4,(HL)
  global h, l, t
  hl = (h << 8) | l

  val = mmu.read(hl)
  result = (val | 16)  #  u8
  t += 1
  mmu.write(hl, result)
def opcode_cb_e7():  #  SET 4,A
  global a
  a = (a | 16)  #  u8

def opcode_cb_e8():  #  SET 5,B
  global b
  b = (b | 32)  #  u8

def opcode_cb_e9():  #  SET 5,C
  global c
  c = (c | 32)  #  u8

def opcode_cb_ea():  #  SET 5,D
  global d
  d = (d | 32)  #  u8

def opcode_cb_eb():  #  SET 5,E
  global e
  e = (e | 32)  #  u8

def opcode_cb_ec():  #  SET 5,H
  global h
  h = (h | 32)  #  u8

def opcode_cb_ed():  #  SET 5,L
  global l
  l = (l | 32)  #  u8

def opcode_cb_ee():  #  SET 5,(HL)
  global h, l, t
  hl = (h << 8) | l

  val = mmu.read(hl)
  result = (val | 32)  #  u8
  t += 1
  mmu.write(hl, result)
def opcode_cb_ef():  #  SET 5,A
  global a
  a = (a | 32)  #  u8

def opcode_cb_f0():  #  SET 6,B
  global b
  b = (b | 64)  #  u8

def opcode_cb_f1():  #  SET 6,C
  global c
  c = (c | 64)  #  u8

def opcode_cb_f2():  #  SET 6,D
  global d
  d = (d | 64)  #  u8

def opcode_cb_f3():  #  SET 6,E
  global e
  e = (e | 64)  #  u8

def opcode_cb_f4():  #  SET 6,H
  global h
  h = (h | 64)  #  u8

def opcode_cb_f5():  #  SET 6,L
  global l
  l = (l | 64)  #  u8

def opcode_cb_f6():  #  SET 6,(HL)
  global h, l, t
  hl = (h << 8) | l

  val = mmu.read(hl)
  result = (val | 64)  #  u8
  t += 1
  mmu.write(hl, result)
def opcode_cb_f7():  #  SET 6,A
  global a
  a = (a | 64)  #  u8

def opcode_cb_f8():  #  SET 7,B
  global b
  b = (b | 128)  #  u8

def opcode_cb_f9():  #  SET 7,C
  global c
  c = (c | 128)  #  u8

def opcode_cb_fa():  #  SET 7,D
  global d
  d = (d | 128)  #  u8

def opcode_cb_fb():  #  SET 7,E
  global e
  e = (e | 128)  #  u8

def opcode_cb_fc():  #  SET 7,H
  global h
  h = (h | 128)  #  u8

def opcode_cb_fd():  #  SET 7,L
  global l
  l = (l | 128)  #  u8

def opcode_cb_fe():  #  SET 7,(HL)
  global h, l, t
  hl = (h << 8) | l

  val = mmu.read(hl)
  result = (val | 128)  #  u8
  t += 1
  mmu.write(hl, result)

def opcode_cb_ff():  #  SET 7,A
  global a
  a = (a | 128)  #  u8

def opcode_dd_9():  #  ADD IX,BC
  global ix, b, c, f, i, r, t, memptr
  bc = (b << 8) | c

  memptr = (ix + 1) & 0xffff
  rr1 = ix  #  u16
  rr2 = bc  #  u16
  add16temp = (rr1 + rr2)  #  u32
  lookup = ((rr1 & 0x0800) >> 11) | ((rr2 & 0x0800) >> 10) | ((add16temp & 0x0800) >> 9)  #  u32
  ix = add16temp & 0xffff
  f = (f & (FLAG_V | FLAG_Z | FLAG_S)) | (FLAG_C if (add16temp & 0x10000) else 0) | ((add16temp >> 8) & (FLAG_3 | FLAG_5)) | halfcarryAddTable[lookup]
  t += 7

def opcode_dd_19():  #  ADD IX,DE
  global ix, d, e, f, i, r, t, memptr
  de = (d << 8) | e

  memptr = (ix + 1) & 0xffff
  rr1 = ix  #  u16
  rr2 = de  #  u16
  add16temp = (rr1 + rr2)  #  u32
  lookup = ((rr1 & 0x0800) >> 11) | ((rr2 & 0x0800) >> 10) | ((add16temp & 0x0800) >> 9)  #  u32
  ix = add16temp & 0Xffff
  f = (f & (FLAG_V | FLAG_Z | FLAG_S)) | (FLAG_C if (add16temp & 0x10000) else 0) | ((add16temp >> 8) & (FLAG_3 | FLAG_5)) | halfcarryAddTable[lookup]
  t += 7

def opcode_dd_21():  #  LD IX,nn
  global pc, ix
  lo = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  hi = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  ix = (lo | (hi << 8))

def opcode_dd_22():  #  LD (nn),IX
  global pc, ix
  lo = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  hi = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  addr = (lo | (hi << 8))
  mmu.write(addr, (ix & 0xff))
  mmu.write((addr + 1), (ix >> 8))

def opcode_dd_23():  #  INC IX
  global ix, t
  ix = (ix + 1)
  t += 2
  ix = ix & 0xffff

def opcode_dd_24():  #  INC IXH
  global ix, f
  ixh = (ix >> 8) & 0xff

  ixh = (ixh + 1) & 0xff  #  u8
  f = (f & FLAG_C) | (FLAG_V if (ixh == 0x80) else 0) | (0 if (ixh & 0x0f) else FLAG_H) | sz53Table[ixh]

  ix = (ixh << 8) | ix & 0xff

def opcode_dd_25():  #  DEC IXH
  global ix, f
  ixh = (ix >> 8) & 0xff

  tempF = (f & FLAG_C) | (0 if (ixh & 0x0f) else FLAG_H) | FLAG_N  #  u8
  ixh = (ixh - 1) & 0xff  #  u8
  f = (tempF | (FLAG_V if (ixh == 0x7f) else 0) | sz53Table[ixh])

  ix = (ixh << 8) | ix & 0xff

def opcode_dd_26():  #  LD IXH,n
  global pc, ix
  ixh = mmu.read(pc)
  pc = (pc + 1) & 0xffff

  ix = (ixh << 8) | ix & 0xff

def opcode_dd_29():  #  ADD IX,IX
  global ix, f, t, memptr
  memptr = (ix + 1) & 0xffff
  add16temp = (ix + ix)  #  u32
  lookup = ((ix & 0x0800) >> 11) | ((ix & 0x0800) >> 10) | ((add16temp & 0x0800) >> 9)  #  u32
  ix = add16temp & 0xffff
  f = (f & (FLAG_V | FLAG_Z | FLAG_S)) | (FLAG_C if (add16temp & 0x10000) else 0) | ((add16temp >> 8) & (FLAG_3 | FLAG_5)) | halfcarryAddTable[lookup]
  t += 7

def opcode_dd_2a():  #  LD IX,(nn)
  global pc, ix
  lo = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  hi = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  addr = (lo | (hi << 8))
  ix = (mmu.read(addr) | (mmu.read((addr + 1)) << 8))

def opcode_dd_2b():  #  DEC IX
  global ix, t
  ix = (ix - 1) & 0xffff
  t += 2

def opcode_dd_2c():  #  INC IXL
  global ix, f
  ixl = ix & 0xff

  ixl = (ixl + 1) & 0xff  #  u8
  f = (f & FLAG_C) | (FLAG_V if (ixl == 0x80) else 0) | (0 if (ixl & 0x0f) else FLAG_H) | sz53Table[ixl]

  ix = (ix & 0xff00) | ixl

def opcode_dd_2d():  #  DEC IXL
  global ix, f
  ixl = ix & 0xff

  tempF = (f & FLAG_C) | (0 if (ixl & 0x0f) else FLAG_H) | FLAG_N  #  u8
  ixl = (ixl - 1) & 0xff  #  u8
  f = (tempF | (FLAG_V if (ixl == 0x7f) else 0) | sz53Table[ixl])

  ix = (ix & 0xff00) | ixl

def opcode_dd_2e():  #  LD IXL,n
  global pc, ix
  ixl = mmu.read(pc)
  pc = (pc + 1) & 0xffff

  ix = (ix & 0xff00) | ixl

def opcode_dd_34():  #  INC (IX+n)
  global ix, pc, t, f, memptr
  ixAddr = (ix + i8(mmu.read(pc)))  #  u16
  memptr = ixAddr
  t += 5
  pc = (pc + 1) & 0xffff
  val = mmu.read(ixAddr)
  result = (val + 1) & 0xff  #  u8
  t += 1
  mmu.write(ixAddr, result)
  f = (f & FLAG_C) | (FLAG_V if (result == 0x80) else 0) | (0 if (result & 0x0f) else FLAG_H) | sz53Table[result]

def opcode_dd_35():  #  DEC (IX+n)
  global ix, pc, t, f, memptr
  ixAddr = (ix + i8(mmu.read(pc)))  #  u16
  memptr = ixAddr
  t += 5
  pc = (pc + 1) & 0xffff
  val = mmu.read(ixAddr)
  tempF = (f & FLAG_C) | (0 if (val & 0x0f) else FLAG_H) | FLAG_N  #  u8
  result = (val - 1) & 0xff  #  u8
  t += 1
  mmu.write(ixAddr, result)
  f = (tempF | (FLAG_V if (result == 0x7f) else 0) | sz53Table[result])

def opcode_dd_36():  #  LD (IX+n),n
  global ix, pc, t, memptr
  ixAddr = (ix + i8(mmu.read(pc)))  #  u16
  memptr = ixAddr
  pc = (pc + 1) & 0xffff
  result = mmu.read(pc)
  t += 2
  pc = (pc + 1) & 0xffff
  mmu.write(ixAddr, result)

def opcode_dd_39():  #  ADD IX,SP
  global ix, sp, f, t, memptr
  memptr = (ix + 1) & 0xffff
  add16temp = (ix + sp)  #  u32
  lookup = ((ix & 0x0800) >> 11) | ((sp & 0x0800) >> 10) | ((add16temp & 0x0800) >> 9)  #  u32
  ix = add16temp & 0xffff
  f = (f & (FLAG_V | FLAG_Z | FLAG_S)) | (FLAG_C if (add16temp & 0x10000) else 0) | ((add16temp >> 8) & (FLAG_3 | FLAG_5)) | halfcarryAddTable[lookup]
  t += 7

def opcode_dd_44():  #  LD B,IXH
  global ix, b
  ixh = (ix >> 8) & 0xff

  b = ixh

def opcode_dd_45():  #  LD B,IXL
  global ix, b
  ixl = ix & 0xff

  b = ixl

def opcode_dd_46():  #  LD B,(IX+n)
  global ix, pc, t, b, memptr
  ixAddr = (ix + i8(mmu.read(pc)))  #  u16
  memptr = ixAddr
  t += 5
  pc = (pc + 1) & 0xffff
  b = mmu.read(ixAddr)

def opcode_dd_4c():  #  LD C,IXH
  global ix, c
  ixh = (ix >> 8) & 0xff

  c = ixh

def opcode_dd_4d():  #  LD C,IXL
  global ix, c
  ixl = ix & 0xff

  c = ixl

def opcode_dd_4e():  #  LD C,(IX+n)
  global ix, pc, t, c, memptr
  ixAddr = (ix + i8(mmu.read(pc)))  #  u16
  memptr = ixAddr
  t += 5
  pc = (pc + 1) & 0xffff
  c = mmu.read(ixAddr)

def opcode_dd_54():  #  LD D,IXH
  global ix, d
  ixh = (ix >> 8) & 0xff

  d = ixh

def opcode_dd_55():  #  LD D,IXL
  global ix, d
  ixl = ix & 0xff

  d = ixl

def opcode_dd_56():  #  LD D,(IX+n)
  global ix, pc, t, d, memptr
  ixAddr = (ix + i8(mmu.read(pc)))  #  u16
  memptr = ixAddr
  t += 5
  pc = (pc + 1) & 0xffff
  d = mmu.read(ixAddr)

def opcode_dd_5c():  #  LD E,IXH
  global ix, e
  ixh = (ix >> 8) & 0xff

  e = ixh

def opcode_dd_5d():  #  LD E,IXL
  global ix, e
  ixl = ix & 0xff

  e = ixl

def opcode_dd_5e():  #  LD E,(IX+n)
  global ix, pc, t, e, memptr
  ixAddr = (ix + i8(mmu.read(pc)))  #  u16
  memptr = ixAddr
  t += 5
  pc = (pc + 1) & 0xffff
  e = mmu.read(ixAddr)

def opcode_dd_60():  #  LD IXH,B
  global b, ix
  ix = (b << 8) | ix & 0xff

def opcode_dd_61():  #  LD IXH,C
  global c, ix
  ix = (c << 8) | ix & 0xff

def opcode_dd_62():  #  LD IXH,D
  global d, ix
  ix = (d << 8) | ix & 0xff

def opcode_dd_63():  #  LD IXH,E
  global e, ix
  ix = (e << 8) | ix & 0xff

def opcode_dd_64():  #  LD IXH,IXH
  pass

def opcode_dd_65():  #  LD IXH,IXL
  global ix
  ixl = ix & 0xff

  ix = (ixl << 8) | ix & 0xff

def opcode_dd_66():  #  LD H,(IX+n)
  global ix, pc, t, h, memptr
  ixAddr = (ix + i8(mmu.read(pc)))  #  u16
  memptr = ixAddr
  t += 5
  pc = (pc + 1) & 0xffff
  h = mmu.read(ixAddr)

def opcode_dd_67():  #  LD IXH,A
  global a, ix
  ix = (a << 8) | ix & 0xff

def opcode_dd_68():  #  LD IXL,B
  global b, ix
  ix = (ix & 0xff00) | b

def opcode_dd_69():  #  LD IXL,C
  global c, ix
  ix = (ix & 0xff00) | c

def opcode_dd_6a():  #  LD IXL,D
  global d, ix
  ix = (ix & 0xff00) | d

def opcode_dd_6b():  #  LD IXL,E
  global e, ix
  ix = (ix & 0xff00) | e

def opcode_dd_6c():  #  LD IXL,IXH
  global ix
  ixh = (ix >> 8) & 0xff

  ix = (ix & 0xff00) | ixh

def opcode_dd_6d():  #  LD IXL,IXL
  pass

def opcode_dd_6e():  #  LD L,(IX+n)
  global ix, pc, t, l, memptr
  ixAddr = (ix + i8(mmu.read(pc)))  #  u16
  memptr = ixAddr
  t += 5
  pc = (pc + 1) & 0xffff
  l = mmu.read(ixAddr)

def opcode_dd_6f():  #  LD IXL,A
  global a, ix
  ix = (ix & 0xff00) | a

def opcode_dd_70():  #  LD (IX+n),B
  global ix, pc, t, b, memptr
  ixAddr = (ix + i8(mmu.read(pc)))  #  u16
  memptr = ixAddr
  t += 5
  pc = (pc + 1) & 0xffff
  mmu.write(ixAddr, b)

def opcode_dd_71():  #  LD (IX+n),C
  global ix, pc, t, c, memptr
  ixAddr = (ix + i8(mmu.read(pc)))  #  u16
  memptr = ixAddr
  t += 5
  pc = (pc + 1) & 0xffff
  mmu.write(ixAddr, c)

def opcode_dd_72():  #  LD (IX+n),D
  global ix, pc, t, d, memptr
  ixAddr = (ix + i8(mmu.read(pc)))  #  u16
  memptr = ixAddr
  t += 5
  pc = (pc + 1) & 0xffff
  mmu.write(ixAddr, d)

def opcode_dd_73():  #  LD (IX+n),E
  global ix, pc, t, e, memptr
  ixAddr = (ix + i8(mmu.read(pc)))  #  u16
  memptr = ixAddr
  t += 5
  pc = (pc + 1) & 0xffff
  mmu.write(ixAddr, e)

def opcode_dd_74():  #  LD (IX+n),H
  global ix, pc, t, h, memptr
  ixAddr = (ix + i8(mmu.read(pc)))  #  u16
  memptr = ixAddr
  t += 5
  pc = (pc + 1) & 0xffff
  mmu.write(ixAddr, h)

def opcode_dd_75():  #  LD (IX+n),L
  global ix, pc, t, l, memptr
  ixAddr = (ix + i8(mmu.read(pc)))  #  u16
  memptr = ixAddr
  t += 5
  pc = (pc + 1) & 0xffff
  mmu.write(ixAddr, l)

def opcode_dd_77():  #  LD (IX+n),A
  global ix, pc, t, a, memptr
  ixAddr = (ix + i8(mmu.read(pc)))  #  u16
  memptr = ixAddr
  t += 5
  pc = (pc + 1) & 0xffff
  mmu.write(ixAddr, a)

def opcode_dd_7c():  #  LD A,IXH
  global ix, a
  ixh = (ix >> 8) & 0xff

  a = ixh

def opcode_dd_7d():  #  LD A,IXL
  global ix, a
  ixl = ix & 0xff

  a = ixl

def opcode_dd_7e():  #  LD A,(IX+n)
  global ix, pc, t, a, memptr
  ixAddr = (ix + i8(mmu.read(pc)))  #  u16
  memptr = ixAddr
  t += 5
  pc = (pc + 1) & 0xffff
  a = mmu.read(ixAddr)

def opcode_dd_84():  #  ADD A,IXH
  global ix, a, f
  ixh = (ix >> 8) & 0xff

  result = (ixh + a)  #  u32
  lookup = ((a & 0x88) >> 3) | ((ixh & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | halfcarryAddTable[(lookup & 0x07)] | overflowAddTable[(lookup >> 4)] | sz53Table[a]

def opcode_dd_85():  #  ADD A,IXL
  global ix, a, f
  ixl = ix & 0xff

  result = (ixl + a)  #  u32
  lookup = ((a & 0x88) >> 3) | ((ixl & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | halfcarryAddTable[(lookup & 0x07)] | overflowAddTable[(lookup >> 4)] | sz53Table[a]

def opcode_dd_86():  #  ADD A,(IX+n)
  global ix, pc, t, a, f, memptr
  ixAddr = (ix + i8(mmu.read(pc)))  #  u16
  memptr = ixAddr
  t += 5
  pc = (pc + 1) & 0xffff
  val = mmu.read(ixAddr)
  result = (val + a)  #  u32
  lookup = ((a & 0x88) >> 3) | ((val & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | halfcarryAddTable[(lookup & 0x07)] | overflowAddTable[(lookup >> 4)] | sz53Table[a]

def opcode_dd_8c():  #  ADC A,IXH
  global ix, a, f
  ixh = (ix >> 8) & 0xff

  result = ((a + ixh) + (f & FLAG_C))  #  u32
  lookup = ((a & 0x88) >> 3) | ((ixh & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | halfcarryAddTable[(lookup & 0x07)] | overflowAddTable[(lookup >> 4)] | sz53Table[a]

def opcode_dd_8d():  #  ADC A,IXL
  global ix, a, f
  ixl = ix & 0xff

  result = ((a + ixl) + (f & FLAG_C))  #  u32
  lookup = ((a & 0x88) >> 3) | ((ixl & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | halfcarryAddTable[(lookup & 0x07)] | overflowAddTable[(lookup >> 4)] | sz53Table[a]

def opcode_dd_8e():  #  ADC A,(IX+n)
  global ix, pc, t, a, f, memptr
  ixAddr = (ix + i8(mmu.read(pc)))  #  u16
  memptr = ixAddr
  t += 5
  pc = (pc + 1) & 0xffff
  val = mmu.read(ixAddr)
  result = ((a + val) + (f & FLAG_C))  #  u32
  lookup = ((a & 0x88) >> 3) | ((val & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | halfcarryAddTable[(lookup & 0x07)] | overflowAddTable[(lookup >> 4)] | sz53Table[a]

def opcode_dd_94():  #  SUB IXH
  global ix, a, f
  ixh = (ix >> 8) & 0xff

  result = (a - ixh)  #  u32
  lookup = ((a & 0x88) >> 3) | ((ixh & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | sz53Table[a]

def opcode_dd_95():  #  SUB IXL
  global ix, a, f
  ixl = ix & 0xff

  result = (a - ixl)  #  u32
  lookup = ((a & 0x88) >> 3) | ((ixl & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | sz53Table[a]

def opcode_dd_96():  #  SUB (IX+n)
  global ix, pc, t, a, f, memptr
  ixAddr = (ix + i8(mmu.read(pc)))  #  u16
  memptr = ixAddr
  t += 5
  pc = (pc + 1) & 0xffff
  val = mmu.read(ixAddr)
  result = (a - val)  #  u32
  lookup = ((a & 0x88) >> 3) | ((val & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | sz53Table[a]

def opcode_dd_9c():  #  SBC A,IXH
  global ix, a, f
  ixh = (ix >> 8) & 0xff

  result = ((a - ixh) - (f & FLAG_C))  #  u32
  lookup = ((a & 0x88) >> 3) | ((ixh & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | sz53Table[a]

def opcode_dd_9d():  #  SBC A,IXL
  global ix, a, f
  ixl = ix & 0xff

  result = ((a - ixl) - (f & FLAG_C))  #  u32
  lookup = ((a & 0x88) >> 3) | ((ixl & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | sz53Table[a]

def opcode_dd_9e():  #  SBC A,(IX+n)
  global ix, pc, t, a, f, memptr
  ixAddr = (ix + i8(mmu.read(pc)))  #  u16
  memptr = ixAddr
  t += 5
  pc = (pc + 1) & 0xffff
  val = mmu.read(ixAddr)
  result = ((a - val) - (f & FLAG_C))  #  u32
  lookup = ((a & 0x88) >> 3) | ((val & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | sz53Table[a]

def opcode_dd_a4():  #  AND IXH
  global ix, a, f
  ixh = (ix >> 8) & 0xff

  a = (a & ixh)  #  u8
  f = (FLAG_H | sz53pTable[a])

def opcode_dd_a5():  #  AND IXL
  global ix, a, f
  ixl = ix & 0xff

  a = (a & ixl)  #  u8
  f = (FLAG_H | sz53pTable[a])

def opcode_dd_a6():  #  AND (IX+n)
  global ix, pc, t, a, f, memptr
  ixAddr = (ix + i8(mmu.read(pc)))  #  u16
  memptr = ixAddr
  t += 5
  pc = (pc + 1) & 0xffff
  val = mmu.read(ixAddr)
  a = (a & val)  #  u8
  f = (FLAG_H | sz53pTable[a])

def opcode_dd_ac():  #  XOR IXH
  global ix, a, f
  ixh = (ix >> 8) & 0xff

  a = (a ^ ixh)  #  u8
  f = sz53pTable[a]

def opcode_dd_ad():  #  XOR IXL
  global ix, a, f
  ixl = ix & 0xff

  a = (a ^ ixl)  #  u8
  f = sz53pTable[a]

def opcode_dd_ae():  #  XOR (IX+n)
  global ix, pc, t, a, f, memptr
  ixAddr = (ix + i8(mmu.read(pc)))  #  u16
  memptr = ixAddr
  t += 5
  pc = (pc + 1) & 0xffff
  val = mmu.read(ixAddr)
  a = (a ^ val)  #  u8
  f = sz53pTable[a]

def opcode_dd_b4():  #  OR IXH
  global ix, a, f
  ixh = (ix >> 8) & 0xff

  a = (a | ixh)  #  u8
  f = sz53pTable[a]

def opcode_dd_b5():  #  OR IXL
  global ix, a, f
  ixl = ix & 0xff

  a = (a | ixl)  #  u8
  f = sz53pTable[a]

def opcode_dd_b6():  #  OR (IX+n)
  global ix, pc, t, a, f, memptr
  ixAddr = (ix + i8(mmu.read(pc)))  #  u16
  memptr = ixAddr
  t += 5
  pc = (pc + 1) & 0xffff
  val = mmu.read(ixAddr)
  a = (a | val)  #  u8
  f = sz53pTable[a]

def opcode_dd_bc():  #  CP IXH
  global ix, a, f
  ixh = (ix >> 8) & 0xff

  val = ixh
  cptemp = (a - val)  #  u32
  lookup = ((a & 0x88) >> 3) | ((val & 0x88) >> 2) | ((cptemp & 0x88) >> 1)  #  u32
  f = (FLAG_C if (cptemp & 0x100) else (0 if cptemp else FLAG_Z)) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | (val & (FLAG_3 | FLAG_5)) | (cptemp & FLAG_S)

def opcode_dd_bd():  #  CP IXL
  global ix, a, f
  ixl = ix & 0xff

  val = ixl
  cptemp = (a - val)  #  u32
  lookup = ((a & 0x88) >> 3) | ((val & 0x88) >> 2) | ((cptemp & 0x88) >> 1)  #  u32
  f = (FLAG_C if (cptemp & 0x100) else (0 if cptemp else FLAG_Z)) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | (val & (FLAG_3 | FLAG_5)) | (cptemp & FLAG_S)

def opcode_dd_be():  #  CP (IX+n)
  global ix, pc, t, a, f, memptr
  ixAddr = (ix + i8(mmu.read(pc)))  #  u16
  memptr = ixAddr
  t += 5
  pc = (pc + 1) & 0xffff
  val = mmu.read(ixAddr)
  cptemp = (a - val)  #  u32
  lookup = ((a & 0x88) >> 3) | ((val & 0x88) >> 2) | ((cptemp & 0x88) >> 1)  #  u32
  f = (FLAG_C if (cptemp & 0x100) else (0 if cptemp else FLAG_Z)) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | (val & (FLAG_3 | FLAG_5)) | (cptemp & FLAG_S)

def opcode_dd_e1():  #  POP IX
  global sp, ix
  #lo = mmu.read(sp)
  #sp = (sp + 1) & 0xffff
  #hi = mmu.read(sp)
  #sp = (sp + 1) & 0xffff
  #ix = (lo | (hi << 8))
  sp, ix = mmu.pop16(sp)

def opcode_dd_e3():  #  EX (SP),IX
  global sp, t, ix, memptr
  lo = mmu.read(sp)
  hi = mmu.read((sp + 1))
  t += 1
  mmu.write((sp + 1), (ix >> 8))
  mmu.write(sp, (ix & 0xff))
  ix = (lo | (hi << 8))
  memptr = ix
  t += 2

def opcode_dd_e5():  #  PUSH IX
  global t, ix, sp
  #t += 1
  #sp = (sp - 1) & 0xffff
  #mmu.write(sp, (ix >> 8))
  #sp = (sp - 1) & 0xffff
  #mmu.write(sp, (ix & 0xff))
  sp = mmu.push16(sp, ix)

def opcode_dd_e9():  #  JP (IX)
  global pc, ix, t
  pc = ix

def opcode_dd_f9():  #  LD SP,IX
  global sp, ix, t
  sp = ix
  t += 2

def opcode_ddcb_0():  #  RLC (IX+n>B)
  global ix, xy_offset, t, f, b
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = ((val << 1) | (val >> 7)) & 0xff  #  u8
  f = ((result & FLAG_C) | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  b = result

  b = b & 0xff

def opcode_ddcb_1():  #  RLC (IX+n>C)
  global ix, xy_offset, t, f, c
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = ((val << 1) | (val >> 7)) & 0xff  #  u8
  f = ((result & FLAG_C) | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  c = result

  c = c & 0xff

def opcode_ddcb_2():  #  RLC (IX+n>D)
  global ix, xy_offset, t, f, d
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = ((val << 1) | (val >> 7)) & 0xff  #  u8
  f = ((result & FLAG_C) | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  d = result

  d = d & 0xff

def opcode_ddcb_3():  #  RLC (IX+n>E)
  global ix, xy_offset, t, f, e
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = ((val << 1) | (val >> 7)) & 0xff  #  u8
  f = ((result & FLAG_C) | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  e = result

  e = e & 0xff

def opcode_ddcb_4():  #  RLC (IX+n>H)
  global ix, xy_offset, t, f, h
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = ((val << 1) | (val >> 7)) & 0xff  #  u8
  f = ((result & FLAG_C) | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  h = result

  h = h & 0xff

def opcode_ddcb_5():  #  RLC (IX+n>L)
  global ix, xy_offset, t, f, l
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = ((val << 1) | (val >> 7)) & 0xff  #  u8
  f = ((result & FLAG_C) | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  l = result

  l = l & 0xff

def opcode_ddcb_6():  #  RLC (IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = ((val << 1) | (val >> 7)) & 0xff  #  u8
  f = ((result & FLAG_C) | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)


def opcode_ddcb_7():  #  RLC (IX+n>A)
  global ix, xy_offset, t, f, a
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = ((val << 1) | (val >> 7)) & 0xff  #  u8
  f = ((result & FLAG_C) | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  a = result

  a = a & 0xff

def opcode_ddcb_8():  #  RRC (IX+n>B)
  global ix, xy_offset, t, f, b
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val & FLAG_C)  #  u8
  result = ((val >> 1) | (val << 7)) & 0xff  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  b = result

  b = b & 0xff

def opcode_ddcb_9():  #  RRC (IX+n>C)
  global ix, xy_offset, t, f, c
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val & FLAG_C)  #  u8
  result = ((val >> 1) | (val << 7)) & 0xff  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  c = result

  c = c & 0xff

def opcode_ddcb_a():  #  RRC (IX+n>D)
  global ix, xy_offset, t, f, d
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val & FLAG_C)  #  u8
  result = ((val >> 1) | (val << 7)) & 0xff  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  d = result

  d = d & 0xff

def opcode_ddcb_b():  #  RRC (IX+n>E)
  global ix, xy_offset, t, f, e
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val & FLAG_C)  #  u8
  result = ((val >> 1) | (val << 7)) & 0xff  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  e = result

  e = e & 0xff

def opcode_ddcb_c():  #  RRC (IX+n>H)
  global ix, xy_offset, t, f, h
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val & FLAG_C)  #  u8
  result = ((val >> 1) | (val << 7)) & 0xff  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  h = result

  h = h & 0xff

def opcode_ddcb_d():  #  RRC (IX+n>L)
  global ix, xy_offset, t, f, l
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val & FLAG_C)  #  u8
  result = ((val >> 1) | (val << 7)) & 0xff  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  l = result

  l = l & 0xff

def opcode_ddcb_e():  #  RRC (IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val & FLAG_C)  #  u8
  result = ((val >> 1) | (val << 7)) & 0xff  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)


def opcode_ddcb_f():  #  RRC (IX+n>A)
  global ix, xy_offset, t, f, a
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val & FLAG_C)  #  u8
  result = ((val >> 1) | (val << 7)) & 0xff #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  a = result

  a = a & 0xff

def opcode_ddcb_10():  #  RL (IX+n>B)
  global ix, xy_offset, t, f, b
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = ((val << 1) | (f & FLAG_C)) & 0xff  #  u8
  f = ((val >> 7) | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  b = result

  b = b & 0xff

def opcode_ddcb_11():  #  RL (IX+n>C)
  global ix, xy_offset, t, f, c
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = ((val << 1) | (f & FLAG_C)) & 0xff  #  u8
  f = ((val >> 7) | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  c = result

  c = c & 0xff

def opcode_ddcb_12():  #  RL (IX+n>D)
  global ix, xy_offset, t, f, d
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = ((val << 1) | (f & FLAG_C)) & 0xff  #  u8
  f = ((val >> 7) | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  d = result

  d = d & 0xff

def opcode_ddcb_13():  #  RL (IX+n>E)
  global ix, xy_offset, t, f, e
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = ((val << 1) | (f & FLAG_C)) & 0xff  #  u8
  f = ((val >> 7) | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  e = result

  e = e & 0xff

def opcode_ddcb_14():  #  RL (IX+n>H)
  global ix, xy_offset, t, f, h
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = ((val << 1) | (f & FLAG_C)) & 0xff  #  u8
  f = ((val >> 7) | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  h = result

  h = h & 0xff

def opcode_ddcb_15():  #  RL (IX+n>L)
  global ix, xy_offset, t, f, l
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = ((val << 1) | (f & FLAG_C)) & 0xff  #  u8
  f = ((val >> 7) | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  l = result

  l = l & 0xff

def opcode_ddcb_16():  #  RL (IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = ((val << 1) | (f & FLAG_C)) & 0xff  #  u8
  f = ((val >> 7) | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)


def opcode_ddcb_17():  #  RL (IX+n>A)
  global ix, xy_offset, t, f, a
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = ((val << 1) | (f & FLAG_C)) & 0xff  #  u8
  f = ((val >> 7) | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  a = result

  a = a & 0xff

def opcode_ddcb_18():  #  RR (IX+n>B)
  global ix, xy_offset, t, f, b
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = ((val >> 1) | (f << 7)) & 0xff  #  u8
  f = ((val & FLAG_C) | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  b = result

  b = b & 0xff

def opcode_ddcb_19():  #  RR (IX+n>C)
  global ix, xy_offset, t, f, c
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = ((val >> 1) | (f << 7)) & 0xff  #  u8
  f = ((val & FLAG_C) | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  c = result

  c = c & 0xff

def opcode_ddcb_1a():  #  RR (IX+n>D)
  global ix, xy_offset, t, f, d
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = ((val >> 1) | (f << 7)) & 0xff  #  u8
  f = ((val & FLAG_C) | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  d = result

  d = d & 0xff

def opcode_ddcb_1b():  #  RR (IX+n>E)
  global ix, xy_offset, t, f, e
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = ((val >> 1) | (f << 7)) & 0xff  #  u8
  f = ((val & FLAG_C) | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  e = result

  e = e & 0xff

def opcode_ddcb_1c():  #  RR (IX+n>H)
  global ix, xy_offset, t, f, h
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = ((val >> 1) | (f << 7)) & 0xff  #  u8
  f = ((val & FLAG_C) | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  h = result

  h = h & 0xff

def opcode_ddcb_1d():  #  RR (IX+n>L)
  global ix, xy_offset, t, f, l
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = ((val >> 1) | (f << 7)) & 0xff  #  u8
  f = ((val & FLAG_C) | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  l = result

  l = l & 0xff

def opcode_ddcb_1e():  #  RR (IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = ((val >> 1) | (f << 7)) & 0xff  #  u8
  f = ((val & FLAG_C) | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)


def opcode_ddcb_1f():  #  RR (IX+n>A)
  global ix, xy_offset, t, f, a
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = ((val >> 1) | (f << 7)) & 0xff  #  u8
  f = ((val & FLAG_C) | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  a = result

  a = a & 0xff

def opcode_ddcb_20():  #  SLA (IX+n>B)
  global ix, xy_offset, t, f, b
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val >> 7)  #  u8
  result = (val << 1) & 0xff  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  b = result

  b = b & 0xff

def opcode_ddcb_21():  #  SLA (IX+n>C)
  global ix, xy_offset, t, f, c
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val >> 7)  #  u8
  result = (val << 1) & 0xff  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  c = result

  c = c & 0xff

def opcode_ddcb_22():  #  SLA (IX+n>D)
  global ix, xy_offset, t, f, d
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val >> 7)  #  u8
  result = (val << 1) & 0xff  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  d = result

  d = d & 0xff

def opcode_ddcb_23():  #  SLA (IX+n>E)
  global ix, xy_offset, t, f, e
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val >> 7)  #  u8
  result = (val << 1) & 0xff  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  e = result

  e = e & 0xff

def opcode_ddcb_24():  #  SLA (IX+n>H)
  global ix, xy_offset, t, f, h
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val >> 7)  #  u8
  result = (val << 1) & 0xff  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  h = result

  h = h & 0xff

def opcode_ddcb_25():  #  SLA (IX+n>L)
  global ix, xy_offset, t, f, l
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val >> 7)  #  u8
  result = (val << 1) & 0xff  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  l = result

  l = l & 0xff

def opcode_ddcb_26():  #  SLA (IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val >> 7)  #  u8
  result = (val << 1) & 0xff  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)


def opcode_ddcb_27():  #  SLA (IX+n>A)
  global ix, xy_offset, t, f, a
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val >> 7)  #  u8
  result = (val << 1) & 0xff  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  a = result

  a = a & 0xff

def opcode_ddcb_28():  #  SRA (IX+n>B)
  global ix, xy_offset, t, f, b
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val & FLAG_C)  #  u8
  result = ((val & 0x80) | (val >> 1))  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  b = result

  b = b & 0xff

def opcode_ddcb_29():  #  SRA (IX+n>C)
  global ix, xy_offset, t, f, c
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val & FLAG_C)  #  u8
  result = ((val & 0x80) | (val >> 1))  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  c = result

  c = c & 0xff

def opcode_ddcb_2a():  #  SRA (IX+n>D)
  global ix, xy_offset, t, f, d
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val & FLAG_C)  #  u8
  result = ((val & 0x80) | (val >> 1))  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  d = result

  d = d & 0xff

def opcode_ddcb_2b():  #  SRA (IX+n>E)
  global ix, xy_offset, t, f, e
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val & FLAG_C)  #  u8
  result = ((val & 0x80) | (val >> 1))  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  e = result

  e = e & 0xff

def opcode_ddcb_2c():  #  SRA (IX+n>H)
  global ix, xy_offset, t, f, h
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val & FLAG_C)  #  u8
  result = ((val & 0x80) | (val >> 1))  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  h = result

  h = h & 0xff

def opcode_ddcb_2d():  #  SRA (IX+n>L)
  global ix, xy_offset, t, f, l
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val & FLAG_C)  #  u8
  result = ((val & 0x80) | (val >> 1))  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  l = result

  l = l & 0xff

def opcode_ddcb_2e():  #  SRA (IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val & FLAG_C)  #  u8
  result = ((val & 0x80) | (val >> 1))  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)


def opcode_ddcb_2f():  #  SRA (IX+n>A)
  global ix, xy_offset, t, f, a
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val & FLAG_C)  #  u8
  result = ((val & 0x80) | (val >> 1))  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  a = result

  a = a & 0xff

def opcode_ddcb_30():  #  SLL (IX+n>B)
  global ix, xy_offset, t, f, b
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val >> 7)  #  u8
  result = ((val << 1) | 0x01) &0xff #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  b = result

  b = b & 0xff

def opcode_ddcb_31():  #  SLL (IX+n>C)
  global ix, xy_offset, t, f, c
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val >> 7)  #  u8
  result = ((val << 1) | 0x01) &0xff #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  c = result

  c = c & 0xff

def opcode_ddcb_32():  #  SLL (IX+n>D)
  global ix, xy_offset, t, f, d
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val >> 7)  #  u8
  result = ((val << 1) | 0x01) &0xff #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  d = result

  d = d & 0xff

def opcode_ddcb_33():  #  SLL (IX+n>E)
  global ix, xy_offset, t, f, e
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val >> 7)  #  u8
  result = ((val << 1) | 0x01) &0xff #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  e = result

  e = e & 0xff

def opcode_ddcb_34():  #  SLL (IX+n>H)
  global ix, xy_offset, t, f, h
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val >> 7)  #  u8
  result = ((val << 1) | 0x01) &0xff #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  h = result

  h = h & 0xff

def opcode_ddcb_35():  #  SLL (IX+n>L)
  global ix, xy_offset, t, f, l
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val >> 7)  #  u8
  result = ((val << 1) | 0x01) &0xff #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  l = result

  l = l & 0xff

def opcode_ddcb_36():  #  SLL (IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val >> 7)  #  u8
  result = ((val << 1) | 0x01) &0xff #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)


def opcode_ddcb_37():  #  SLL (IX+n>A)
  global ix, xy_offset, t, f, a
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val >> 7)  #  u8
  result = ((val << 1) | 0x01) &0xff #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  a = result

  a = a & 0xff

def opcode_ddcb_38():  #  SRL (IX+n>B)
  global ix, xy_offset, t, f, b
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val & FLAG_C)  #  u8
  result = (val >> 1)  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  b = result

  b = b & 0xff

def opcode_ddcb_39():  #  SRL (IX+n>C)
  global ix, xy_offset, t, f, c
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val & FLAG_C)  #  u8
  result = (val >> 1)  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  c = result

  c = c & 0xff

def opcode_ddcb_3a():  #  SRL (IX+n>D)
  global ix, xy_offset, t, f, d
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val & FLAG_C)  #  u8
  result = (val >> 1)  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  d = result

  d = d & 0xff

def opcode_ddcb_3b():  #  SRL (IX+n>E)
  global ix, xy_offset, t, f, e
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val & FLAG_C)  #  u8
  result = (val >> 1)  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  e = result

  e = e & 0xff

def opcode_ddcb_3c():  #  SRL (IX+n>H)
  global ix, xy_offset, t, f, h
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val & FLAG_C)  #  u8
  result = (val >> 1)  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  h = result

  h = h & 0xff

def opcode_ddcb_3d():  #  SRL (IX+n>L)
  global ix, xy_offset, t, f, l
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val & FLAG_C)  #  u8
  result = (val >> 1)  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  l = result

  l = l & 0xff

def opcode_ddcb_3e():  #  SRL (IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val & FLAG_C)  #  u8
  result = (val >> 1)  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)


def opcode_ddcb_3f():  #  SRL (IX+n>A)
  global ix, xy_offset, t, f, a
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (val & FLAG_C)  #  u8
  result = (val >> 1)  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(ixAddr, result)
  a = result

  a = a & 0xff

def opcode_ddcb_40():  #  BIT 0,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 1)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_41():  #  BIT 0,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 1)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_42():  #  BIT 0,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 1)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_43():  #  BIT 0,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 1)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_44():  #  BIT 0,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 1)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_45():  #  BIT 0,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 1)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_46():  #  BIT 0,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 1)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_47():  #  BIT 0,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 1)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_48():  #  BIT 1,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 2)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_49():  #  BIT 1,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 2)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_4a():  #  BIT 1,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 2)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_4b():  #  BIT 1,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 2)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_4c():  #  BIT 1,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 2)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_4d():  #  BIT 1,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 2)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_4e():  #  BIT 1,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 2)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_4f():  #  BIT 1,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 2)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_50():  #  BIT 2,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 4)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_51():  #  BIT 2,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 4)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_52():  #  BIT 2,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 4)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_53():  #  BIT 2,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 4)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_54():  #  BIT 2,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 4)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_55():  #  BIT 2,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 4)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_56():  #  BIT 2,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 4)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_57():  #  BIT 2,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 4)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_58():  #  BIT 3,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 8)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_59():  #  BIT 3,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 8)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_5a():  #  BIT 3,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 8)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_5b():  #  BIT 3,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 8)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_5c():  #  BIT 3,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 8)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_5d():  #  BIT 3,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 8)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_5e():  #  BIT 3,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 8)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_5f():  #  BIT 3,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 8)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_60():  #  BIT 4,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 16)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_61():  #  BIT 4,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 16)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_62():  #  BIT 4,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 16)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_63():  #  BIT 4,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 16)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_64():  #  BIT 4,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 16)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_65():  #  BIT 4,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 16)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_66():  #  BIT 4,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 16)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_67():  #  BIT 4,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 16)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_68():  #  BIT 5,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 32)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_69():  #  BIT 5,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 32)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_6a():  #  BIT 5,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 32)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_6b():  #  BIT 5,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 32)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_6c():  #  BIT 5,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 32)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_6d():  #  BIT 5,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 32)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_6e():  #  BIT 5,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 32)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_6f():  #  BIT 5,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 32)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_70():  #  BIT 6,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 64)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_71():  #  BIT 6,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 64)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_72():  #  BIT 6,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 64)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_73():  #  BIT 6,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 64)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_74():  #  BIT 6,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 64)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_75():  #  BIT 6,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 64)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_76():  #  BIT 6,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 64)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_77():  #  BIT 6,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 64)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_ddcb_78():  #  BIT 7,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 128)):
    F |= (FLAG_P | FLAG_Z)
  if (val & 0x80):
    F |= FLAG_S
  f = F
  t += 5


def opcode_ddcb_79():  #  BIT 7,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 128)):
    F |= (FLAG_P | FLAG_Z)
  if (val & 0x80):
    F |= FLAG_S
  f = F
  t += 5


def opcode_ddcb_7a():  #  BIT 7,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 128)):
    F |= (FLAG_P | FLAG_Z)
  if (val & 0x80):
    F |= FLAG_S
  f = F
  t += 5


def opcode_ddcb_7b():  #  BIT 7,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 128)):
    F |= (FLAG_P | FLAG_Z)
  if (val & 0x80):
    F |= FLAG_S
  f = F
  t += 5


def opcode_ddcb_7c():  #  BIT 7,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 128)):
    F |= (FLAG_P | FLAG_Z)
  if (val & 0x80):
    F |= FLAG_S
  f = F
  t += 5


def opcode_ddcb_7d():  #  BIT 7,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 128)):
    F |= (FLAG_P | FLAG_Z)
  if (val & 0x80):
    F |= FLAG_S
  f = F
  t += 5


def opcode_ddcb_7e():  #  BIT 7,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 128)):
    F |= (FLAG_P | FLAG_Z)
  if (val & 0x80):
    F |= FLAG_S
  f = F
  t += 5


def opcode_ddcb_7f():  #  BIT 7,(IX+n)
  global ix, xy_offset, t, f
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  F = (f & FLAG_C) | FLAG_H | ((ixAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 128)):
    F |= (FLAG_P | FLAG_Z)
  if (val & 0x80):
    F |= FLAG_S
  f = F
  t += 5


def opcode_ddcb_80():  #  RES 0,(IX+n>B)
  global ix, xy_offset, t, b
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 254)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  b = result

  b = b & 0xff

def opcode_ddcb_81():  #  RES 0,(IX+n>C)
  global ix, xy_offset, t, c
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 254)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  c = result

  c = c & 0xff

def opcode_ddcb_82():  #  RES 0,(IX+n>D)
  global ix, xy_offset, t, d
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 254)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  d = result

  d = d & 0xff

def opcode_ddcb_83():  #  RES 0,(IX+n>E)
  global ix, xy_offset, t, e
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 254)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  e = result

  e = e & 0xff

def opcode_ddcb_84():  #  RES 0,(IX+n>H)
  global ix, xy_offset, t, h
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 254)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  h = result

  h = h & 0xff

def opcode_ddcb_85():  #  RES 0,(IX+n>L)
  global ix, xy_offset, t, l
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 254)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  l = result

  l = l & 0xff

def opcode_ddcb_86():  #  RES 0,(IX+n)
  global ix, xy_offset, t
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 254)  #  u8
  t += 5
  mmu.write(ixAddr, result)


def opcode_ddcb_87():  #  RES 0,(IX+n>A)
  global ix, xy_offset, t, a
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 254)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  a = result

  a = a & 0xff

def opcode_ddcb_88():  #  RES 1,(IX+n>B)
  global ix, xy_offset, t, b
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 253)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  b = result

  b = b & 0xff

def opcode_ddcb_89():  #  RES 1,(IX+n>C)
  global ix, xy_offset, t, c
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 253)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  c = result

  c = c & 0xff

def opcode_ddcb_8a():  #  RES 1,(IX+n>D)
  global ix, xy_offset, t, d
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 253)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  d = result

  d = d & 0xff

def opcode_ddcb_8b():  #  RES 1,(IX+n>E)
  global ix, xy_offset, t, e
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 253)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  e = result

  e = e & 0xff

def opcode_ddcb_8c():  #  RES 1,(IX+n>H)
  global ix, xy_offset, t, h
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 253)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  h = result

  h = h & 0xff

def opcode_ddcb_8d():  #  RES 1,(IX+n>L)
  global ix, xy_offset, t, l
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 253)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  l = result

  l = l & 0xff

def opcode_ddcb_8e():  #  RES 1,(IX+n)
  global ix, xy_offset, t
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 253)  #  u8
  t += 5
  mmu.write(ixAddr, result)


def opcode_ddcb_8f():  #  RES 1,(IX+n>A)
  global ix, xy_offset, t, a
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 253)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  a = result

  a = a & 0xff

def opcode_ddcb_90():  #  RES 2,(IX+n>B)
  global ix, xy_offset, t, b
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 251)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  b = result

  b = b & 0xff

def opcode_ddcb_91():  #  RES 2,(IX+n>C)
  global ix, xy_offset, t, c
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 251)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  c = result

  c = c & 0xff

def opcode_ddcb_92():  #  RES 2,(IX+n>D)
  global ix, xy_offset, t, d
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 251)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  d = result

  d = d & 0xff

def opcode_ddcb_93():  #  RES 2,(IX+n>E)
  global ix, xy_offset, t, e
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 251)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  e = result

  e = e & 0xff

def opcode_ddcb_94():  #  RES 2,(IX+n>H)
  global ix, xy_offset, t, h
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 251)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  h = result

  h = h & 0xff

def opcode_ddcb_95():  #  RES 2,(IX+n>L)
  global ix, xy_offset, t, l
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 251)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  l = result

  l = l & 0xff

def opcode_ddcb_96():  #  RES 2,(IX+n)
  global ix, xy_offset, t
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 251)  #  u8
  t += 5
  mmu.write(ixAddr, result)


def opcode_ddcb_97():  #  RES 2,(IX+n>A)
  global ix, xy_offset, t, a
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 251)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  a = result

  a = a & 0xff

def opcode_ddcb_98():  #  RES 3,(IX+n>B)
  global ix, xy_offset, t, b
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 247)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  b = result

  b = b & 0xff

def opcode_ddcb_99():  #  RES 3,(IX+n>C)
  global ix, xy_offset, t, c
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 247)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  c = result

  c = c & 0xff

def opcode_ddcb_9a():  #  RES 3,(IX+n>D)
  global ix, xy_offset, t, d
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 247)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  d = result

  d = d & 0xff

def opcode_ddcb_9b():  #  RES 3,(IX+n>E)
  global ix, xy_offset, t, e
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 247)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  e = result

  e = e & 0xff

def opcode_ddcb_9c():  #  RES 3,(IX+n>H)
  global ix, xy_offset, t, h
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 247)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  h = result

  h = h & 0xff

def opcode_ddcb_9d():  #  RES 3,(IX+n>L)
  global ix, xy_offset, t, l
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 247)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  l = result

  l = l & 0xff

def opcode_ddcb_9e():  #  RES 3,(IX+n)
  global ix, xy_offset, t
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 247)  #  u8
  t += 5
  mmu.write(ixAddr, result)


def opcode_ddcb_9f():  #  RES 3,(IX+n>A)
  global ix, xy_offset, t, a
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 247)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  a = result

  a = a & 0xff

def opcode_ddcb_a0():  #  RES 4,(IX+n>B)
  global ix, xy_offset, t, b
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 239)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  b = result

  b = b & 0xff

def opcode_ddcb_a1():  #  RES 4,(IX+n>C)
  global ix, xy_offset, t, c
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 239)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  c = result

  c = c & 0xff

def opcode_ddcb_a2():  #  RES 4,(IX+n>D)
  global ix, xy_offset, t, d
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 239)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  d = result

  d = d & 0xff

def opcode_ddcb_a3():  #  RES 4,(IX+n>E)
  global ix, xy_offset, t, e
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 239)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  e = result

  e = e & 0xff

def opcode_ddcb_a4():  #  RES 4,(IX+n>H)
  global ix, xy_offset, t, h
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 239)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  h = result

  h = h & 0xff

def opcode_ddcb_a5():  #  RES 4,(IX+n>L)
  global ix, xy_offset, t, l
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 239)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  l = result

  l = l & 0xff

def opcode_ddcb_a6():  #  RES 4,(IX+n)
  global ix, xy_offset, t
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 239)  #  u8
  t += 5
  mmu.write(ixAddr, result)


def opcode_ddcb_a7():  #  RES 4,(IX+n>A)
  global ix, xy_offset, t, a
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 239)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  a = result

  a = a & 0xff

def opcode_ddcb_a8():  #  RES 5,(IX+n>B)
  global ix, xy_offset, t, b
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 223)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  b = result

  b = b & 0xff

def opcode_ddcb_a9():  #  RES 5,(IX+n>C)
  global ix, xy_offset, t, c
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 223)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  c = result

  c = c & 0xff

def opcode_ddcb_aa():  #  RES 5,(IX+n>D)
  global ix, xy_offset, t, d
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 223)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  d = result

  d = d & 0xff

def opcode_ddcb_ab():  #  RES 5,(IX+n>E)
  global ix, xy_offset, t, e
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 223)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  e = result

  e = e & 0xff

def opcode_ddcb_ac():  #  RES 5,(IX+n>H)
  global ix, xy_offset, t, h
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 223)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  h = result

  h = h & 0xff

def opcode_ddcb_ad():  #  RES 5,(IX+n>L)
  global ix, xy_offset, t, l
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 223)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  l = result

  l = l & 0xff

def opcode_ddcb_ae():  #  RES 5,(IX+n)
  global ix, xy_offset, t
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 223)  #  u8
  t += 5
  mmu.write(ixAddr, result)


def opcode_ddcb_af():  #  RES 5,(IX+n>A)
  global ix, xy_offset, t, a
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 223)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  a = result

  a = a & 0xff

def opcode_ddcb_b0():  #  RES 6,(IX+n>B)
  global ix, xy_offset, t, b
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 191)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  b = result

  b = b & 0xff

def opcode_ddcb_b1():  #  RES 6,(IX+n>C)
  global ix, xy_offset, t, c
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 191)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  c = result

  c = c & 0xff

def opcode_ddcb_b2():  #  RES 6,(IX+n>D)
  global ix, xy_offset, t, d
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 191)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  d = result

  d = d & 0xff

def opcode_ddcb_b3():  #  RES 6,(IX+n>E)
  global ix, xy_offset, t, e
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 191)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  e = result

  e = e & 0xff

def opcode_ddcb_b4():  #  RES 6,(IX+n>H)
  global ix, xy_offset, t, h
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 191)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  h = result

  h = h & 0xff

def opcode_ddcb_b5():  #  RES 6,(IX+n>L)
  global ix, xy_offset, t, l
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 191)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  l = result

  l = l & 0xff

def opcode_ddcb_b6():  #  RES 6,(IX+n)
  global ix, xy_offset, t
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 191)  #  u8
  t += 5
  mmu.write(ixAddr, result)


def opcode_ddcb_b7():  #  RES 6,(IX+n>A)
  global ix, xy_offset, t, a
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 191)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  a = result

  a = a & 0xff

def opcode_ddcb_b8():  #  RES 7,(IX+n>B)
  global ix, xy_offset, t, b
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 127)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  b = result

  b = b & 0xff

def opcode_ddcb_b9():  #  RES 7,(IX+n>C)
  global ix, xy_offset, t, c
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 127)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  c = result

  c = c & 0xff

def opcode_ddcb_ba():  #  RES 7,(IX+n>D)
  global ix, xy_offset, t, d
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 127)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  d = result

  d = d & 0xff

def opcode_ddcb_bb():  #  RES 7,(IX+n>E)
  global ix, xy_offset, t, e
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 127)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  e = result

  e = e & 0xff

def opcode_ddcb_bc():  #  RES 7,(IX+n>H)
  global ix, xy_offset, t, h
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 127)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  h = result

  h = h & 0xff

def opcode_ddcb_bd():  #  RES 7,(IX+n>L)
  global ix, xy_offset, t, l
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 127)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  l = result

  l = l & 0xff

def opcode_ddcb_be():  #  RES 7,(IX+n)
  global ix, xy_offset, t
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 127)  #  u8
  t += 5
  mmu.write(ixAddr, result)


def opcode_ddcb_bf():  #  RES 7,(IX+n>A)
  global ix, xy_offset, t, a
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val & 127)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  a = result

  a = a & 0xff

def opcode_ddcb_c0():  #  SET 0,(IX+n>B)
  global ix, xy_offset, t, b
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 1)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  b = result

  b = b & 0xff

def opcode_ddcb_c1():  #  SET 0,(IX+n>C)
  global ix, xy_offset, t, c
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 1)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  c = result

  c = c & 0xff

def opcode_ddcb_c2():  #  SET 0,(IX+n>D)
  global ix, xy_offset, t, d
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 1)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  d = result

  d = d & 0xff

def opcode_ddcb_c3():  #  SET 0,(IX+n>E)
  global ix, xy_offset, t, e
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 1)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  e = result

  e = e & 0xff

def opcode_ddcb_c4():  #  SET 0,(IX+n>H)
  global ix, xy_offset, t, h
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 1)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  h = result

  h = h & 0xff

def opcode_ddcb_c5():  #  SET 0,(IX+n>L)
  global ix, xy_offset, t, l
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 1)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  l = result

  l = l & 0xff

def opcode_ddcb_c6():  #  SET 0,(IX+n)
  global ix, xy_offset, t
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 1)  #  u8
  t += 5
  mmu.write(ixAddr, result)


def opcode_ddcb_c7():  #  SET 0,(IX+n>A)
  global ix, xy_offset, t, a
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 1)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  a = result

  a = a & 0xff

def opcode_ddcb_c8():  #  SET 1,(IX+n>B)
  global ix, xy_offset, t, b
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 2)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  b = result

  b = b & 0xff

def opcode_ddcb_c9():  #  SET 1,(IX+n>C)
  global ix, xy_offset, t, c
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 2)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  c = result

  c = c & 0xff

def opcode_ddcb_ca():  #  SET 1,(IX+n>D)
  global ix, xy_offset, t, d
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 2)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  d = result

  d = d & 0xff

def opcode_ddcb_cb():  #  SET 1,(IX+n>E)
  global ix, xy_offset, t, e
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 2)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  e = result

  e = e & 0xff

def opcode_ddcb_cc():  #  SET 1,(IX+n>H)
  global ix, xy_offset, t, h
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 2)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  h = result

  h = h & 0xff

def opcode_ddcb_cd():  #  SET 1,(IX+n>L)
  global ix, xy_offset, t, l
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 2)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  l = result

  l = l & 0xff

def opcode_ddcb_ce():  #  SET 1,(IX+n)
  global ix, xy_offset, t
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 2)  #  u8
  t += 5
  mmu.write(ixAddr, result)


def opcode_ddcb_cf():  #  SET 1,(IX+n>A)
  global ix, xy_offset, t, a
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 2)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  a = result

  a = a & 0xff

def opcode_ddcb_d0():  #  SET 2,(IX+n>B)
  global ix, xy_offset, t, b
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 4)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  b = result

  b = b & 0xff

def opcode_ddcb_d1():  #  SET 2,(IX+n>C)
  global ix, xy_offset, t, c
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 4)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  c = result

  c = c & 0xff

def opcode_ddcb_d2():  #  SET 2,(IX+n>D)
  global ix, xy_offset, t, d
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 4)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  d = result

  d = d & 0xff

def opcode_ddcb_d3():  #  SET 2,(IX+n>E)
  global ix, xy_offset, t, e
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 4)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  e = result

  e = e & 0xff

def opcode_ddcb_d4():  #  SET 2,(IX+n>H)
  global ix, xy_offset, t, h
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 4)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  h = result

  h = h & 0xff

def opcode_ddcb_d5():  #  SET 2,(IX+n>L)
  global ix, xy_offset, t, l
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 4)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  l = result

  l = l & 0xff

def opcode_ddcb_d6():  #  SET 2,(IX+n)
  global ix, xy_offset, t
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 4)  #  u8
  t += 5
  mmu.write(ixAddr, result)


def opcode_ddcb_d7():  #  SET 2,(IX+n>A)
  global ix, xy_offset, t, a
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 4)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  a = result

  a = a & 0xff

def opcode_ddcb_d8():  #  SET 3,(IX+n>B)
  global ix, xy_offset, t, b
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 8)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  b = result

  b = b & 0xff

def opcode_ddcb_d9():  #  SET 3,(IX+n>C)
  global ix, xy_offset, t, c
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 8)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  c = result

  c = c & 0xff

def opcode_ddcb_da():  #  SET 3,(IX+n>D)
  global ix, xy_offset, t, d
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 8)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  d = result

  d = d & 0xff

def opcode_ddcb_db():  #  SET 3,(IX+n>E)
  global ix, xy_offset, t, e
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 8)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  e = result

  e = e & 0xff

def opcode_ddcb_dc():  #  SET 3,(IX+n>H)
  global ix, xy_offset, t, h
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 8)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  h = result

  h = h & 0xff

def opcode_ddcb_dd():  #  SET 3,(IX+n>L)
  global ix, xy_offset, t, l
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 8)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  l = result

  l = l & 0xff

def opcode_ddcb_de():  #  SET 3,(IX+n)
  global ix, xy_offset, t
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 8)  #  u8
  t += 5
  mmu.write(ixAddr, result)


def opcode_ddcb_df():  #  SET 3,(IX+n>A)
  global ix, xy_offset, t, a
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 8)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  a = result

  a = a & 0xff

def opcode_ddcb_e0():  #  SET 4,(IX+n>B)
  global ix, xy_offset, t, b
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 16)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  b = result

  b = b & 0xff

def opcode_ddcb_e1():  #  SET 4,(IX+n>C)
  global ix, xy_offset, t, c
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 16)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  c = result

  c = c & 0xff

def opcode_ddcb_e2():  #  SET 4,(IX+n>D)
  global ix, xy_offset, t, d
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 16)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  d = result

  d = d & 0xff

def opcode_ddcb_e3():  #  SET 4,(IX+n>E)
  global ix, xy_offset, t, e
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 16)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  e = result

  e = e & 0xff

def opcode_ddcb_e4():  #  SET 4,(IX+n>H)
  global ix, xy_offset, t, h
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 16)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  h = result

  h = h & 0xff

def opcode_ddcb_e5():  #  SET 4,(IX+n>L)
  global ix, xy_offset, t, l
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 16)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  l = result

  l = l & 0xff

def opcode_ddcb_e6():  #  SET 4,(IX+n)
  global ix, xy_offset, t
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 16)  #  u8
  t += 5
  mmu.write(ixAddr, result)


def opcode_ddcb_e7():  #  SET 4,(IX+n>A)
  global ix, xy_offset, t, a
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 16)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  a = result

  a = a & 0xff

def opcode_ddcb_e8():  #  SET 5,(IX+n>B)
  global ix, xy_offset, t, b
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 32)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  b = result

  b = b & 0xff

def opcode_ddcb_e9():  #  SET 5,(IX+n>C)
  global ix, xy_offset, t, c
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 32)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  c = result

  c = c & 0xff

def opcode_ddcb_ea():  #  SET 5,(IX+n>D)
  global ix, xy_offset, t, d
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 32)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  d = result

  d = d & 0xff

def opcode_ddcb_eb():  #  SET 5,(IX+n>E)
  global ix, xy_offset, t, e
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 32)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  e = result

  e = e & 0xff

def opcode_ddcb_ec():  #  SET 5,(IX+n>H)
  global ix, xy_offset, t, h
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 32)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  h = result

  h = h & 0xff

def opcode_ddcb_ed():  #  SET 5,(IX+n>L)
  global ix, xy_offset, t, l
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 32)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  l = result

  l = l & 0xff

def opcode_ddcb_ee():  #  SET 5,(IX+n)
  global ix, xy_offset, t
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 32)  #  u8
  t += 5
  mmu.write(ixAddr, result)


def opcode_ddcb_ef():  #  SET 5,(IX+n>A)
  global ix, xy_offset, t, a
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 32)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  a = result

  a = a & 0xff

def opcode_ddcb_f0():  #  SET 6,(IX+n>B)
  global ix, xy_offset, t, b
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 64)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  b = result

  b = b & 0xff

def opcode_ddcb_f1():  #  SET 6,(IX+n>C)
  global ix, xy_offset, t, c
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 64)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  c = result

  c = c & 0xff

def opcode_ddcb_f2():  #  SET 6,(IX+n>D)
  global ix, xy_offset, t, d
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 64)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  d = result

  d = d & 0xff

def opcode_ddcb_f3():  #  SET 6,(IX+n>E)
  global ix, xy_offset, t, e
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 64)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  e = result

  e = e & 0xff

def opcode_ddcb_f4():  #  SET 6,(IX+n>H)
  global ix, xy_offset, t, h
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 64)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  h = result

  h = h & 0xff

def opcode_ddcb_f5():  #  SET 6,(IX+n>L)
  global ix, xy_offset, t, l
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 64)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  l = result

  l = l & 0xff

def opcode_ddcb_f6():  #  SET 6,(IX+n)
  global ix, xy_offset, t
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 64)  #  u8
  t += 5
  mmu.write(ixAddr, result)


def opcode_ddcb_f7():  #  SET 6,(IX+n>A)
  global ix, xy_offset, t, a
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 64)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  a = result

  a = a & 0xff

def opcode_ddcb_f8():  #  SET 7,(IX+n>B)
  global ix, xy_offset, t, b
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 128)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  b = result

  b = b & 0xff

def opcode_ddcb_f9():  #  SET 7,(IX+n>C)
  global ix, xy_offset, t, c
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 128)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  c = result

  c = c & 0xff

def opcode_ddcb_fa():  #  SET 7,(IX+n>D)
  global ix, xy_offset, t, d
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 128)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  d = result

  d = d & 0xff

def opcode_ddcb_fb():  #  SET 7,(IX+n>E)
  global ix, xy_offset, t, e
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 128)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  e = result

  e = e & 0xff

def opcode_ddcb_fc():  #  SET 7,(IX+n>H)
  global ix, xy_offset, t, h
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 128)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  h = result

  h = h & 0xff

def opcode_ddcb_fd():  #  SET 7,(IX+n>L)
  global ix, xy_offset, t, l
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 128)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  l = result

  l = l & 0xff

def opcode_ddcb_fe():  #  SET 7,(IX+n)
  global ix, xy_offset, t
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 128)  #  u8
  t += 5
  mmu.write(ixAddr, result)


def opcode_ddcb_ff():  #  SET 7,(IX+n>A)
  global ix, xy_offset, t, a
  ixAddr = (ix + xy_offset) & 0xffff  #  u16
  val = mmu.read(ixAddr)
  result = (val | 128)  #  u8
  t += 5
  mmu.write(ixAddr, result)
  a = result

  a = a & 0xff

def opcode_ed_40():  #  IN B,(C)
  global b, c, f, memptr
  bc = (b << 8) | c

  memptr = (bc + 1) & 0xffff
  b = ports.read(bc) & 0xff #  u8
  f = ((f & FLAG_C) | sz53pTable[b])

def opcode_ed_41():  #  OUT (C),B
  global b, c, memptr
  bc = (b << 8) | c

  memptr = (bc + 1) & 0xffff
  ports.write(bc, b)

def opcode_ed_42():  #  SBC HL,BC
  global h, l, b, c, f, i, r, t, memptr
  hl = (h << 8) | l
  bc = (b << 8) | c

  memptr = (hl + 1) & 0xffff
  rr = bc  #  u16
  sub16temp = ((hl - rr) - (f & FLAG_C))  #  u32
  lookup = ((hl & 0x8800) >> 11) | ((rr & 0x8800) >> 10) | ((sub16temp & 0x8800) >> 9)  #  u32
  f = ((FLAG_C if (sub16temp & 0x10000) else 0) | FLAG_N | overflowSubTable[(lookup >> 4)] | (((sub16temp & 0xff00) >> 8) & (FLAG_3 | FLAG_5 | FLAG_S)) | halfcarrySubTable[(lookup & 0x07)] | (0 if (sub16temp & 0xffff) else FLAG_Z))
  t += 7

  h = (sub16temp >> 8) & 0xff; l = sub16temp & 0xff

def opcode_ed_43():  #  LD (nn),BC
  global pc, b, c, memptr

  lo = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  hi = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  addr = (lo | (hi << 8))
  mmu.write(addr, c)
  addr = (addr + 1) & 0xffff
  mmu.write(addr, b)
  memptr = addr

def opcode_ed_44():  #  NEG
  global a, f
  A = i32(a)  #  i32
  result = (- A)  #  i32
  lookup = ((A & 0x88) >> 2) | ((result & 0x88) >> 1)  #  i32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | sz53Table[a]

def opcode_ed_45():  #  RETN
  global iff1, iff2, sp, pc, memptr
  iff1 = iff2
  lo = mmu.read(sp)
  sp = (sp + 1) & 0xffff
  hi = mmu.read(sp)
  sp = (sp + 1) & 0xffff
  pc = (lo | (hi << 8))
  memptr = pc

def opcode_ed_46():  #  IM 0
  global im
  im = 0

def opcode_ed_47():  #  LD I,A
  global i, a, t
  i = a
  t += 1

def opcode_ed_48():  #  IN C,(C)
  global b, c, f, memptr
  bc = (b << 8) | c

  memptr = (bc + 1) & 0xffff
  c = ports.read(bc)
  c = c & 0xff #  u8
  f = ((f & FLAG_C) | sz53pTable[c])

def opcode_ed_49():  #  OUT (C),C
  global b, c, memptr
  bc = (b << 8) | c

  memptr = (bc + 1) & 0xffff
  ports.write(bc, c)

def opcode_ed_4a():  #  ADC HL,BC
  global h, l, b, c, f, t, memptr
  hl = (h << 8) | l
  bc = (b << 8) | c

  memptr = (hl + 1) & 0xffff
  rr = bc  #  u32
  result = ((hl + rr) + (f & FLAG_C))  #  u32
  lookup = ((hl & 0x8800) >> 11) | ((rr & 0x8800) >> 10) | ((result & 0x8800) >> 9)  #  u32
  hl = result
  f = ((FLAG_C if (result & 0x10000) else 0) | overflowAddTable[(lookup >> 4)] | ((result >> 8) & (FLAG_3 | FLAG_5 | FLAG_S)) | halfcarryAddTable[(lookup & 0x07)] | (0 if (result & 0xffff) else FLAG_Z))
  t += 7

  h = (hl >> 8) & 0xff; l = hl & 0xff

def opcode_ed_4b():  #  LD BC,(nn)
  global pc, b, c, memptr

  lo = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  hi = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  addr = (lo | (hi << 8))
  c = mmu.read(addr)
  addr = (addr + 1) & 0xffff
  b = mmu.read(addr)
  memptr = addr

def opcode_ed_4d():  #  RETI
  global iff1, iff2, sp, pc, memptr
  lo = mmu.read(sp)
  sp = (sp + 1) & 0xffff
  hi = mmu.read(sp)
  sp = (sp + 1) & 0xffff
  pc = (lo | (hi << 8))
  memptr = pc

def opcode_ed_4f():  #  LD R,A
  global r, a, t
  r = a   #  r & 0x80 | a & 0x7f ?
  t += 1

def opcode_ed_50():  #  IN D,(C)
  global b, c, d, f, memptr
  bc = (b << 8) | c

  memptr = (bc + 1) & 0xffff
  d = ports.read(bc) & 0xff #  u8
  f = ((f & FLAG_C) | sz53pTable[d])

def opcode_ed_51():  #  OUT (C),D
  global b, c, d, memptr
  bc = (b << 8) | c

  memptr = (bc + 1) & 0xffff
  ports.write(bc, d)

def opcode_ed_52():  #  SBC HL,DE
  global h, l, d, e, f, t, memptr
  hl = (h << 8) | l
  de = (d << 8) | e

  memptr = (hl + 1) & 0xffff
  rr = de  #  u16
  sub16temp = ((hl - rr) - (f & FLAG_C))  #  u32
  lookup = ((hl & 0x8800) >> 11) | ((rr & 0x8800) >> 10) | ((sub16temp & 0x8800) >> 9)  #  u32
  f = ((FLAG_C if (sub16temp & 0x10000) else 0) | FLAG_N | overflowSubTable[(lookup >> 4)] | (((sub16temp & 0xff00) >> 8) & (FLAG_3 | FLAG_5 | FLAG_S)) | halfcarrySubTable[(lookup & 0x07)] | (0 if (sub16temp & 0xffff) else FLAG_Z))
  t += 7

  h = (sub16temp >> 8) & 0xff; l = sub16temp & 0xff

def opcode_ed_53():  #  LD (nn),DE
  global pc, d, e, memptr

  lo = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  hi = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  addr = (lo | (hi << 8))
  mmu.write(addr, e)
  addr = (addr + 1) & 0xffff
  mmu.write(addr, d)
  memptr = addr

def opcode_ed_56():  #  IM 1
  global im
  im = 1

def opcode_ed_57():  #  LD A,I
  global i, r, t, a, f

  t += 1
  a = i #  u8
  f = (f & FLAG_C) | sz53Table[a] | (FLAG_V if iff2 else 0)

def opcode_ed_58():  #  IN E,(C)
  global b, c, e, f, memptr
  bc = (b << 8) | c

  memptr = (bc + 1) & 0xffff
  e = ports.read(bc)  #  u8
  f = ((f & FLAG_C) | sz53pTable[e])

def opcode_ed_59():  #  OUT (C),E
  global b, c, e, memptr
  bc = (b << 8) | c

  memptr = (bc + 1) & 0xffff
  ports.write(bc, e)

def opcode_ed_5a():  #  ADC HL,DE
  global h, l, d, e, f, t, memptr
  hl = (h << 8) | l
  de = (d << 8) | e

  memptr = (hl + 1) & 0xffff
  rr = de  #  u32
  result = ((hl + rr) + (f & FLAG_C))  #  u32
  lookup = ((hl & 0x8800) >> 11) | ((rr & 0x8800) >> 10) | ((result & 0x8800) >> 9)  #  u32
  f = ((FLAG_C if (result & 0x10000) else 0) | overflowAddTable[(lookup >> 4)] | ((result >> 8) & (FLAG_3 | FLAG_5 | FLAG_S)) | halfcarryAddTable[(lookup & 0x07)] | (0 if (result & 0xffff) else FLAG_Z))
  t += 7

  h = (result >> 8) & 0xff; l = result & 0xff

def opcode_ed_5b():  #  LD DE,(nn)
  global pc, d, e, memptr

  lo = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  hi = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  addr = (lo | (hi << 8))
  e = mmu.read(addr)
  addr = (addr + 1) & 0xffff
  d = mmu.read(addr)
  memptr = addr

def opcode_ed_5e():  #  IM 2
  global im
  im = 2

def opcode_ed_5f():  #  LD A,R
  global r, t, a, f

  t += 1
  a = r
  f = (f & FLAG_C) | sz53Table[a] | (FLAG_V if iff2 else 0)

def opcode_ed_60():  #  IN H,(C)
  global b, c, h, f, memptr
  bc = (b << 8) | c

  memptr = (bc + 1) & 0xffff
  h = ports.read(bc)  #  u8
  f = ((f & FLAG_C) | sz53pTable[h])

def opcode_ed_61():  #  OUT (C),H
  global b, c, h, memptr
  bc = (b << 8) | c

  memptr = (bc + 1) & 0xffff
  ports.write(bc, h)

def opcode_ed_62():  #  SBC HL,HL
  global h, l, f, t, memptr
  hl = (h << 8) | l

  memptr = (hl + 1) & 0xffff
  rr = hl  #  u16
  sub16temp = ((hl - rr) - (f & FLAG_C))  #  u32
  lookup = ((hl & 0x8800) >> 11) | ((rr & 0x8800) >> 10) | ((sub16temp & 0x8800) >> 9)  #  u32
  f = ((FLAG_C if (sub16temp & 0x10000) else 0) | FLAG_N | overflowSubTable[(lookup >> 4)] | (((sub16temp & 0xff00) >> 8) & (FLAG_3 | FLAG_5 | FLAG_S)) | halfcarrySubTable[(lookup & 0x07)] | (0 if (sub16temp & 0xffff) else FLAG_Z))
  t += 7

  h = (sub16temp >> 8) & 0xff; l = sub16temp & 0xff

def opcode_ed_63():  #  LD (nn),HL
  global pc, h, l, memptr

  lo = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  hi = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  addr = (lo | (hi << 8))
  mmu.write(addr, l)
  addr = (addr + 1) & 0xffff
  mmu.write(addr, h)
  memptr = addr

def opcode_ed_67():  #  RRD
  global h, l, t, a, f, memptr
  hl = (h << 8) | l

  memptr = (hl + 1) & 0xffff
  val = mmu.read(hl)  #  u8
  t += 4
  result = ((a << 4) | (val >> 4)) & 0xff #  u8
  mmu.write(hl, result)
  finalA = ((a & 0xf0) | (val & 0x0f))  #  u8
  a = finalA
  f = ((f & FLAG_C) | sz53pTable[finalA])

def opcode_ed_68():  #  IN L,(C)
  global b, c, l, f, memptr
  bc = (b << 8) | c

  memptr = (bc + 1) & 0xffff
  l = ports.read(bc) & 0xff #  u8
  f = ((f & FLAG_C) | sz53pTable[l])

def opcode_ed_69():  #  OUT (C),L
  global b, c, l, memptr
  bc = (b << 8) | c

  memptr = (bc + 1) & 0xffff
  ports.write(bc, l)

def opcode_ed_6a():  #  ADC HL,HL
  global h, l, f, t, memptr
  hl = (h << 8) | l

  memptr = (hl + 1) & 0xffff
  rr = hl  #  u32
  result = ((hl + rr) + (f & FLAG_C))  #  u32
  lookup = ((hl & 0x8800) >> 11) | ((rr & 0x8800) >> 10) | ((result & 0x8800) >> 9)  #  u32
  f = ((FLAG_C if (result & 0x10000) else 0) | overflowAddTable[(lookup >> 4)] | ((result >> 8) & (FLAG_3 | FLAG_5 | FLAG_S)) | halfcarryAddTable[(lookup & 0x07)] | (0 if (result & 0xffff) else FLAG_Z))
  t += 7

  h = (result >> 8) & 0xff; l = result & 0xff

def opcode_ed_6b():  #  LD HL,(nn)
  global pc, h, l, memptr

  lo = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  hi = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  addr = (lo | (hi << 8))
  l = mmu.read(addr)
  addr = (addr + 1) & 0xffff
  h = mmu.read(addr)
  memptr = addr

def opcode_ed_6f():  #  RLD
  global h, l, t, a, f, memptr
  hl = (h << 8) | l

  memptr = (hl + 1) & 0xffff
  val = mmu.read(hl)  #  u8
  t += 4
  A = a  #  u8
  result = ((val << 4) | (A & 0x0f)) & 0xff #  u8
  mmu.write(hl, result)
  finalA = ((A & 0xf0) | (val >> 4))  #  u8
  a = finalA
  f = ((f & FLAG_C) | sz53pTable[finalA])

def opcode_ed_70():  #  IN F,(C)
  global b, c, f, memptr
  bc = (b << 8) | c

  memptr = (bc + 1) & 0xffff
  result = ports.read(bc) & 0xff #  u8
  f = ((f & FLAG_C) | sz53pTable[result])

def opcode_ed_71():  #  OUT (C),0
  global b, c, memptr
  bc = (b << 8) | c

  memptr = (bc + 1) & 0xffff
  ports.write(bc, 0)

def opcode_ed_72():  #  SBC HL,SP
  global h, l, sp, f, t, memptr
  hl = (h << 8) | l

  memptr = (hl + 1) & 0xffff
  rr = sp  #  u16
  sub16temp = ((hl - rr) - (f & FLAG_C))  #  u32
  lookup = ((hl & 0x8800) >> 11) | ((rr & 0x8800) >> 10) | ((sub16temp & 0x8800) >> 9)  #  u32
  f = ((FLAG_C if (sub16temp & 0x10000) else 0) | FLAG_N | overflowSubTable[(lookup >> 4)] | (((sub16temp & 0xff00) >> 8) & (FLAG_3 | FLAG_5 | FLAG_S)) | halfcarrySubTable[(lookup & 0x07)] | (0 if (sub16temp & 0xffff) else FLAG_Z))
  t += 7

  h = (sub16temp >> 8) & 0xff; l = sub16temp & 0xff

def opcode_ed_73():  #  LD (nn),SP
  global pc, sp, t, memptr
  lo = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  hi = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  addr = (lo | (hi << 8))
  mmu.write(addr, (sp & 0xff))
  addr = (addr + 1) & 0xffff
  mmu.write(addr, (sp >> 8) & 0xff)
  memptr = addr

def opcode_ed_78():  #  IN A,(C)
  global b, c, a, f, memptr
  bc = (b << 8) | c

  memptr = (bc + 1) & 0xffff
  a = ports.read(bc)  #  u8
  f = ((f & FLAG_C) | sz53pTable[a])

def opcode_ed_79():  #  OUT (C),A
  global b, c, a, memptr
  bc = (b << 8) | c

  memptr = (bc + 1) & 0xffff
  ports.write(bc, a)

def opcode_ed_7a():  #  ADC HL,SP
  global h, l, sp, f, t, memptr
  hl = (h << 8) | l

  memptr = (hl + 1) & 0xffff
  rr = sp  #  u32
  result = ((hl + rr) + (f & FLAG_C))  #  u32
  lookup = ((hl & 0x8800) >> 11) | ((rr & 0x8800) >> 10) | ((result & 0x8800) >> 9)  #  u32
  hl = result
  f = ((FLAG_C if (result & 0x10000) else 0) | overflowAddTable[(lookup >> 4)] | ((result >> 8) & (FLAG_3 | FLAG_5 | FLAG_S)) | halfcarryAddTable[(lookup & 0x07)] | (0 if (result & 0xffff) else FLAG_Z))
  t += 7

  h = (result >> 8) & 0xff; l = result & 0xff

def opcode_ed_7b():  #  LD SP,(nn)
  global pc, sp, memptr
  lo = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  hi = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  addr = (lo | (hi << 8))
  sp = (mmu.read(addr) | (mmu.read((addr + 1)) << 8))
  memptr = (addr + 1) & 0xffff

def opcode_ed_7e():  #  IM 2
  global im
  im = 2

def opcode_ed_a0():  #  LDI
  global h, l, d, e, b, c, a, f, t
  hl = (h << 8) | l
  de = (d << 8) | e
  bc = (b << 8) | c

  val = mmu.read(hl)  #  u8
  mmu.write(de, val)
  bc = (bc - 1)
  val += a
  f = ((f & (FLAG_C | FLAG_Z | FLAG_S)) | (FLAG_V if bc else 0) | (val & FLAG_3) | (FLAG_5 if (val & 0x02) else 0))
  hl = (hl + 1)
  de = (de + 1)
  t += 2

  b = (bc >> 8) & 0xff; c = bc & 0xff
  h = (hl >> 8) & 0xff; l = hl & 0xff
  d = (de >> 8) & 0xff; e = de & 0xff

def opcode_ed_a1():  #  CPI
  global h, l, a, b, c, f, t, memptr
  hl = (h << 8) | l
  bc = (b << 8) | c

  val = mmu.read(hl)  #  u8
  result = (a - val) & 0xff  #  u8
  lookup = ((a & 0x08) >> 3) | ((val & 0x08) >> 2) | ((result & 0x08) >> 1)  #  u8
  hl = (hl + 1)
  bc = (bc - 1)  #  u16
  F = (f & FLAG_C) | ((FLAG_V | FLAG_N) if bc else FLAG_N) | halfcarrySubTable[lookup] | (0 if result else FLAG_Z) | (result & FLAG_S)  #  u8
  if (F & FLAG_H):
    result -= 1
  f = (F | (result & FLAG_3) | (FLAG_5 if (result & 0x02) else 0))
  t += 5
  memptr = (memptr + 1) & 0xffff

  h = (hl >> 8) & 0xff; l = hl & 0xff
  b = (bc >> 8) & 0xff; c = bc & 0xff

def opcode_ed_a2():  #  INI
  global t, b, c, h, l, f, memptr
  bc = (b << 8) | c
  hl = (h << 8) | l

  t += 1
  result = ports.read(bc)  #  u8
  mmu.write(hl, result)
  memptr = (bc + 1) & 0xffff
  b = (b - 1) & 0xff #  u8
  hl = (hl + 1) & 0xffff
  initemp2 = (result + c + 1) & 0xff  #  u8
  f = ((FLAG_N if (result & 0x80) else 0) | ((FLAG_H | FLAG_C) if (initemp2 < result) else 0) | (FLAG_P if parityTable[((initemp2 & 0x07) ^ b)] else 0) | sz53Table[b])

  h = (hl >> 8) & 0xff; l = hl & 0xff

def opcode_ed_a3():  #  OUTI
  global t, h, l, b, c, f, memptr
  hl = (h << 8) | l

  t += 1
  val = mmu.read(hl)  #  u8
  b = (b - 1) & 0xff #  u16
  bc = (b << 8) | c
  memptr = (bc + 1) & 0xffff
  ports.write(bc, val)
  hl = (hl + 1) & 0xffff
  h = (hl >> 8) & 0xff; l = hl & 0xff
  outitemp2 = (val + l) & 0xff  #  u8
  f = ((FLAG_N if (val & 0x80) else 0) | ((FLAG_H | FLAG_C) if (outitemp2 < val) else 0) | (FLAG_P if parityTable[((outitemp2 & 0x07) ^ b)] else 0) | (sz53Table[b]))

def opcode_ed_a8():  #  LDD
  global h, l, d, e, b, c, a, f, t
  hl = (h << 8) | l
  de = (d << 8) | e
  bc = (b << 8) | c

  val = mmu.read(hl)  #  u8
  mmu.write(de, val)
  bc = (bc - 1)
  val += a
  f = ((f & (FLAG_C | FLAG_Z | FLAG_S)) | (FLAG_V if bc else 0) | (val & FLAG_3) | (FLAG_5 if (val & 0x02) else 0))
  hl = (hl - 1)
  de = (de - 1)
  t += 2

  b = (bc >> 8) & 0xff; c = bc & 0xff
  h = (hl >> 8) & 0xff; l = hl & 0xff
  d = (de >> 8) & 0xff; e = de & 0xff

def opcode_ed_a9():  #  CPD
  global h, l, a, b, c, f, t, memptr
  hl = (h << 8) | l
  bc = (b << 8) | c

  val = mmu.read(hl)  #  u8
  result = (a - val) & 0xff  #  u8
  lookup = ((a & 0x08) >> 3) | ((val & 0x08) >> 2) | ((result & 0x08) >> 1)  #  u8
  hl = (hl - 1)
  bc = (bc - 1)  #  u16
  F = (f & FLAG_C) | ((FLAG_V | FLAG_N) if bc else FLAG_N) | halfcarrySubTable[lookup] | (0 if result else FLAG_Z) | (result & FLAG_S)  #  u8
  if (F & FLAG_H):
    result -= 1
  f = (F | (result & FLAG_3) | (FLAG_5 if (result & 0x02) else 0))
  t += 5
  memptr = (memptr - 1) & 0xffff

  h = (hl >> 8) & 0xff; l = hl & 0xff
  b = (bc >> 8) & 0xff; c = bc & 0xff

def opcode_ed_aa():  #  IND
  global t, b, c, h, l, f, memptr
  bc = (b << 8) | c
  hl = (h << 8) | l

  t += 1
  result = ports.read(bc)  #  u8
  mmu.write(hl, result)
  memptr = (bc - 1) & 0xffff
  b = (b - 1) & 0xff #  u8
  hl = (hl - 1)
  initemp2 = (result + c - 1) & 0xff  #  u8
  f = ((FLAG_N if (result & 0x80) else 0) | ((FLAG_H | FLAG_C) if (initemp2 < result) else 0) | (FLAG_P if parityTable[((initemp2 & 0x07) ^ b)] else 0) | sz53Table[b])

  h = (hl >> 8) & 0xff; l = hl & 0xff

def opcode_ed_ab():  #  OUTD
  global t, h, l, b, c, f, memptr
  hl = (h << 8) | l

  t += 1
  val = mmu.read(hl)  #  u8
  b = (b - 1) & 0xff
  bc = (b << 8) | c
  ports.write(bc, val)
  memptr = (bc - 1) & 0xffff
  hl = hl - 1
  h = (hl >> 8) & 0xff; l = hl & 0xff
  outitemp2 = (val + l) & 0xff #  u8
  f = ((FLAG_N if (val & 0x80) else 0) | ((FLAG_H | FLAG_C) if (outitemp2 < val) else 0) | (FLAG_P if parityTable[((outitemp2 & 0x07) ^ b)] else 0) | (sz53Table[b]))

def opcode_ed_b0():  #  LDIR
  global h, l, d, e, b, c, a, f, t, pc, memptr
  hl = (h << 8) | l
  de = (d << 8) | e
  bc = (b << 8) | c

  val = mmu.read(hl)  #  u8
  mmu.write(de, val)
  bc = (bc - 1)
  val += a
  f = ((f & (FLAG_C | FLAG_Z | FLAG_S)) | (FLAG_V if bc else 0) | (val & FLAG_3) | (FLAG_5 if (val & 0x02) else 0))
  hl = (hl + 1)
  de = (de + 1)
  t += 2
  if bc:
    memptr = (pc - 1) & 0xffff # b0 or next op ?
    pc = (pc - 2) & 0xffff
    t += 5

  b = (bc >> 8) & 0xff; c = bc & 0xff
  h = (hl >> 8) & 0xff; l = hl & 0xff
  d = (de >> 8) & 0xff; e = de & 0xff

def opcode_ed_b1():  #  CPIR
  global h, l, a, b, c, f, t, pc, memptr
  hl = (h << 8) | l
  bc = (b << 8) | c

  val = mmu.read(hl)  #  u8
  result = (a - val) & 0xff  #  u8
  lookup = ((a & 0x08) >> 3) | ((val & 0x08) >> 2) | ((result & 0x08) >> 1)  #  u8
  hl = (hl + 1)
  bc = (bc - 1)  #  u16
  f = (f & FLAG_C) | ((FLAG_V | FLAG_N) if bc else FLAG_N) | halfcarrySubTable[lookup] | (0 if result else FLAG_Z) | (result & FLAG_S)  #  u8
  if (f & FLAG_H):
    result -= 1
  f |= (result & FLAG_3) | (FLAG_5 if (result & 0x02) else 0)
  t += 5
  if ((f & (FLAG_V | FLAG_Z)) == FLAG_V):
    memptr = pc
    pc = (pc - 2) & 0xffff
    t += 5
  else:
    memptr = (memptr + 1) & 0xffff

  h = (hl >> 8) & 0xff; l = hl & 0xff
  b = (bc >> 8) & 0xff; c = bc & 0xff

def opcode_ed_b2():  #  INIR
  global t, b, c, h, l, f, pc, memptr
  bc = (b << 8) | c
  hl = (h << 8) | l

  t += 1
  result = ports.read(bc)  #  u8
  mmu.write(hl, result)
  memptr = (bc + 1) & 0xffff
  b = (b - 1) & 0xff  #  u8
  hl = (hl + 1)
  initemp2 = (result + c + 1) & 0xff #  u8
  f = ((FLAG_N if (result & 0x80) else 0) | ((FLAG_H | FLAG_C) if (initemp2 < result) else 0) | (FLAG_P if parityTable[((initemp2 & 0x07) ^ b)] else 0) | sz53Table[b])
  if b:
    t += 5
    memptr = pc
    pc = (pc - 2) & 0xffff

  h = (hl >> 8) & 0xff; l = hl & 0xff

def opcode_ed_b3():  #  OTIR
  global t, h, l, b, c, f, pc, memptr
  hl = (h << 8) | l

  t += 1
  val = mmu.read(hl)  #  u8
  b = (b - 1) & 0xff
  bc = (b << 8) | c
  memptr = (bc + 1) & 0xffff
  ports.write(bc, val)
  hl = (hl + 1) & 0xffff
  h = (hl >> 8) & 0xff; l = hl & 0xff
  outitemp2 = (val + l) & 0xff  #  u8
  f = ((FLAG_N if (val & 0x80) else 0) | ((FLAG_H | FLAG_C) if (outitemp2 < val) else 0) | (FLAG_P if parityTable[((outitemp2 & 0x07) ^ b)] else 0) | (sz53Table[b]))
  if b:
    memptr = pc
    pc = (pc - 2) & 0xffff
    t += 5

def opcode_ed_b8():  #  LDDR
  global h, l, d, e, b, c, a, f, t, pc, memptr
  hl = (h << 8) | l
  de = (d << 8) | e
  bc = (b << 8) | c

  val = mmu.read(hl)  #  u8
  mmu.write(de, val)
  bc = (bc - 1)
  val += a
  f = ((f & (FLAG_C | FLAG_Z | FLAG_S)) | (FLAG_V if bc else 0) | (val & FLAG_3) | (FLAG_5 if (val & 0x02) else 0))
  hl = (hl - 1)
  de = (de - 1)
  t += 2
  if bc:
    memptr = (pc - 1) & 0xffff # b8
    pc = (pc - 2) & 0xffff
    t += 5

  b = (bc >> 8) & 0xff; c = bc & 0xff
  h = (hl >> 8) & 0xff; l = hl & 0xff
  d = (de >> 8) & 0xff; e = de & 0xff

def opcode_ed_b9():  #  CPDR
  global h, l, a, b, c, f, t, pc, memptr
  hl = (h << 8) | l
  bc = (b << 8) | c

  val = mmu.read(hl)  #  u8
  result = (a - val) & 0xff  #  u8
  lookup = ((a & 0x08) >> 3) | ((val & 0x08) >> 2) | ((result & 0x08) >> 1)  #  u8
  hl = (hl - 1)
  bc = (bc - 1)  #  u16
  f = (f & FLAG_C) | ((FLAG_V | FLAG_N) if bc else FLAG_N) | halfcarrySubTable[lookup] | (0 if result else FLAG_Z) | (result & FLAG_S)  #  u8
  if (f & FLAG_H):
    result -= 1
  f |= (result & FLAG_3) | (FLAG_5 if (result & 0x02) else 0)
  t += 5
  if ((f & (FLAG_V | FLAG_Z)) == FLAG_V):
    memptr = pc
    pc = (pc - 2) & 0xffff
    t += 5
  else:
    memptr = (memptr + 1) & 0xffff

  h = (hl >> 8) & 0xff; l = hl & 0xff
  b = (bc >> 8) & 0xff; c = bc & 0xff

def opcode_ed_ba():  #  INDR
  global t, b, c, h, l, f, pc, memptr
  bc = (b << 8) | c
  hl = (h << 8) | l

  t += 1
  result = ports.read(bc)  #  u8
  mmu.write(hl, result)
  memptr = (bc - 1) & 0xffff
  b = (b - 1) & 0xff  #  u8
  hl = (hl - 1)
  initemp2 = (result + c - 1) & 0xff #  u8
  f = ((FLAG_N if (result & 0x80) else 0) | ((FLAG_H | FLAG_C) if (initemp2 < result) else 0) | (FLAG_P if parityTable[((initemp2 & 0x07) ^ b)] else 0) | sz53Table[b])
  if b:
    t += 5
    memptr = pc
    pc = (pc - 2) & 0xffff

  h = (hl >> 8) & 0xff; l = hl & 0xff

def opcode_ed_bb():  #  OTDR
  global t, h, l, b, c, f, pc, memptr
  hl = (h << 8) | l

  t += 1
  val = mmu.read(hl)  #  u8
  b = (b - 1) & 0xff
  bc = (b << 8) | c
  memptr = (bc - 1) & 0xffff
  ports.write(bc, val)
  hl = (hl - 1) & 0xffff
  h = (hl >> 8) & 0xff; l = hl & 0xff
  outitemp2 = (val + l) & 0xff #  u8
  f = ((FLAG_N if (val & 0x80) else 0) | ((FLAG_H | FLAG_C) if (outitemp2 < val) else 0) | (FLAG_P if parityTable[((outitemp2 & 0x07) ^ b)] else 0) | (sz53Table[b]))
  if b:
    memptr = pc
    pc = (pc - 2) & 0xffff
    t += 5

def opcode_fd_9():  #  ADD IY,BC
  global iy, b, c, f, i, r, t, memptr
  bc = (b << 8) | c

  memptr = (iy + 1) & 0xffff
  rr1 = iy  #  u16
  rr2 = bc  #  u16
  add16temp = (rr1 + rr2)  #  u32
  lookup = ((rr1 & 0x0800) >> 11) | ((rr2 & 0x0800) >> 10) | ((add16temp & 0x0800) >> 9)  #  u32
  iy = add16temp & 0xffff
  f = (f & (FLAG_V | FLAG_Z | FLAG_S)) | (FLAG_C if (add16temp & 0x10000) else 0) | ((add16temp >> 8) & (FLAG_3 | FLAG_5)) | halfcarryAddTable[lookup]
  t += 7

def opcode_fd_19():  #  ADD IY,DE
  global iy, d, e, f, i, r, t, memptr
  de = (d << 8) | e

  memptr = (iy + 1) & 0xffff
  rr1 = iy  #  u16
  rr2 = de  #  u16
  add16temp = (rr1 + rr2)  #  u32
  lookup = ((rr1 & 0x0800) >> 11) | ((rr2 & 0x0800) >> 10) | ((add16temp & 0x0800) >> 9)  #  u32
  iy = add16temp & 0Xffff
  f = (f & (FLAG_V | FLAG_Z | FLAG_S)) | (FLAG_C if (add16temp & 0x10000) else 0) | ((add16temp >> 8) & (FLAG_3 | FLAG_5)) | halfcarryAddTable[lookup]
  t += 7

def opcode_fd_21():  #  LD IY,nn
  global pc, iy
  lo = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  hi = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  iy = (lo | (hi << 8))

def opcode_fd_22():  #  LD (nn),IY
  global pc, iy
  lo = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  hi = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  addr = (lo | (hi << 8))
  mmu.write(addr, (iy & 0xff))
  mmu.write((addr + 1), (iy >> 8))

def opcode_fd_23():  #  INC IY
  global iy, t
  iy = (iy + 1)
  t += 2
  iy = iy & 0xffff

def opcode_fd_24():  #  INC IYH
  global iy, f
  iyh = (iy >> 8) & 0xff

  iyh = (iyh + 1) & 0xff  #  u8
  f = (f & FLAG_C) | (FLAG_V if (iyh == 0x80) else 0) | (0 if (iyh & 0x0f) else FLAG_H) | sz53Table[iyh]

  iy = (iyh << 8) | iy & 0xff

def opcode_fd_25():  #  DEC IYH
  global iy, f
  iyh = (iy >> 8) & 0xff

  tempF = (f & FLAG_C) | (0 if (iyh & 0x0f) else FLAG_H) | FLAG_N  #  u8
  iyh = (iyh - 1) & 0xff  #  u8
  f = (tempF | (FLAG_V if (iyh == 0x7f) else 0) | sz53Table[iyh])

  iy = (iyh << 8) | iy & 0xff

def opcode_fd_26():  #  LD IYH,n
  global pc, iy

  iyh = mmu.read(pc)
  pc = (pc + 1) & 0xffff

  iy = (iyh << 8) | iy & 0xff

def opcode_fd_29():  #  ADD IY,IY
  global iy, f, t, memptr
  memptr = (iy + 1) & 0xffff
  add16temp = (iy + iy)  #  u32
  lookup = ((iy & 0x0800) >> 11) | ((iy & 0x0800) >> 10) | ((add16temp & 0x0800) >> 9)  #  u32
  iy = add16temp & 0xffff
  f = (f & (FLAG_V | FLAG_Z | FLAG_S)) | (FLAG_C if (add16temp & 0x10000) else 0) | ((add16temp >> 8) & (FLAG_3 | FLAG_5)) | halfcarryAddTable[lookup]
  t += 7

def opcode_fd_2a():  #  LD IY,(nn)
  global pc, iy
  lo = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  hi = mmu.read(pc)
  pc = (pc + 1) & 0xffff
  addr = (lo | (hi << 8))
  iy = (mmu.read(addr) | (mmu.read((addr + 1)) << 8))

def opcode_fd_2b():  #  DEC IY
  global iy, t
  iy = (iy - 1) & 0xffff
  t += 2

def opcode_fd_2c():  #  INC IYL
  global iy, f
  iyl = iy & 0xff

  iyl = (iyl + 1) & 0xff  #  u8
  f = (f & FLAG_C) | (FLAG_V if (iyl == 0x80) else 0) | (0 if (iyl & 0x0f) else FLAG_H) | sz53Table[iyl]

  iy = (iy & 0xff00) | iyl

def opcode_fd_2d():  #  DEC IYL
  global iy, f
  iyl = iy & 0xff

  tempF = (f & FLAG_C) | (0 if (iyl & 0x0f) else FLAG_H) | FLAG_N  #  u8
  iyl = (iyl - 1) & 0xff  #  u8
  f = (tempF | (FLAG_V if (iyl == 0x7f) else 0) | sz53Table[iyl])

  iy = (iy & 0xff00) | iyl

def opcode_fd_2e():  #  LD IYL,n
  global pc, iy
  iyl = iy & 0xff

  iyl = mmu.read(pc)
  pc = (pc + 1) & 0xffff

  iy = (iy & 0xff00) | iyl

def opcode_fd_34():  #  INC (IY+n)
  global iy, pc, t, f, memptr
  iyAddr = (iy + i8(mmu.read(pc)))  #  u16
  memptr = iyAddr
  t += 5
  pc = (pc + 1) & 0xffff
  val = mmu.read(iyAddr)
  result = (val + 1) & 0xff  #  u8
  t += 1
  mmu.write(iyAddr, result)
  f = (f & FLAG_C) | (FLAG_V if (result == 0x80) else 0) | (0 if (result & 0x0f) else FLAG_H) | sz53Table[result]

def opcode_fd_35():  #  DEC (IY+n)
  global iy, pc, t, f, memptr
  iyAddr = (iy + i8(mmu.read(pc)))  #  u16
  memptr = iyAddr
  t += 5
  pc = (pc + 1) & 0xffff
  val = mmu.read(iyAddr)
  tempF = (f & FLAG_C) | (0 if (val & 0x0f) else FLAG_H) | FLAG_N  #  u8
  result = (val - 1) & 0xff  #  u8
  t += 1
  mmu.write(iyAddr, result)
  f = (tempF | (FLAG_V if (result == 0x7f) else 0) | sz53Table[result])

def opcode_fd_36():  #  LD (IY+n),n
  global iy, pc, t, memptr
  iyAddr = (iy + i8(mmu.read(pc)))  #  u16
  memptr = iyAddr
  pc = (pc + 1) & 0xffff
  result = mmu.read(pc)
  t += 2
  pc = (pc + 1) & 0xffff
  mmu.write(iyAddr, result)

def opcode_fd_39():  #  ADD IY,SP
  global iy, sp, f, t, memptr
  memptr = (iy + 1) & 0xffff
  add16temp = (iy + sp)  #  u32
  lookup = ((iy & 0x0800) >> 11) | ((sp & 0x0800) >> 10) | ((add16temp & 0x0800) >> 9)  #  u32
  iy = add16temp & 0xffff
  f = (f & (FLAG_V | FLAG_Z | FLAG_S)) | (FLAG_C if (add16temp & 0x10000) else 0) | ((add16temp >> 8) & (FLAG_3 | FLAG_5)) | halfcarryAddTable[lookup]
  t += 7

def opcode_fd_44():  #  LD B,IYH
  global iy, b
  iyh = (iy >> 8) & 0xff

  b = iyh

def opcode_fd_45():  #  LD B,IYL
  global iy, b
  iyl = iy & 0xff

  b = iyl

def opcode_fd_46():  #  LD B,(IY+n)
  global iy, pc, t, b, memptr
  iyAddr = (iy + i8(mmu.read(pc)))  #  u16
  memptr = iyAddr
  t += 5
  pc = (pc + 1) & 0xffff
  b = mmu.read(iyAddr)

def opcode_fd_4c():  #  LD C,IYH
  global iy, c
  iyh = (iy >> 8) & 0xff

  c = iyh

def opcode_fd_4d():  #  LD C,IYL
  global iy, c
  iyl = iy & 0xff

  c = iyl

def opcode_fd_4e():  #  LD C,(IY+n)
  global iy, pc, t, c, memptr
  iyAddr = (iy + i8(mmu.read(pc)))  #  u16
  memptr = iyAddr
  t += 5
  pc = (pc + 1) & 0xffff
  c = mmu.read(iyAddr)

def opcode_fd_54():  #  LD D,IYH
  global iy, d
  iyh = (iy >> 8) & 0xff

  d = iyh

def opcode_fd_55():  #  LD D,IYL
  global iy, d
  iyl = iy & 0xff

  d = iyl

def opcode_fd_56():  #  LD D,(IY+n)
  global iy, pc, t, d, memptr
  iyAddr = (iy + i8(mmu.read(pc)))  #  u16
  memptr = iyAddr
  t += 5
  pc = (pc + 1) & 0xffff
  d = mmu.read(iyAddr)

def opcode_fd_5c():  #  LD E,IYH
  global iy, e
  iyh = (iy >> 8) & 0xff

  e = iyh

def opcode_fd_5d():  #  LD E,IYL
  global iy, e
  iyl = iy & 0xff

  e = iyl

def opcode_fd_5e():  #  LD E,(IY+n)
  global iy, pc, t, e, memptr
  iyAddr = (iy + i8(mmu.read(pc)))  #  u16
  memptr = iyAddr
  t += 5
  pc = (pc + 1) & 0xffff
  e = mmu.read(iyAddr)

def opcode_fd_60():  #  LD IYH,B
  global b, iy
  iyh = (iy >> 8) & 0xff

  iyh = b

  iy = (iyh << 8) | iy & 0xff

def opcode_fd_61():  #  LD IYH,C
  global c, iy
  iyh = (iy >> 8) & 0xff

  iyh = c

  iy = (iyh << 8) | iy & 0xff

def opcode_fd_62():  #  LD IYH,D
  global d, iy
  iyh = (iy >> 8) & 0xff

  iyh = d

  iy = (iyh << 8) | iy & 0xff

def opcode_fd_63():  #  LD IYH,E
  global e, iy
  iyh = (iy >> 8) & 0xff

  iyh = e

  iy = (iyh << 8) | iy & 0xff

def opcode_fd_64():  #  LD IYH,IYH
  pass

def opcode_fd_65():  #  LD IYH,IYL
  global iy
  iyl = iy & 0xff
  iyh = (iy >> 8) & 0xff

  iyh = iyl

  iy = (iyh << 8) | iy & 0xff

def opcode_fd_66():  #  LD H,(IY+n)
  global iy, pc, t, h, memptr
  iyAddr = (iy + i8(mmu.read(pc)))  #  u16
  memptr = iyAddr
  t += 5
  pc = (pc + 1) & 0xffff
  h = mmu.read(iyAddr)

def opcode_fd_67():  #  LD IYH,A
  global a, iy
  iyh = (iy >> 8) & 0xff

  iyh = a

  iy = (iyh << 8) | iy & 0xff

def opcode_fd_68():  #  LD IYL,B
  global b, iy
  iyl = iy & 0xff

  iyl = b

  iy = (iy & 0xff00) | iyl & 0xff

def opcode_fd_69():  #  LD IYL,C
  global c, iy
  iyl = iy & 0xff

  iyl = c

  c = c & 0xff
  iy = (iy & 0xff00) | iyl & 0xff

def opcode_fd_6a():  #  LD IYL,D
  global d, iy
  iyl = iy & 0xff

  iyl = d

  iy = (iy & 0xff00) | iyl & 0xff

def opcode_fd_6b():  #  LD IYL,E
  global e, iy
  iyl = iy & 0xff

  iyl = e

  iy = (iy & 0xff00) | iyl & 0xff

def opcode_fd_6c():  #  LD IYL,IYH
  global iy
  iyh = (iy >> 8) & 0xff
  iyl = iy & 0xff

  iyl = iyh

  iy = (iy & 0xff00) | iyl & 0xff

def opcode_fd_6d():  #  LD IYL,IYL
  pass

def opcode_fd_6e():  #  LD L,(IY+n)
  global iy, pc, t, l, memptr
  iyAddr = (iy + i8(mmu.read(pc)))  #  u16
  memptr = iyAddr
  t += 5
  pc = (pc + 1) & 0xffff
  l = mmu.read(iyAddr)

def opcode_fd_6f():  #  LD IYL,A
  global a, iy
  iyl = iy & 0xff

  iyl = a

  iy = (iy & 0xff00) | iyl & 0xff

def opcode_fd_70():  #  LD (IY+n),B
  global iy, pc, t, b, memptr
  iyAddr = (iy + i8(mmu.read(pc)))  #  u16
  memptr = iyAddr
  t += 5
  pc = (pc + 1) & 0xffff
  mmu.write(iyAddr, b)

def opcode_fd_71():  #  LD (IY+n),C
  global iy, pc, t, c, memptr
  iyAddr = (iy + i8(mmu.read(pc)))  #  u16
  memptr = iyAddr
  t += 5
  pc = (pc + 1) & 0xffff
  mmu.write(iyAddr, c)

def opcode_fd_72():  #  LD (IY+n),D
  global iy, pc, t, d, memptr
  iyAddr = (iy + i8(mmu.read(pc)))  #  u16
  memptr = iyAddr
  t += 5
  pc = (pc + 1) & 0xffff
  mmu.write(iyAddr, d)

def opcode_fd_73():  #  LD (IY+n),E
  global iy, pc, t, e, memptr
  iyAddr = (iy + i8(mmu.read(pc)))  #  u16
  memptr = iyAddr
  t += 5
  pc = (pc + 1) & 0xffff
  mmu.write(iyAddr, e)

def opcode_fd_74():  #  LD (IY+n),H
  global iy, pc, t, h, memptr
  iyAddr = (iy + i8(mmu.read(pc)))  #  u16
  memptr = iyAddr
  t += 5
  pc = (pc + 1) & 0xffff
  mmu.write(iyAddr, h)

def opcode_fd_75():  #  LD (IY+n),L
  global iy, pc, t, l, memptr
  iyAddr = (iy + i8(mmu.read(pc)))  #  u16
  memptr = iyAddr
  t += 5
  pc = (pc + 1) & 0xffff
  mmu.write(iyAddr, l)

def opcode_fd_77():  #  LD (IY+n),A
  global iy, pc, t, a, memptr
  iyAddr = (iy + i8(mmu.read(pc)))  #  u16
  memptr = iyAddr
  t += 5
  pc = (pc + 1) & 0xffff
  mmu.write(iyAddr, a)

def opcode_fd_7c():  #  LD A,IYH
  global iy, a
  iyh = (iy >> 8) & 0xff

  a = iyh

def opcode_fd_7d():  #  LD A,IYL
  global iy, a
  iyl = iy & 0xff

  a = iyl

def opcode_fd_7e():  #  LD A,(IY+n)
  global iy, pc, t, a, memptr
  iyAddr = (iy + i8(mmu.read(pc)))  #  u16
  memptr = iyAddr
  t += 5
  pc = (pc + 1) & 0xffff
  a = mmu.read(iyAddr)

def opcode_fd_84():  #  ADD A,IYH
  global iy, a, f
  iyh = (iy >> 8) & 0xff

  result = (iyh + a)  #  u32
  lookup = ((a & 0x88) >> 3) | ((iyh & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | halfcarryAddTable[(lookup & 0x07)] | overflowAddTable[(lookup >> 4)] | sz53Table[a]

def opcode_fd_85():  #  ADD A,IYL
  global iy, a, f
  iyl = iy & 0xff

  result = (iyl + a)  #  u32
  lookup = ((a & 0x88) >> 3) | ((iyl & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | halfcarryAddTable[(lookup & 0x07)] | overflowAddTable[(lookup >> 4)] | sz53Table[a]

def opcode_fd_86():  #  ADD A,(IY+n)
  global iy, pc, t, a, f, memptr
  iyAddr = (iy + i8(mmu.read(pc)))  #  u16
  memptr = iyAddr
  t += 5
  pc = (pc + 1) & 0xffff
  val = mmu.read(iyAddr)
  result = (val + a)  #  u32
  lookup = ((a & 0x88) >> 3) | ((val & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | halfcarryAddTable[(lookup & 0x07)] | overflowAddTable[(lookup >> 4)] | sz53Table[a]

def opcode_fd_8c():  #  ADC A,IYH
  global iy, a, f
  iyh = (iy >> 8) & 0xff

  result = ((a + iyh) + (f & FLAG_C))  #  u32
  lookup = ((a & 0x88) >> 3) | ((iyh & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | halfcarryAddTable[(lookup & 0x07)] | overflowAddTable[(lookup >> 4)] | sz53Table[a]

def opcode_fd_8d():  #  ADC A,IYL
  global iy, a, f
  iyl = iy & 0xff

  result = ((a + iyl) + (f & FLAG_C))  #  u32
  lookup = ((a & 0x88) >> 3) | ((iyl & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | halfcarryAddTable[(lookup & 0x07)] | overflowAddTable[(lookup >> 4)] | sz53Table[a]

def opcode_fd_8e():  #  ADC A,(IY+n)
  global iy, pc, t, a, f, memptr
  iyAddr = (iy + i8(mmu.read(pc)))  #  u16
  memptr = iyAddr
  t += 5
  pc = (pc + 1) & 0xffff
  val = mmu.read(iyAddr)
  result = ((a + val) + (f & FLAG_C))  #  u32
  lookup = ((a & 0x88) >> 3) | ((val & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | halfcarryAddTable[(lookup & 0x07)] | overflowAddTable[(lookup >> 4)] | sz53Table[a]

def opcode_fd_94():  #  SUB IYH
  global iy, a, f
  iyh = (iy >> 8) & 0xff

  result = (a - iyh)  #  u32
  lookup = ((a & 0x88) >> 3) | ((iyh & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | sz53Table[a]

def opcode_fd_95():  #  SUB IYL
  global iy, a, f
  iyl = iy & 0xff

  result = (a - iyl)  #  u32
  lookup = ((a & 0x88) >> 3) | ((iyl & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | sz53Table[a]

def opcode_fd_96():  #  SUB (IY+n)
  global iy, pc, t, a, f, memptr
  iyAddr = (iy + i8(mmu.read(pc)))  #  u16
  memptr = iyAddr
  t += 5
  pc = (pc + 1) & 0xffff
  val = mmu.read(iyAddr)
  result = (a - val)  #  u32
  lookup = ((a & 0x88) >> 3) | ((val & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | sz53Table[a]

def opcode_fd_9c():  #  SBC A,IYH
  global iy, a, f
  iyh = (iy >> 8) & 0xff

  result = ((a - iyh) - (f & FLAG_C))  #  u32
  lookup = ((a & 0x88) >> 3) | ((iyh & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | sz53Table[a]

def opcode_fd_9d():  #  SBC A,IYL
  global iy, a, f
  iyl = iy & 0xff

  result = ((a - iyl) - (f & FLAG_C))  #  u32
  lookup = ((a & 0x88) >> 3) | ((iyl & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | sz53Table[a]

def opcode_fd_9e():  #  SBC A,(IY+n)
  global iy, pc, t, a, f, memptr
  iyAddr = (iy + i8(mmu.read(pc)))  #  u16
  memptr = iyAddr
  t += 5
  pc = (pc + 1) & 0xffff
  val = mmu.read(iyAddr)
  result = ((a - val) - (f & FLAG_C))  #  u32
  lookup = ((a & 0x88) >> 3) | ((val & 0x88) >> 2) | ((result & 0x88) >> 1)  #  u32
  a = result & 0xff
  f = (FLAG_C if (result & 0x100) else 0) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | sz53Table[a]

def opcode_fd_a4():  #  AND IYH
  global iy, a, f
  iyh = (iy >> 8) & 0xff

  a = (a & iyh)  #  u8
  f = (FLAG_H | sz53pTable[a])

def opcode_fd_a5():  #  AND IYL
  global iy, a, f
  iyl = iy & 0xff

  a = (a & iyl)  #  u8
  f = (FLAG_H | sz53pTable[a])

def opcode_fd_a6():  #  AND (IY+n)
  global iy, pc, t, a, f, memptr
  iyAddr = (iy + i8(mmu.read(pc)))  #  u16
  memptr = iyAddr
  t += 5
  pc = (pc + 1) & 0xffff
  val = mmu.read(iyAddr)
  a = (a & val)  #  u8
  f = (FLAG_H | sz53pTable[a])

def opcode_fd_ac():  #  XOR IYH
  global iy, a, f
  iyh = (iy >> 8) & 0xff

  a = (a ^ iyh)  #  u8
  f = sz53pTable[a]

def opcode_fd_ad():  #  XOR IYL
  global iy, a, f
  iyl = iy & 0xff

  a = (a ^ iyl)  #  u8
  f = sz53pTable[a]

def opcode_fd_ae():  #  XOR (IY+n)
  global iy, pc, t, a, f, memptr
  iyAddr = (iy + i8(mmu.read(pc)))  #  u16
  memptr = iyAddr
  t += 5
  pc = (pc + 1) & 0xffff
  val = mmu.read(iyAddr)
  a = (a ^ val)  #  u8
  f = sz53pTable[a]

def opcode_fd_b4():  #  OR IYH
  global iy, a, f
  iyh = (iy >> 8) & 0xff

  a = (a | iyh)  #  u8
  f = sz53pTable[a]

def opcode_fd_b5():  #  OR IYL
  global iy, a, f
  iyl = iy & 0xff

  a = (a | iyl)  #  u8
  f = sz53pTable[a]

def opcode_fd_b6():  #  OR (IY+n)
  global iy, pc, t, a, f, memptr
  iyAddr = (iy + i8(mmu.read(pc)))  #  u16
  memptr = iyAddr
  t += 5
  pc = (pc + 1) & 0xffff
  val = mmu.read(iyAddr)
  a = (a | val)  #  u8
  f = sz53pTable[a]

def opcode_fd_bc():  #  CP IYH
  global iy, a, f
  iyh = (iy >> 8) & 0xff

  val = iyh
  cptemp = (a - val)  #  u32
  lookup = ((a & 0x88) >> 3) | ((val & 0x88) >> 2) | ((cptemp & 0x88) >> 1)  #  u32
  f = (FLAG_C if (cptemp & 0x100) else (0 if cptemp else FLAG_Z)) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | (val & (FLAG_3 | FLAG_5)) | (cptemp & FLAG_S)

def opcode_fd_bd():  #  CP IYL
  global iy, a, f
  iyl = iy & 0xff

  val = iyl
  cptemp = (a - val)  #  u32
  lookup = ((a & 0x88) >> 3) | ((val & 0x88) >> 2) | ((cptemp & 0x88) >> 1)  #  u32
  f = (FLAG_C if (cptemp & 0x100) else (0 if cptemp else FLAG_Z)) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | (val & (FLAG_3 | FLAG_5)) | (cptemp & FLAG_S)

def opcode_fd_be():  #  CP (IY+n)
  global iy, pc, t, a, f, memptr
  iyAddr = (iy + i8(mmu.read(pc)))  #  u16
  memptr = iyAddr
  t += 5
  pc = (pc + 1) & 0xffff
  val = mmu.read(iyAddr)
  cptemp = (a - val)  #  u32
  lookup = ((a & 0x88) >> 3) | ((val & 0x88) >> 2) | ((cptemp & 0x88) >> 1)  #  u32
  f = (FLAG_C if (cptemp & 0x100) else (0 if cptemp else FLAG_Z)) | FLAG_N | halfcarrySubTable[(lookup & 0x07)] | overflowSubTable[(lookup >> 4)] | (val & (FLAG_3 | FLAG_5)) | (cptemp & FLAG_S)

def opcode_fd_e1():  #  POP IY
  global sp, iy
  #lo = mmu.read(sp)
  #sp = (sp + 1) & 0xffff
  #hi = mmu.read(sp)
  #sp = (sp + 1) & 0xffff
  #iy = (lo | (hi << 8))
  sp, iy = mmu.pop16(sp)

def opcode_fd_e3():  #  EX (SP),IY
  global sp, t, iy, memptr
  lo = mmu.read(sp)
  hi = mmu.read((sp + 1))
  t += 1
  mmu.write((sp + 1), (iy >> 8))
  mmu.write(sp, (iy & 0xff))
  iy = (lo | (hi << 8))
  memptr = iy
  t += 2

def opcode_fd_e5():  #  PUSH IY
  global t, iy, sp
  #t += 1
  #sp = (sp - 1) & 0xffff
  #mmu.write(sp, (iy >> 8))
  #sp = (sp - 1) & 0xffff
  #mmu.write(sp, (iy & 0xff))
  sp = mmu.push16(sp, iy)

def opcode_fd_e9():  #  JP (IY)
  global pc, iy, t
  pc = iy

def opcode_fd_f9():  #  LD SP,IY
  global sp, iy, t
  sp = iy
  t += 2

def opcode_fdcb_0():  #  RLC (IY+n>B)
  global iy, xy_offset, t, f, b
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = ((val << 1) | (val >> 7)) & 0xff  #  u8
  f = ((result & FLAG_C) | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  b = result

  b = b & 0xff

def opcode_fdcb_1():  #  RLC (IY+n>C)
  global iy, xy_offset, t, f, c
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = ((val << 1) | (val >> 7)) & 0xff  #  u8
  f = ((result & FLAG_C) | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  c = result

  c = c & 0xff

def opcode_fdcb_2():  #  RLC (IY+n>D)
  global iy, xy_offset, t, f, d
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = ((val << 1) | (val >> 7)) & 0xff  #  u8
  f = ((result & FLAG_C) | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  d = result

  d = d & 0xff

def opcode_fdcb_3():  #  RLC (IY+n>E)
  global iy, xy_offset, t, f, e
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = ((val << 1) | (val >> 7)) & 0xff  #  u8
  f = ((result & FLAG_C) | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  e = result

  e = e & 0xff

def opcode_fdcb_4():  #  RLC (IY+n>H)
  global iy, xy_offset, t, f, h
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = ((val << 1) | (val >> 7)) & 0xff  #  u8
  f = ((result & FLAG_C) | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  h = result

  h = h & 0xff

def opcode_fdcb_5():  #  RLC (IY+n>L)
  global iy, xy_offset, t, f, l
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = ((val << 1) | (val >> 7)) & 0xff  #  u8
  f = ((result & FLAG_C) | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  l = result

  l = l & 0xff

def opcode_fdcb_6():  #  RLC (IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = ((val << 1) | (val >> 7)) & 0xff  #  u8
  f = ((result & FLAG_C) | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)


def opcode_fdcb_7():  #  RLC (IY+n>A)
  global iy, xy_offset, t, f, a
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = ((val << 1) | (val >> 7)) & 0xff  #  u8
  f = ((result & FLAG_C) | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  a = result

  a = a & 0xff

def opcode_fdcb_8():  #  RRC (IY+n>B)
  global iy, xy_offset, t, f, b
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val & FLAG_C)  #  u8
  result = ((val >> 1) | (val << 7)) & 0xff  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  b = result

  b = b & 0xff

def opcode_fdcb_9():  #  RRC (IY+n>C)
  global iy, xy_offset, t, f, c
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val & FLAG_C)  #  u8
  result = ((val >> 1) | (val << 7)) & 0xff  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  c = result

  c = c & 0xff

def opcode_fdcb_a():  #  RRC (IY+n>D)
  global iy, xy_offset, t, f, d
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val & FLAG_C)  #  u8
  result = ((val >> 1) | (val << 7)) & 0xff  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  d = result

  d = d & 0xff

def opcode_fdcb_b():  #  RRC (IY+n>E)
  global iy, xy_offset, t, f, e
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val & FLAG_C)  #  u8
  result = ((val >> 1) | (val << 7)) & 0xff  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  e = result

  e = e & 0xff

def opcode_fdcb_c():  #  RRC (IY+n>H)
  global iy, xy_offset, t, f, h
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val & FLAG_C)  #  u8
  result = ((val >> 1) | (val << 7)) & 0xff  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  h = result

  h = h & 0xff

def opcode_fdcb_d():  #  RRC (IY+n>L)
  global iy, xy_offset, t, f, l
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val & FLAG_C)  #  u8
  result = ((val >> 1) | (val << 7)) & 0xff  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  l = result

  l = l & 0xff

def opcode_fdcb_e():  #  RRC (IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val & FLAG_C)  #  u8
  result = ((val >> 1) | (val << 7)) & 0xff  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)


def opcode_fdcb_f():  #  RRC (IY+n>A)
  global iy, xy_offset, t, f, a
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val & FLAG_C)  #  u8
  result = ((val >> 1) | (val << 7)) & 0xff  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  a = result

  a = a & 0xff

def opcode_fdcb_10():  #  RL (IY+n>B)
  global iy, xy_offset, t, f, b
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = ((val << 1) | (f & FLAG_C)) & 0xff  #  u8
  f = ((val >> 7) | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  b = result

  b = b & 0xff

def opcode_fdcb_11():  #  RL (IY+n>C)
  global iy, xy_offset, t, f, c
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = ((val << 1) | (f & FLAG_C)) & 0xff  #  u8
  f = ((val >> 7) | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  c = result

  c = c & 0xff

def opcode_fdcb_12():  #  RL (IY+n>D)
  global iy, xy_offset, t, f, d
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = ((val << 1) | (f & FLAG_C)) & 0xff  #  u8
  f = ((val >> 7) | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  d = result

  d = d & 0xff

def opcode_fdcb_13():  #  RL (IY+n>E)
  global iy, xy_offset, t, f, e
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = ((val << 1) | (f & FLAG_C)) & 0xff  #  u8
  f = ((val >> 7) | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  e = result

  e = e & 0xff

def opcode_fdcb_14():  #  RL (IY+n>H)
  global iy, xy_offset, t, f, h
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = ((val << 1) | (f & FLAG_C)) & 0xff  #  u8
  f = ((val >> 7) | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  h = result

  h = h & 0xff

def opcode_fdcb_15():  #  RL (IY+n>L)
  global iy, xy_offset, t, f, l
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = ((val << 1) | (f & FLAG_C)) & 0xff  #  u8
  f = ((val >> 7) | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  l = result

  l = l & 0xff

def opcode_fdcb_16():  #  RL (IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = ((val << 1) | (f & FLAG_C)) & 0xff  #  u8
  f = ((val >> 7) | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)


def opcode_fdcb_17():  #  RL (IY+n>A)
  global iy, xy_offset, t, f, a
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = ((val << 1) | (f & FLAG_C)) & 0xff  #  u8
  f = ((val >> 7) | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  a = result

  a = a & 0xff

def opcode_fdcb_18():  #  RR (IY+n>B)
  global iy, xy_offset, t, f, b
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = ((val >> 1) | (f << 7)) & 0xff  #  u8
  f = ((val & FLAG_C) | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  b = result

  b = b & 0xff

def opcode_fdcb_19():  #  RR (IY+n>C)
  global iy, xy_offset, t, f, c
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = ((val >> 1) | (f << 7)) & 0xff  #  u8
  f = ((val & FLAG_C) | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  c = result

  c = c & 0xff

def opcode_fdcb_1a():  #  RR (IY+n>D)
  global iy, xy_offset, t, f, d
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = ((val >> 1) | (f << 7)) & 0xff  #  u8
  f = ((val & FLAG_C) | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  d = result

  d = d & 0xff

def opcode_fdcb_1b():  #  RR (IY+n>E)
  global iy, xy_offset, t, f, e
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = ((val >> 1) | (f << 7)) & 0xff  #  u8
  f = ((val & FLAG_C) | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  e = result

  e = e & 0xff

def opcode_fdcb_1c():  #  RR (IY+n>H)
  global iy, xy_offset, t, f, h
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = ((val >> 1) | (f << 7)) & 0xff  #  u8
  f = ((val & FLAG_C) | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  h = result

  h = h & 0xff

def opcode_fdcb_1d():  #  RR (IY+n>L)
  global iy, xy_offset, t, f, l
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = ((val >> 1) | (f << 7)) & 0xff  #  u8
  f = ((val & FLAG_C) | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  l = result

  l = l & 0xff

def opcode_fdcb_1e():  #  RR (IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = ((val >> 1) | (f << 7)) & 0xff  #  u8
  f = ((val & FLAG_C) | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)


def opcode_fdcb_1f():  #  RR (IY+n>A)
  global iy, xy_offset, t, f, a
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = ((val >> 1) | (f << 7)) & 0xff  #  u8
  f = ((val & FLAG_C) | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  a = result

  a = a & 0xff

def opcode_fdcb_20():  #  SLA (IY+n>B)
  global iy, xy_offset, t, f, b
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val >> 7)  #  u8
  result = (val << 1) & 0xff  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  b = result

  b = b & 0xff

def opcode_fdcb_21():  #  SLA (IY+n>C)
  global iy, xy_offset, t, f, c
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val >> 7)  #  u8
  result = (val << 1) & 0xff  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  c = result

  c = c & 0xff

def opcode_fdcb_22():  #  SLA (IY+n>D)
  global iy, xy_offset, t, f, d
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val >> 7)  #  u8
  result = (val << 1) & 0xff  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  d = result

  d = d & 0xff

def opcode_fdcb_23():  #  SLA (IY+n>E)
  global iy, xy_offset, t, f, e
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val >> 7)  #  u8
  result = (val << 1) & 0xff  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  e = result

  e = e & 0xff

def opcode_fdcb_24():  #  SLA (IY+n>H)
  global iy, xy_offset, t, f, h
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val >> 7)  #  u8
  result = (val << 1) & 0xff  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  h = result

  h = h & 0xff

def opcode_fdcb_25():  #  SLA (IY+n>L)
  global iy, xy_offset, t, f, l
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val >> 7)  #  u8
  result = (val << 1) & 0xff  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  l = result

  l = l & 0xff

def opcode_fdcb_26():  #  SLA (IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val >> 7)  #  u8
  result = (val << 1) & 0xff  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)


def opcode_fdcb_27():  #  SLA (IY+n>A)
  global iy, xy_offset, t, f, a
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val >> 7)  #  u8
  result = (val << 1) & 0xff  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  a = result

  a = a & 0xff

def opcode_fdcb_28():  #  SRA (IY+n>B)
  global iy, xy_offset, t, f, b
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val & FLAG_C)  #  u8
  result = ((val & 0x80) | (val >> 1))  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  b = result

  b = b & 0xff

def opcode_fdcb_29():  #  SRA (IY+n>C)
  global iy, xy_offset, t, f, c
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val & FLAG_C)  #  u8
  result = ((val & 0x80) | (val >> 1))  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  c = result

  c = c & 0xff

def opcode_fdcb_2a():  #  SRA (IY+n>D)
  global iy, xy_offset, t, f, d
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val & FLAG_C)  #  u8
  result = ((val & 0x80) | (val >> 1))  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  d = result

  d = d & 0xff

def opcode_fdcb_2b():  #  SRA (IY+n>E)
  global iy, xy_offset, t, f, e
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val & FLAG_C)  #  u8
  result = ((val & 0x80) | (val >> 1))  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  e = result

  e = e & 0xff

def opcode_fdcb_2c():  #  SRA (IY+n>H)
  global iy, xy_offset, t, f, h
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val & FLAG_C)  #  u8
  result = ((val & 0x80) | (val >> 1))  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  h = result

  h = h & 0xff

def opcode_fdcb_2d():  #  SRA (IY+n>L)
  global iy, xy_offset, t, f, l
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val & FLAG_C)  #  u8
  result = ((val & 0x80) | (val >> 1))  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  l = result

  l = l & 0xff

def opcode_fdcb_2e():  #  SRA (IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val & FLAG_C)  #  u8
  result = ((val & 0x80) | (val >> 1))  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)


def opcode_fdcb_2f():  #  SRA (IY+n>A)
  global iy, xy_offset, t, f, a
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val & FLAG_C)  #  u8
  result = ((val & 0x80) | (val >> 1))  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  a = result

  a = a & 0xff

def opcode_fdcb_30():  #  SLL (IY+n>B)
  global iy, xy_offset, t, f, b
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val >> 7)  #  u8
  result = ((val << 1) | 0x01) &0xff #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  b = result

  b = b & 0xff

def opcode_fdcb_31():  #  SLL (IY+n>C)
  global iy, xy_offset, t, f, c
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val >> 7)  #  u8
  result = ((val << 1) | 0x01) &0xff #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  c = result

  c = c & 0xff

def opcode_fdcb_32():  #  SLL (IY+n>D)
  global iy, xy_offset, t, f, d
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val >> 7)  #  u8
  result = ((val << 1) | 0x01) &0xff #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  d = result

  d = d & 0xff

def opcode_fdcb_33():  #  SLL (IY+n>E)
  global iy, xy_offset, t, f, e
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val >> 7)  #  u8
  result = ((val << 1) | 0x01) &0xff #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  e = result

  e = e & 0xff

def opcode_fdcb_34():  #  SLL (IY+n>H)
  global iy, xy_offset, t, f, h
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val >> 7)  #  u8
  result = ((val << 1) | 0x01) &0xff #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  h = result

  h = h & 0xff

def opcode_fdcb_35():  #  SLL (IY+n>L)
  global iy, xy_offset, t, f, l
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val >> 7)  #  u8
  result = ((val << 1) | 0x01) &0xff #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  l = result

  l = l & 0xff

def opcode_fdcb_36():  #  SLL (IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val >> 7)  #  u8
  result = ((val << 1) | 0x01) &0xff #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)


def opcode_fdcb_37():  #  SLL (IY+n>A)
  global iy, xy_offset, t, f, a
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val >> 7)  #  u8
  result = ((val << 1) | 0x01) &0xff #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  a = result

  a = a & 0xff

def opcode_fdcb_38():  #  SRL (IY+n>B)
  global iy, xy_offset, t, f, b
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val & FLAG_C)  #  u8
  result = (val >> 1)  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  b = result

  b = b & 0xff

def opcode_fdcb_39():  #  SRL (IY+n>C)
  global iy, xy_offset, t, f, c
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val & FLAG_C)  #  u8
  result = (val >> 1)  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  c = result

  c = c & 0xff

def opcode_fdcb_3a():  #  SRL (IY+n>D)
  global iy, xy_offset, t, f, d
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val & FLAG_C)  #  u8
  result = (val >> 1)  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  d = result

  d = d & 0xff

def opcode_fdcb_3b():  #  SRL (IY+n>E)
  global iy, xy_offset, t, f, e
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val & FLAG_C)  #  u8
  result = (val >> 1)  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  e = result

  e = e & 0xff

def opcode_fdcb_3c():  #  SRL (IY+n>H)
  global iy, xy_offset, t, f, h
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val & FLAG_C)  #  u8
  result = (val >> 1)  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  h = result

  h = h & 0xff

def opcode_fdcb_3d():  #  SRL (IY+n>L)
  global iy, xy_offset, t, f, l
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val & FLAG_C)  #  u8
  result = (val >> 1)  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  l = result

  l = l & 0xff

def opcode_fdcb_3e():  #  SRL (IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val & FLAG_C)  #  u8
  result = (val >> 1)  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)


def opcode_fdcb_3f():  #  SRL (IY+n>A)
  global iy, xy_offset, t, f, a
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (val & FLAG_C)  #  u8
  result = (val >> 1)  #  u8
  f = (F | sz53pTable[result])
  t += 5
  mmu.write(iyAddr, result)
  a = result

  a = a & 0xff

def opcode_fdcb_40():  #  BIT 0,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 1)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_41():  #  BIT 0,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 1)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5

def opcode_fdcb_42():  #  BIT 0,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 1)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_43():  #  BIT 0,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 1)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_44():  #  BIT 0,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 1)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_45():  #  BIT 0,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 1)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_46():  #  BIT 0,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 1)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_47():  #  BIT 0,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 1)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_48():  #  BIT 1,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 2)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_49():  #  BIT 1,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 2)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_4a():  #  BIT 1,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 2)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_4b():  #  BIT 1,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 2)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_4c():  #  BIT 1,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 2)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_4d():  #  BIT 1,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 2)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_4e():  #  BIT 1,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 2)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_4f():  #  BIT 1,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 2)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_50():  #  BIT 2,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 4)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_51():  #  BIT 2,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 4)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_52():  #  BIT 2,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 4)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_53():  #  BIT 2,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 4)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_54():  #  BIT 2,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 4)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_55():  #  BIT 2,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 4)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_56():  #  BIT 2,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 4)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_57():  #  BIT 2,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 4)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_58():  #  BIT 3,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 8)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_59():  #  BIT 3,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 8)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_5a():  #  BIT 3,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 8)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_5b():  #  BIT 3,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 8)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_5c():  #  BIT 3,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 8)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_5d():  #  BIT 3,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 8)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_5e():  #  BIT 3,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 8)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_5f():  #  BIT 3,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 8)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_60():  #  BIT 4,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 16)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_61():  #  BIT 4,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 16)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_62():  #  BIT 4,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 16)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_63():  #  BIT 4,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 16)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_64():  #  BIT 4,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 16)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_65():  #  BIT 4,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 16)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_66():  #  BIT 4,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 16)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_67():  #  BIT 4,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 16)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_68():  #  BIT 5,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 32)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_69():  #  BIT 5,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 32)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_6a():  #  BIT 5,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 32)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_6b():  #  BIT 5,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 32)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_6c():  #  BIT 5,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 32)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_6d():  #  BIT 5,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 32)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_6e():  #  BIT 5,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 32)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_6f():  #  BIT 5,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 32)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_70():  #  BIT 6,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 64)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_71():  #  BIT 6,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 64)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_72():  #  BIT 6,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 64)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_73():  #  BIT 6,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 64)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_74():  #  BIT 6,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 64)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_75():  #  BIT 6,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 64)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_76():  #  BIT 6,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 64)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_77():  #  BIT 6,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 64)):
    F |= (FLAG_P | FLAG_Z)
  f = F
  t += 5


def opcode_fdcb_78():  #  BIT 7,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 128)):
    F |= (FLAG_P | FLAG_Z)
  if (val & 0x80):
    F |= FLAG_S
  f = F
  t += 5


def opcode_fdcb_79():  #  BIT 7,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 128)):
    F |= (FLAG_P | FLAG_Z)
  if (val & 0x80):
    F |= FLAG_S
  f = F
  t += 5


def opcode_fdcb_7a():  #  BIT 7,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 128)):
    F |= (FLAG_P | FLAG_Z)
  if (val & 0x80):
    F |= FLAG_S
  f = F
  t += 5


def opcode_fdcb_7b():  #  BIT 7,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 128)):
    F |= (FLAG_P | FLAG_Z)
  if (val & 0x80):
    F |= FLAG_S
  f = F
  t += 5


def opcode_fdcb_7c():  #  BIT 7,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 128)):
    F |= (FLAG_P | FLAG_Z)
  if (val & 0x80):
    F |= FLAG_S
  f = F
  t += 5


def opcode_fdcb_7d():  #  BIT 7,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 128)):
    F |= (FLAG_P | FLAG_Z)
  if (val & 0x80):
    F |= FLAG_S
  f = F
  t += 5


def opcode_fdcb_7e():  #  BIT 7,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 128)):
    F |= (FLAG_P | FLAG_Z)
  if (val & 0x80):
    F |= FLAG_S
  f = F
  t += 5


def opcode_fdcb_7f():  #  BIT 7,(IY+n)
  global iy, xy_offset, t, f
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  F = (f & FLAG_C) | FLAG_H | ((iyAddr >> 8) & (FLAG_3 | FLAG_5))  #  u8
  if (not (val & 128)):
    F |= (FLAG_P | FLAG_Z)
  if (val & 0x80):
    F |= FLAG_S
  f = F
  t += 5


def opcode_fdcb_80():  #  RES 0,(IY+n>B)
  global iy, xy_offset, t, b
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 254)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  b = result

  b = b & 0xff

def opcode_fdcb_81():  #  RES 0,(IY+n>C)
  global iy, xy_offset, t, c
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 254)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  c = result

  c = c & 0xff

def opcode_fdcb_82():  #  RES 0,(IY+n>D)
  global iy, xy_offset, t, d
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 254)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  d = result

  d = d & 0xff

def opcode_fdcb_83():  #  RES 0,(IY+n>E)
  global iy, xy_offset, t, e
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 254)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  e = result

  e = e & 0xff

def opcode_fdcb_84():  #  RES 0,(IY+n>H)
  global iy, xy_offset, t, h
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 254)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  h = result

  h = h & 0xff

def opcode_fdcb_85():  #  RES 0,(IY+n>L)
  global iy, xy_offset, t, l
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 254)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  l = result

  l = l & 0xff

def opcode_fdcb_86():  #  RES 0,(IY+n)
  global iy, xy_offset, t
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 254)  #  u8
  t += 5
  mmu.write(iyAddr, result)


def opcode_fdcb_87():  #  RES 0,(IY+n>A)
  global iy, xy_offset, t, a
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 254)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  a = result

  a = a & 0xff

def opcode_fdcb_88():  #  RES 1,(IY+n>B)
  global iy, xy_offset, t, b
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 253)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  b = result

  b = b & 0xff

def opcode_fdcb_89():  #  RES 1,(IY+n>C)
  global iy, xy_offset, t, c
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 253)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  c = result

  c = c & 0xff

def opcode_fdcb_8a():  #  RES 1,(IY+n>D)
  global iy, xy_offset, t, d
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 253)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  d = result

  d = d & 0xff

def opcode_fdcb_8b():  #  RES 1,(IY+n>E)
  global iy, xy_offset, t, e
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 253)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  e = result

  e = e & 0xff

def opcode_fdcb_8c():  #  RES 1,(IY+n>H)
  global iy, xy_offset, t, h
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 253)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  h = result

  h = h & 0xff

def opcode_fdcb_8d():  #  RES 1,(IY+n>L)
  global iy, xy_offset, t, l
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 253)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  l = result

  l = l & 0xff

def opcode_fdcb_8e():  #  RES 1,(IY+n)
  global iy, xy_offset, t
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 253)  #  u8
  t += 5
  mmu.write(iyAddr, result)


def opcode_fdcb_8f():  #  RES 1,(IY+n>A)
  global iy, xy_offset, t, a
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 253)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  a = result

  a = a & 0xff

def opcode_fdcb_90():  #  RES 2,(IY+n>B)
  global iy, xy_offset, t, b
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 251)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  b = result

  b = b & 0xff

def opcode_fdcb_91():  #  RES 2,(IY+n>C)
  global iy, xy_offset, t, c
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 251)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  c = result

  c = c & 0xff

def opcode_fdcb_92():  #  RES 2,(IY+n>D)
  global iy, xy_offset, t, d
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 251)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  d = result

  d = d & 0xff

def opcode_fdcb_93():  #  RES 2,(IY+n>E)
  global iy, xy_offset, t, e
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 251)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  e = result

  e = e & 0xff

def opcode_fdcb_94():  #  RES 2,(IY+n>H)
  global iy, xy_offset, t, h
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 251)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  h = result

  h = h & 0xff

def opcode_fdcb_95():  #  RES 2,(IY+n>L)
  global iy, xy_offset, t, l
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 251)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  l = result

  l = l & 0xff

def opcode_fdcb_96():  #  RES 2,(IY+n)
  global iy, xy_offset, t
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 251)  #  u8
  t += 5
  mmu.write(iyAddr, result)


def opcode_fdcb_97():  #  RES 2,(IY+n>A)
  global iy, xy_offset, t, a
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 251)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  a = result

  a = a & 0xff

def opcode_fdcb_98():  #  RES 3,(IY+n>B)
  global iy, xy_offset, t, b
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 247)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  b = result

  b = b & 0xff

def opcode_fdcb_99():  #  RES 3,(IY+n>C)
  global iy, xy_offset, t, c
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 247)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  c = result

  c = c & 0xff

def opcode_fdcb_9a():  #  RES 3,(IY+n>D)
  global iy, xy_offset, t, d
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 247)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  d = result

  d = d & 0xff

def opcode_fdcb_9b():  #  RES 3,(IY+n>E)
  global iy, xy_offset, t, e
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 247)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  e = result

  e = e & 0xff

def opcode_fdcb_9c():  #  RES 3,(IY+n>H)
  global iy, xy_offset, t, h
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 247)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  h = result

  h = h & 0xff

def opcode_fdcb_9d():  #  RES 3,(IY+n>L)
  global iy, xy_offset, t, l
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 247)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  l = result

  l = l & 0xff

def opcode_fdcb_9e():  #  RES 3,(IY+n)
  global iy, xy_offset, t
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 247)  #  u8
  t += 5
  mmu.write(iyAddr, result)


def opcode_fdcb_9f():  #  RES 3,(IY+n>A)
  global iy, xy_offset, t, a
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 247)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  a = result

  a = a & 0xff

def opcode_fdcb_a0():  #  RES 4,(IY+n>B)
  global iy, xy_offset, t, b
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 239)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  b = result

  b = b & 0xff

def opcode_fdcb_a1():  #  RES 4,(IY+n>C)
  global iy, xy_offset, t, c
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 239)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  c = result

  c = c & 0xff

def opcode_fdcb_a2():  #  RES 4,(IY+n>D)
  global iy, xy_offset, t, d
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 239)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  d = result

  d = d & 0xff

def opcode_fdcb_a3():  #  RES 4,(IY+n>E)
  global iy, xy_offset, t, e
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 239)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  e = result

  e = e & 0xff

def opcode_fdcb_a4():  #  RES 4,(IY+n>H)
  global iy, xy_offset, t, h
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 239)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  h = result

  h = h & 0xff

def opcode_fdcb_a5():  #  RES 4,(IY+n>L)
  global iy, xy_offset, t, l
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 239)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  l = result

  l = l & 0xff

def opcode_fdcb_a6():  #  RES 4,(IY+n)
  global iy, xy_offset, t
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 239)  #  u8
  t += 5
  mmu.write(iyAddr, result)


def opcode_fdcb_a7():  #  RES 4,(IY+n>A)
  global iy, xy_offset, t, a
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 239)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  a = result

  a = a & 0xff

def opcode_fdcb_a8():  #  RES 5,(IY+n>B)
  global iy, xy_offset, t, b
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 223)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  b = result

  b = b & 0xff

def opcode_fdcb_a9():  #  RES 5,(IY+n>C)
  global iy, xy_offset, t, c
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 223)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  c = result

  c = c & 0xff

def opcode_fdcb_aa():  #  RES 5,(IY+n>D)
  global iy, xy_offset, t, d
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 223)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  d = result

  d = d & 0xff

def opcode_fdcb_ab():  #  RES 5,(IY+n>E)
  global iy, xy_offset, t, e
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 223)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  e = result

  e = e & 0xff

def opcode_fdcb_ac():  #  RES 5,(IY+n>H)
  global iy, xy_offset, t, h
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 223)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  h = result

  h = h & 0xff

def opcode_fdcb_ad():  #  RES 5,(IY+n>L)
  global iy, xy_offset, t, l
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 223)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  l = result

  l = l & 0xff

def opcode_fdcb_ae():  #  RES 5,(IY+n)
  global iy, xy_offset, t
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 223)  #  u8
  t += 5
  mmu.write(iyAddr, result)


def opcode_fdcb_af():  #  RES 5,(IY+n>A)
  global iy, xy_offset, t, a
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 223)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  a = result

  a = a & 0xff

def opcode_fdcb_b0():  #  RES 6,(IY+n>B)
  global iy, xy_offset, t, b
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 191)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  b = result

  b = b & 0xff

def opcode_fdcb_b1():  #  RES 6,(IY+n>C)
  global iy, xy_offset, t, c
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 191)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  c = result

  c = c & 0xff

def opcode_fdcb_b2():  #  RES 6,(IY+n>D)
  global iy, xy_offset, t, d
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 191)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  d = result

  d = d & 0xff

def opcode_fdcb_b3():  #  RES 6,(IY+n>E)
  global iy, xy_offset, t, e
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 191)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  e = result

  e = e & 0xff

def opcode_fdcb_b4():  #  RES 6,(IY+n>H)
  global iy, xy_offset, t, h
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 191)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  h = result

  h = h & 0xff

def opcode_fdcb_b5():  #  RES 6,(IY+n>L)
  global iy, xy_offset, t, l
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 191)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  l = result

  l = l & 0xff

def opcode_fdcb_b6():  #  RES 6,(IY+n)
  global iy, xy_offset, t
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 191)  #  u8
  t += 5
  mmu.write(iyAddr, result)


def opcode_fdcb_b7():  #  RES 6,(IY+n>A)
  global iy, xy_offset, t, a
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 191)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  a = result

  a = a & 0xff

def opcode_fdcb_b8():  #  RES 7,(IY+n>B)
  global iy, xy_offset, t, b
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 127)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  b = result

  b = b & 0xff

def opcode_fdcb_b9():  #  RES 7,(IY+n>C)
  global iy, xy_offset, t, c
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 127)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  c = result

  c = c & 0xff

def opcode_fdcb_ba():  #  RES 7,(IY+n>D)
  global iy, xy_offset, t, d
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 127)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  d = result

  d = d & 0xff

def opcode_fdcb_bb():  #  RES 7,(IY+n>E)
  global iy, xy_offset, t, e
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 127)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  e = result

  e = e & 0xff

def opcode_fdcb_bc():  #  RES 7,(IY+n>H)
  global iy, xy_offset, t, h
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 127)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  h = result

  h = h & 0xff

def opcode_fdcb_bd():  #  RES 7,(IY+n>L)
  global iy, xy_offset, t, l
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 127)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  l = result

  l = l & 0xff

def opcode_fdcb_be():  #  RES 7,(IY+n)
  global iy, xy_offset, t
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 127)  #  u8
  t += 5
  mmu.write(iyAddr, result)


def opcode_fdcb_bf():  #  RES 7,(IY+n>A)
  global iy, xy_offset, t, a
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val & 127)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  a = result

  a = a & 0xff

def opcode_fdcb_c0():  #  SET 0,(IY+n>B)
  global iy, xy_offset, t, b
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 1)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  b = result

  b = b & 0xff

def opcode_fdcb_c1():  #  SET 0,(IY+n>C)
  global iy, xy_offset, t, c
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 1)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  c = result

  c = c & 0xff

def opcode_fdcb_c2():  #  SET 0,(IY+n>D)
  global iy, xy_offset, t, d
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 1)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  d = result

  d = d & 0xff

def opcode_fdcb_c3():  #  SET 0,(IY+n>E)
  global iy, xy_offset, t, e
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 1)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  e = result

  e = e & 0xff

def opcode_fdcb_c4():  #  SET 0,(IY+n>H)
  global iy, xy_offset, t, h
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 1)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  h = result

  h = h & 0xff

def opcode_fdcb_c5():  #  SET 0,(IY+n>L)
  global iy, xy_offset, t, l
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 1)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  l = result

  l = l & 0xff

def opcode_fdcb_c6():  #  SET 0,(IY+n)
  global iy, xy_offset, t
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 1)  #  u8
  t += 5
  mmu.write(iyAddr, result)


def opcode_fdcb_c7():  #  SET 0,(IY+n>A)
  global iy, xy_offset, t, a
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 1)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  a = result

  a = a & 0xff

def opcode_fdcb_c8():  #  SET 1,(IY+n>B)
  global iy, xy_offset, t, b
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 2)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  b = result

  b = b & 0xff

def opcode_fdcb_c9():  #  SET 1,(IY+n>C)
  global iy, xy_offset, t, c
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 2)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  c = result

  c = c & 0xff

def opcode_fdcb_ca():  #  SET 1,(IY+n>D)
  global iy, xy_offset, t, d
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 2)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  d = result

  d = d & 0xff

def opcode_fdcb_cb():  #  SET 1,(IY+n>E)
  global iy, xy_offset, t, e
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 2)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  e = result

  e = e & 0xff

def opcode_fdcb_cc():  #  SET 1,(IY+n>H)
  global iy, xy_offset, t, h
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 2)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  h = result

  h = h & 0xff

def opcode_fdcb_cd():  #  SET 1,(IY+n>L)
  global iy, xy_offset, t, l
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 2)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  l = result

  l = l & 0xff

def opcode_fdcb_ce():  #  SET 1,(IY+n)
  global iy, xy_offset, t
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 2)  #  u8
  t += 5
  mmu.write(iyAddr, result)


def opcode_fdcb_cf():  #  SET 1,(IY+n>A)
  global iy, xy_offset, t, a
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 2)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  a = result

  a = a & 0xff

def opcode_fdcb_d0():  #  SET 2,(IY+n>B)
  global iy, xy_offset, t, b
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 4)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  b = result

  b = b & 0xff

def opcode_fdcb_d1():  #  SET 2,(IY+n>C)
  global iy, xy_offset, t, c
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 4)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  c = result

  c = c & 0xff

def opcode_fdcb_d2():  #  SET 2,(IY+n>D)
  global iy, xy_offset, t, d
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 4)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  d = result

  d = d & 0xff

def opcode_fdcb_d3():  #  SET 2,(IY+n>E)
  global iy, xy_offset, t, e
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 4)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  e = result

  e = e & 0xff

def opcode_fdcb_d4():  #  SET 2,(IY+n>H)
  global iy, xy_offset, t, h
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 4)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  h = result

  h = h & 0xff

def opcode_fdcb_d5():  #  SET 2,(IY+n>L)
  global iy, xy_offset, t, l
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 4)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  l = result

  l = l & 0xff

def opcode_fdcb_d6():  #  SET 2,(IY+n)
  global iy, xy_offset, t
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 4)  #  u8
  t += 5
  mmu.write(iyAddr, result)


def opcode_fdcb_d7():  #  SET 2,(IY+n>A)
  global iy, xy_offset, t, a
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 4)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  a = result

  a = a & 0xff

def opcode_fdcb_d8():  #  SET 3,(IY+n>B)
  global iy, xy_offset, t, b
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 8)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  b = result

  b = b & 0xff

def opcode_fdcb_d9():  #  SET 3,(IY+n>C)
  global iy, xy_offset, t, c
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 8)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  c = result

  c = c & 0xff

def opcode_fdcb_da():  #  SET 3,(IY+n>D)
  global iy, xy_offset, t, d
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 8)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  d = result

  d = d & 0xff

def opcode_fdcb_db():  #  SET 3,(IY+n>E)
  global iy, xy_offset, t, e
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 8)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  e = result

  e = e & 0xff

def opcode_fdcb_dc():  #  SET 3,(IY+n>H)
  global iy, xy_offset, t, h
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 8)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  h = result

  h = h & 0xff

def opcode_fdcb_dd():  #  SET 3,(IY+n>L)
  global iy, xy_offset, t, l
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 8)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  l = result

  l = l & 0xff

def opcode_fdcb_de():  #  SET 3,(IY+n)
  global iy, xy_offset, t
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 8)  #  u8
  t += 5
  mmu.write(iyAddr, result)


def opcode_fdcb_df():  #  SET 3,(IY+n>A)
  global iy, xy_offset, t, a
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 8)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  a = result

  a = a & 0xff

def opcode_fdcb_e0():  #  SET 4,(IY+n>B)
  global iy, xy_offset, t, b
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 16)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  b = result

  b = b & 0xff

def opcode_fdcb_e1():  #  SET 4,(IY+n>C)
  global iy, xy_offset, t, c
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 16)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  c = result

  c = c & 0xff

def opcode_fdcb_e2():  #  SET 4,(IY+n>D)
  global iy, xy_offset, t, d
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 16)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  d = result

  d = d & 0xff

def opcode_fdcb_e3():  #  SET 4,(IY+n>E)
  global iy, xy_offset, t, e
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 16)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  e = result

  e = e & 0xff

def opcode_fdcb_e4():  #  SET 4,(IY+n>H)
  global iy, xy_offset, t, h
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 16)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  h = result

  h = h & 0xff

def opcode_fdcb_e5():  #  SET 4,(IY+n>L)
  global iy, xy_offset, t, l
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 16)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  l = result

  l = l & 0xff

def opcode_fdcb_e6():  #  SET 4,(IY+n)
  global iy, xy_offset, t
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 16)  #  u8
  t += 5
  mmu.write(iyAddr, result)


def opcode_fdcb_e7():  #  SET 4,(IY+n>A)
  global iy, xy_offset, t, a
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 16)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  a = result

  a = a & 0xff

def opcode_fdcb_e8():  #  SET 5,(IY+n>B)
  global iy, xy_offset, t, b
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 32)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  b = result

  b = b & 0xff

def opcode_fdcb_e9():  #  SET 5,(IY+n>C)
  global iy, xy_offset, t, c
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 32)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  c = result

  c = c & 0xff

def opcode_fdcb_ea():  #  SET 5,(IY+n>D)
  global iy, xy_offset, t, d
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 32)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  d = result

  d = d & 0xff

def opcode_fdcb_eb():  #  SET 5,(IY+n>E)
  global iy, xy_offset, t, e
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 32)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  e = result

  e = e & 0xff

def opcode_fdcb_ec():  #  SET 5,(IY+n>H)
  global iy, xy_offset, t, h
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 32)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  h = result

  h = h & 0xff

def opcode_fdcb_ed():  #  SET 5,(IY+n>L)
  global iy, xy_offset, t, l
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 32)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  l = result

  l = l & 0xff

def opcode_fdcb_ee():  #  SET 5,(IY+n)
  global iy, xy_offset, t
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 32)  #  u8
  t += 5
  mmu.write(iyAddr, result)


def opcode_fdcb_ef():  #  SET 5,(IY+n>A)
  global iy, xy_offset, t, a
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 32)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  a = result

  a = a & 0xff

def opcode_fdcb_f0():  #  SET 6,(IY+n>B)
  global iy, xy_offset, t, b
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 64)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  b = result

  b = b & 0xff

def opcode_fdcb_f1():  #  SET 6,(IY+n>C)
  global iy, xy_offset, t, c
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 64)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  c = result

  c = c & 0xff

def opcode_fdcb_f2():  #  SET 6,(IY+n>D)
  global iy, xy_offset, t, d
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 64)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  d = result

  d = d & 0xff

def opcode_fdcb_f3():  #  SET 6,(IY+n>E)
  global iy, xy_offset, t, e
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 64)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  e = result

  e = e & 0xff

def opcode_fdcb_f4():  #  SET 6,(IY+n>H)
  global iy, xy_offset, t, h
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 64)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  h = result

  h = h & 0xff

def opcode_fdcb_f5():  #  SET 6,(IY+n>L)
  global iy, xy_offset, t, l
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 64)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  l = result

  l = l & 0xff

def opcode_fdcb_f6():  #  SET 6,(IY+n)
  global iy, xy_offset, t
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 64)  #  u8
  t += 5
  mmu.write(iyAddr, result)


def opcode_fdcb_f7():  #  SET 6,(IY+n>A)
  global iy, xy_offset, t, a
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 64)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  a = result

  a = a & 0xff

def opcode_fdcb_f8():  #  SET 7,(IY+n>B)
  global iy, xy_offset, t, b
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 128)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  b = result

  b = b & 0xff

def opcode_fdcb_f9():  #  SET 7,(IY+n>C)
  global iy, xy_offset, t, c
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 128)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  c = result

  c = c & 0xff

def opcode_fdcb_fa():  #  SET 7,(IY+n>D)
  global iy, xy_offset, t, d
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 128)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  d = result

  d = d & 0xff

def opcode_fdcb_fb():  #  SET 7,(IY+n>E)
  global iy, xy_offset, t, e
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 128)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  e = result

  e = e & 0xff

def opcode_fdcb_fc():  #  SET 7,(IY+n>H)
  global iy, xy_offset, t, h
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 128)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  h = result

  h = h & 0xff

def opcode_fdcb_fd():  #  SET 7,(IY+n>L)
  global iy, xy_offset, t, l
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 128)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  l = result

  l = l & 0xff

def opcode_fdcb_fe():  #  SET 7,(IY+n)
  global iy, xy_offset, t
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 128)  #  u8
  t += 5
  mmu.write(iyAddr, result)


def opcode_fdcb_ff():  #  SET 7,(IY+n>A)
  global iy, xy_offset, t, a
  iyAddr = (iy + xy_offset) & 0xffff  #  u16
  val = mmu.read(iyAddr)
  result = (val | 128)  #  u8
  t += 5
  mmu.write(iyAddr, result)
  a = result

  a = a & 0xff

opcodes[0x0] = opcode_nop
opcodes[0x1] = opcode_1
opcodes[0x2] = opcode_2
opcodes[0x3] = opcode_3
opcodes[0x4] = opcode_4
opcodes[0x5] = opcode_5
opcodes[0x6] = opcode_6
opcodes[0x7] = opcode_7
opcodes[0x8] = opcode_8
opcodes[0x9] = opcode_9
opcodes[0xa] = opcode_a
opcodes[0xb] = opcode_b
opcodes[0xc] = opcode_c
opcodes[0xd] = opcode_d
opcodes[0xe] = opcode_e
opcodes[0xf] = opcode_f
opcodes[0x10] = opcode_10
opcodes[0x11] = opcode_11
opcodes[0x12] = opcode_12
opcodes[0x13] = opcode_13
opcodes[0x14] = opcode_14
opcodes[0x15] = opcode_15
opcodes[0x16] = opcode_16
opcodes[0x17] = opcode_17
opcodes[0x18] = opcode_18
opcodes[0x19] = opcode_19
opcodes[0x1a] = opcode_1a
opcodes[0x1b] = opcode_1b
opcodes[0x1c] = opcode_1c
opcodes[0x1d] = opcode_1d
opcodes[0x1e] = opcode_1e
opcodes[0x1f] = opcode_1f
opcodes[0x20] = opcode_20
opcodes[0x21] = opcode_21
opcodes[0x22] = opcode_22
opcodes[0x23] = opcode_23
opcodes[0x24] = opcode_24
opcodes[0x25] = opcode_25
opcodes[0x26] = opcode_26
opcodes[0x27] = opcode_27
opcodes[0x28] = opcode_28
opcodes[0x29] = opcode_29
opcodes[0x2a] = opcode_2a
opcodes[0x2b] = opcode_2b
opcodes[0x2c] = opcode_2c
opcodes[0x2d] = opcode_2d
opcodes[0x2e] = opcode_2e
opcodes[0x2f] = opcode_2f
opcodes[0x30] = opcode_30
opcodes[0x31] = opcode_31
opcodes[0x32] = opcode_32
opcodes[0x33] = opcode_33
opcodes[0x34] = opcode_34
opcodes[0x35] = opcode_35
opcodes[0x36] = opcode_36
opcodes[0x37] = opcode_37
opcodes[0x38] = opcode_38
opcodes[0x39] = opcode_39
opcodes[0x3a] = opcode_3a
opcodes[0x3b] = opcode_3b
opcodes[0x3c] = opcode_3c
opcodes[0x3d] = opcode_3d
opcodes[0x3e] = opcode_3e
opcodes[0x3f] = opcode_3f
opcodes[0x40] = opcode_40
opcodes[0x41] = opcode_41
opcodes[0x42] = opcode_42
opcodes[0x43] = opcode_43
opcodes[0x44] = opcode_44
opcodes[0x45] = opcode_45
opcodes[0x46] = opcode_46
opcodes[0x47] = opcode_47
opcodes[0x48] = opcode_48
opcodes[0x49] = opcode_49
opcodes[0x4a] = opcode_4a
opcodes[0x4b] = opcode_4b
opcodes[0x4c] = opcode_4c
opcodes[0x4d] = opcode_4d
opcodes[0x4e] = opcode_4e
opcodes[0x4f] = opcode_4f
opcodes[0x50] = opcode_50
opcodes[0x51] = opcode_51
opcodes[0x52] = opcode_52
opcodes[0x53] = opcode_53
opcodes[0x54] = opcode_54
opcodes[0x55] = opcode_55
opcodes[0x56] = opcode_56
opcodes[0x57] = opcode_57
opcodes[0x58] = opcode_58
opcodes[0x59] = opcode_59
opcodes[0x5a] = opcode_5a
opcodes[0x5b] = opcode_5b
opcodes[0x5c] = opcode_5c
opcodes[0x5d] = opcode_5d
opcodes[0x5e] = opcode_5e
opcodes[0x5f] = opcode_5f
opcodes[0x60] = opcode_60
opcodes[0x61] = opcode_61
opcodes[0x62] = opcode_62
opcodes[0x63] = opcode_63
opcodes[0x64] = opcode_64
opcodes[0x65] = opcode_65
opcodes[0x66] = opcode_66
opcodes[0x67] = opcode_67
opcodes[0x68] = opcode_68
opcodes[0x69] = opcode_69
opcodes[0x6a] = opcode_6a
opcodes[0x6b] = opcode_6b
opcodes[0x6c] = opcode_6c
opcodes[0x6d] = opcode_6d
opcodes[0x6e] = opcode_6e
opcodes[0x6f] = opcode_6f
opcodes[0x70] = opcode_70
opcodes[0x71] = opcode_71
opcodes[0x72] = opcode_72
opcodes[0x73] = opcode_73
opcodes[0x74] = opcode_74
opcodes[0x75] = opcode_75
opcodes[0x76] = opcode_76
opcodes[0x77] = opcode_77
opcodes[0x78] = opcode_78
opcodes[0x79] = opcode_79
opcodes[0x7a] = opcode_7a
opcodes[0x7b] = opcode_7b
opcodes[0x7c] = opcode_7c
opcodes[0x7d] = opcode_7d
opcodes[0x7e] = opcode_7e
opcodes[0x7f] = opcode_7f
opcodes[0x80] = opcode_80
opcodes[0x81] = opcode_81
opcodes[0x82] = opcode_82
opcodes[0x83] = opcode_83
opcodes[0x84] = opcode_84
opcodes[0x85] = opcode_85
opcodes[0x86] = opcode_86
opcodes[0x87] = opcode_87
opcodes[0x88] = opcode_88
opcodes[0x89] = opcode_89
opcodes[0x8a] = opcode_8a
opcodes[0x8b] = opcode_8b
opcodes[0x8c] = opcode_8c
opcodes[0x8d] = opcode_8d
opcodes[0x8e] = opcode_8e
opcodes[0x8f] = opcode_8f
opcodes[0x90] = opcode_90
opcodes[0x91] = opcode_91
opcodes[0x92] = opcode_92
opcodes[0x93] = opcode_93
opcodes[0x94] = opcode_94
opcodes[0x95] = opcode_95
opcodes[0x96] = opcode_96
opcodes[0x97] = opcode_97
opcodes[0x98] = opcode_98
opcodes[0x99] = opcode_99
opcodes[0x9a] = opcode_9a
opcodes[0x9b] = opcode_9b
opcodes[0x9c] = opcode_9c
opcodes[0x9d] = opcode_9d
opcodes[0x9e] = opcode_9e
opcodes[0x9f] = opcode_9f
opcodes[0xa0] = opcode_a0
opcodes[0xa1] = opcode_a1
opcodes[0xa2] = opcode_a2
opcodes[0xa3] = opcode_a3
opcodes[0xa4] = opcode_a4
opcodes[0xa5] = opcode_a5
opcodes[0xa6] = opcode_a6
opcodes[0xa7] = opcode_a7
opcodes[0xa8] = opcode_a8
opcodes[0xa9] = opcode_a9
opcodes[0xaa] = opcode_aa
opcodes[0xab] = opcode_ab
opcodes[0xac] = opcode_ac
opcodes[0xad] = opcode_ad
opcodes[0xae] = opcode_ae
opcodes[0xaf] = opcode_af
opcodes[0xb0] = opcode_b0
opcodes[0xb1] = opcode_b1
opcodes[0xb2] = opcode_b2
opcodes[0xb3] = opcode_b3
opcodes[0xb4] = opcode_b4
opcodes[0xb5] = opcode_b5
opcodes[0xb6] = opcode_b6
opcodes[0xb7] = opcode_b7
opcodes[0xb8] = opcode_b8
opcodes[0xb9] = opcode_b9
opcodes[0xba] = opcode_ba
opcodes[0xbb] = opcode_bb
opcodes[0xbc] = opcode_bc
opcodes[0xbd] = opcode_bd
opcodes[0xbe] = opcode_be
opcodes[0xbf] = opcode_bf
opcodes[0xc0] = opcode_c0
opcodes[0xc1] = opcode_c1
opcodes[0xc2] = opcode_c2
opcodes[0xc3] = opcode_c3
opcodes[0xc4] = opcode_c4
opcodes[0xc5] = opcode_c5
opcodes[0xc6] = opcode_c6
opcodes[0xc7] = opcode_c7
opcodes[0xc8] = opcode_c8
opcodes[0xc9] = opcode_c9
opcodes[0xca] = opcode_ca
opcodes[0xcb] = opcode_cb
opcodes[0xcc] = opcode_cc
opcodes[0xcd] = opcode_cd
opcodes[0xce] = opcode_ce
opcodes[0xcf] = opcode_cf
opcodes[0xd0] = opcode_d0
opcodes[0xd1] = opcode_d1
opcodes[0xd2] = opcode_d2
opcodes[0xd3] = opcode_d3
opcodes[0xd4] = opcode_d4
opcodes[0xd5] = opcode_d5
opcodes[0xd6] = opcode_d6
opcodes[0xd7] = opcode_d7
opcodes[0xd8] = opcode_d8
opcodes[0xd9] = opcode_d9
opcodes[0xda] = opcode_da
opcodes[0xdb] = opcode_db
opcodes[0xdc] = opcode_dc
opcodes[0xdd] = opcode_dd
opcodes[0xde] = opcode_de
opcodes[0xdf] = opcode_df
opcodes[0xe0] = opcode_e0
opcodes[0xe1] = opcode_e1
opcodes[0xe2] = opcode_e2
opcodes[0xe3] = opcode_e3
opcodes[0xe4] = opcode_e4
opcodes[0xe5] = opcode_e5
opcodes[0xe6] = opcode_e6
opcodes[0xe7] = opcode_e7
opcodes[0xe8] = opcode_e8
opcodes[0xe9] = opcode_e9
opcodes[0xea] = opcode_ea
opcodes[0xeb] = opcode_eb
opcodes[0xec] = opcode_ec
opcodes[0xed] = opcode_ed
opcodes[0xee] = opcode_ee
opcodes[0xef] = opcode_ef
opcodes[0xf0] = opcode_f0
opcodes[0xf1] = opcode_f1
opcodes[0xf2] = opcode_f2
opcodes[0xf3] = opcode_f3
opcodes[0xf4] = opcode_f4
opcodes[0xf5] = opcode_f5
opcodes[0xf6] = opcode_f6
opcodes[0xf7] = opcode_f7
opcodes[0xf8] = opcode_f8
opcodes[0xf9] = opcode_f9
opcodes[0xfa] = opcode_fa
opcodes[0xfb] = opcode_fb
opcodes[0xfc] = opcode_fc
opcodes[0xfd] = opcode_fd
opcodes[0xfe] = opcode_fe
opcodes[0xff] = opcode_ff

opcodes_cb[0x0] = opcode_cb_0
opcodes_cb[0x1] = opcode_cb_1
opcodes_cb[0x2] = opcode_cb_2
opcodes_cb[0x3] = opcode_cb_3
opcodes_cb[0x4] = opcode_cb_4
opcodes_cb[0x5] = opcode_cb_5
opcodes_cb[0x6] = opcode_cb_6
opcodes_cb[0x7] = opcode_cb_7
opcodes_cb[0x8] = opcode_cb_8
opcodes_cb[0x9] = opcode_cb_9
opcodes_cb[0xa] = opcode_cb_a
opcodes_cb[0xb] = opcode_cb_b
opcodes_cb[0xc] = opcode_cb_c
opcodes_cb[0xd] = opcode_cb_d
opcodes_cb[0xe] = opcode_cb_e
opcodes_cb[0xf] = opcode_cb_f
opcodes_cb[0x10] = opcode_cb_10
opcodes_cb[0x11] = opcode_cb_11
opcodes_cb[0x12] = opcode_cb_12
opcodes_cb[0x13] = opcode_cb_13
opcodes_cb[0x14] = opcode_cb_14
opcodes_cb[0x15] = opcode_cb_15
opcodes_cb[0x16] = opcode_cb_16
opcodes_cb[0x17] = opcode_cb_17
opcodes_cb[0x18] = opcode_cb_18
opcodes_cb[0x19] = opcode_cb_19
opcodes_cb[0x1a] = opcode_cb_1a
opcodes_cb[0x1b] = opcode_cb_1b
opcodes_cb[0x1c] = opcode_cb_1c
opcodes_cb[0x1d] = opcode_cb_1d
opcodes_cb[0x1e] = opcode_cb_1e
opcodes_cb[0x1f] = opcode_cb_1f
opcodes_cb[0x20] = opcode_cb_20
opcodes_cb[0x21] = opcode_cb_21
opcodes_cb[0x22] = opcode_cb_22
opcodes_cb[0x23] = opcode_cb_23
opcodes_cb[0x24] = opcode_cb_24
opcodes_cb[0x25] = opcode_cb_25
opcodes_cb[0x26] = opcode_cb_26
opcodes_cb[0x27] = opcode_cb_27
opcodes_cb[0x28] = opcode_cb_28
opcodes_cb[0x29] = opcode_cb_29
opcodes_cb[0x2a] = opcode_cb_2a
opcodes_cb[0x2b] = opcode_cb_2b
opcodes_cb[0x2c] = opcode_cb_2c
opcodes_cb[0x2d] = opcode_cb_2d
opcodes_cb[0x2e] = opcode_cb_2e
opcodes_cb[0x2f] = opcode_cb_2f
opcodes_cb[0x30] = opcode_cb_30
opcodes_cb[0x31] = opcode_cb_31
opcodes_cb[0x32] = opcode_cb_32
opcodes_cb[0x33] = opcode_cb_33
opcodes_cb[0x34] = opcode_cb_34
opcodes_cb[0x35] = opcode_cb_35
opcodes_cb[0x36] = opcode_cb_36
opcodes_cb[0x37] = opcode_cb_37
opcodes_cb[0x38] = opcode_cb_38
opcodes_cb[0x39] = opcode_cb_39
opcodes_cb[0x3a] = opcode_cb_3a
opcodes_cb[0x3b] = opcode_cb_3b
opcodes_cb[0x3c] = opcode_cb_3c
opcodes_cb[0x3d] = opcode_cb_3d
opcodes_cb[0x3e] = opcode_cb_3e
opcodes_cb[0x3f] = opcode_cb_3f
opcodes_cb[0x40] = opcode_cb_40
opcodes_cb[0x41] = opcode_cb_41
opcodes_cb[0x42] = opcode_cb_42
opcodes_cb[0x43] = opcode_cb_43
opcodes_cb[0x44] = opcode_cb_44
opcodes_cb[0x45] = opcode_cb_45
opcodes_cb[0x46] = opcode_cb_46
opcodes_cb[0x47] = opcode_cb_47
opcodes_cb[0x48] = opcode_cb_48
opcodes_cb[0x49] = opcode_cb_49
opcodes_cb[0x4a] = opcode_cb_4a
opcodes_cb[0x4b] = opcode_cb_4b
opcodes_cb[0x4c] = opcode_cb_4c
opcodes_cb[0x4d] = opcode_cb_4d
opcodes_cb[0x4e] = opcode_cb_4e
opcodes_cb[0x4f] = opcode_cb_4f
opcodes_cb[0x50] = opcode_cb_50
opcodes_cb[0x51] = opcode_cb_51
opcodes_cb[0x52] = opcode_cb_52
opcodes_cb[0x53] = opcode_cb_53
opcodes_cb[0x54] = opcode_cb_54
opcodes_cb[0x55] = opcode_cb_55
opcodes_cb[0x56] = opcode_cb_56
opcodes_cb[0x57] = opcode_cb_57
opcodes_cb[0x58] = opcode_cb_58
opcodes_cb[0x59] = opcode_cb_59
opcodes_cb[0x5a] = opcode_cb_5a
opcodes_cb[0x5b] = opcode_cb_5b
opcodes_cb[0x5c] = opcode_cb_5c
opcodes_cb[0x5d] = opcode_cb_5d
opcodes_cb[0x5e] = opcode_cb_5e
opcodes_cb[0x5f] = opcode_cb_5f
opcodes_cb[0x60] = opcode_cb_60
opcodes_cb[0x61] = opcode_cb_61
opcodes_cb[0x62] = opcode_cb_62
opcodes_cb[0x63] = opcode_cb_63
opcodes_cb[0x64] = opcode_cb_64
opcodes_cb[0x65] = opcode_cb_65
opcodes_cb[0x66] = opcode_cb_66
opcodes_cb[0x67] = opcode_cb_67
opcodes_cb[0x68] = opcode_cb_68
opcodes_cb[0x69] = opcode_cb_69
opcodes_cb[0x6a] = opcode_cb_6a
opcodes_cb[0x6b] = opcode_cb_6b
opcodes_cb[0x6c] = opcode_cb_6c
opcodes_cb[0x6d] = opcode_cb_6d
opcodes_cb[0x6e] = opcode_cb_6e
opcodes_cb[0x6f] = opcode_cb_6f
opcodes_cb[0x70] = opcode_cb_70
opcodes_cb[0x71] = opcode_cb_71
opcodes_cb[0x72] = opcode_cb_72
opcodes_cb[0x73] = opcode_cb_73
opcodes_cb[0x74] = opcode_cb_74
opcodes_cb[0x75] = opcode_cb_75
opcodes_cb[0x76] = opcode_cb_76
opcodes_cb[0x77] = opcode_cb_77
opcodes_cb[0x78] = opcode_cb_78
opcodes_cb[0x79] = opcode_cb_79
opcodes_cb[0x7a] = opcode_cb_7a
opcodes_cb[0x7b] = opcode_cb_7b
opcodes_cb[0x7c] = opcode_cb_7c
opcodes_cb[0x7d] = opcode_cb_7d
opcodes_cb[0x7e] = opcode_cb_7e
opcodes_cb[0x7f] = opcode_cb_7f
opcodes_cb[0x80] = opcode_cb_80
opcodes_cb[0x81] = opcode_cb_81
opcodes_cb[0x82] = opcode_cb_82
opcodes_cb[0x83] = opcode_cb_83
opcodes_cb[0x84] = opcode_cb_84
opcodes_cb[0x85] = opcode_cb_85
opcodes_cb[0x86] = opcode_cb_86
opcodes_cb[0x87] = opcode_cb_87
opcodes_cb[0x88] = opcode_cb_88
opcodes_cb[0x89] = opcode_cb_89
opcodes_cb[0x8a] = opcode_cb_8a
opcodes_cb[0x8b] = opcode_cb_8b
opcodes_cb[0x8c] = opcode_cb_8c
opcodes_cb[0x8d] = opcode_cb_8d
opcodes_cb[0x8e] = opcode_cb_8e
opcodes_cb[0x8f] = opcode_cb_8f
opcodes_cb[0x90] = opcode_cb_90
opcodes_cb[0x91] = opcode_cb_91
opcodes_cb[0x92] = opcode_cb_92
opcodes_cb[0x93] = opcode_cb_93
opcodes_cb[0x94] = opcode_cb_94
opcodes_cb[0x95] = opcode_cb_95
opcodes_cb[0x96] = opcode_cb_96
opcodes_cb[0x97] = opcode_cb_97
opcodes_cb[0x98] = opcode_cb_98
opcodes_cb[0x99] = opcode_cb_99
opcodes_cb[0x9a] = opcode_cb_9a
opcodes_cb[0x9b] = opcode_cb_9b
opcodes_cb[0x9c] = opcode_cb_9c
opcodes_cb[0x9d] = opcode_cb_9d
opcodes_cb[0x9e] = opcode_cb_9e
opcodes_cb[0x9f] = opcode_cb_9f
opcodes_cb[0xa0] = opcode_cb_a0
opcodes_cb[0xa1] = opcode_cb_a1
opcodes_cb[0xa2] = opcode_cb_a2
opcodes_cb[0xa3] = opcode_cb_a3
opcodes_cb[0xa4] = opcode_cb_a4
opcodes_cb[0xa5] = opcode_cb_a5
opcodes_cb[0xa6] = opcode_cb_a6
opcodes_cb[0xa7] = opcode_cb_a7
opcodes_cb[0xa8] = opcode_cb_a8
opcodes_cb[0xa9] = opcode_cb_a9
opcodes_cb[0xaa] = opcode_cb_aa
opcodes_cb[0xab] = opcode_cb_ab
opcodes_cb[0xac] = opcode_cb_ac
opcodes_cb[0xad] = opcode_cb_ad
opcodes_cb[0xae] = opcode_cb_ae
opcodes_cb[0xaf] = opcode_cb_af
opcodes_cb[0xb0] = opcode_cb_b0
opcodes_cb[0xb1] = opcode_cb_b1
opcodes_cb[0xb2] = opcode_cb_b2
opcodes_cb[0xb3] = opcode_cb_b3
opcodes_cb[0xb4] = opcode_cb_b4
opcodes_cb[0xb5] = opcode_cb_b5
opcodes_cb[0xb6] = opcode_cb_b6
opcodes_cb[0xb7] = opcode_cb_b7
opcodes_cb[0xb8] = opcode_cb_b8
opcodes_cb[0xb9] = opcode_cb_b9
opcodes_cb[0xba] = opcode_cb_ba
opcodes_cb[0xbb] = opcode_cb_bb
opcodes_cb[0xbc] = opcode_cb_bc
opcodes_cb[0xbd] = opcode_cb_bd
opcodes_cb[0xbe] = opcode_cb_be
opcodes_cb[0xbf] = opcode_cb_bf
opcodes_cb[0xc0] = opcode_cb_c0
opcodes_cb[0xc1] = opcode_cb_c1
opcodes_cb[0xc2] = opcode_cb_c2
opcodes_cb[0xc3] = opcode_cb_c3
opcodes_cb[0xc4] = opcode_cb_c4
opcodes_cb[0xc5] = opcode_cb_c5
opcodes_cb[0xc6] = opcode_cb_c6
opcodes_cb[0xc7] = opcode_cb_c7
opcodes_cb[0xc8] = opcode_cb_c8
opcodes_cb[0xc9] = opcode_cb_c9
opcodes_cb[0xca] = opcode_cb_ca
opcodes_cb[0xcb] = opcode_cb_cb
opcodes_cb[0xcc] = opcode_cb_cc
opcodes_cb[0xcd] = opcode_cb_cd
opcodes_cb[0xce] = opcode_cb_ce
opcodes_cb[0xcf] = opcode_cb_cf
opcodes_cb[0xd0] = opcode_cb_d0
opcodes_cb[0xd1] = opcode_cb_d1
opcodes_cb[0xd2] = opcode_cb_d2
opcodes_cb[0xd3] = opcode_cb_d3
opcodes_cb[0xd4] = opcode_cb_d4
opcodes_cb[0xd5] = opcode_cb_d5
opcodes_cb[0xd6] = opcode_cb_d6
opcodes_cb[0xd7] = opcode_cb_d7
opcodes_cb[0xd8] = opcode_cb_d8
opcodes_cb[0xd9] = opcode_cb_d9
opcodes_cb[0xda] = opcode_cb_da
opcodes_cb[0xdb] = opcode_cb_db
opcodes_cb[0xdc] = opcode_cb_dc
opcodes_cb[0xdd] = opcode_cb_dd
opcodes_cb[0xde] = opcode_cb_de
opcodes_cb[0xdf] = opcode_cb_df
opcodes_cb[0xe0] = opcode_cb_e0
opcodes_cb[0xe1] = opcode_cb_e1
opcodes_cb[0xe2] = opcode_cb_e2
opcodes_cb[0xe3] = opcode_cb_e3
opcodes_cb[0xe4] = opcode_cb_e4
opcodes_cb[0xe5] = opcode_cb_e5
opcodes_cb[0xe6] = opcode_cb_e6
opcodes_cb[0xe7] = opcode_cb_e7
opcodes_cb[0xe8] = opcode_cb_e8
opcodes_cb[0xe9] = opcode_cb_e9
opcodes_cb[0xea] = opcode_cb_ea
opcodes_cb[0xeb] = opcode_cb_eb
opcodes_cb[0xec] = opcode_cb_ec
opcodes_cb[0xed] = opcode_cb_ed
opcodes_cb[0xee] = opcode_cb_ee
opcodes_cb[0xef] = opcode_cb_ef
opcodes_cb[0xf0] = opcode_cb_f0
opcodes_cb[0xf1] = opcode_cb_f1
opcodes_cb[0xf2] = opcode_cb_f2
opcodes_cb[0xf3] = opcode_cb_f3
opcodes_cb[0xf4] = opcode_cb_f4
opcodes_cb[0xf5] = opcode_cb_f5
opcodes_cb[0xf6] = opcode_cb_f6
opcodes_cb[0xf7] = opcode_cb_f7
opcodes_cb[0xf8] = opcode_cb_f8
opcodes_cb[0xf9] = opcode_cb_f9
opcodes_cb[0xfa] = opcode_cb_fa
opcodes_cb[0xfb] = opcode_cb_fb
opcodes_cb[0xfc] = opcode_cb_fc
opcodes_cb[0xfd] = opcode_cb_fd
opcodes_cb[0xfe] = opcode_cb_fe
opcodes_cb[0xff] = opcode_cb_ff

opcodes_dd[0x0] = opcode_nop
opcodes_dd[0x1] = opcode_1
opcodes_dd[0x2] = opcode_2
opcodes_dd[0x3] = opcode_3
opcodes_dd[0x4] = opcode_4
opcodes_dd[0x5] = opcode_5
opcodes_dd[0x6] = opcode_6
opcodes_dd[0x7] = opcode_7
opcodes_dd[0x8] = opcode_8
opcodes_dd[0x9] = opcode_dd_9
opcodes_dd[0xa] = opcode_a
opcodes_dd[0xb] = opcode_b
opcodes_dd[0xc] = opcode_c
opcodes_dd[0xd] = opcode_d
opcodes_dd[0xe] = opcode_e
opcodes_dd[0xf] = opcode_f
opcodes_dd[0x10] = opcode_10
opcodes_dd[0x11] = opcode_11
opcodes_dd[0x12] = opcode_12
opcodes_dd[0x13] = opcode_13
opcodes_dd[0x14] = opcode_14
opcodes_dd[0x15] = opcode_15
opcodes_dd[0x16] = opcode_16
opcodes_dd[0x17] = opcode_17
opcodes_dd[0x18] = opcode_18
opcodes_dd[0x19] = opcode_dd_19
opcodes_dd[0x1a] = opcode_1a
opcodes_dd[0x1b] = opcode_1b
opcodes_dd[0x1c] = opcode_1c
opcodes_dd[0x1d] = opcode_1d
opcodes_dd[0x1e] = opcode_1e
opcodes_dd[0x1f] = opcode_1f
opcodes_dd[0x20] = opcode_20
opcodes_dd[0x21] = opcode_dd_21
opcodes_dd[0x22] = opcode_dd_22
opcodes_dd[0x23] = opcode_dd_23
opcodes_dd[0x24] = opcode_dd_24
opcodes_dd[0x25] = opcode_dd_25
opcodes_dd[0x26] = opcode_dd_26
opcodes_dd[0x27] = opcode_27
opcodes_dd[0x28] = opcode_28
opcodes_dd[0x29] = opcode_dd_29
opcodes_dd[0x2a] = opcode_dd_2a
opcodes_dd[0x2b] = opcode_dd_2b
opcodes_dd[0x2c] = opcode_dd_2c
opcodes_dd[0x2d] = opcode_dd_2d
opcodes_dd[0x2e] = opcode_dd_2e
opcodes_dd[0x2f] = opcode_2f
opcodes_dd[0x30] = opcode_30
opcodes_dd[0x31] = opcode_31
opcodes_dd[0x32] = opcode_32
opcodes_dd[0x33] = opcode_33
opcodes_dd[0x34] = opcode_dd_34
opcodes_dd[0x35] = opcode_dd_35
opcodes_dd[0x36] = opcode_dd_36
opcodes_dd[0x37] = opcode_37
opcodes_dd[0x38] = opcode_38
opcodes_dd[0x39] = opcode_dd_39
opcodes_dd[0x3a] = opcode_3a
opcodes_dd[0x3b] = opcode_3b
opcodes_dd[0x3c] = opcode_3c
opcodes_dd[0x3d] = opcode_3d
opcodes_dd[0x3e] = opcode_3e
opcodes_dd[0x3f] = opcode_3f
opcodes_dd[0x40] = opcode_40
opcodes_dd[0x41] = opcode_41
opcodes_dd[0x42] = opcode_42
opcodes_dd[0x43] = opcode_43
opcodes_dd[0x44] = opcode_dd_44
opcodes_dd[0x45] = opcode_dd_45
opcodes_dd[0x46] = opcode_dd_46
opcodes_dd[0x47] = opcode_47
opcodes_dd[0x48] = opcode_48
opcodes_dd[0x49] = opcode_49
opcodes_dd[0x4a] = opcode_4a
opcodes_dd[0x4b] = opcode_4b
opcodes_dd[0x4c] = opcode_dd_4c
opcodes_dd[0x4d] = opcode_dd_4d
opcodes_dd[0x4e] = opcode_dd_4e
opcodes_dd[0x4f] = opcode_4f
opcodes_dd[0x50] = opcode_50
opcodes_dd[0x51] = opcode_51
opcodes_dd[0x52] = opcode_52
opcodes_dd[0x53] = opcode_53
opcodes_dd[0x54] = opcode_dd_54
opcodes_dd[0x55] = opcode_dd_55
opcodes_dd[0x56] = opcode_dd_56
opcodes_dd[0x57] = opcode_57
opcodes_dd[0x58] = opcode_58
opcodes_dd[0x59] = opcode_59
opcodes_dd[0x5a] = opcode_5a
opcodes_dd[0x5b] = opcode_5b
opcodes_dd[0x5c] = opcode_dd_5c
opcodes_dd[0x5d] = opcode_dd_5d
opcodes_dd[0x5e] = opcode_dd_5e
opcodes_dd[0x5f] = opcode_5f
opcodes_dd[0x60] = opcode_dd_60
opcodes_dd[0x61] = opcode_dd_61
opcodes_dd[0x62] = opcode_dd_62
opcodes_dd[0x63] = opcode_dd_63
opcodes_dd[0x64] = opcode_dd_64
opcodes_dd[0x65] = opcode_dd_65
opcodes_dd[0x66] = opcode_dd_66
opcodes_dd[0x67] = opcode_dd_67
opcodes_dd[0x68] = opcode_dd_68
opcodes_dd[0x69] = opcode_dd_69
opcodes_dd[0x6a] = opcode_dd_6a
opcodes_dd[0x6b] = opcode_dd_6b
opcodes_dd[0x6c] = opcode_dd_6c
opcodes_dd[0x6d] = opcode_dd_6d
opcodes_dd[0x6e] = opcode_dd_6e
opcodes_dd[0x6f] = opcode_dd_6f
opcodes_dd[0x70] = opcode_dd_70
opcodes_dd[0x71] = opcode_dd_71
opcodes_dd[0x72] = opcode_dd_72
opcodes_dd[0x73] = opcode_dd_73
opcodes_dd[0x74] = opcode_dd_74
opcodes_dd[0x75] = opcode_dd_75
opcodes_dd[0x76] = opcode_76
opcodes_dd[0x77] = opcode_dd_77
opcodes_dd[0x78] = opcode_78
opcodes_dd[0x79] = opcode_79
opcodes_dd[0x7a] = opcode_7a
opcodes_dd[0x7b] = opcode_7b
opcodes_dd[0x7c] = opcode_dd_7c
opcodes_dd[0x7d] = opcode_dd_7d
opcodes_dd[0x7e] = opcode_dd_7e
opcodes_dd[0x7f] = opcode_7f
opcodes_dd[0x80] = opcode_80
opcodes_dd[0x81] = opcode_81
opcodes_dd[0x82] = opcode_82
opcodes_dd[0x83] = opcode_83
opcodes_dd[0x84] = opcode_dd_84
opcodes_dd[0x85] = opcode_dd_85
opcodes_dd[0x86] = opcode_dd_86
opcodes_dd[0x87] = opcode_87
opcodes_dd[0x88] = opcode_88
opcodes_dd[0x89] = opcode_89
opcodes_dd[0x8a] = opcode_8a
opcodes_dd[0x8b] = opcode_8b
opcodes_dd[0x8c] = opcode_dd_8c
opcodes_dd[0x8d] = opcode_dd_8d
opcodes_dd[0x8e] = opcode_dd_8e
opcodes_dd[0x8f] = opcode_8f
opcodes_dd[0x90] = opcode_90
opcodes_dd[0x91] = opcode_91
opcodes_dd[0x92] = opcode_92
opcodes_dd[0x93] = opcode_93
opcodes_dd[0x94] = opcode_dd_94
opcodes_dd[0x95] = opcode_dd_95
opcodes_dd[0x96] = opcode_dd_96
opcodes_dd[0x97] = opcode_97
opcodes_dd[0x98] = opcode_98
opcodes_dd[0x99] = opcode_99
opcodes_dd[0x9a] = opcode_9a
opcodes_dd[0x9b] = opcode_9b
opcodes_dd[0x9c] = opcode_dd_9c
opcodes_dd[0x9d] = opcode_dd_9d
opcodes_dd[0x9e] = opcode_dd_9e
opcodes_dd[0x9f] = opcode_9f
opcodes_dd[0xa0] = opcode_a0
opcodes_dd[0xa1] = opcode_a1
opcodes_dd[0xa2] = opcode_a2
opcodes_dd[0xa3] = opcode_a3
opcodes_dd[0xa4] = opcode_dd_a4
opcodes_dd[0xa5] = opcode_dd_a5
opcodes_dd[0xa6] = opcode_dd_a6
opcodes_dd[0xa7] = opcode_a7
opcodes_dd[0xa8] = opcode_a8
opcodes_dd[0xa9] = opcode_a9
opcodes_dd[0xaa] = opcode_aa
opcodes_dd[0xab] = opcode_ab
opcodes_dd[0xac] = opcode_dd_ac
opcodes_dd[0xad] = opcode_dd_ad
opcodes_dd[0xae] = opcode_dd_ae
opcodes_dd[0xaf] = opcode_af
opcodes_dd[0xb0] = opcode_b0
opcodes_dd[0xb1] = opcode_b1
opcodes_dd[0xb2] = opcode_b2
opcodes_dd[0xb3] = opcode_b3
opcodes_dd[0xb4] = opcode_dd_b4
opcodes_dd[0xb5] = opcode_dd_b5
opcodes_dd[0xb6] = opcode_dd_b6
opcodes_dd[0xb7] = opcode_b7
opcodes_dd[0xb8] = opcode_b8
opcodes_dd[0xb9] = opcode_b9
opcodes_dd[0xba] = opcode_ba
opcodes_dd[0xbb] = opcode_bb
opcodes_dd[0xbc] = opcode_dd_bc
opcodes_dd[0xbd] = opcode_dd_bd
opcodes_dd[0xbe] = opcode_dd_be
opcodes_dd[0xbf] = opcode_bf
opcodes_dd[0xc0] = opcode_c0
opcodes_dd[0xc1] = opcode_c1
opcodes_dd[0xc2] = opcode_c2
opcodes_dd[0xc3] = opcode_c3
opcodes_dd[0xc4] = opcode_c4
opcodes_dd[0xc5] = opcode_c5
opcodes_dd[0xc6] = opcode_c6
opcodes_dd[0xc7] = opcode_c7
opcodes_dd[0xc8] = opcode_c8
opcodes_dd[0xc9] = opcode_c9
opcodes_dd[0xca] = opcode_ca
opcodes_dd[0xcb] = opcode_ddcb
opcodes_dd[0xcc] = opcode_cc
opcodes_dd[0xcd] = opcode_cd
opcodes_dd[0xce] = opcode_ce
opcodes_dd[0xcf] = opcode_cf
opcodes_dd[0xd0] = opcode_d0
opcodes_dd[0xd1] = opcode_d1
opcodes_dd[0xd2] = opcode_d2
opcodes_dd[0xd3] = opcode_d3
opcodes_dd[0xd4] = opcode_d4
opcodes_dd[0xd5] = opcode_d5
opcodes_dd[0xd6] = opcode_d6
opcodes_dd[0xd7] = opcode_d7
opcodes_dd[0xd8] = opcode_d8
opcodes_dd[0xd9] = opcode_d9
opcodes_dd[0xda] = opcode_da
opcodes_dd[0xdb] = opcode_db
opcodes_dd[0xdc] = opcode_dc
opcodes_dd[0xde] = opcode_de
opcodes_dd[0xdd] = opcode_nop
opcodes_dd[0xdf] = opcode_df
opcodes_dd[0xe0] = opcode_e0
opcodes_dd[0xe1] = opcode_dd_e1
opcodes_dd[0xe2] = opcode_e2
opcodes_dd[0xe3] = opcode_dd_e3
opcodes_dd[0xe4] = opcode_e4
opcodes_dd[0xe5] = opcode_dd_e5
opcodes_dd[0xe6] = opcode_e6
opcodes_dd[0xe7] = opcode_e7
opcodes_dd[0xe8] = opcode_e8
opcodes_dd[0xe9] = opcode_dd_e9
opcodes_dd[0xea] = opcode_ea
opcodes_dd[0xeb] = opcode_eb
opcodes_dd[0xec] = opcode_ec
opcodes_dd[0xee] = opcode_ee
opcodes_dd[0xef] = opcode_ef
opcodes_dd[0xf0] = opcode_f0
opcodes_dd[0xf1] = opcode_f1
opcodes_dd[0xf2] = opcode_f2
opcodes_dd[0xf3] = opcode_f3
opcodes_dd[0xf4] = opcode_f4
opcodes_dd[0xf5] = opcode_f5
opcodes_dd[0xf6] = opcode_f6
opcodes_dd[0xf7] = opcode_f7
opcodes_dd[0xf8] = opcode_f8
opcodes_dd[0xf9] = opcode_dd_f9
opcodes_dd[0xfa] = opcode_fa
opcodes_dd[0xfb] = opcode_fb
opcodes_dd[0xfc] = opcode_fc
opcodes_dd[0xfd] = opcode_nop
opcodes_dd[0xfe] = opcode_fe
opcodes_dd[0xff] = opcode_ff

opcodes_ddcb[0x0] = opcode_ddcb_0
opcodes_ddcb[0x1] = opcode_ddcb_1
opcodes_ddcb[0x2] = opcode_ddcb_2
opcodes_ddcb[0x3] = opcode_ddcb_3
opcodes_ddcb[0x4] = opcode_ddcb_4
opcodes_ddcb[0x5] = opcode_ddcb_5
opcodes_ddcb[0x6] = opcode_ddcb_6
opcodes_ddcb[0x7] = opcode_ddcb_7
opcodes_ddcb[0x8] = opcode_ddcb_8
opcodes_ddcb[0x9] = opcode_ddcb_9
opcodes_ddcb[0xa] = opcode_ddcb_a
opcodes_ddcb[0xb] = opcode_ddcb_b
opcodes_ddcb[0xc] = opcode_ddcb_c
opcodes_ddcb[0xd] = opcode_ddcb_d
opcodes_ddcb[0xe] = opcode_ddcb_e
opcodes_ddcb[0xf] = opcode_ddcb_f
opcodes_ddcb[0x10] = opcode_ddcb_10
opcodes_ddcb[0x11] = opcode_ddcb_11
opcodes_ddcb[0x12] = opcode_ddcb_12
opcodes_ddcb[0x13] = opcode_ddcb_13
opcodes_ddcb[0x14] = opcode_ddcb_14
opcodes_ddcb[0x15] = opcode_ddcb_15
opcodes_ddcb[0x16] = opcode_ddcb_16
opcodes_ddcb[0x17] = opcode_ddcb_17
opcodes_ddcb[0x18] = opcode_ddcb_18
opcodes_ddcb[0x19] = opcode_ddcb_19
opcodes_ddcb[0x1a] = opcode_ddcb_1a
opcodes_ddcb[0x1b] = opcode_ddcb_1b
opcodes_ddcb[0x1c] = opcode_ddcb_1c
opcodes_ddcb[0x1d] = opcode_ddcb_1d
opcodes_ddcb[0x1e] = opcode_ddcb_1e
opcodes_ddcb[0x1f] = opcode_ddcb_1f
opcodes_ddcb[0x20] = opcode_ddcb_20
opcodes_ddcb[0x21] = opcode_ddcb_21
opcodes_ddcb[0x22] = opcode_ddcb_22
opcodes_ddcb[0x23] = opcode_ddcb_23
opcodes_ddcb[0x24] = opcode_ddcb_24
opcodes_ddcb[0x25] = opcode_ddcb_25
opcodes_ddcb[0x26] = opcode_ddcb_26
opcodes_ddcb[0x27] = opcode_ddcb_27
opcodes_ddcb[0x28] = opcode_ddcb_28
opcodes_ddcb[0x29] = opcode_ddcb_29
opcodes_ddcb[0x2a] = opcode_ddcb_2a
opcodes_ddcb[0x2b] = opcode_ddcb_2b
opcodes_ddcb[0x2c] = opcode_ddcb_2c
opcodes_ddcb[0x2d] = opcode_ddcb_2d
opcodes_ddcb[0x2e] = opcode_ddcb_2e
opcodes_ddcb[0x2f] = opcode_ddcb_2f
opcodes_ddcb[0x30] = opcode_ddcb_30
opcodes_ddcb[0x31] = opcode_ddcb_31
opcodes_ddcb[0x32] = opcode_ddcb_32
opcodes_ddcb[0x33] = opcode_ddcb_33
opcodes_ddcb[0x34] = opcode_ddcb_34
opcodes_ddcb[0x35] = opcode_ddcb_35
opcodes_ddcb[0x36] = opcode_ddcb_36
opcodes_ddcb[0x37] = opcode_ddcb_37
opcodes_ddcb[0x38] = opcode_ddcb_38
opcodes_ddcb[0x39] = opcode_ddcb_39
opcodes_ddcb[0x3a] = opcode_ddcb_3a
opcodes_ddcb[0x3b] = opcode_ddcb_3b
opcodes_ddcb[0x3c] = opcode_ddcb_3c
opcodes_ddcb[0x3d] = opcode_ddcb_3d
opcodes_ddcb[0x3e] = opcode_ddcb_3e
opcodes_ddcb[0x3f] = opcode_ddcb_3f
opcodes_ddcb[0x40] = opcode_ddcb_40
opcodes_ddcb[0x41] = opcode_ddcb_41
opcodes_ddcb[0x42] = opcode_ddcb_42
opcodes_ddcb[0x43] = opcode_ddcb_43
opcodes_ddcb[0x44] = opcode_ddcb_44
opcodes_ddcb[0x45] = opcode_ddcb_45
opcodes_ddcb[0x46] = opcode_ddcb_46
opcodes_ddcb[0x47] = opcode_ddcb_47
opcodes_ddcb[0x48] = opcode_ddcb_48
opcodes_ddcb[0x49] = opcode_ddcb_49
opcodes_ddcb[0x4a] = opcode_ddcb_4a
opcodes_ddcb[0x4b] = opcode_ddcb_4b
opcodes_ddcb[0x4c] = opcode_ddcb_4c
opcodes_ddcb[0x4d] = opcode_ddcb_4d
opcodes_ddcb[0x4e] = opcode_ddcb_4e
opcodes_ddcb[0x4f] = opcode_ddcb_4f
opcodes_ddcb[0x50] = opcode_ddcb_50
opcodes_ddcb[0x51] = opcode_ddcb_51
opcodes_ddcb[0x52] = opcode_ddcb_52
opcodes_ddcb[0x53] = opcode_ddcb_53
opcodes_ddcb[0x54] = opcode_ddcb_54
opcodes_ddcb[0x55] = opcode_ddcb_55
opcodes_ddcb[0x56] = opcode_ddcb_56
opcodes_ddcb[0x57] = opcode_ddcb_57
opcodes_ddcb[0x58] = opcode_ddcb_58
opcodes_ddcb[0x59] = opcode_ddcb_59
opcodes_ddcb[0x5a] = opcode_ddcb_5a
opcodes_ddcb[0x5b] = opcode_ddcb_5b
opcodes_ddcb[0x5c] = opcode_ddcb_5c
opcodes_ddcb[0x5d] = opcode_ddcb_5d
opcodes_ddcb[0x5e] = opcode_ddcb_5e
opcodes_ddcb[0x5f] = opcode_ddcb_5f
opcodes_ddcb[0x60] = opcode_ddcb_60
opcodes_ddcb[0x61] = opcode_ddcb_61
opcodes_ddcb[0x62] = opcode_ddcb_62
opcodes_ddcb[0x63] = opcode_ddcb_63
opcodes_ddcb[0x64] = opcode_ddcb_64
opcodes_ddcb[0x65] = opcode_ddcb_65
opcodes_ddcb[0x66] = opcode_ddcb_66
opcodes_ddcb[0x67] = opcode_ddcb_67
opcodes_ddcb[0x68] = opcode_ddcb_68
opcodes_ddcb[0x69] = opcode_ddcb_69
opcodes_ddcb[0x6a] = opcode_ddcb_6a
opcodes_ddcb[0x6b] = opcode_ddcb_6b
opcodes_ddcb[0x6c] = opcode_ddcb_6c
opcodes_ddcb[0x6d] = opcode_ddcb_6d
opcodes_ddcb[0x6e] = opcode_ddcb_6e
opcodes_ddcb[0x6f] = opcode_ddcb_6f
opcodes_ddcb[0x70] = opcode_ddcb_70
opcodes_ddcb[0x71] = opcode_ddcb_71
opcodes_ddcb[0x72] = opcode_ddcb_72
opcodes_ddcb[0x73] = opcode_ddcb_73
opcodes_ddcb[0x74] = opcode_ddcb_74
opcodes_ddcb[0x75] = opcode_ddcb_75
opcodes_ddcb[0x76] = opcode_ddcb_76
opcodes_ddcb[0x77] = opcode_ddcb_77
opcodes_ddcb[0x78] = opcode_ddcb_78
opcodes_ddcb[0x79] = opcode_ddcb_79
opcodes_ddcb[0x7a] = opcode_ddcb_7a
opcodes_ddcb[0x7b] = opcode_ddcb_7b
opcodes_ddcb[0x7c] = opcode_ddcb_7c
opcodes_ddcb[0x7d] = opcode_ddcb_7d
opcodes_ddcb[0x7e] = opcode_ddcb_7e
opcodes_ddcb[0x7f] = opcode_ddcb_7f
opcodes_ddcb[0x80] = opcode_ddcb_80
opcodes_ddcb[0x81] = opcode_ddcb_81
opcodes_ddcb[0x82] = opcode_ddcb_82
opcodes_ddcb[0x83] = opcode_ddcb_83
opcodes_ddcb[0x84] = opcode_ddcb_84
opcodes_ddcb[0x85] = opcode_ddcb_85
opcodes_ddcb[0x86] = opcode_ddcb_86
opcodes_ddcb[0x87] = opcode_ddcb_87
opcodes_ddcb[0x88] = opcode_ddcb_88
opcodes_ddcb[0x89] = opcode_ddcb_89
opcodes_ddcb[0x8a] = opcode_ddcb_8a
opcodes_ddcb[0x8b] = opcode_ddcb_8b
opcodes_ddcb[0x8c] = opcode_ddcb_8c
opcodes_ddcb[0x8d] = opcode_ddcb_8d
opcodes_ddcb[0x8e] = opcode_ddcb_8e
opcodes_ddcb[0x8f] = opcode_ddcb_8f
opcodes_ddcb[0x90] = opcode_ddcb_90
opcodes_ddcb[0x91] = opcode_ddcb_91
opcodes_ddcb[0x92] = opcode_ddcb_92
opcodes_ddcb[0x93] = opcode_ddcb_93
opcodes_ddcb[0x94] = opcode_ddcb_94
opcodes_ddcb[0x95] = opcode_ddcb_95
opcodes_ddcb[0x96] = opcode_ddcb_96
opcodes_ddcb[0x97] = opcode_ddcb_97
opcodes_ddcb[0x98] = opcode_ddcb_98
opcodes_ddcb[0x99] = opcode_ddcb_99
opcodes_ddcb[0x9a] = opcode_ddcb_9a
opcodes_ddcb[0x9b] = opcode_ddcb_9b
opcodes_ddcb[0x9c] = opcode_ddcb_9c
opcodes_ddcb[0x9d] = opcode_ddcb_9d
opcodes_ddcb[0x9e] = opcode_ddcb_9e
opcodes_ddcb[0x9f] = opcode_ddcb_9f
opcodes_ddcb[0xa0] = opcode_ddcb_a0
opcodes_ddcb[0xa1] = opcode_ddcb_a1
opcodes_ddcb[0xa2] = opcode_ddcb_a2
opcodes_ddcb[0xa3] = opcode_ddcb_a3
opcodes_ddcb[0xa4] = opcode_ddcb_a4
opcodes_ddcb[0xa5] = opcode_ddcb_a5
opcodes_ddcb[0xa6] = opcode_ddcb_a6
opcodes_ddcb[0xa7] = opcode_ddcb_a7
opcodes_ddcb[0xa8] = opcode_ddcb_a8
opcodes_ddcb[0xa9] = opcode_ddcb_a9
opcodes_ddcb[0xaa] = opcode_ddcb_aa
opcodes_ddcb[0xab] = opcode_ddcb_ab
opcodes_ddcb[0xac] = opcode_ddcb_ac
opcodes_ddcb[0xad] = opcode_ddcb_ad
opcodes_ddcb[0xae] = opcode_ddcb_ae
opcodes_ddcb[0xaf] = opcode_ddcb_af
opcodes_ddcb[0xb0] = opcode_ddcb_b0
opcodes_ddcb[0xb1] = opcode_ddcb_b1
opcodes_ddcb[0xb2] = opcode_ddcb_b2
opcodes_ddcb[0xb3] = opcode_ddcb_b3
opcodes_ddcb[0xb4] = opcode_ddcb_b4
opcodes_ddcb[0xb5] = opcode_ddcb_b5
opcodes_ddcb[0xb6] = opcode_ddcb_b6
opcodes_ddcb[0xb7] = opcode_ddcb_b7
opcodes_ddcb[0xb8] = opcode_ddcb_b8
opcodes_ddcb[0xb9] = opcode_ddcb_b9
opcodes_ddcb[0xba] = opcode_ddcb_ba
opcodes_ddcb[0xbb] = opcode_ddcb_bb
opcodes_ddcb[0xbc] = opcode_ddcb_bc
opcodes_ddcb[0xbd] = opcode_ddcb_bd
opcodes_ddcb[0xbe] = opcode_ddcb_be
opcodes_ddcb[0xbf] = opcode_ddcb_bf
opcodes_ddcb[0xc0] = opcode_ddcb_c0
opcodes_ddcb[0xc1] = opcode_ddcb_c1
opcodes_ddcb[0xc2] = opcode_ddcb_c2
opcodes_ddcb[0xc3] = opcode_ddcb_c3
opcodes_ddcb[0xc4] = opcode_ddcb_c4
opcodes_ddcb[0xc5] = opcode_ddcb_c5
opcodes_ddcb[0xc6] = opcode_ddcb_c6
opcodes_ddcb[0xc7] = opcode_ddcb_c7
opcodes_ddcb[0xc8] = opcode_ddcb_c8
opcodes_ddcb[0xc9] = opcode_ddcb_c9
opcodes_ddcb[0xca] = opcode_ddcb_ca
opcodes_ddcb[0xcb] = opcode_ddcb_cb
opcodes_ddcb[0xcc] = opcode_ddcb_cc
opcodes_ddcb[0xcd] = opcode_ddcb_cd
opcodes_ddcb[0xce] = opcode_ddcb_ce
opcodes_ddcb[0xcf] = opcode_ddcb_cf
opcodes_ddcb[0xd0] = opcode_ddcb_d0
opcodes_ddcb[0xd1] = opcode_ddcb_d1
opcodes_ddcb[0xd2] = opcode_ddcb_d2
opcodes_ddcb[0xd3] = opcode_ddcb_d3
opcodes_ddcb[0xd4] = opcode_ddcb_d4
opcodes_ddcb[0xd5] = opcode_ddcb_d5
opcodes_ddcb[0xd6] = opcode_ddcb_d6
opcodes_ddcb[0xd7] = opcode_ddcb_d7
opcodes_ddcb[0xd8] = opcode_ddcb_d8
opcodes_ddcb[0xd9] = opcode_ddcb_d9
opcodes_ddcb[0xda] = opcode_ddcb_da
opcodes_ddcb[0xdb] = opcode_ddcb_db
opcodes_ddcb[0xdc] = opcode_ddcb_dc
opcodes_ddcb[0xdd] = opcode_ddcb_dd
opcodes_ddcb[0xde] = opcode_ddcb_de
opcodes_ddcb[0xdf] = opcode_ddcb_df
opcodes_ddcb[0xe0] = opcode_ddcb_e0
opcodes_ddcb[0xe1] = opcode_ddcb_e1
opcodes_ddcb[0xe2] = opcode_ddcb_e2
opcodes_ddcb[0xe3] = opcode_ddcb_e3
opcodes_ddcb[0xe4] = opcode_ddcb_e4
opcodes_ddcb[0xe5] = opcode_ddcb_e5
opcodes_ddcb[0xe6] = opcode_ddcb_e6
opcodes_ddcb[0xe7] = opcode_ddcb_e7
opcodes_ddcb[0xe8] = opcode_ddcb_e8
opcodes_ddcb[0xe9] = opcode_ddcb_e9
opcodes_ddcb[0xea] = opcode_ddcb_ea
opcodes_ddcb[0xeb] = opcode_ddcb_eb
opcodes_ddcb[0xec] = opcode_ddcb_ec
opcodes_ddcb[0xed] = opcode_ddcb_ed
opcodes_ddcb[0xee] = opcode_ddcb_ee
opcodes_ddcb[0xef] = opcode_ddcb_ef
opcodes_ddcb[0xf0] = opcode_ddcb_f0
opcodes_ddcb[0xf1] = opcode_ddcb_f1
opcodes_ddcb[0xf2] = opcode_ddcb_f2
opcodes_ddcb[0xf3] = opcode_ddcb_f3
opcodes_ddcb[0xf4] = opcode_ddcb_f4
opcodes_ddcb[0xf5] = opcode_ddcb_f5
opcodes_ddcb[0xf6] = opcode_ddcb_f6
opcodes_ddcb[0xf7] = opcode_ddcb_f7
opcodes_ddcb[0xf8] = opcode_ddcb_f8
opcodes_ddcb[0xf9] = opcode_ddcb_f9
opcodes_ddcb[0xfa] = opcode_ddcb_fa
opcodes_ddcb[0xfb] = opcode_ddcb_fb
opcodes_ddcb[0xfc] = opcode_ddcb_fc
opcodes_ddcb[0xfd] = opcode_ddcb_fd
opcodes_ddcb[0xfe] = opcode_ddcb_fe
opcodes_ddcb[0xff] = opcode_ddcb_ff

opcodes_ed[0x0] = opcode_nop
opcodes_ed[0x1] = opcode_nop
opcodes_ed[0x2] = opcode_ed_2
opcodes_ed[0x3] = opcode_nop
opcodes_ed[0x4] = opcode_nop
opcodes_ed[0x5] = opcode_nop
opcodes_ed[0x6] = opcode_nop
opcodes_ed[0x7] = opcode_nop
opcodes_ed[0x8] = opcode_nop
opcodes_ed[0x9] = opcode_nop
opcodes_ed[0xa] = opcode_nop
opcodes_ed[0xb] = opcode_nop
opcodes_ed[0xc] = opcode_nop
opcodes_ed[0xd] = opcode_nop
opcodes_ed[0xe] = opcode_nop
opcodes_ed[0xf] = opcode_nop
opcodes_ed[0x10] = opcode_nop
opcodes_ed[0x11] = opcode_nop
opcodes_ed[0x12] = opcode_nop
opcodes_ed[0x13] = opcode_nop
opcodes_ed[0x14] = opcode_nop
opcodes_ed[0x15] = opcode_nop
opcodes_ed[0x16] = opcode_nop
opcodes_ed[0x17] = opcode_nop
opcodes_ed[0x18] = opcode_nop
opcodes_ed[0x19] = opcode_nop
opcodes_ed[0x1a] = opcode_nop
opcodes_ed[0x1b] = opcode_nop
opcodes_ed[0x1c] = opcode_nop
opcodes_ed[0x1d] = opcode_nop
opcodes_ed[0x1e] = opcode_nop
opcodes_ed[0x1f] = opcode_nop
opcodes_ed[0x20] = opcode_nop
opcodes_ed[0x21] = opcode_nop
opcodes_ed[0x22] = opcode_nop
opcodes_ed[0x23] = opcode_nop
opcodes_ed[0x24] = opcode_nop
opcodes_ed[0x25] = opcode_nop
opcodes_ed[0x26] = opcode_nop
opcodes_ed[0x27] = opcode_nop
opcodes_ed[0x28] = opcode_nop
opcodes_ed[0x29] = opcode_nop
opcodes_ed[0x2a] = opcode_nop
opcodes_ed[0x2b] = opcode_nop
opcodes_ed[0x2c] = opcode_nop
opcodes_ed[0x2d] = opcode_nop
opcodes_ed[0x2e] = opcode_nop
opcodes_ed[0x2f] = opcode_nop
opcodes_ed[0x30] = opcode_nop
opcodes_ed[0x31] = opcode_nop
opcodes_ed[0x32] = opcode_nop
opcodes_ed[0x33] = opcode_nop
opcodes_ed[0x34] = opcode_nop
opcodes_ed[0x35] = opcode_nop
opcodes_ed[0x36] = opcode_nop
opcodes_ed[0x37] = opcode_nop
opcodes_ed[0x38] = opcode_nop
opcodes_ed[0x39] = opcode_nop
opcodes_ed[0x3a] = opcode_nop
opcodes_ed[0x3b] = opcode_nop
opcodes_ed[0x3c] = opcode_nop
opcodes_ed[0x3d] = opcode_nop
opcodes_ed[0x3e] = opcode_nop
opcodes_ed[0x3f] = opcode_nop

opcodes_ed[0x40] = opcode_ed_40
opcodes_ed[0x41] = opcode_ed_41
opcodes_ed[0x42] = opcode_ed_42
opcodes_ed[0x43] = opcode_ed_43
opcodes_ed[0x44] = opcode_ed_44
opcodes_ed[0x45] = opcode_ed_45
opcodes_ed[0x46] = opcode_ed_46
opcodes_ed[0x47] = opcode_ed_47
opcodes_ed[0x48] = opcode_ed_48
opcodes_ed[0x49] = opcode_ed_49
opcodes_ed[0x4a] = opcode_ed_4a
opcodes_ed[0x4b] = opcode_ed_4b
opcodes_ed[0x4c] = opcode_ed_44 #
opcodes_ed[0x4d] = opcode_ed_4d
opcodes_ed[0x4e] = opcode_ed_46 #
opcodes_ed[0x4f] = opcode_ed_4f
opcodes_ed[0x50] = opcode_ed_50
opcodes_ed[0x51] = opcode_ed_51
opcodes_ed[0x52] = opcode_ed_52
opcodes_ed[0x53] = opcode_ed_53
opcodes_ed[0x54] = opcode_ed_44 #
opcodes_ed[0x55] = opcode_ed_45 #
opcodes_ed[0x56] = opcode_ed_56
opcodes_ed[0x57] = opcode_ed_57
opcodes_ed[0x58] = opcode_ed_58
opcodes_ed[0x59] = opcode_ed_59
opcodes_ed[0x5a] = opcode_ed_5a
opcodes_ed[0x5b] = opcode_ed_5b
opcodes_ed[0x5c] = opcode_ed_44 #
opcodes_ed[0x5d] = opcode_ed_45 #
opcodes_ed[0x5e] = opcode_ed_5e
opcodes_ed[0x5f] = opcode_ed_5f
opcodes_ed[0x60] = opcode_ed_60
opcodes_ed[0x61] = opcode_ed_61
opcodes_ed[0x62] = opcode_ed_62
opcodes_ed[0x63] = opcode_ed_63
opcodes_ed[0x64] = opcode_ed_44 #
opcodes_ed[0x65] = opcode_ed_45 #
opcodes_ed[0x66] = opcode_ed_46 #
opcodes_ed[0x67] = opcode_ed_67
opcodes_ed[0x68] = opcode_ed_68
opcodes_ed[0x69] = opcode_ed_69
opcodes_ed[0x6a] = opcode_ed_6a
opcodes_ed[0x6b] = opcode_ed_6b
opcodes_ed[0x6c] = opcode_ed_44 #
opcodes_ed[0x6d] = opcode_ed_45 #
opcodes_ed[0x6e] = opcode_ed_46 #
opcodes_ed[0x6f] = opcode_ed_6f
opcodes_ed[0x70] = opcode_ed_70
opcodes_ed[0x71] = opcode_ed_71
opcodes_ed[0x72] = opcode_ed_72
opcodes_ed[0x73] = opcode_ed_73
opcodes_ed[0x74] = opcode_ed_44 #
opcodes_ed[0x75] = opcode_ed_45 #
opcodes_ed[0x76] = opcode_ed_56 #
opcodes_ed[0x77] = opcode_nop
opcodes_ed[0x78] = opcode_ed_78
opcodes_ed[0x79] = opcode_ed_79
opcodes_ed[0x7a] = opcode_ed_7a
opcodes_ed[0x7b] = opcode_ed_7b
opcodes_ed[0x7c] = opcode_ed_44 #
opcodes_ed[0x7d] = opcode_ed_45 #
opcodes_ed[0x7e] = opcode_ed_7e
opcodes_ed[0x7f] = opcode_nop
opcodes_ed[0x80] = opcode_nop
opcodes_ed[0x81] = opcode_nop
opcodes_ed[0x82] = opcode_nop
opcodes_ed[0x83] = opcode_nop
opcodes_ed[0x84] = opcode_nop
opcodes_ed[0x85] = opcode_nop
opcodes_ed[0x86] = opcode_nop
opcodes_ed[0x87] = opcode_nop
opcodes_ed[0x88] = opcode_nop
opcodes_ed[0x89] = opcode_nop
opcodes_ed[0x8a] = opcode_nop
opcodes_ed[0x8b] = opcode_nop
opcodes_ed[0x8c] = opcode_nop
opcodes_ed[0x8d] = opcode_nop
opcodes_ed[0x8e] = opcode_nop
opcodes_ed[0x8f] = opcode_nop
opcodes_ed[0x90] = opcode_nop
opcodes_ed[0x91] = opcode_nop
opcodes_ed[0x92] = opcode_nop
opcodes_ed[0x93] = opcode_nop
opcodes_ed[0x94] = opcode_nop
opcodes_ed[0x95] = opcode_nop
opcodes_ed[0x96] = opcode_nop
opcodes_ed[0x97] = opcode_nop
opcodes_ed[0x98] = opcode_nop
opcodes_ed[0x99] = opcode_nop
opcodes_ed[0x9a] = opcode_nop
opcodes_ed[0x9b] = opcode_nop
opcodes_ed[0x9c] = opcode_nop
opcodes_ed[0x9d] = opcode_nop
opcodes_ed[0x9e] = opcode_nop
opcodes_ed[0x9f] = opcode_nop
opcodes_ed[0xa0] = opcode_ed_a0
opcodes_ed[0xa1] = opcode_ed_a1
opcodes_ed[0xa2] = opcode_ed_a2
opcodes_ed[0xa3] = opcode_ed_a3
opcodes_ed[0xa4] = opcode_nop
opcodes_ed[0xa5] = opcode_nop
opcodes_ed[0xa6] = opcode_nop
opcodes_ed[0xa7] = opcode_nop
opcodes_ed[0xa8] = opcode_ed_a8
opcodes_ed[0xa9] = opcode_ed_a9
opcodes_ed[0xaa] = opcode_ed_aa
opcodes_ed[0xab] = opcode_ed_ab
opcodes_ed[0xac] = opcode_nop
opcodes_ed[0xad] = opcode_nop
opcodes_ed[0xae] = opcode_nop
opcodes_ed[0xaf] = opcode_nop
opcodes_ed[0xb0] = opcode_ed_b0
opcodes_ed[0xb1] = opcode_ed_b1
opcodes_ed[0xb2] = opcode_ed_b2
opcodes_ed[0xb3] = opcode_ed_b3
opcodes_ed[0xb4] = opcode_nop
opcodes_ed[0xb5] = opcode_nop
opcodes_ed[0xb6] = opcode_nop
opcodes_ed[0xb7] = opcode_nop
opcodes_ed[0xb8] = opcode_ed_b8
opcodes_ed[0xb9] = opcode_ed_b9
opcodes_ed[0xba] = opcode_ed_ba
opcodes_ed[0xbb] = opcode_ed_bb
opcodes_ed[0xbc] = opcode_nop
opcodes_ed[0xbd] = opcode_nop
opcodes_ed[0xbe] = opcode_nop
opcodes_ed[0xbf] = opcode_nop
opcodes_ed[0xc0] = opcode_nop
opcodes_ed[0xc1] = opcode_nop
opcodes_ed[0xc2] = opcode_nop
opcodes_ed[0xc3] = opcode_nop
opcodes_ed[0xc4] = opcode_nop
opcodes_ed[0xc5] = opcode_nop
opcodes_ed[0xc6] = opcode_nop
opcodes_ed[0xc7] = opcode_nop
opcodes_ed[0xc8] = opcode_nop
opcodes_ed[0xc9] = opcode_nop
opcodes_ed[0xca] = opcode_nop
opcodes_ed[0xcb] = opcode_nop
opcodes_ed[0xcc] = opcode_nop
opcodes_ed[0xcd] = opcode_ed_cd
opcodes_ed[0xce] = opcode_nop
opcodes_ed[0xcf] = opcode_nop
opcodes_ed[0xd0] = opcode_nop
opcodes_ed[0xd1] = opcode_nop
opcodes_ed[0xd2] = opcode_nop
opcodes_ed[0xd3] = opcode_nop
opcodes_ed[0xd4] = opcode_nop
opcodes_ed[0xd5] = opcode_nop
opcodes_ed[0xd6] = opcode_nop
opcodes_ed[0xd7] = opcode_nop
opcodes_ed[0xd8] = opcode_nop
opcodes_ed[0xd9] = opcode_nop
opcodes_ed[0xda] = opcode_nop
opcodes_ed[0xdb] = opcode_nop
opcodes_ed[0xdc] = opcode_nop
opcodes_ed[0xdd] = opcode_nop
opcodes_ed[0xde] = opcode_nop
opcodes_ed[0xdf] = opcode_nop
opcodes_ed[0xe0] = opcode_nop
opcodes_ed[0xe1] = opcode_nop
opcodes_ed[0xe2] = opcode_nop
opcodes_ed[0xe3] = opcode_nop
opcodes_ed[0xe4] = opcode_nop
opcodes_ed[0xe5] = opcode_nop
opcodes_ed[0xe6] = opcode_nop
opcodes_ed[0xe7] = opcode_nop
opcodes_ed[0xe8] = opcode_nop
opcodes_ed[0xe9] = opcode_nop
opcodes_ed[0xea] = opcode_nop
opcodes_ed[0xeb] = opcode_nop
opcodes_ed[0xec] = opcode_nop
opcodes_ed[0xed] = opcode_nop
opcodes_ed[0xee] = opcode_nop
opcodes_ed[0xef] = opcode_nop
opcodes_ed[0xf0] = opcode_nop
opcodes_ed[0xf1] = opcode_nop
opcodes_ed[0xf2] = opcode_nop
opcodes_ed[0xf3] = opcode_nop
opcodes_ed[0xf4] = opcode_nop
opcodes_ed[0xf5] = opcode_nop
opcodes_ed[0xf6] = opcode_nop
opcodes_ed[0xf7] = opcode_nop
opcodes_ed[0xf8] = opcode_nop
opcodes_ed[0xf9] = opcode_nop
opcodes_ed[0xfa] = opcode_nop
opcodes_ed[0xfb] = opcode_nop
opcodes_ed[0xfc] = opcode_nop
opcodes_ed[0xfd] = opcode_nop
opcodes_ed[0xfe] = opcode_nop
opcodes_ed[0xff] = opcode_nop

opcodes_fd[0x0] = opcode_nop
opcodes_fd[0x1] = opcode_1
opcodes_fd[0x2] = opcode_2
opcodes_fd[0x3] = opcode_3
opcodes_fd[0x4] = opcode_4
opcodes_fd[0x5] = opcode_5
opcodes_fd[0x6] = opcode_6
opcodes_fd[0x7] = opcode_7
opcodes_fd[0x8] = opcode_8
opcodes_fd[0x9] = opcode_fd_9
opcodes_fd[0xa] = opcode_a
opcodes_fd[0xb] = opcode_b
opcodes_fd[0xc] = opcode_c
opcodes_fd[0xd] = opcode_d
opcodes_fd[0xe] = opcode_e
opcodes_fd[0xf] = opcode_f
opcodes_fd[0x10] = opcode_10
opcodes_fd[0x11] = opcode_11
opcodes_fd[0x12] = opcode_12
opcodes_fd[0x13] = opcode_13
opcodes_fd[0x14] = opcode_14
opcodes_fd[0x15] = opcode_15
opcodes_fd[0x16] = opcode_16
opcodes_fd[0x17] = opcode_17
opcodes_fd[0x18] = opcode_18
opcodes_fd[0x19] = opcode_fd_19
opcodes_fd[0x1a] = opcode_1a
opcodes_fd[0x1b] = opcode_1b
opcodes_fd[0x1c] = opcode_1c
opcodes_fd[0x1d] = opcode_1d
opcodes_fd[0x1e] = opcode_1e
opcodes_fd[0x1f] = opcode_1f
opcodes_fd[0x20] = opcode_20
opcodes_fd[0x21] = opcode_fd_21
opcodes_fd[0x22] = opcode_fd_22
opcodes_fd[0x23] = opcode_fd_23
opcodes_fd[0x24] = opcode_fd_24
opcodes_fd[0x25] = opcode_fd_25
opcodes_fd[0x26] = opcode_fd_26
opcodes_fd[0x27] = opcode_27
opcodes_fd[0x28] = opcode_28
opcodes_fd[0x29] = opcode_fd_29
opcodes_fd[0x2a] = opcode_fd_2a
opcodes_fd[0x2b] = opcode_fd_2b
opcodes_fd[0x2c] = opcode_fd_2c
opcodes_fd[0x2d] = opcode_fd_2d
opcodes_fd[0x2e] = opcode_fd_2e
opcodes_fd[0x2f] = opcode_2f
opcodes_fd[0x30] = opcode_30
opcodes_fd[0x31] = opcode_31
opcodes_fd[0x32] = opcode_32
opcodes_fd[0x33] = opcode_33
opcodes_fd[0x34] = opcode_fd_34
opcodes_fd[0x35] = opcode_fd_35
opcodes_fd[0x36] = opcode_fd_36
opcodes_fd[0x37] = opcode_37
opcodes_fd[0x38] = opcode_38
opcodes_fd[0x39] = opcode_fd_39
opcodes_fd[0x3a] = opcode_3a
opcodes_fd[0x3b] = opcode_3b
opcodes_fd[0x3c] = opcode_3c
opcodes_fd[0x3d] = opcode_3d
opcodes_fd[0x3e] = opcode_3e
opcodes_fd[0x3f] = opcode_3f
opcodes_fd[0x40] = opcode_40
opcodes_fd[0x41] = opcode_41
opcodes_fd[0x42] = opcode_42
opcodes_fd[0x43] = opcode_43
opcodes_fd[0x44] = opcode_fd_44
opcodes_fd[0x45] = opcode_fd_45
opcodes_fd[0x46] = opcode_fd_46
opcodes_fd[0x47] = opcode_47
opcodes_fd[0x48] = opcode_48
opcodes_fd[0x49] = opcode_49
opcodes_fd[0x4a] = opcode_4a
opcodes_fd[0x4b] = opcode_4b
opcodes_fd[0x4c] = opcode_fd_4c
opcodes_fd[0x4d] = opcode_fd_4d
opcodes_fd[0x4e] = opcode_fd_4e
opcodes_fd[0x4f] = opcode_4f
opcodes_fd[0x50] = opcode_50
opcodes_fd[0x51] = opcode_51
opcodes_fd[0x52] = opcode_52
opcodes_fd[0x53] = opcode_53
opcodes_fd[0x54] = opcode_fd_54
opcodes_fd[0x55] = opcode_fd_55
opcodes_fd[0x56] = opcode_fd_56
opcodes_fd[0x57] = opcode_57
opcodes_fd[0x58] = opcode_58
opcodes_fd[0x59] = opcode_59
opcodes_fd[0x5a] = opcode_5a
opcodes_fd[0x5b] = opcode_5b
opcodes_fd[0x5c] = opcode_fd_5c
opcodes_fd[0x5d] = opcode_fd_5d
opcodes_fd[0x5e] = opcode_fd_5e
opcodes_fd[0x5f] = opcode_5f
opcodes_fd[0x60] = opcode_fd_60
opcodes_fd[0x61] = opcode_fd_61
opcodes_fd[0x62] = opcode_fd_62
opcodes_fd[0x63] = opcode_fd_63
opcodes_fd[0x64] = opcode_fd_64
opcodes_fd[0x65] = opcode_fd_65
opcodes_fd[0x66] = opcode_fd_66
opcodes_fd[0x67] = opcode_fd_67
opcodes_fd[0x68] = opcode_fd_68
opcodes_fd[0x69] = opcode_fd_69
opcodes_fd[0x6a] = opcode_fd_6a
opcodes_fd[0x6b] = opcode_fd_6b
opcodes_fd[0x6c] = opcode_fd_6c
opcodes_fd[0x6d] = opcode_fd_6d
opcodes_fd[0x6e] = opcode_fd_6e
opcodes_fd[0x6f] = opcode_fd_6f
opcodes_fd[0x70] = opcode_fd_70
opcodes_fd[0x71] = opcode_fd_71
opcodes_fd[0x72] = opcode_fd_72
opcodes_fd[0x73] = opcode_fd_73
opcodes_fd[0x74] = opcode_fd_74
opcodes_fd[0x75] = opcode_fd_75
opcodes_fd[0x76] = opcode_76
opcodes_fd[0x77] = opcode_fd_77
opcodes_fd[0x78] = opcode_78
opcodes_fd[0x79] = opcode_79
opcodes_fd[0x7a] = opcode_7a
opcodes_fd[0x7b] = opcode_7b
opcodes_fd[0x7c] = opcode_fd_7c
opcodes_fd[0x7d] = opcode_fd_7d
opcodes_fd[0x7e] = opcode_fd_7e
opcodes_fd[0x7f] = opcode_7f
opcodes_fd[0x80] = opcode_80
opcodes_fd[0x81] = opcode_81
opcodes_fd[0x82] = opcode_82
opcodes_fd[0x83] = opcode_83
opcodes_fd[0x84] = opcode_fd_84
opcodes_fd[0x85] = opcode_fd_85
opcodes_fd[0x86] = opcode_fd_86
opcodes_fd[0x87] = opcode_87
opcodes_fd[0x88] = opcode_88
opcodes_fd[0x89] = opcode_89
opcodes_fd[0x8a] = opcode_8a
opcodes_fd[0x8b] = opcode_8b
opcodes_fd[0x8c] = opcode_fd_8c
opcodes_fd[0x8d] = opcode_fd_8d
opcodes_fd[0x8e] = opcode_fd_8e
opcodes_fd[0x8f] = opcode_8f
opcodes_fd[0x90] = opcode_90
opcodes_fd[0x91] = opcode_91
opcodes_fd[0x92] = opcode_92
opcodes_fd[0x93] = opcode_93
opcodes_fd[0x94] = opcode_fd_94
opcodes_fd[0x95] = opcode_fd_95
opcodes_fd[0x96] = opcode_fd_96
opcodes_fd[0x97] = opcode_97
opcodes_fd[0x98] = opcode_98
opcodes_fd[0x99] = opcode_99
opcodes_fd[0x9a] = opcode_9a
opcodes_fd[0x9b] = opcode_9b
opcodes_fd[0x9c] = opcode_fd_9c
opcodes_fd[0x9d] = opcode_fd_9d
opcodes_fd[0x9e] = opcode_fd_9e
opcodes_fd[0x9f] = opcode_9f
opcodes_fd[0xa0] = opcode_a0
opcodes_fd[0xa1] = opcode_a1
opcodes_fd[0xa2] = opcode_a2
opcodes_fd[0xa3] = opcode_a3
opcodes_fd[0xa4] = opcode_fd_a4
opcodes_fd[0xa5] = opcode_fd_a5
opcodes_fd[0xa6] = opcode_fd_a6
opcodes_fd[0xa7] = opcode_a7
opcodes_fd[0xa8] = opcode_a8
opcodes_fd[0xa9] = opcode_a9
opcodes_fd[0xaa] = opcode_aa
opcodes_fd[0xab] = opcode_ab
opcodes_fd[0xac] = opcode_fd_ac
opcodes_fd[0xad] = opcode_fd_ad
opcodes_fd[0xae] = opcode_fd_ae
opcodes_fd[0xaf] = opcode_af
opcodes_fd[0xb0] = opcode_b0
opcodes_fd[0xb1] = opcode_b1
opcodes_fd[0xb2] = opcode_b2
opcodes_fd[0xb3] = opcode_b3
opcodes_fd[0xb4] = opcode_fd_b4
opcodes_fd[0xb5] = opcode_fd_b5
opcodes_fd[0xb6] = opcode_fd_b6
opcodes_fd[0xb7] = opcode_b7
opcodes_fd[0xb8] = opcode_b8
opcodes_fd[0xb9] = opcode_b9
opcodes_fd[0xba] = opcode_ba
opcodes_fd[0xbb] = opcode_bb
opcodes_fd[0xbc] = opcode_fd_bc
opcodes_fd[0xbd] = opcode_fd_bd
opcodes_fd[0xbe] = opcode_fd_be
opcodes_fd[0xbf] = opcode_bf
opcodes_fd[0xc0] = opcode_c0
opcodes_fd[0xc1] = opcode_c1
opcodes_fd[0xc2] = opcode_c2
opcodes_fd[0xc3] = opcode_c3
opcodes_fd[0xc4] = opcode_c4
opcodes_fd[0xc5] = opcode_c5
opcodes_fd[0xc6] = opcode_c6
opcodes_fd[0xc7] = opcode_c7
opcodes_fd[0xc8] = opcode_c8
opcodes_fd[0xc9] = opcode_c9
opcodes_fd[0xca] = opcode_ca
opcodes_fd[0xcb] = opcode_fdcb
opcodes_fd[0xcc] = opcode_cc
opcodes_fd[0xcd] = opcode_cd
opcodes_fd[0xce] = opcode_ce
opcodes_fd[0xcf] = opcode_cf
opcodes_fd[0xd0] = opcode_d0
opcodes_fd[0xd1] = opcode_d1
opcodes_fd[0xd2] = opcode_d2
opcodes_fd[0xd3] = opcode_d3
opcodes_fd[0xd4] = opcode_d4
opcodes_fd[0xd5] = opcode_d5
opcodes_fd[0xd6] = opcode_d6
opcodes_fd[0xd7] = opcode_d7
opcodes_fd[0xd8] = opcode_d8
opcodes_fd[0xd9] = opcode_d9
opcodes_fd[0xda] = opcode_da
opcodes_fd[0xdb] = opcode_db
opcodes_fd[0xdc] = opcode_dc
opcodes_fd[0xdd] = opcode_nop
opcodes_fd[0xde] = opcode_de
opcodes_fd[0xdf] = opcode_df
opcodes_fd[0xe0] = opcode_e0
opcodes_fd[0xe1] = opcode_fd_e1
opcodes_fd[0xe2] = opcode_e2
opcodes_fd[0xe3] = opcode_fd_e3
opcodes_fd[0xe4] = opcode_e4
opcodes_fd[0xe5] = opcode_fd_e5
opcodes_fd[0xe6] = opcode_e6
opcodes_fd[0xe7] = opcode_e7
opcodes_fd[0xe8] = opcode_e8
opcodes_fd[0xe9] = opcode_fd_e9
opcodes_fd[0xea] = opcode_ea
opcodes_fd[0xeb] = opcode_eb
opcodes_fd[0xec] = opcode_ec
opcodes_fd[0xee] = opcode_ee
opcodes_fd[0xef] = opcode_ef
opcodes_fd[0xf0] = opcode_f0
opcodes_fd[0xf1] = opcode_f1
opcodes_fd[0xf2] = opcode_f2
opcodes_fd[0xf3] = opcode_f3
opcodes_fd[0xf4] = opcode_f4
opcodes_fd[0xf5] = opcode_f5
opcodes_fd[0xf6] = opcode_f6
opcodes_fd[0xf7] = opcode_f7
opcodes_fd[0xf8] = opcode_f8
opcodes_fd[0xf9] = opcode_fd_f9
opcodes_fd[0xfa] = opcode_fa
opcodes_fd[0xfb] = opcode_fb
opcodes_fd[0xfc] = opcode_fc
opcodes_fd[0xfd] = opcode_nop
opcodes_fd[0xfe] = opcode_fe
opcodes_fd[0xff] = opcode_ff

opcodes_fdcb[0x0] = opcode_fdcb_0
opcodes_fdcb[0x1] = opcode_fdcb_1
opcodes_fdcb[0x2] = opcode_fdcb_2
opcodes_fdcb[0x3] = opcode_fdcb_3
opcodes_fdcb[0x4] = opcode_fdcb_4
opcodes_fdcb[0x5] = opcode_fdcb_5
opcodes_fdcb[0x6] = opcode_fdcb_6
opcodes_fdcb[0x7] = opcode_fdcb_7
opcodes_fdcb[0x8] = opcode_fdcb_8
opcodes_fdcb[0x9] = opcode_fdcb_9
opcodes_fdcb[0xa] = opcode_fdcb_a
opcodes_fdcb[0xb] = opcode_fdcb_b
opcodes_fdcb[0xc] = opcode_fdcb_c
opcodes_fdcb[0xd] = opcode_fdcb_d
opcodes_fdcb[0xe] = opcode_fdcb_e
opcodes_fdcb[0xf] = opcode_fdcb_f
opcodes_fdcb[0x10] = opcode_fdcb_10
opcodes_fdcb[0x11] = opcode_fdcb_11
opcodes_fdcb[0x12] = opcode_fdcb_12
opcodes_fdcb[0x13] = opcode_fdcb_13
opcodes_fdcb[0x14] = opcode_fdcb_14
opcodes_fdcb[0x15] = opcode_fdcb_15
opcodes_fdcb[0x16] = opcode_fdcb_16
opcodes_fdcb[0x17] = opcode_fdcb_17
opcodes_fdcb[0x18] = opcode_fdcb_18
opcodes_fdcb[0x19] = opcode_fdcb_19
opcodes_fdcb[0x1a] = opcode_fdcb_1a
opcodes_fdcb[0x1b] = opcode_fdcb_1b
opcodes_fdcb[0x1c] = opcode_fdcb_1c
opcodes_fdcb[0x1d] = opcode_fdcb_1d
opcodes_fdcb[0x1e] = opcode_fdcb_1e
opcodes_fdcb[0x1f] = opcode_fdcb_1f
opcodes_fdcb[0x20] = opcode_fdcb_20
opcodes_fdcb[0x21] = opcode_fdcb_21
opcodes_fdcb[0x22] = opcode_fdcb_22
opcodes_fdcb[0x23] = opcode_fdcb_23
opcodes_fdcb[0x24] = opcode_fdcb_24
opcodes_fdcb[0x25] = opcode_fdcb_25
opcodes_fdcb[0x26] = opcode_fdcb_26
opcodes_fdcb[0x27] = opcode_fdcb_27
opcodes_fdcb[0x28] = opcode_fdcb_28
opcodes_fdcb[0x29] = opcode_fdcb_29
opcodes_fdcb[0x2a] = opcode_fdcb_2a
opcodes_fdcb[0x2b] = opcode_fdcb_2b
opcodes_fdcb[0x2c] = opcode_fdcb_2c
opcodes_fdcb[0x2d] = opcode_fdcb_2d
opcodes_fdcb[0x2e] = opcode_fdcb_2e
opcodes_fdcb[0x2f] = opcode_fdcb_2f
opcodes_fdcb[0x30] = opcode_fdcb_30
opcodes_fdcb[0x31] = opcode_fdcb_31
opcodes_fdcb[0x32] = opcode_fdcb_32
opcodes_fdcb[0x33] = opcode_fdcb_33
opcodes_fdcb[0x34] = opcode_fdcb_34
opcodes_fdcb[0x35] = opcode_fdcb_35
opcodes_fdcb[0x36] = opcode_fdcb_36
opcodes_fdcb[0x37] = opcode_fdcb_37
opcodes_fdcb[0x38] = opcode_fdcb_38
opcodes_fdcb[0x39] = opcode_fdcb_39
opcodes_fdcb[0x3a] = opcode_fdcb_3a
opcodes_fdcb[0x3b] = opcode_fdcb_3b
opcodes_fdcb[0x3c] = opcode_fdcb_3c
opcodes_fdcb[0x3d] = opcode_fdcb_3d
opcodes_fdcb[0x3e] = opcode_fdcb_3e
opcodes_fdcb[0x3f] = opcode_fdcb_3f
opcodes_fdcb[0x40] = opcode_fdcb_40
opcodes_fdcb[0x41] = opcode_fdcb_41
opcodes_fdcb[0x42] = opcode_fdcb_42
opcodes_fdcb[0x43] = opcode_fdcb_43
opcodes_fdcb[0x44] = opcode_fdcb_44
opcodes_fdcb[0x45] = opcode_fdcb_45
opcodes_fdcb[0x46] = opcode_fdcb_46
opcodes_fdcb[0x47] = opcode_fdcb_47
opcodes_fdcb[0x48] = opcode_fdcb_48
opcodes_fdcb[0x49] = opcode_fdcb_49
opcodes_fdcb[0x4a] = opcode_fdcb_4a
opcodes_fdcb[0x4b] = opcode_fdcb_4b
opcodes_fdcb[0x4c] = opcode_fdcb_4c
opcodes_fdcb[0x4d] = opcode_fdcb_4d
opcodes_fdcb[0x4e] = opcode_fdcb_4e
opcodes_fdcb[0x4f] = opcode_fdcb_4f
opcodes_fdcb[0x50] = opcode_fdcb_50
opcodes_fdcb[0x51] = opcode_fdcb_51
opcodes_fdcb[0x52] = opcode_fdcb_52
opcodes_fdcb[0x53] = opcode_fdcb_53
opcodes_fdcb[0x54] = opcode_fdcb_54
opcodes_fdcb[0x55] = opcode_fdcb_55
opcodes_fdcb[0x56] = opcode_fdcb_56
opcodes_fdcb[0x57] = opcode_fdcb_57
opcodes_fdcb[0x58] = opcode_fdcb_58
opcodes_fdcb[0x59] = opcode_fdcb_59
opcodes_fdcb[0x5a] = opcode_fdcb_5a
opcodes_fdcb[0x5b] = opcode_fdcb_5b
opcodes_fdcb[0x5c] = opcode_fdcb_5c
opcodes_fdcb[0x5d] = opcode_fdcb_5d
opcodes_fdcb[0x5e] = opcode_fdcb_5e
opcodes_fdcb[0x5f] = opcode_fdcb_5f
opcodes_fdcb[0x60] = opcode_fdcb_60
opcodes_fdcb[0x61] = opcode_fdcb_61
opcodes_fdcb[0x62] = opcode_fdcb_62
opcodes_fdcb[0x63] = opcode_fdcb_63
opcodes_fdcb[0x64] = opcode_fdcb_64
opcodes_fdcb[0x65] = opcode_fdcb_65
opcodes_fdcb[0x66] = opcode_fdcb_66
opcodes_fdcb[0x67] = opcode_fdcb_67
opcodes_fdcb[0x68] = opcode_fdcb_68
opcodes_fdcb[0x69] = opcode_fdcb_69
opcodes_fdcb[0x6a] = opcode_fdcb_6a
opcodes_fdcb[0x6b] = opcode_fdcb_6b
opcodes_fdcb[0x6c] = opcode_fdcb_6c
opcodes_fdcb[0x6d] = opcode_fdcb_6d
opcodes_fdcb[0x6e] = opcode_fdcb_6e
opcodes_fdcb[0x6f] = opcode_fdcb_6f
opcodes_fdcb[0x70] = opcode_fdcb_70
opcodes_fdcb[0x71] = opcode_fdcb_71
opcodes_fdcb[0x72] = opcode_fdcb_72
opcodes_fdcb[0x73] = opcode_fdcb_73
opcodes_fdcb[0x74] = opcode_fdcb_74
opcodes_fdcb[0x75] = opcode_fdcb_75
opcodes_fdcb[0x76] = opcode_fdcb_76
opcodes_fdcb[0x77] = opcode_fdcb_77
opcodes_fdcb[0x78] = opcode_fdcb_78
opcodes_fdcb[0x79] = opcode_fdcb_79
opcodes_fdcb[0x7a] = opcode_fdcb_7a
opcodes_fdcb[0x7b] = opcode_fdcb_7b
opcodes_fdcb[0x7c] = opcode_fdcb_7c
opcodes_fdcb[0x7d] = opcode_fdcb_7d
opcodes_fdcb[0x7e] = opcode_fdcb_7e
opcodes_fdcb[0x7f] = opcode_fdcb_7f
opcodes_fdcb[0x80] = opcode_fdcb_80
opcodes_fdcb[0x81] = opcode_fdcb_81
opcodes_fdcb[0x82] = opcode_fdcb_82
opcodes_fdcb[0x83] = opcode_fdcb_83
opcodes_fdcb[0x84] = opcode_fdcb_84
opcodes_fdcb[0x85] = opcode_fdcb_85
opcodes_fdcb[0x86] = opcode_fdcb_86
opcodes_fdcb[0x87] = opcode_fdcb_87
opcodes_fdcb[0x88] = opcode_fdcb_88
opcodes_fdcb[0x89] = opcode_fdcb_89
opcodes_fdcb[0x8a] = opcode_fdcb_8a
opcodes_fdcb[0x8b] = opcode_fdcb_8b
opcodes_fdcb[0x8c] = opcode_fdcb_8c
opcodes_fdcb[0x8d] = opcode_fdcb_8d
opcodes_fdcb[0x8e] = opcode_fdcb_8e
opcodes_fdcb[0x8f] = opcode_fdcb_8f
opcodes_fdcb[0x90] = opcode_fdcb_90
opcodes_fdcb[0x91] = opcode_fdcb_91
opcodes_fdcb[0x92] = opcode_fdcb_92
opcodes_fdcb[0x93] = opcode_fdcb_93
opcodes_fdcb[0x94] = opcode_fdcb_94
opcodes_fdcb[0x95] = opcode_fdcb_95
opcodes_fdcb[0x96] = opcode_fdcb_96
opcodes_fdcb[0x97] = opcode_fdcb_97
opcodes_fdcb[0x98] = opcode_fdcb_98
opcodes_fdcb[0x99] = opcode_fdcb_99
opcodes_fdcb[0x9a] = opcode_fdcb_9a
opcodes_fdcb[0x9b] = opcode_fdcb_9b
opcodes_fdcb[0x9c] = opcode_fdcb_9c
opcodes_fdcb[0x9d] = opcode_fdcb_9d
opcodes_fdcb[0x9e] = opcode_fdcb_9e
opcodes_fdcb[0x9f] = opcode_fdcb_9f
opcodes_fdcb[0xa0] = opcode_fdcb_a0
opcodes_fdcb[0xa1] = opcode_fdcb_a1
opcodes_fdcb[0xa2] = opcode_fdcb_a2
opcodes_fdcb[0xa3] = opcode_fdcb_a3
opcodes_fdcb[0xa4] = opcode_fdcb_a4
opcodes_fdcb[0xa5] = opcode_fdcb_a5
opcodes_fdcb[0xa6] = opcode_fdcb_a6
opcodes_fdcb[0xa7] = opcode_fdcb_a7
opcodes_fdcb[0xa8] = opcode_fdcb_a8
opcodes_fdcb[0xa9] = opcode_fdcb_a9
opcodes_fdcb[0xaa] = opcode_fdcb_aa
opcodes_fdcb[0xab] = opcode_fdcb_ab
opcodes_fdcb[0xac] = opcode_fdcb_ac
opcodes_fdcb[0xad] = opcode_fdcb_ad
opcodes_fdcb[0xae] = opcode_fdcb_ae
opcodes_fdcb[0xaf] = opcode_fdcb_af
opcodes_fdcb[0xb0] = opcode_fdcb_b0
opcodes_fdcb[0xb1] = opcode_fdcb_b1
opcodes_fdcb[0xb2] = opcode_fdcb_b2
opcodes_fdcb[0xb3] = opcode_fdcb_b3
opcodes_fdcb[0xb4] = opcode_fdcb_b4
opcodes_fdcb[0xb5] = opcode_fdcb_b5
opcodes_fdcb[0xb6] = opcode_fdcb_b6
opcodes_fdcb[0xb7] = opcode_fdcb_b7
opcodes_fdcb[0xb8] = opcode_fdcb_b8
opcodes_fdcb[0xb9] = opcode_fdcb_b9
opcodes_fdcb[0xba] = opcode_fdcb_ba
opcodes_fdcb[0xbb] = opcode_fdcb_bb
opcodes_fdcb[0xbc] = opcode_fdcb_bc
opcodes_fdcb[0xbd] = opcode_fdcb_bd
opcodes_fdcb[0xbe] = opcode_fdcb_be
opcodes_fdcb[0xbf] = opcode_fdcb_bf
opcodes_fdcb[0xc0] = opcode_fdcb_c0
opcodes_fdcb[0xc1] = opcode_fdcb_c1
opcodes_fdcb[0xc2] = opcode_fdcb_c2
opcodes_fdcb[0xc3] = opcode_fdcb_c3
opcodes_fdcb[0xc4] = opcode_fdcb_c4
opcodes_fdcb[0xc5] = opcode_fdcb_c5
opcodes_fdcb[0xc6] = opcode_fdcb_c6
opcodes_fdcb[0xc7] = opcode_fdcb_c7
opcodes_fdcb[0xc8] = opcode_fdcb_c8
opcodes_fdcb[0xc9] = opcode_fdcb_c9
opcodes_fdcb[0xca] = opcode_fdcb_ca
opcodes_fdcb[0xcb] = opcode_fdcb_cb
opcodes_fdcb[0xcc] = opcode_fdcb_cc
opcodes_fdcb[0xcd] = opcode_fdcb_cd
opcodes_fdcb[0xce] = opcode_fdcb_ce
opcodes_fdcb[0xcf] = opcode_fdcb_cf
opcodes_fdcb[0xd0] = opcode_fdcb_d0
opcodes_fdcb[0xd1] = opcode_fdcb_d1
opcodes_fdcb[0xd2] = opcode_fdcb_d2
opcodes_fdcb[0xd3] = opcode_fdcb_d3
opcodes_fdcb[0xd4] = opcode_fdcb_d4
opcodes_fdcb[0xd5] = opcode_fdcb_d5
opcodes_fdcb[0xd6] = opcode_fdcb_d6
opcodes_fdcb[0xd7] = opcode_fdcb_d7
opcodes_fdcb[0xd8] = opcode_fdcb_d8
opcodes_fdcb[0xd9] = opcode_fdcb_d9
opcodes_fdcb[0xda] = opcode_fdcb_da
opcodes_fdcb[0xdb] = opcode_fdcb_db
opcodes_fdcb[0xdc] = opcode_fdcb_dc
opcodes_fdcb[0xdd] = opcode_fdcb_dd
opcodes_fdcb[0xde] = opcode_fdcb_de
opcodes_fdcb[0xdf] = opcode_fdcb_df
opcodes_fdcb[0xe0] = opcode_fdcb_e0
opcodes_fdcb[0xe1] = opcode_fdcb_e1
opcodes_fdcb[0xe2] = opcode_fdcb_e2
opcodes_fdcb[0xe3] = opcode_fdcb_e3
opcodes_fdcb[0xe4] = opcode_fdcb_e4
opcodes_fdcb[0xe5] = opcode_fdcb_e5
opcodes_fdcb[0xe6] = opcode_fdcb_e6
opcodes_fdcb[0xe7] = opcode_fdcb_e7
opcodes_fdcb[0xe8] = opcode_fdcb_e8
opcodes_fdcb[0xe9] = opcode_fdcb_e9
opcodes_fdcb[0xea] = opcode_fdcb_ea
opcodes_fdcb[0xeb] = opcode_fdcb_eb
opcodes_fdcb[0xec] = opcode_fdcb_ec
opcodes_fdcb[0xed] = opcode_fdcb_ed
opcodes_fdcb[0xee] = opcode_fdcb_ee
opcodes_fdcb[0xef] = opcode_fdcb_ef
opcodes_fdcb[0xf0] = opcode_fdcb_f0
opcodes_fdcb[0xf1] = opcode_fdcb_f1
opcodes_fdcb[0xf2] = opcode_fdcb_f2
opcodes_fdcb[0xf3] = opcode_fdcb_f3
opcodes_fdcb[0xf4] = opcode_fdcb_f4
opcodes_fdcb[0xf5] = opcode_fdcb_f5
opcodes_fdcb[0xf6] = opcode_fdcb_f6
opcodes_fdcb[0xf7] = opcode_fdcb_f7
opcodes_fdcb[0xf8] = opcode_fdcb_f8
opcodes_fdcb[0xf9] = opcode_fdcb_f9
opcodes_fdcb[0xfa] = opcode_fdcb_fa
opcodes_fdcb[0xfb] = opcode_fdcb_fb
opcodes_fdcb[0xfc] = opcode_fdcb_fc
opcodes_fdcb[0xfd] = opcode_fdcb_fd
opcodes_fdcb[0xfe] = opcode_fdcb_fe
opcodes_fdcb[0xff] = opcode_fdcb_ff

#end