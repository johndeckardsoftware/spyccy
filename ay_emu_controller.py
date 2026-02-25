#
# Adapted from HOME OF SPECTRUM 48  https://softspectrum48.weebly.com/
#
#   The AY-8912 has 16 registers, of which register 0-13 control
#   the tone and noise signals of three sound channels (A-C).
#
#    Register    Function                        Range
#    0           Channel A fine tone period      8-bit(0-255)
#    1           Channel A coarse tone period    4-bit(0-15)
#    2           Channel B fine tone period      8-bit(0-255)
#    3           Channel B coarse tone period    4-bit(0-15)
#    4           Channel C fine tone period      8-bit(0-255)
#    5           Channel C coarse tone period    4-bit(0-15)
#    6           Noise period                    5-bit(0-31)
#    7           Mixer                           8-bit(see below)
#    8           Channel A volume                4-bit(0-15, see below)
#    9           Channel B volume                4-bit(0-15, see below)
#   10           Channel C volume                4-bit(0-15, see below)
#   11           Envelope fine duration          8-bit(0-255)
#   12           Envelope coarse duration        8-bit(0-255)
#   13           Envelope shape                  4-bit(0-15)
#   14           I/O port A                      8-bit(0-255)
#   15           I/O port B                      8-bit(0-255)
#
#   The mixer (register 7) is made up of the following bits (0 = enabled):
#   Bit:     7       6       5       4       3       2       1       0
#   Control: I/O     I/O     Noise   Noise   Noise   Tone    Tone    Tone
#   Channel: B       A       C       B       A       C       B       A
#
import time
from array import array
from pygame import mixer as mixer
from config import Config
import app_globals
from cffi import FFI

