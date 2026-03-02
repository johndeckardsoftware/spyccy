from tape import Tape, TapeBlock, TapeSignal

class TZXTape(Tape):
	data_index_adjustment = 2

	def __init__(self, file_content):
		super().__init__(file_content)

	def process_tape(self):
		if len(self._file_content) == 0:
			return

		pause_length = 0
		leader_pulses = 0
		leader_pulse_length = 0
		first_sync_pulse_length = 0
		second_sync_pulse_length = 0
		zero_bit_pulse_length = 0
		one_bit_pulse_length = 0
		last_bits = 0
		loop_times = 0
		loop_start = 0
		loop_end = 0
		t_z_xblock_type = 0

		self._file_content_index = 10

		def update_tape_listing_from_tzx_text_item():
			block_name = ""
			text_length = self._file_content[self._file_content_index]
			for i in range(0, text_length):
				ascii_code = self._file_content[self._file_content_index + 1 + i]
				block_name_local = block_name + chr(ascii_code)
				block_name_nonlocal[0] = block_name_local

			self.tape_listing.append(TapeBlock(file_name=block_name_nonlocal[0], start_position=len(self.signals), index=self._tape_listing_index))

		block_name_nonlocal = [""]
		update_tape_listing_from_tzx_text_item_local = update_tape_listing_from_tzx_text_item

		while True:
			t_z_xblock_type = self.get_byte(0)

			self._file_content_index += 1

			current_file_listing_index = self._tape_listing_index

			if t_z_xblock_type == 0x10:
				pause_length = self.get_word(0x00)
				self._block_length = int(self.get_word(0x02))

				if self._block_length == 19:
					self.update_tape_listing(self._block_length, self._file_content_index, TZXTape.data_index_adjustment, self._tape_listing_index, len(self.signals))
					self._tape_listing_index += 1
					self.apply_leader_and_sync_pulses(self.header_leader_pulses, self.leader_pulse_length, self.first_sync_pulse_length, self.second_sync_pulse_length)
				else:
					self.update_tape_listing(self._block_length, self._file_content_index, TZXTape.data_index_adjustment, self._tape_listing_index, len(self.signals))
					self._tape_listing_index += 1
					self.apply_leader_and_sync_pulses(self.data_leader_pulses, self.leader_pulse_length, self.first_sync_pulse_length, self.second_sync_pulse_length)

				self._file_content_index += 4

				self.convert_block_data(self._block_length, self._file_content_index, self.zero_bit_pulse_length, self.one_bit_pulse_length, 8)

				self.add_pause(pause_length)

				self._file_content_index += self._block_length

			elif t_z_xblock_type == 0x11:
				leader_pulse_length = self.get_word(0x00)
				first_sync_pulse_length = self.get_word(0x02)
				second_sync_pulse_length = self.get_word(0x04)
				zero_bit_pulse_length = self.get_word(0x06)
				one_bit_pulse_length = self.get_word(0x08)
				leader_pulses = self.get_word(0x0a)
				last_bits = self.get_byte(0x0c)
				pause_length = self.get_word(0x0d)
				self._block_length = self.get_long_word(0x0f)

				self.update_tape_listing(self._block_length, self._file_content_index, TZXTape.data_index_adjustment, self._tape_listing_index, len(self.signals))
				self._tape_listing_index += 1

				self.apply_leader_and_sync_pulses(leader_pulses, leader_pulse_length, first_sync_pulse_length, second_sync_pulse_length)

				self._file_content_index += 18

				self.convert_block_data(self._block_length, self._file_content_index, zero_bit_pulse_length, one_bit_pulse_length, last_bits)

				self.add_pause(pause_length)

				self._file_content_index += self._block_length

			elif t_z_xblock_type == 0x12:
				self.signals.append(TapeSignal(number_of_pulses=self.get_word(0x02), pulse_length=self.get_word(0x00)))
				self._file_content_index += 4

			elif t_z_xblock_type == 0x13:
				number_of_pulses = self.get_byte(0x00)

				for pulse in range(0, number_of_pulses):
					self.signals.append(TapeSignal(number_of_pulses=1, pulse_length=self.get_word(0x01)))
					self._file_content_index += 2
				self._file_content_index += 1

			elif t_z_xblock_type == 0x14:
				zero_bit_pulse_length = self.get_word(0x00)
				one_bit_pulse_length = self.get_word(0x02)
				last_bits = self.get_byte(0x04)
				pause_length = self.get_word(0x05)
				self._block_length = int(self.get_word(0x07))

				self._file_content_index += 10

				self.convert_block_data(self._block_length, self._file_content_index, zero_bit_pulse_length, one_bit_pulse_length, last_bits)

				self.add_pause(pause_length)

				self._file_content_index += self._block_length

			elif t_z_xblock_type == 0x20:
				pause_length = self.get_word(0x00)
				if pause_length > 0:
					self.signals.append(TapeSignal(number_of_pulses=1, pulse_length=self.t_states_per_milli_second))
					self.signals.append(TapeSignal(number_of_pulses=1, pulse_length=pause_length * self.t_states_per_milli_second - self.t_states_per_milli_second, pause=True))
				else:
					self.signals.append(TapeSignal(number_of_pulses=0, pulse_length=0, stop_tape=True))

				self._file_content_index += 2

			elif t_z_xblock_type == 0x21:
				update_tape_listing_from_tzx_text_item_local()
				self._tape_listing_index += 1
				self._file_content_index = self._file_content_index + self.get_byte(0x00) + 1

			elif t_z_xblock_type == 0x22:
				pass

			elif t_z_xblock_type == 0x24:
				loop_times = self.get_word(0x00)
				loop_start = len(self.signals)
				self._file_content_index += 2

			elif t_z_xblock_type == 0x25:
				loop_end = len(self.signals) - 1
				for loop_repeat in range(0, loop_times - 1):
					self.signals.add_range(self.signals.get_range(loop_start, loop_end - loop_start + 1))

			elif t_z_xblock_type == 0x30:
				if self._tape_listing_index > 0:
					update_tape_listing_from_tzx_text_item_local()
					self._tape_listing_index += 1

				self._file_content_index = self._file_content_index + self.get_byte(0x00) + 1

			elif t_z_xblock_type == 0x32:
				self._file_content_index = self._file_content_index + int(self.get_word(0x00)) + 2

			elif t_z_xblock_type == 0x33:
				self._file_content_index = self._file_content_index + self.get_byte(0x00) * 3 + 1

			elif t_z_xblock_type == 0x35:
				length = self.get_long_word(0x10)
				self._file_content_index = self._file_content_index + 16 + length + 4

			elif t_z_xblock_type == 0x5a:
				self._file_content_index += 9

			if current_file_listing_index != self._tape_listing_index:
				self.tape_listing[self._tape_listing_index - 1].number_of_pulses = len(self.signals) - self.tape_listing[self._tape_listing_index - 1].start_position

			if not (self._file_content_index < len(self._file_content)):
				break

		self.signals.append(TapeSignal(number_of_pulses=1, pulse_length=500000))