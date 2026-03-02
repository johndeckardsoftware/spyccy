from tape import Tape

class TAPTape(Tape):
    def __init__(self, fileContent):
        super().__init__(fileContent)

    def process_tape(self):
        if len(self._file_content) == 0:
            return

        while True:
            self._block_length = self._file_content[self._file_content_index] + (256 * self._file_content[self._file_content_index + 1])

            self.update_tape_listing(self._block_length, self._file_content_index, 0, self._tape_listing_index, len(self.signals))
            self._tape_listing_index += 1

            # check if this is a header block.
            if self._block_length == 19:
                self.apply_leader_and_sync_pulses(self.header_leader_pulses, self.leader_pulse_length, self.first_sync_pulse_length, self.second_sync_pulse_length)
            else:
                self.apply_leader_and_sync_pulses(self.data_leader_pulses, self.leader_pulse_length, self.first_sync_pulse_length, self.second_sync_pulse_length)

            self._file_content_index += 2

            # process the block data
            self.convert_block_data(self._block_length, self._file_content_index, self.zero_bit_pulse_length, self.one_bit_pulse_length, 8)

            self._file_content_index += self._block_length

            # add a 2s pause after the block (except the last block). the reason for the pause is that some loaders
            # need time to execute after loading a block and before proceeding with the next block.
            if self._file_content_index < len(self._file_content):
                # why two pauses? one pause will change the port value between blocks, causing tape loading error.
                self.add_pause(1000)
                self.add_pause(1000)

            # when a tape block has been processed, store the number of pulses generated in the block data.
            self.tape_listing[self._tape_listing_index - 1].number_of_pulses = len(self.signals) - self.tape_listing[self._tape_listing_index - 1].start_position

            if not (self._file_content_index < len(self._file_content)):
                break