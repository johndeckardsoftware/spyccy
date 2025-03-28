#
# Adapted from HOME OF SPECTRUM 48  https://softspectrum48.weebly.com/
#
#
# Western Digital WD1773-00 / WD1793-00 chip emulator
# Handles the Beta Disk interface interaction with the Z80 (via ports 0x1f, 0x3f, 0x5f, 0x7f, 0xff)
# and the Beta Disk drives (up to 4: A, B, C, D).
#

from enum import Enum
from beta_disk_drive import BetaDiskDrive

class COMMANDS(Enum):
    RESTORE = 0
    SEEK = 16
    STEP = 32
    STEP_IN = 64
    STEP_OUT = 96
    READ_SECTOR = 128
    WRITE_SECTOR = 160
    READ_ADDRESS = 192
    READ_TRACK = 224
    WRITE_TRACK = 240
    FORCE_INTERRUPT = 208
    NONE = 256
    INVALID = 257

class BetaDiskController:

    # Initializes a Beta Disk controller object.

    def __init__(self, drive_number):
        # The attached Beta Disk drives.
        self.drive_number = drive_number
        self.drives = []
        for i in range(0, drive_number):
            self.drives.append(BetaDiskDrive(i, f"disk{i}"))
        self.current_drive = self.drives[0]
        # The currently selected drive
        self.selected_drive = 0

        # Status flags which are not managed and therefore always ok
        self.CRCERRORSTATUS = 0
        self.SEEKERRORSTATUS = 0
        self.WRITEPROTECTSTATUS = 0
        self.LOSTDATASTATUS = 0

        # FDC flags changed by commands
        self.write_fault_status = 0

        # The Interrupt Request status flag
        self.interrupt_request = 0

        # The Data Request status flag
        self.data_request = 0

        # The Busy status flag
        self.busy_status = 0

        # Command control.
        self.current_command = COMMANDS.NONE.value
        self.command_type = 0       # (0 = no command, 1-3 = type [n] command).
        self.result_counter = 0

        # data register
        self.data = 0

        # log
        self.log_enabled = 0  # 0 = no log, 1 = log, 2 = full log 
        self.log_last_text = ""
        self.log_same_as_last_count = 0

    # The Status Register.
    #
    # The Status Register represent various flags (which ones depend on the
    # previous command executed by the controller).
    #
    def get_status_register(self):
        track0_status = self.current_drive.track0_status()
        index_status = self.current_drive.index_status
        head_loaded_status = 1 if self.current_drive.disk_loaded else 0
        not_ready_status = 0 if self.current_drive.disk_loaded else 1
        record_not_found_status = 0 if self.current_drive.disk_loaded else 1

        if self.command_type == 1 or self.command_type == 0:
            statusRegister = (self.busy_status + 2 * index_status + 4 * track0_status + 8 * self.CRCERRORSTATUS + 16 * self.SEEKERRORSTATUS + 32 * head_loaded_status + 64 * self.WRITEPROTECTSTATUS + 128 * not_ready_status)
        else:
            statusRegister = (self.busy_status + 2 * self.data_request + 4 * self.LOSTDATASTATUS + 8 * self.CRCERRORSTATUS + 16 * record_not_found_status + 32 * self.write_fault_status + 64 * self.WRITEPROTECTSTATUS + 128 * not_ready_status)

        if self.log_enabled:
            self.log(f"sr: {bin(statusRegister)} {hex(statusRegister)} {self.command_type=} {self.interrupt_request=}")

        # Clear some flags.
        self.interrupt_request = 0
        self.current_drive.index_status = 0

        return statusRegister

    # Receive and initiate incoming commands and parameters.
    def set_command_register(self, val):
        # If there is no command currently being processed and if the FDC is prepared to receive data
        # from the processor; proceed and interpret the in parameter as a command code.
        # When an input byte is received, it can be treated in three different ways.
        # - A new command.
        # - In parameter to an active command.
        # - Data to write to disk.
        self.interrupt_request = 0
        if self.busy_status == 0:
            # Receive a new command.
            if (val & 0xF0) == COMMANDS.RESTORE.value:
                self.restore()
            elif (val & 0xF0) == COMMANDS.SEEK.value:
                self.seek()
            elif (val & 0xE0) == COMMANDS.STEP.value:
                self.step()
            elif (val & 0xE0) == COMMANDS.STEP_IN.value:
                self.step_in()
            elif (val & 0xE0) == COMMANDS.STEP_OUT.value:
                self.step_out()
            elif (val & 0xE0) == COMMANDS.READ_SECTOR.value:
                self.read_sector(val)
            elif (val & 0xE0) == COMMANDS.WRITE_SECTOR.value:
                self.write_sector()
            elif (val & 0xFB) == COMMANDS.READ_ADDRESS.value:
                self.read_address()
            elif (val & 0xFB) == COMMANDS.READ_TRACK.value:
                self.read_track()
            elif (val & 0xFB) == COMMANDS.WRITE_TRACK.value:
                self.write_track()
            elif (val & 0xF0) == COMMANDS.FORCE_INTERRUPT.value:
                self.force_interrupt()
            else:
                self.current_command = COMMANDS.INVALID.value
                self.command_type = 0
                self.interrupt_request = 1

        if self.log_enabled:
            self.log(f"cr: {bin(val)} {hex(val)} {val} {COMMANDS(self.current_command).name} {self.interrupt_request=} {self.data_request=}")

    # The Track Register.
    #
    # This 8-bit register holds the track number of the current Read/Write head position.
    # It is incremented by one every time the head is stepped in (towards track 76) and
    # decremented by one when the head is stepped out (towards track 00). The contents of
    # the register are compared with the recorded track number in the ID field during disk
    # Read, Write and Verify operations.
    # The Track Register is stored in the DiskDrive object so that several disk drives can be handled.
    def get_track(self):
        if self.log_enabled:
            self.log(f"gt: {self.current_drive.current_track=} {self.interrupt_request=} {self.data_request=}")
        return self.current_drive.current_track

    def set_track(self, val):
        if self.log_enabled:
            self.log(f"st: {self.current_drive.current_track=} {val=} {self.interrupt_request=} {self.data_request=}")
        self.current_drive.current_track = val

    # The Sector Register.
    #
    # This 8-bit register holds the address of the desired sector position.
    # The contents of the register are compared with the recorded sector number in the ID
    # field during disk Read or Write operations.
    # The Sector Register is stored in the DiskDrive object so that several disk drives can be handled.
    def get_sector(self):
        if self.log_enabled:
            self.log(f"gs: {self.current_drive.current_sector=} {self.interrupt_request=} {self.data_request=}")
        return self.current_drive.current_sector

    def set_sector(self, val):
        if self.log_enabled:
            self.log(f"ss: {self.current_drive.current_sector=} {val=} {self.interrupt_request=} {self.data_request=}")
        self.current_drive.current_sector = val

    # The Data Register.
    #
    # This 8-bit register is used as a holding register during Disk Read and Write operations.
    # In Disk Read operations the assembled data byte is transferred in parallel to the
    # Data Register from the Data Shift Register. In Disk Write operations information is
    # transferred in parallel from the Data Register to the Data Shift Register.
    # When executing the Seek command the Data Register holds the address of the desired
    # Track position.
    # When the Data Register is read the DRQ bit in the Status register and the DRQ line
    # (in the Control Register) are automatically reset. A write to the Data Register
    # also causes both DRQ’s to reset.
    def get_data(self):
        _intrq = self.interrupt_request
        _drq = self.data_request
        if self.data_request == 1: # There is something in the Data Shift Register.
            self.data = self.get_data_shift_register()
        
        if self.log_enabled > 1:
            self.log(f"gd: {hex(self.data)} {chr(self.data) if self.data > 31 and self.data < 128 else ' '} {_intrq=} {self.interrupt_request=} {_drq=} {self.data_request=} {self.result_counter=}")
        return self.data

    def set_data(self, data):
        _intrq = self.interrupt_request
        _drq = self.data_request
        if self.data_request == 1: # data to be passed to Data Shift Register.
            self.set_data_shift_register(data)

        self.data = data
        if self.log_enabled > 1:
            self.log(f"sd: {hex(self.data)} {chr(self.data) if self.data > 31 and self.data < 128 else ' '} {_intrq=} {self.interrupt_request=} {_drq=} {self.data_request=} {self.result_counter=}")

    #
    # Return data from any Read command.
    # This method will be called as long as the Data Request flag is set.
    # Every Read command sets a counter to the number of bytes that will
    # be returned by the command. When the counter reaches zero,
    # the Interrupt Request flag is set and the Data Request flag is reset.
    def get_data_shift_register(self):
        dataShiftRegister = 0

        if self.result_counter > 0:
            if self.current_command == COMMANDS.READ_ADDRESS.value:
                match self.result_counter:
                    case 6:
                        dataShiftRegister = self.get_track()
                    case 5:
                        dataShiftRegister = self.get_side()
                    case 4:
                        dataShiftRegister = self.get_sector()
                    case 3:
                        dataShiftRegister = 1 # Sector length 256 bytes is encoded as "1".
                    case 2:
                        dataShiftRegister = 0 # CRC byte
                    case 1:
                        dataShiftRegister = 0 # CRC byte

            elif self.current_command == COMMANDS.READ_SECTOR.value:
                dataShiftRegister = self.current_drive.read_sector(256 - self.result_counter)

            self.result_counter -= 1

            if self.result_counter == 0:
                self.data_request = 0
                self.busy_status = 0
                self.interrupt_request = 1
                if self.log_enabled:
                    self.log(f"END {COMMANDS(self.current_command).name} {self.interrupt_request=} {self.data_request=}")
                self.current_command = COMMANDS.NONE.value

        return dataShiftRegister

    def set_data_shift_register(self, data):
        if self.result_counter > 0:
            if self.current_command == COMMANDS.WRITE_SECTOR.value:
                self.write_fault_status = self.current_drive.write_sector(256 - self.result_counter, data)

                self.result_counter -= 1

            if self.result_counter == 0:
                self.data_request = 0
                self.busy_status = 0
                self.interrupt_request = 1
                if self.log_enabled:
                    self.log(f"END {COMMANDS(self.current_command).name} {self.interrupt_request=} {self.data_request=}")
                self.current_command = COMMANDS.NONE.value

    # program control register: check DRQ and INTRQ using Status Register bits instead of chip pins.
    def get_control_register(self):
        interruptRequest = self.interrupt_request
        self.interrupt_request = 0
        if self.log_enabled > 1:
            self.log(f"CR: {self.data_request=} {interruptRequest=}")
        return 0x40 * self.data_request + 0x80 * interruptRequest

    def set_control_register(self, val):
        self.set_current_drive(val & 3)
        side = 0 if (val & 0x10) else 1
        # setting
        self.current_drive.current_side = side
        # 0x20 = density, reset = FM, set = MFM */
        self.current_drive.density = 1 if (val & 0x20) else 0

    #The current Side of the selected drive.
    def get_side(self):
        if self.log_enabled:
            self.log(f"ge: {self.current_drive.current_side=} {self.interrupt_request=} {self.data_request=}")
        return self.current_drive.current_side

    # Seek command.
    # Move the head to track 0.
    def restore(self):
        self.command_type = 1
        self.current_command = COMMANDS.RESTORE.value
        self.current_drive.restore()
        self.interrupt_request = 1

    # Seek command.
    # Move the head to the track number in the Data Register.
    def seek(self):
        self.command_type = 1
        self.current_command = COMMANDS.SEEK.value
        self.current_drive.seek(self.get_data())
        self.interrupt_request = 1

    # Step Out command.
    # Move the head one track in the same direction as the last Step command.
    def step(self):
        self.command_type = 1
        self.current_command = COMMANDS.STEP.value
        self.current_drive.step()
        self.interrupt_request = 1

    # Step In command.
    # Move the head one track towards the disk center.
    def step_in(self):
        self.command_type = 1
        self.current_command = COMMANDS.STEP_IN.value
        self.current_drive.step_in()
        self.interrupt_request = 1

    # Step Out command.
    # Move the head one track towards the disk edge.
    def step_out(self):
        self.command_type = 1
        self.current_command = COMMANDS.STEP_OUT.value
        self.current_drive.step_out()
        self.interrupt_request = 1

    # The Read Sector Command.
    # Upon receipt of the command, the head is loaded, the busy status bit set
    # and when an ID field is encountered that has the correct track number,
    # correct sector number, correct side number, and correct CRC, the data field
    # is presented to the computer. An DRQ is generated each time a byte is transferred
    # to the DR. At the end of the Read operation, the type of Data Address Mark
    # encountered in the data field is recorded in the Status Register (bit 5).
    def read_sector(self, val):
        self.command_type = 2
        self.current_command = COMMANDS.READ_SECTOR.value
        self.result_counter = 256
        self.data_request = 1
        self.busy_status = 1
        if (val & 0x18):
            self.interrupt_request = 1

    # Write Sector command.
    # <remarks>
    # NOT IMPLEMENTED.
    # </remarks>
    def write_sector(self):
        self.command_type = 2
        self.current_command = COMMANDS.WRITE_SECTOR.value
        self.result_counter = 256
        self.data_request = 1
        self.busy_status = 1

    # Read Address command.
    # Upon receipt of the Read Address command, the head is loaded and the Busy Status bit is set.
    # The next encountered ID field is then read in from the disk, and the six data bytes of the
    # ID field are assembled and transferred to the DR, and a DRQ is generated for each byte.
    # The six bytes of the ID field are:
    # Track address, Side number, Sector address, Sector Length, CRC1, CRC2.
    def read_address(self):
        self.command_type = 3
        self.current_command = COMMANDS.READ_ADDRESS.value
        self.result_counter = 6
        self.data_request = 1
        self.busy_status = 1

    # Read Track command. (mainly for debug)
    # NOT IMPLEMENTED.
    def read_track(self):
        self.command_type = 3
        self.current_command = COMMANDS.READ_TRACK.value

    # Write Track command. (used by format)
    # NOT IMPLEMENTED.
    def write_track(self):
        self.command_type = 3
        self.current_command = COMMANDS.WRITE_TRACK.value

    # Execute a Force Interrupt command.
    # If the Force Interrupt command is received when there is a current command under execution,
    # the Busy status bit is reset and the rest of the status bits are unchanged.
    # If the ForceInterrupt command is received when there is not a current command under execution,
    # the Busy Status bit is reset and the rest of the status bits are updated or cleared.
    # In this case, Status reflects the Type I commands.
    # The Force Interrupt command sets the Interrupt Request flag.
    def force_interrupt(self):
        if self.current_command != COMMANDS.NONE.value:
            self.command_type = 1
        self.current_command = COMMANDS.FORCE_INTERRUPT.value
        self.busy_status = 0
        self.interrupt_request = 1

    #
    # virtual disk handling
    #
    def set_current_drive(self, drive):
        if self.drive_number and drive >= 0 and drive < self.drive_number:
            if self.log_enabled:
                self.log(f"set_current_drive {self.current_drive.name} > {self.drives[drive].name}")
            self.current_drive = self.drives[drive]
            self.selected_drive = drive

    def load_disk(self, drive, filename):
        if drive >= self.drive_number:
            self.msgbox(f"drive {drive} unavailable")
            return 0

        return self.drives[drive].load_disk(filename)

    def save_disk(self, drive, filename):
        return self.drives[drive].save_disk(filename)

    def eject_disk(self, drive):
        return self.drives[drive].eject_disk()

    # debug
    def log(self, text):
        s = f"cntrl {text}\n"
        if s == self.log_last_text:
            self.log_same_as_last_count += 1
            if self.log_same_as_last_count > 10000:
                self.log_same_as_last_count = 0
                s = f"(10000) {s}"
            else:
                return
        else:
            if self.log_same_as_last_count:
                s = f"({self.log_same_as_last_count}) {self.log_last_text}{s}"
                self.log_same_as_last_count = 0 
            self.log_last_text = s

        log = open('./tmp/betadisk.log', 'a')
        log.write(s)
        log.close
