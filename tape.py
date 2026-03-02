from tkinter import messagebox
from app_globals import APP_NAME

class TapeBlock:
    class BlockType:
        PROGRAM_HEADER = 0
        NUMBER_ARRAY_HEADER = 1
        CHARACTER_ARRAY_HEADER = 2
        CODE_HEADER = 3
        DATA_BLOCK = 4
        INFO = 5
        UNASSIGNED = 6

    def __init__(self, file_name=None, type=None, start_position=0, index=0, block_content=None,
                    is_headerless=False, checksum=0, block_type_num=0):
        # index (position) of the tape block in the tape file.
        self.index = index

        # type of tape block (enum).
        self.type = type

        # file name in header block.
        self.file_name = file_name

        # the block data.
        self.block_content = block_content

        # set to True for data blocks without a header.
        self.is_headerless = is_headerless

        # header checksum byte.
        self.checksum = checksum

        # block type, 0x00 = header; 0x_ff = data block.
        self.block_type_num = block_type_num

        # where in the translated tape data is the start point of this block?
        self.start_position = start_position

        # number of pulses in the translated tape data.
        self.number_of_pulses = 0

    @property
    def block_length(self):
        if self.block_content is not None:
            return f"{len(self.block_content)}"
        else:
            return "0"

class TapeSignal:
    def __init__(self, number_of_pulses=0, pause=False, force_high=False, force_low=False, pulse_length=0, stop_tape=False, is_leader=False):
        self.number_of_pulses: int = number_of_pulses
        self.pause: bool = pause
        self.force_high: bool = force_high
        self.force_low: bool = force_low
        self.pulse_length: int = pulse_length
        self.stop_tape: bool = stop_tape
        self.is_leader: bool = is_leader