class AYController:

	def __init__(self, sample_rate, stereo, muted, frame_t_state_count):
		self.ffi = FFI()
		self.libayemu = self.ffi.dlopen(app_globals.lib_ay_emu)
		self.ffi.cdef("void ayemu_init();")
		self.ffi.cdef("void ayemu_reset();")
		self.ffi.cdef("int ayemu_set_chip_type(int chip, int *custom_table);")
		self.ffi.cdef("void ayemu_set_chip_freq(int chipfreq);")
		self.ffi.cdef("int ayemu_set_stereo(int stereo, int *custom_eq);")
		self.ffi.cdef("int ayemu_set_sound_format(int freq, int chans, int bits);")
		self.ffi.cdef("void ayemu_set_regs(unsigned char * regs);")
		self.ffi.cdef("void *ayemu_gen_sound(void *buf, size_t bufsize);")

		self.registers = bytearray(16)
		self.selected_register = 0

		self.audio_freq = sample_rate
		self.audio_chans = stereo+1; #/* 1=mono, 2=stereo */
		self.audio_bits = 16; #/* 16 or 8 bit */

		self.set_audio_buffers(fps=Config.get('ay.c.fps', 35))

		self.audio_abc_index = Config.get('ay.c.abc', 1)
		self.stereo_high_volume = 0.9
		self.stereo_low_volume = 0.5
		self.mono_volume = 0.8

		self.libayemu.ayemu_init()
		self.libayemu.ayemu_set_sound_format(self.audio_freq, self.audio_chans, self.audio_bits)
		self.libayemu.ayemu_set_stereo(self.audio_abc_index, self.ffi.NULL)

		self.mixer = mixer
		self.mixer.pre_init(size=-self.audio_bits, buffer=512, channels=self.audio_chans)
		self.mixer.init()

		self.muted = muted
		self.channels = {0: {}, 1: {}, 2: {}}
		self.channels[0]['muted'] = Config.get('ay.c.a.muted', 0)
		self.channels[0]['lvolume'] = Config.get('ay.c.a.lvolume', 5)
		self.channels[0]['rvolume'] = Config.get('ay.c.a.rvolume', 5)
		self.channels[1]['muted'] = Config.get('ay.c.b.muted', 0)
		self.channels[1]['lvolume'] = Config.get('ay.c.b.lvolume', 5)
		self.channels[1]['rvolume'] = Config.get('ay.c.b.rvolume', 5)
		self.channels[2]['muted'] = Config.get('ay.c.c.muted', 0)
		self.channels[2]['lvolume'] = Config.get('ay.c.c.lvolume', 5)
		self.channels[2]['rvolume'] = Config.get('ay.c.c.rvolume', 5)

		self.tuning = False

	def set_audio_buffers(self, fps=None):
		if fps == None: fps = self.audio_fps
		self.audio_fps = fps
		self.audio_frame_size = self.audio_chans * (self.audio_bits >> 3)
		self.audio_buf_1s_size = self.audio_freq * self.audio_frame_size
		self.audio_buf_size = int(self.audio_buf_1s_size / self.audio_fps)
		self.audio_buf_max_size = self.audio_buf_1s_size
		self.audio_buf = array('b', [0] * self.audio_buf_max_size)
		self.audio_buf_final = array('b')
		self.audio_frame_count = 0

	def init(self):
		self.libayemu.ayemu_init()

	def set_regs(self, regs=None):
		if regs:
			self.libayemu.ayemu_set_regs(self.ffi.from_buffer(regs))
		else:
			self.libayemu.ayemu_set_regs(self.ffi.from_buffer(self.registers))

	def gen_sound(self, buffer, size):
		self.libayemu.ayemu_gen_sound(self.ffi.from_buffer(buffer), size)

	def out_sound(self):
		#self.registers[7] |= 0x38 #noise
		#self.registers[7] |= 0x07  #tone

		self.libayemu.ayemu_set_regs(self.ffi.from_buffer(self.registers))
		self.audio_buf_size = int(self.audio_buf_1s_size / self.audio_fps)
		self.libayemu.ayemu_gen_sound(self.ffi.from_buffer(self.audio_buf), self.audio_buf_size)
		if self.audio_frame_count < self.audio_fps:
			self.audio_buf_final.extend(self.audio_buf[0:self.audio_buf_size])
			self.audio_frame_count += 1
		else:
			sound = self.mixer.Sound(self.audio_buf_final)
			while self.mixer.Channel(0).get_busy(): time.sleep(0.009)	#queue seems buggy
			self.mixer.Channel(0).queue(sound)
			self.audio_buf_final[0:] = self.audio_buf[0:self.audio_buf_size]
			#self.audio_buf_final.extend(self.audio_buf[0:self.audio_buf_size])
			self.audio_frame_count = 1
			self.audio_buf_index = 0

	# Selects a register (0-15) to be read from or written to.
	def select_register(self, register):
		# Register 0-15 can be selected.
		self.selected_register = register & 15

	def get_selected_register(self):
		return self.selected_register

	# Reads from the selected register or a specific register.
	def read_register(self, register=255):
		if register == 255: register = self.selected_register
		return self.registers[register]

	# Writes a value to the selected AY register.
	def write_register(self, value, t):
		self.registers[self.selected_register] = value

	def mute(self, val):
		self.muted = val

	def set_abc_order(self, val):
		self.audio_abc_index = val
		ret = self.libayemu.ayemu_set_stereo(val, self.ffi.NULL)

	def set_frame_cycle_count(self, val):
		self.frame_t_state_count = val

	def run_frame_setup(self):
		pass

	def run_frame_end(self):
		if (self.registers[8] != 0 or self.registers[9] != 0 or self.registers[10] != 0) and not self.muted:
			self.out_sound()

	# Stops the player.
	def stop(self):
		self.mixer.stop()

	def log(self, text):
		if self.log_enabled:
			log = open('./tmp/ay.log', 'a')
			s = f'{time.monotonic()}: {text}\n'
			log.write(s)
			log.close
