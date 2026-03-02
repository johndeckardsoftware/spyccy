import os
from array import array
from tkinter import filedialog

def execute(z80):
    opcode = z80.a
    if opcode == 0:
        load_vt2player_file(z80)
    else:
        pass

def load_vt2player_file(z80):
    file_path = filedialog.askopenfilename(title='Select a file', filetypes=[('PT3 sound', '*.pt3')])
    if file_path:
        with open(file_path, 'rb') as file:
            buffer = array('B')
            buffer_len = os.stat(file_path).st_size
            if buffer_len < 0x2000:
                buffer.fromfile(file, buffer_len)
                dest_addr = z80.pack(z80.h, z80.l)
                for i in range(0, buffer_len):
                    z80.mmu.poke(dest_addr + i, buffer[i])
                z80.h, z80.l = z80.unpack(buffer_len)
            else:
                z80.h = 0; z80.l = 0
    else:
        z80.h = 0; z80.l = 0

    z80.machine.keyboard.reset()