# Base class for tape file processing.
class Tape:
    # extra offset for the start of the actual block data in a tape file data block.
    data_index_adjustment = 0

    # the standard number of leader pulses for header blocks.
    header_leader_pulses = 8063

    # the standard number of leader pulses for data blocks.
    data_leader_pulses = 3223

    # the standard length in t-states for leader pulses.
    leader_pulse_length = 2168

    # the standard length in t-states for the first sync pulse.
    first_sync_pulse_length = 667

    # the standard length in t-states for the second sync pulse.
    second_sync_pulse_length = 735

    # the standard length in t-states for zero bit pulses.
    zero_bit_pulse_length = 855

    # the standard length in t-states for one bit pulses.
    one_bit_pulse_length = 1710

    # number of t-states per millsecond.
    t_states_per_milli_second = 3500

    def __init__(self, file_content):
        # the content of a tape file in the form of a byte array.
        self._file_content = file_content

        # the current read position in the <see cref="_file_content"/> array during the tape data processing.
        self._file_content_index = 0

        # the currently processed <see cref="TapeBlock"/> in the <see cref="tape_listing"/>.
        self._tape_listing_index = 0

        # the length of the currently processed tape block.
        self._block_length = 0

        # create a list of tape_blocks.
        self.tape_listing = []

        # create a list of signals.
        self.signals = []

        self.process_tape()

    def process_tape(self):
        raise NotImplementedError

    def update_tape_listing(self, block_length, file_content_index, data_index_adjustment, tape_listing_index, signal_index):
        if file_content_index + block_length > len(self._file_content):
            self.file_error()
            return False

        # get the start of the block content.
        block_content_index = file_content_index + data_index_adjustment

        # read the flag byte from the block.
        # if the last block is a fragmented data block, there is no flag byte, so set the flag to 255
        # to indicate a data block.
        if block_content_index + 2 < len(self._file_content):
            flag_byte = self._file_content[block_content_index + 2]
        else:
            flag_byte = 255

        if flag_byte == 0 and block_length > 19:
            flag_byte = 0

        # process the block depending on if it is a header or a data block.
        # block type 0 should be a header block, but it happens that headerless blocks also
        # have block type 0, so we need to check the block length as well.
        if flag_byte == 0 and block_length == 19:
            # this is a header.

            # get the block type.
            b = self._file_content[block_content_index + 3]
            if b == 0:
                data_block_type = TapeBlock.BlockType.PROGRAM_HEADER
            elif b == 1:
                data_block_type = TapeBlock.BlockType.NUMBER_ARRAY_HEADER
            elif b == 2:
                data_block_type = TapeBlock.BlockType.CHARACTER_ARRAY_HEADER
            elif b == 3:
                data_block_type = TapeBlock.BlockType.CODE_HEADER
            else:
                data_block_type = TapeBlock.BlockType.UNASSIGNED

            # get the filename.
            file_name = ""
            for i in range(0, 10):
                ascii_code = self._file_content[block_content_index + 4 + i]
                file_name += chr(ascii_code)

            # get the block content (the 17 bytes of the header, including block type, filename and header info).
            block_content = bytearray(17)
            for i in range(0, 17):
                block_content[i] = self._file_content[block_content_index + 3 + i]

            # get the checksum.
            checksum = self._file_content[block_content_index + 20]

            # add the block information to the tape listing.
            self.tape_listing.append(
                TapeBlock(
                    file_name=file_name,
                    type=data_block_type,
                    start_position=signal_index,
                    index=tape_listing_index,
                    block_content=block_content,
                    is_headerless=False,
                    checksum=checksum,
                    block_type_num=0,
                )
            )
        else:
            # this is a data block.

            # get the block content length.
            if block_length >= 2:
                # normally the content length equals the block length minus two
                # (the flag byte and the checksum are not included in the content).
                content_length = block_length - 2

                # the content is found at an offset of 3 (two byte block size + one flag byte).
                content_offset = 3
            else:
                # fragmented data doesn't have a flag byte or a checksum.
                content_length = block_length

                # the content is found at an offset of 2 (two byte block size).
                content_offset = 2

            # get the block content.
            block_content = bytearray(content_length)

            for i in range(0, content_length):
                block_content[i] = self._file_content[block_content_index + content_offset + i]

            # if the preceeding block is a data block, this is a headerless block.
            if tape_listing_index > 0 and self.tape_listing[tape_listing_index - 1].type == TapeBlock.BlockType.DATA_BLOCK:
                is_headerless = True
            else:
                is_headerless = False

            # get the checksum.
            checksum = self._file_content[block_content_index + 1 + block_length]

            # add the block information to the tape listing.
            self.tape_listing.append(
                TapeBlock(
                    type=TapeBlock.BlockType.DATA_BLOCK,
                    start_position=signal_index,
                    index=self._tape_listing_index,
                    block_content=bytes(block_content),
                    is_headerless=is_headerless,
                    checksum=checksum,
                    block_type_num=flag_byte,
                )
            )

        return True

    def apply_leader_and_sync_pulses(self, number_of_leader_pulses, leader_pulse_length, first_sync_pulse_length, second_sync_pulse_length):
        self.signals.append(TapeSignal(number_of_pulses=number_of_leader_pulses, pulse_length=leader_pulse_length, is_leader=True))
        self.signals.append(TapeSignal(number_of_pulses=1, pulse_length=first_sync_pulse_length))
        self.signals.append(TapeSignal(number_of_pulses=1, pulse_length=second_sync_pulse_length))

    def convert_block_data(self, block_length, file_content_index, zero_bit_pulse_length, one_bit_pulse_length, last_bits):
        # process the block data
        for i in range(0, block_length):
            # step through every bit in every byte in the data block and create pulses.
            value = self._file_content[file_content_index + i]

            # on the last byte in the block, check if all bits should be handled.
            if i == block_length - 1:
                used_bits = last_bits
            else:
                used_bits = 8

            # loop through the bits and create pulses.
            for bit_index in range(0, used_bits):
                bitvalue = (value & 128) // 128
                if bitvalue == 0:
                    self.signals.append(TapeSignal(number_of_pulses=2, pulse_length=zero_bit_pulse_length))
                else:
                    self.signals.append(TapeSignal(number_of_pulses=2, pulse_length=one_bit_pulse_length))

                value <<= 1

    def add_pause(self, pause_length):
        if pause_length > 0:
            self.signals.append(TapeSignal(number_of_pulses=1, pulse_length=pause_length * Tape.t_states_per_milli_second))

    def get_byte(self, offset):
        return self._file_content[self._file_content_index + offset]

    def get_word(self, offset):
        return int(self._file_content[self._file_content_index + offset] + 256 * self._file_content[self._file_content_index + 1 + offset])

    def get_long_word(self, offset):
        return (
            self._file_content[self._file_content_index + offset]
            + 256 * self._file_content[self._file_content_index + 1 + offset]
            + 65536 * self._file_content[self._file_content_index + 2 + offset]
        )

    def get_double_word(self, offset):
        return (
            self._file_content[self._file_content_index + offset]
            + 256 * self._file_content[self._file_content_index + 1 + offset]
            + 65536 * self._file_content[self._file_content_index + 2 + offset]
            + 16777216 * self._file_content[self._file_content_index + 3 + offset]
        )

    def check_for_eof(self, value):
        if value > len(self._file_content):
            self.file_error()
            return True
        else:
            return False

    def file_error(self):
       messagebox.showerror(APP_NAME, "file read error.")