import os
from array import array
from tape_tap import TAPTape
from tape_tzx import TZXTape
from app_globals import APP_NAME
from config import *
from tkinter import messagebox
from tkinter import filedialog
from snapshot import parse_z80_file, parse_szx_file
import binascii

class TapeManager:
    def __init__(self, machine):
        self.machine = machine
        self.ports = None

        # tape object.
        self._tape = None

        # some counters.
        self._pulse_duration_counter = 0
        self._pulse_counter = 0

        # the simulated tape signals which will be sent to the in port are stored in a list.
        self._current_signal = None

        # events
        self.tape_progress = None
        self.tape_status_change = None

        # properties (auto-implemented in c#)
        self.current_tape_position = 0
        self.current_pulse_repetitions = 0
        self.current_pulse_length = 0
        self.curent_signal_is_leader = False
        self.current_block_index = 0
        self.file_path = None
        self.file_name = None
        self.file_type = None
        self.tape_content = None
        self.is_tape_playing = False
        self.is_tape_pause_handled = False
        self.is_recording = False
        self.is_on_block_start = False
        self.is_manually_paused = False
        self.is_speed_loading = True
        self.is_opening = False

        self._low_ula_port_read_frequency_frame_counter = 0
        self._last_read_tape_index = 0

        #user setting
        self.tape_auto_load = Config.get('tape.auto_load', False)
        self.tape_fast_load = Config.get('tape.fast_load', False)
        self.tape_speed_load = False      # actually fixed
        self.tape_edge_detect = False     # actually fixed
        self.tape_auto_pause = False      # actually fixed

        self.dirty = 0
        self.count = 0
        self.patched = 0

        self.new_tape()

    @property
    def current_block(self):
        return self._tape.tape_listing[self.current_block_index]

    @property
    def next_block(self):
        if self.current_tape_position <= 0:
            return self._tape.tape_listing[0]
        elif self.current_block_index < len(self._tape.tape_listing) - 1:
            return self._tape.tape_listing[self.current_block_index + 1]
        else:
            return None

    @property
    def is_tape_empty(self):
        if len(self.tape_content) == 0:
            return True
        else:
            return False

    @property
    def tape_listing(self):
        if self._tape is not None:
            return self._tape.tape_listing
        else:
            return None

    def set_file_path(self, file):
        self.file_path = file
        if file and file != "":
            self.file_name = os.path.split(file)[1]
            self.file_type = file[len(file) - 3 :].lower()
        else:
            self.file_name = ""
            self.file_type = "tap"

    def update_in_port(self, in_port):
        self._in_port = in_port

    def new_tape(self):
        self.tape_content = array('B')
        self._tape = TAPTape(self.tape_content)
        self.set_file_path(None)
        self.is_recording = False
        self.rewind_tape(0)

    def open_tape(self, file):
        if os.path.exists(file):
            self.pause_tape()

            self.is_opening = True

            self.set_file_path(file)
            with open(file, 'rb') as f:
                self.tape_content = array('B')
                self.tape_content.fromfile(f, os.stat(file).st_size)

            if self.file_type == "tap":
                self._tape = TAPTape(self.tape_content)
            elif self.file_type == "tzx":
                self._tape = TZXTape(self.tape_content)

            if len(self._tape.tape_listing) == 0:
                self._tape = None
                messagebox.showerror(APP_NAME, f'{file}: invalid tape file')
                return False

            self.is_opening = False
            self.is_recording = False
            self.rewind_tape(0)

            self.ports = self.machine.ports

            self.auto_load_tape()

            return True
        else:
            return False

    def refresh_tape_content(self):
        self._tape = TAPTape(self.tape_content)
        self.is_recording = True
        self.on_tape_status_change(None)

    def rewind_tape(self, block_index):
        self.current_block_index = block_index
        if self.current_block_index == 0:
            self.current_tape_position = -1
        else:
            self.current_tape_position = self._tape.tape_listing[self.current_block_index].start_position - 1
        self.is_tape_playing = False
        self.is_tape_pause_handled = False  # this ensures that the controller restores the emulation speed when tape loading is finished.
        self.is_on_block_start = True
        self.on_tape_status_change(None)

        self._pulse_counter = 0
        self._pulse_duration_counter = 0
        self.current_pulse_length = 0
        self.current_pulse_repetitions = 0

    def reset_ear_input(self):
        self.ports.ear_input = 0x00

    def play_tape(self, set_audio_to_low):
        # set audio level to "low".
        if self.ports and set_audio_to_low is True:
            self.ports.ear_input = 0x00

        # indicate that tape play has been started.
        self.is_tape_playing = True
        self.is_on_block_start = False
        self.is_manually_paused = False
        self.is_recording = False
        self.is_speed_loading = False

        self.on_tape_status_change(None)

    def pause_tape(self):
        self.is_tape_playing = False
        self.is_tape_pause_handled = False
        self.on_tape_status_change(None)

    def manually_pause_tape(self):
        self.is_tape_playing = False
        self.is_tape_pause_handled = False
        self.is_manually_paused = True
        self.on_tape_status_change(None)

    def process_tape_data(self, elapsed_t_states):
        # check if the current tape position has entered a new tape block.
        if self.next_block is not None and self.current_tape_position > self.next_block.start_position:
            self.select_tape_block(self.current_block_index + 1)

        # keep track of how long time the current pulse has been sustained.
        self._pulse_duration_counter += elapsed_t_states

        # check if a new pulse should be generated.
        if self._pulse_duration_counter >= self.current_pulse_length:
            self._pulse_duration_counter = 0

            self._pulse_counter += 1

            # check if we have reached the end of the current signal.
            if self._pulse_counter >= self.current_pulse_repetitions:
                self.current_tape_position += 1

                # set up the next signal unless the end of the tape has been reached.
                if self.current_tape_position < len(self._tape.signals):
                    self._current_signal = self._tape.signals[self.current_tape_position]

                    self.current_pulse_repetitions = self._current_signal.number_of_pulses
                    self.current_pulse_length = self._current_signal.pulse_length
                    self.curent_signal_is_leader = self._current_signal.is_leader
                    self._pulse_counter = 0
                else:
                    self.rewind_tape(0)

            # if the current signal is a pause, just generate zero to the in port ear input,
            # otherwise toggle the input.
            if self._current_signal.pause is True:
                self.ports.ear_input = 0x00
            elif self._current_signal.force_high is True:
                self.ports.ear_input = 0x40
            elif self._current_signal.force_low is True:
                self.ports.ear_input = 0x00
            else:
                self.ports.ear_input ^= 0x40

            # handle any stop tape command.
            if self._current_signal.stop_tape is True:
                self.pause_tape()

    def skip_signal(self):
        # check that more than 100 pulse repetitions remains for the current signal.
        if self.current_pulse_repetitions > self._pulse_counter + 80:
            # decrease the current pulse repetitions so that only 100 repetitions remains.
            self.current_pulse_repetitions = self._pulse_counter + 80

            # make sure that the remaining pulse repetitions is an even number.
            if 2 * (self.current_pulse_repetitions // 2) != self.current_pulse_repetitions:
                self.current_pulse_repetitions += 1

    def go_to_end_of_block(self, target_block):
        if target_block >= 0 and target_block < len(self._tape.tape_listing) - 1:
            self.select_tape_block(target_block)
            self.current_tape_position = self.current_block.start_position + self.current_block.number_of_pulses - 1
        else:
            self.rewind_tape(0)

    def toggle_in_port(self):
        if self.ports.ear_input == 0x40:
            self.ports.ear_input = 0x00
        else:
            self.ports.ear_input = 0x40

    def on_tape_progress(self, e):
        handler = self.tape_progress
        if handler is not None:
            handler(self, e)

    def on_tape_status_change(self, e):
        handler = self.tape_status_change
        if handler is not None:
            handler(self, e)

    def select_tape_block(self, block_index):
        self.current_block_index = block_index
        self.on_tape_progress(None)

    # https://skoolkid.github.io/rom/asm/0556.html
    # https://retroisle.com/sinclair/zxspectrum/technical/firmware/tape_loading_routine.php
    def fast_load(self, z80):
        # the return value, representing the index of the tape_block which was flash loaded.
        last_block_index = -1

        # if we encounter a block with no data to load (for example a text block), just skip ahead.
        if self.next_block is not None and self.next_block.block_content is None:
            return last_block_index

        # the ld bytes rom routine is intercepted at an early stage just before the edge detection is started.
        # check that the tape position is at the end of a block and that there is a following block to flash load.
        #if z80.pc == 0x056b and self.next_block is not None and self.current_tape_position > self.next_block.start_position - 10:
        if not self.next_block is None and self.current_tape_position > self.next_block.start_position - 10:
            # get expected block type and load vs verify flag from af'
            af_ = z80.af_
            expected_block_type = af_ >> 8
            should_load = af_ & 0x0001  # load rather than verify
            addr = z80.ix
            requested_length = z80.pack(z80.d, z80.e)
            actual_block_type = self.next_block.block_type_num
            actual_block_len = len(self.next_block.block_content)
            success = True
            if expected_block_type != actual_block_type:
                success = False
            else:
                if should_load:
                    offset = 0
                    loaded_bytes = 0
                    checksum = actual_block_type
                    while loaded_bytes < requested_length:
                        if (offset >= actual_block_len):
                            # have run out of bytes to load
                            success = False
                            break
                        byte = self.next_block.block_content[offset]
                        offset += 1
                        loaded_bytes += 1
                        self.machine.mmu.poke(addr, byte)
                        addr = (addr + 1) & 0xffff
                        checksum ^= byte

                    # if loading is going right, we should still have a checksum byte left to read
                    success &= (loaded_bytes == actual_block_len)
                    if success:
                        expected_checksum = self.next_block.checksum
                        success = checksum == expected_checksum
                    else:
                        # verify. todo: actually verify.
                        success = True
            if success:
                # set carry to indicate success
                z80.f = z80.f | 0x01
                # set ix to the same value as if the block had been loaded by the rom routine
                z80.ix = addr & 0xffff
                z80.d = 0; z80.e = 0
            else:
                # reset carry to indicate failure
                z80.f = z80.f & 0xfe

            # keep track of the index of the last loaded tape block. this information
            # can be used to rewind the tape to the start position of the next block
            # after an auto pause.
            last_block_index = self.next_block.index

            # skip forward to the end of the block which was just flash loaded into ram.
            self.go_to_end_of_block(self.next_block.index)

            # skip to the end of the ld bytes rom routine (actually a ret, so it doesn't really matter which ret instruction we point to here).
            self.machine.cpu.set_pc(0x05e2)  # address at which to exit the tape trap

        return last_block_index

    def edge_detection(self, z80):
        edge_detected = False

        # edge detection is performed in the ld-edge-2 routine at 0x05ed.
        # upon entering the routine, b holds a timing constant with different
        # values depending on the kind of edge being detected.
        # b is then increased for every pass in the ld-edge-2 loop.
        # the routine exits when an edge is detected or when b reaches 0.
        # when detecting bit data, the routine is called from ld-8-bits at 0x05ca
        # and the timing constant is 0x_b0. after an edge has been detected,
        # b is compared with 0x_cb in the ld-8-bits routine where a value less than
        # 0x_cb is interpreted as a 0-bit and a value greater than 0x_cb is
        # interpreted as a 1-bit.
        if z80.pc == 0x05ee and z80.b == 0x_b0:
            if self.current_pulse_length == 855:      # handle a 0-bit.
                z80.b = 0x_b0
                z80.pc = 0x05fa
                self.process_tape_data(855)
                edge_detected = True
            elif self.current_pulse_length == 1710:   # handle a 1-bit.
                z80.b = 0x_d0
                z80.pc = 0x05fa
                self.process_tape_data(1710)
                edge_detected = True

        # handle leader pulses by intercepting ld-leader at 0x0580.
        # if a leader pulse is encountered, set h to 0x_ff to skip ahead.
        if z80.pc == 0x0581 and self.current_pulse_length == 2168:
            z80.h = 0x_ff
            self.skip_signal()
            edge_detected = True

        return edge_detected

    def auto_load_tape(self):
        if self.tape_auto_load:
            filename = TAPE_LOADERS_BY_MACHINE[str(self.machine.type)]['default']
            with open(filename, 'rb') as file:
                loader = array('B')
                loader.fromfile(file, os.stat(filename).st_size)
                if filename.lower().endswith('.z80'):
                    snap = parse_z80_file(loader)
                    return self.machine.load_snapshot(snap)
                if filename.lower().endswith('.szx'):
                    snap = parse_szx_file(loader)
                    return self.machine.load_snapshot(snap)

    # this class extracts data to be saved to tape, when the rom routine
    # sa-bytes 0x04c2 has been reached and appends it to the currently opened tap-file.
    def basic_save(self, z80):
        tape_block_appended = False

        block_length = z80.pack(z80.d, z80.e)
        if block_length > 48 * 1024:
            return tape_block_appended  

        block_start = z80.ix
        block_type = z80.a

        block_data = array('B', [0] * (block_length + 4))

        # the first two bytes of the block contains the data length plus the flag byte and the checksum.
        block_data[0] = (block_length + 2) & 0xff
        block_data[1] = ((block_length + 2) >> 8) &0xff

        # the third byte is block type (flag byte).
        block_data[2] = block_type

        # the checksum is calculated by xor the block data, includiung the block type.
        checksum = block_type

        # get the block data from memory.
        addr = block_start
        for i in range(0, block_length):
            block_data[3 + i] = self.machine.mmu.peek(addr)
            checksum = checksum ^ block_data[3 + i]
            addr = (addr + 1) & 0xffff

        # append the checksum.
        block_data[3 + block_length] = checksum

        if self.file_type == "tap":
            # append the block to the currently opened tap data.
            self.tape_content.extend(block_data)
            # refresh the tape player listing.
            self.refresh_tape_content()
            # indicate that the process was successful.
            tape_block_appended = True
            self.dirty = 1
        return tape_block_appended

    def save_to_tape(self):
        if not self.dirty:
            messagebox.showerror(APP_NAME, f'nothing to save')
            return 1

        if not self.file_path or self.file_path == "":
            title = f"{APP_NAME} - save {self.file_name}"
            filename = filedialog.asksaveasfilename(title=title, filetypes=[('tape tap format', '*.tap'), ('all files', '*.*')])
            if not filename:
                return 0
        else:
            filename = self.file_path

        # save tape buffer
        confirm = True
        if os.path.exists(filename):
            confirm = messagebox.askyesno(APP_NAME, f"{filename} already exists.\n" + "do you want to overwrite it?")

        if confirm:
            self.pause_tape()
            with open(filename, 'wb') as file:
                self.tape_content.tofile(file)
            self.dirty = 0

        return 1

    # rom patch with meta opcode ed cd and ed 02
    def patch(self, do_patch=-1):
        if do_patch == -1:
            do_patch = self.patched

        if self.machine.type == 48 or self.machine.type == 128:
            if self.machine.type == 48:
                rom_page = self.machine.SYS_ROM0_PAGE
            else:
                rom_page = self.machine.SYS_ROM1_PAGE
            ram = self.machine.mmu.get_page_ram(rom_page)
            if not do_patch:
                # load
                #ram[0x056b] = 0xed
                ##ram[0x056c] = 0xcd  # luckily ed cd is not used
                # save
                #print(f"save before patch: {binascii.b2a_hex(ram[0x04c2: 0x04c4], b' ')}")
                ram[0x04c2] = 0xed
                ram[0x04c3] = 0x02
                #print(f"save after patch: {binascii.b2a_hex(ram[0x04c2: 0x04c4], b' ')}")
                self.patched = 1
            else:
                #restore original
                #ram[0x056b] = 0xc0
                ##ram[0x056c] = 0xcd
                ram[0x04c2] = 0x21
                ram[0x04c3] = 0x3f
                self.patched = 0

    def run_frame_end(self):
        if self.ports:
            # clean up some stuff if the tape has paused.
            if not self.is_tape_pause_handled:
                # reset bit 6 (ear bit) of port 0x_fe.
                self.reset_ear_input()

                # make sure that the user selected cpu speed is applied.
                if not self.is_tape_playing == False:
                    self.reset_standard_speed()

                self.is_tape_pause_handled = True

            # detect if tape loading is not active, by keeping track of how often the ula ports are read.
            if self.tape_auto_pause and self.is_tape_playing and self.file_type == "tap" and self.ports.ula_port_read_freq < 200:
                # in the first frame with a low amount of ula port reads, save the current tape index for later.
                if self._low_ula_port_read_frequency_frame_counter == 0:
                    self._last_read_tape_index = self.current_block_index
                # count the number of frames with low amount of ula port reads.
                self._low_ula_port_read_frequency_frame_counter += 1
            else:
                self._low_ula_port_read_frequency_frame_counter = 0

            self.ports.ula_port_read_freq = 0

        # pause tape when ula port reading is less frequent, but only for tap-files.
        # the reason for excluding tzx files from the auto stop function is that some custom loaders will trigger a pause
        # with the current settings, and that the tzx format includes a tape stop command.
        if self.tape_auto_pause and self.is_tape_playing and self._low_ula_port_read_frequency_frame_counter > 50 and self.file_type == "tap":
            self.pause_tape()
            self._low_ula_port_read_frequency_frame_counter = 0

            # if we have entered a new block since we first detected a low amount of ula port reads,
            # rewind the tape to the beginning of the block.
            if self.current_block_index > self._last_read_tape_index:
                self.go_to_end_of_block(self._last_read_tape_index)
                self.reset_standard_speed()

    def reset_standard_speed(self):
        self.is_speed_loading = False
        self.machine.constrain_50_fps = Config.get('machine.constrain', 0)
        self.machine.beeper.mute(Config.get('audio.muted', 0))
        self.machine.AY.mute(Config.get('ay.c.muted', 0)) # libemu !

    def stop(self):
        self._tape = None
        self.set_file_path(None)
        self.is_tape_playing = False
