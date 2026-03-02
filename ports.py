import app_globals
import joystick

class InOutManager:

    def __init__(self, machine):
        self.machine = machine
        self.type = machine.type
        self.mmu = machine.mmu
        self.beeper = machine.beeper
        self.AY = machine.AY
        self.keyboard = machine.keyboard
        self.betadisk = machine.betadisk
        self.joystick = machine.joystick
        self.mouse = None
        self.ear_input = 0
        self.ULA_port_read_freq = 0
        self.frame_cycle_count = 0
        self.last_paging_value = 0
        self.last_ay_register = 0
        self.cpu = machine.cpu
        self.get_t_state = machine.cpu.get_t_state if machine.cpu else None
        self.add_t_state = machine.cpu.add_t_state if machine.cpu else None
        self.inc_t_state = machine.cpu.inc_t_state if machine.cpu else None

        # log
        self.log_enabled = 1  # 0 = no log, 1 = log, 2 = full log
        self.log_last_text = ""
        self.log_same_as_last_count = 0

    def set_frame_cycle_count(self, value):
        self.frame_cycle_count = value

    def read(self, addr):
        result = 0xff
        addr_low = addr & 0xff

        #if (self.type == 1212):
            # on port reads, the test machine just responds with the high byte of the port address.
            # That's a thing now, RDR(I) decided. (Well, Phil Kendall decided it to be exact.)
        #    result = (addr >> 8)

        # The ULA functions (keybord and audio in) are accessible via all even numbered ports.
        # even if to avoid problems with other I/O devices only Port 0xfe should be used.
        if (addr & 0x0001) == 0:
            result = self.keyboard.poll((addr >> 8))
            #if result != 0xbf:
            #    self.log(f"in {self.get_t_state()} {hex(addr)} {hex(result)}")

            if self.joystick and result == 0xbf:
                if self.joystick.key_mapping:
                    result = self.joystick.key_map(addr)

                #if result != 0xbf:
                #    self.log(f"joy {self.get_t_state()} {hex(addr)} {hex(result)}")

            # Add bit 6, the Ear input bit to the result. Note that on a real Spectrum, bit 6 is affected by
            # what was last output to bits 3 and 4 according to https://worldofspectrum.org/faq/reference/48kreference.htm.
            result |= self.ear_input

            self.ULA_port_read_freq += 1

        elif (addr == 0xfffd):
            result = self.AY.read_register(self.AY.get_selected_register())
            #self.log(f"read_register {self.get_t_state()} {hex(addr)} {hex(result)}")

        elif self.cpu.betadisk_active:
            if addr_low == 0x1f:
                result = self.betadisk.get_status_register()
            elif addr_low == 0x3f:
                result = self.betadisk.get_track()
            elif addr_low == 0x5f:
                result = self.betadisk.get_sector()
            elif addr_low == 0x7f:
                result = self.betadisk.get_data()
            elif addr_low == 0xff:
                result = self.betadisk.get_control_register()

        elif addr_low == 0x1f: # kempston
            if (self.joystick.type == joystick.KEMPSTON):
                result = self.joystick.poll()

        elif addr_low == 0x7f: # fuller
            if (self.joystick.type == joystick.FULLER):
                result = self.joystick.poll()

        elif addr_low == 0xdf: # Kempston mouse or joystick.
            if self.mouse:
                # Kempston mouse interface.
                if addr == 0xfbdf:
                    result = int(self.mouse.x_pos)
                elif addr == 0xffdf:
                    result = int(self.mouse.y_pos)
                elif addr == 0xfadf:
                    result = self.mouse.Button
                else:
                    result = app_globals.floating_bus_value
            else:
                # Normally, the Kempston joystick interface
                # uses port 0x1F, but some games checks port
                # 0xDF instead, which the emulator reserves for
                # the Kempston mouse if it is enabled, but if
                # there is no mouse, port 0xDF will be connected
                # to the joystick.
                result = 0 #_in31

        elif ((self.type == 48) or (self.type == 128)):
            #  floating bus
            result = app_globals.floating_bus_value

        self.add_t_state(4)

        return result & 0xff

    def write(self, addr, val):
        addr_low = addr & 0xff

        if (not (addr & 0x0001)): #  border colour / speaker
            app_globals.border_color = (val & 0x07)
            speakerState = ((val & 0x10) >> 4)
            self.beeper.write(speakerState, self.get_t_state())

        elif (not (addr & 0x8002)): #  128/+2 paging
            if (not self.mmu.paging_locked):
                # Bits 0-2: RAM page (0-7) to map into memory at 0xc000.
                self.mmu.switch_in_ram(val & 0x07)
                # Bit 3: Select normal (0) or shadow (1) screen to be displayed.
                # The normal screen is in bank 5, whilst the shadow screen is in bank 7.
                # Note that this does not affect the memory between 0x4000 and 0x7fff, which is always bank 5.
                self.mmu.set_screen_page(7 if (val & 0x08) else 5)
                # Bit 4: ROM select. ROM 0 is the 128k editor and menu system; ROM 1 contains 48K BASIC.
                self.mmu.switch_in_rom(self.machine.SYS_ROM1_PAGE if (val & 0x10) else self.machine.SYS_ROM0_PAGE)
                # Bit 5: If set, memory paging will be disabled and further output to this port will be ignored until the computer is reset.
                self.mmu.set_paging_locked(bool((val & 0x20)))
                self.last_paging_value = val

        #OUT (0xfffd)   - Select a register 0-14
        #IN  (0xfffd)   - Read the value of the selected register
        #OUT (0xbffd)   - Write to the selected register
        # The port is partially decoded: Bit 1 must be reset and bits 14-15 set.
        elif (((addr & 0xc002) == 0xc000)):
            self.AY.select_register(val)
            #self.log(f"select_register {hex(addr)} {hex(val)}")

        # The port is partially decoded: Bit 1 must be reset and bit 15 set.
        elif ((addr & 0x8002) == 0x8000):
            self.AY.write_register(val, self.get_t_state())
            #self.log(f"write_register {hex(addr)} {self.AY.get_selected_register()} {hex(val)}")

        elif (addr_low == 0x1f):
            if self.cpu.betadisk_active:
                self.betadisk.set_command_register(val)
        elif (addr_low == 0x3f):
            if self.cpu.betadisk_active:
                self.betadisk.set_track(val)
        elif (addr_low == 0x5f):
            if self.cpu.betadisk_active:
                self.betadisk.set_sector(val)
        elif (addr_low == 0x7f):
            if self.cpu.betadisk_active:
                self.betadisk.set_data(val)
        elif (addr_low == 0xff):
            if self.cpu.betadisk_active:
                self.betadisk.set_control_register(val)

        self.add_t_state(4)

    # debug
    def log(self, text):
        if text == self.log_last_text:
            self.log_same_as_last_count += 1
            if self.log_same_as_last_count > 10000:
                self.log_same_as_last_count = 0
                s = f"(10000) {text}\n"
            else:
                return
        else:
            if self.log_same_as_last_count:
                s = f"({self.log_same_as_last_count}) {self.log_last_text}\n{text}\n"
                self.log_same_as_last_count = 0
            else:
                self.log_last_text = text
                s = f"{text}\n"

        log = open('./tmp/ports.log', 'a')
        log.write(s)
        log.close
