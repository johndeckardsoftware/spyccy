#
# https://map.grauw.nl/resources/z80instr.php
# https://worldofspectrum.org/faq/reference/z80reference.htm
# http://stor.altervista.org/z80-sub/istruzioni.php
#
from array import array
from tzxtools.tzxlib.z80dis import disassemble
from config import *
import z80tstates

opcodes_trace = {}

#
# log every cpu step
#
trace_enabled = False
log_enabled = False
log_filename = '' 
opcode_sequence = []
opcode_pc = 0
pc_range_enabled = False
pc_range_start = 0
pc_range_end = 0xffff
opcode_list = []
opcode_list_enabled = []
opcode_profile = False
ldir_max_bc = 0
lddr_max_bc = 0

def get_flag_c(F) -> bool:
    return (F & (1 << 0)) != 0

def get_flag_n(F) -> bool:
    return (F & (1 << 1)) != 0

def get_flag_pv(F) -> bool:
    return (F & (1 << 2)) != 0

def get_flag_h(F) -> bool:
    return (F & (1 << 4)) != 0

def get_flag_z(F) -> bool:
    return (F & (1 << 6)) != 0

def get_flag_s(F) -> bool:
    return (F & (1 << 7)) != 0

def reg_str(regs) -> str:
    F = regs['F']
    out = '{ %02x ' % (F & 0xd7)

    out += 's' if F & 0b10000000 else ' '
    out += 'z' if F & 0b1000000 else ' '
    out += '1' if F & 0b100000 else '0'
    out += 'h' if F & 0b10000 else ' '
    out += '1' if F & 0b1000 else '0'
    out += 'v' if F & 0b100 else ' '
    out += 'n' if F & 0b10 else ' '
    out += 'c' if F & 0b1 else ' '

    out += ' | AF: %04x, BC: %04x, DE: %04x, HL: %04x, PC: %04x, SP: %04x, IX: %04x, IY: %04x' % (regs['AF'], regs['BC'], regs['DE'], regs['HL'], regs['pc'], regs['SP'], regs['IX'], regs['IY'])
    #out += ' | AF_: %04x, BC_: %04x, DE_: %04x, HL_: %04x | %04x }' % (regs.AF_.value, regs.BC_.value, regs.DE_.value, regs.HL_.value, mmu.peek16(regs.SP.value))
    out += ' | AF_: %04x, BC_: %04x, DE_: %04x, HL_: %04x | %04x }' % (regs['AF_'], regs['BC_'], regs['DE_'], regs['HL_'], regs['memptr'])
    return out

def init_trace(log='./tmp/z80a.log', pcr_enabled=False, pcr_start=0, pcr_end=0xffff, profile=False, ops_list=[]):
    global trace_enabled, log_enabled, log_filename, pc_range_enabled, pc_range_start, pc_range_end, opcode_profile, opcode_list
    global opcode_list_enabled

    trace_enabled = False
    log_enabled = False
    log_filename = log
    pc_range_enabled = pcr_enabled
    pc_range_start = pcr_start
    pc_range_end = pcr_end
    opcode_profile = profile
    opcode_list = ops_list
    if len(ops_list):
        opcode_list_enabled = True
    else:
        opcode_list_enabled = False

def enable_trace():
    global trace_enabled
    trace_enabled = True

def disable_trace():
    global trace_enabled
    trace_enabled = False

def enable_log():
    global log_enabled
    log_enabled = True

def disable_log():
    global log_enabled
    log_enabled = False

def trace_step(cpu_state):
    global trace_enabled, log_enabled, opcode_sequence, opcode_pc
    if trace_enabled:
        if log_enabled:
            trace = True
            if opcode_list_enabled:
                if not find_opcode(opcode_sequence, opcode_list):
                    trace = False
            if pc_range_enabled:
                if not (opcode_pc >= pc_range_start and opcode_pc <= pc_range_end):
                    trace = False
            if trace:
                #log(f"PC {(opcode_pc):04x} OP {bytearray(opcode_sequence).hex()} {cpu_state['iff1']=} {cpu_state['iff2']=} t={cpu_state['t']} {reg_str(cpu_state)}")
                log(f"PC {(opcode_pc):04x} OP {bytearray(opcode_sequence).hex()} {reg_str(cpu_state)}")

        if opcode_profile:
            end_opcode(cpu_state['t'])

    opcode_sequence.clear()
#

def add_opcode(opcode, pc = -1, t=-1):
    global opcode_sequence, opcode_pc, t_start

    opcode_sequence.append(opcode)
    if pc != -1:
        opcode_pc = pc
    if t != -1:
        t_start = t

def end_opcode(t_end:int):
    global opcode_sequence, t_start

    t = t_end - t_start
    opcode = bytearray(opcode_sequence).hex().upper()
    if opcode in opcodes_trace:
        op = opcodes_trace.get(opcode)
        op['count'] = op['count'] + 1
        if 't0' in op:
            t0 = op['t0']
            if t < t0: op['t0'] = t
        t1 = op['t1']
        if t > t1: op['t1'] = t
    else:
        if opcode in z80tstates.z80_opcodes_tstate:
            if 't0' in z80tstates.z80_opcodes_tstate[opcode]:
                op = {"count": 1, "t1": t, "t0": t}
            else:
                op = {"count": 1, "t1": t}
        else:
            op = {"count": 1, "t1": t}
        opcodes_trace[opcode] = op

    #opcode_sequence.clear()

def find_opcode(ops, op_traceable):
    for opt in op_traceable:
        if opt == ops[0]:
            return True 
    return False

def save():
    with open(Config.get('cpu.profile_file', "./tmp/profile.log"), "w") as p:
        for k, v in sorted(opcodes_trace.items(), key=lambda item: item[1]['count'], reverse=True):
            ba_opcode = bytearray().fromhex(k)
            data = array('B', ba_opcode)
            data.extend([0, 0])
            asm = disassemble(data, 0, 0)[0]
            msg = ''
            t1 = t0 = 0
            op = ba_opcode.hex().upper()
            if op in z80tstates.z80_opcodes_tstate:
                opr = z80tstates.z80_opcodes_tstate[op]
                if 't0' in opr:
                    t0r = opr['t0']
                    t0 = v['t0']
                    if t0 != t0r:
                        msg = f'{t0=} != {t0r=}'
                t1r = opr['t1']
                t1 = v['t1']
                if t1 != t1r:
                    msg = f'{msg} {t1=} != {t1r=}'
            else:
                msg = f'no tstate ref for {op}'
                t0r = 0
                t1r = 0

            if t0:
                tm = f'{t1=} {t0=}'
            else:
                tm = f'{t1=}'

            op_asm = f'{op} {asm:<22}'    
            op_asm = op_asm[:24]
            p.write(f"{op_asm} count: {v['count']:<9}, {tm} {msg}\n")

def clear():
    opcodes_trace.clear()

def log(text):
    log = open(log_filename, 'a')
    log.write(text)
    log.write("\n")
    log.close