#
#   t e s t
#
def gen_sound(AY, tonea, toneb, tonec, noise, control, vola, volb, volc, envfreq, envstyle):

	audio_fps = 50
	audio_freq = 44100
	audio_chans = 2 #/* 1=mono, 2=stereo */
	audio_bits = 16 #/* 16 or 8 bit */
	audio_frame_size = audio_chans * (audio_bits >> 3)
	audio_buf_size = int(audio_freq * audio_frame_size / audio_fps)
	audio_buf = array('b', [0] * audio_buf_size)
	audio_buf_final = array('b')

	#/* setup regs */
	regs = bytearray(14)
	regs[0] = tonea & 0xff
	regs[1] = tonea >> 8
	regs[2] = toneb & 0xff
	regs[3] = toneb >> 8
	regs[4] = tonec & 0xff
	regs[5] = tonec >> 8
	regs[6] = noise
	regs[7] = (~control) & 0x3f  #/* invert bits 0-5 */
	regs[8] = vola               #/* included bit 4 */
	regs[9] = volb
	regs[10] = volc
	regs[11] = envfreq & 0xff
	regs[12] = envfreq >> 8
	regs[13] = envstyle

	AY.set_regs(regs)

	#/* generate sound */
	for n in range(0, 50): # 50 = emulator frame per seconds
		AY.gen_sound(audio_buf, audio_buf_size)
		if n < 49:
			audio_buf_final.extend(audio_buf)
		else:
			audio_buf_final.extend(audio_buf)        	# size should be 176400
			sound = AY.mixer.Sound(audio_buf_final)
			AY.mixer.Channel(0).queue(sound)            # works?
			audio_buf_final[0:] = audio_buf[0:audio_buf_size]
	time.sleep(1)                                       # don't work

def test():
	AY = AYController(44100, 2, 0, 0)

	MUTE = 0
	TONE_A = 1
	TONE_B = 2
	TONE_C = 4
	NOISE_A = 8
	NOISE_B = 16
	NOISE_C = 32

	testcases = [

		["Mute: tones 400, volumes 15 noise 15",
		400, 400, 400, 15 , MUTE , 15, 15, 15, 4000, 4],
		["Mute: tones 400, noise 25, volumes 31 (use env)",
		400, 400, 400, 25, MUTE, 31, 31, 31, 4000, 4],

		["Channel A: tone 400, volume 0",
		400, 0, 0, 0, TONE_A, 0, 0, 0, 0, 0],
		["Channel A: tone 400, volume 5",
		400, 0, 0, 0, TONE_A, 5, 0, 0, 0, 0],
		["Channel A: tone 400, volume 10",
		400, 0, 0, 0, TONE_A, 10, 0, 0, 0, 0],
		["Channel A: tone 400, volume 15",
		400, 0, 0, 0, TONE_A, 15, 0, 0, 0, 0],

		["Channel B: tone 400, volume 0",
		0, 400, 0, 0 , TONE_B , 0, 0, 0, 0, 0],
		["Channel B: tone 400, volume 5",
		0, 400, 0, 0 , TONE_B , 0, 5, 0, 0, 0],
		["Channel B: tone 400, volume 10",
		0, 400, 0, 0 , TONE_B , 0, 10, 0, 0, 0],
		["Channel B: tone 400, volume 15",
		0, 400, 0, 0 , TONE_B , 0, 15, 0, 0, 0],

		["Channel C: tone 400, volume 0",
		0, 0, 400, 0 , TONE_C , 0, 0, 0, 0, 0],
		["Channel C: tone 400, volume 5",
		0, 0, 400, 0 , TONE_C , 0, 0, 5, 0, 0],
		["Channel C: tone 400, volume 10",
		0, 0, 400, 0 , TONE_C , 0, 0, 10, 0, 0],
		["Channel C: tone 400, volume 15",
		0, 0, 400, 0 , TONE_C , 0, 0, 15, 0, 0],

		["Channel B: noise period = 0, volume = 15",
		0, 3000, 0, 0, NOISE_B, 0, 15, 0, 0, 0],
		["Channel B: noise period = 5, volume = 15",
		0, 3000, 0, 5, NOISE_B, 0, 15, 0, 0, 0],
		["Channel B: noise period = 10, volume = 15",
		0, 3000, 0, 10, NOISE_B, 0, 15, 0, 0, 0],
		["Channel B: noise period = 15, volume = 15",
		0, 3000, 0, 15, NOISE_B, 0, 15, 0, 0, 0],
		["Channel B: noise period = 20, volume = 15",
		0, 3000, 0, 20, NOISE_B, 0, 15, 0, 0, 0],
		["Channel B: noise period = 25, volume = 15",
		0, 3000, 0, 25, NOISE_B, 0, 15, 0, 0, 0],
		["Channel B: noise period = 31, volume = 15",
		0, 3000, 0, 31, NOISE_B, 0, 15, 0, 0, 0],

		["Channel A: tone 400, volume = 15, envelop 0 freq 4000",
		400, 0, 0, 0, TONE_A, 15 | 0x10, 0, 0, 4000, 0],
		["Channel A: tone 400, volume = 15, envelop 1 freq 4000",
		400, 0, 0, 0, TONE_A, 15 | 0x10, 0, 0, 4000, 1],
		["Channel A: tone 400, volume = 15, envelop 2 freq 4000",
		400, 0, 0, 0, TONE_A, 15 | 0x10, 0, 0, 4000, 2],
		["Channel A: tone 400, volume = 15, envelop 3 freq 4000",
		400, 0, 0, 0, TONE_A, 15 | 0x10, 0, 0, 4000, 3],
		["Channel A: tone 400, volume = 15, envelop 4 freq 4000",
		400, 0, 0, 0, TONE_A, 15 | 0x10, 0, 0, 4000, 4],
		["Channel A: tone 400, volume = 15, envelop 5 freq 4000",
		400, 0, 0, 0, TONE_A, 15 | 0x10, 0, 0, 4000, 5],
		["Channel A: tone 400, volume = 15, envelop 6 freq 4000",
		400, 0, 0, 0, TONE_A, 15 | 0x10, 0, 0, 4000, 6],
		["Channel A: tone 400, volume = 15, envelop 7 freq 4000",
		400, 0, 0, 0, TONE_A, 15 | 0x10, 0, 0, 4000, 7],
		["Channel A: tone 400, volume = 15, envelop 8 freq 4000",
		400, 0, 0, 0, TONE_A, 15 | 0x10, 0, 0, 4000, 8],
		["Channel A: tone 400, volume = 15, envelop 9 freq 4000",
		400, 0, 0, 0, TONE_A, 15 | 0x10, 0, 0, 4000, 9],
		["Channel A: tone 400, volume = 15, envelop 10 freq 4000",
		400, 0, 0, 0, TONE_A, 15 | 0x10, 0, 0, 4000, 10],
		["Channel A: tone 400, volume = 15, envelop 11 freq 4000",
		400, 0, 0, 0, TONE_A, 15 | 0x10, 0, 0, 4000, 11],
		["Channel A: tone 400, volume = 15, envelop 12 freq 4000",
		400, 0, 0, 0, TONE_A, 15 | 0x10, 0, 0, 4000, 12],
		["Channel A: tone 400, volume = 15, envelop 13 freq 4000",
		400, 0, 0, 0, TONE_A, 15 | 0x10, 0, 0, 4000, 13],
		["Channel A: tone 400, volume = 15, envelop 14 freq 4000",
		400, 0, 0, 0, TONE_A, 15 | 0x10, 0, 0, 400, 14],
		["Channel A: tone 400, volume = 15, envelop 15 freq 4000",
		400, 0, 0, 0, TONE_A, 15 | 0x10, 0, 0, 4000, 15],
	]

	for test in testcases:
		rem, tonea, toneb, tonec, noise, control, vola, volb, volc, envfreq, envstyle = test
		print(rem)
		gen_sound(AY, tonea, toneb, tonec, noise, control, vola, volb, volc, envfreq, envstyle)

if __name__ == '__main__':
	test()
