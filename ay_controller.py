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

#
# Handles AY sound emulation
# Low level interface with sound card via pygame mixer class
#
try:
	from pygame import mixer as mixer
except Exception as e:
	from audio_null import mixer
import time
from ay_channel import AYChannel
from config import Config

class AYController():

    # Creates a AYController object.
    def __init__(self, sample_rate, stereo, muted, frame_t_state_count):
        self.sample_rate = sample_rate
        self.stereo = stereo
        self.muted = muted
        self.frame_t_state_count = frame_t_state_count
        self.log_enabled = 1
        self.cpu_freq = 3500000	#MHz
        self.t_span_real = 500		# real t state duration in ns
        self.t_span_emul = 500 // 2   # here
        self.last_write_time = time.monotonic() #ms
        self.last_write_t = 0

        # AY registers
        self.AY_clock_frequency = 1773400  # zx 1773400 Hz
        self.registers = bytearray([0] * 16)
        self.registers[14] = 0xbf
        self.registers[15] = 0xbf
        self.selected_register = 0

        # channels
        self.channelA = None
        self.channelB = None
        self.channelC = None
        self.channels = [None, None, None]

        # wave parameters
        self.stereo_high_volume = 0.9
        self.stereo_low_volume = 0.5
        self.mono_volume = 0.8
        self.cpu_frame_count = 1
        self.play_frame = Config.get('ay.py.interval', 1)

        # pygame.mixer
        self.mixer = None
        self.intialize_player(stereo)

    # Set up a pygame mixer for the three AY channels.
    def intialize_player(self, stereo):
        self.mixer = mixer
        self.mixer.pre_init(size=-16, buffer=512, channels=stereo+1)
        self.mixer.init()

        self.channels[0] = AYChannel(0, "A", self, self.mixer)
        self.channels[1] = AYChannel(1, "B", self, self.mixer)
        self.channels[2] = AYChannel(2, "C", self, self.mixer)

        self.channelA = self.channels[Config.get('ay.py.a.ord', 0)]
        self.channelA.muted = Config.get('ay.py.a.muted', 0)
        self.channelB = self.channels[Config.get('ay.py.b.ord', 1)]
        self.channelB.muted = Config.get('ay.py.b.muted', 0)
        self.channelC = self.channels[Config.get('ay.py.c.ord', 2)]
        self.channelC.muted = Config.get('ay.py.c.muted', 0)

        #self.channelA = AYChannel(0, "A", self, self.mixer)
        #self.channelA.muted = 0
        #self.channelB = AYChannel(1, "B", self, self.mixer)
        #self.channelB.muted = 0
        #self.channelC = AYChannel(2, "C", self, self.mixer)
        #self.channelC.muted = 0

        if stereo:
            self.stereo_on()
        else:
            self.stereo_off()

    # Selects a register (0-15) to be read from or written to.
    def select_register(self, register):
        # Register 0-15 can be selected.
        self.selected_register = register & 15

    def get_selected_register(self):
        #self.log(f"#get_selected_register {self.selected_register}")
        return self.selected_register

    # Reads from the selected register or a specific register.
    def read_register(self, register=255):
        if register == 255: register = self.selected_register
        return self.registers[register]

    # Writes a value to the selected AY register.
    def write_register(self, value, t):
        reg = self.selected_register
        #now = time.monotonic()
        if reg < 14:
            #self.log(f"write_register: {reg} = {hex(value)} ({bin(value)})")
            match reg:
                case 0:
                    self.channelA.set_tone_period_low_byte(t, value)
                case 1:
                    self.channelA.set_tone_period_high_byte(t, value & 15)
                case 2:
                    self.channelB.set_tone_period_low_byte(t, value)
                case 3:
                    self.channelB.set_tone_period_high_byte(t, value & 15)
                case 4:
                    self.channelC.set_tone_period_low_byte(t, value)
                case 5:
                    self.channelC.set_tone_period_high_byte(t, value & 15)
                case 6:
                    self.channelA.set_noise_period(t, value & 31)
                    self.channelB.set_noise_period(t, value & 31)
                    self.channelC.set_noise_period(t, value & 31)
                case 7:
                    if value & 1:
                        self.channelA.set_tone_in_mix(t, False)
                    else:
                        self.channelA.set_tone_in_mix(t, True)

                    if value & 2:
                        self.channelB.set_tone_in_mix(t, False)
                    else:
                        self.channelB.set_tone_in_mix(t, True)

                    if value & 4:
                        self.channelC.set_tone_in_mix(t, False)
                    else:
                        self.channelC.set_tone_in_mix(t, True)

                    if value & 8:
                        self.channelA.set_noise_in_mix(t, False)
                    else:
                        self.channelA.set_noise_in_mix(t, True)

                    if value & 16:
                        self.channelB.set_noise_in_mix(t, False)
                    else:
                        self.channelB.set_noise_in_mix(t, True)

                    if value & 32:
                        self.channelC.set_noise_in_mix(t, False)
                    else:
                        self.channelC.set_noise_in_mix(t, True)

                case 8:
                    self.channelA.set_volume(t, value)
                case 9:
                    self.channelB.set_volume(t, value)
                case 10:
                    self.channelC.set_volume(t, value)
                case 11:
                    self.channelA.set_envelope_period_low_byte(t, value)
                    self.channelB.set_envelope_period_low_byte(t, value)
                    self.channelC.set_envelope_period_low_byte(t, value)
                case 12:
                    self.channelA.set_envelope_period_high_byte(t, value)
                    self.channelB.set_envelope_period_high_byte(t, value)
                    self.channelC.set_envelope_period_high_byte(t, value)
                case 13:
                    self.channelA.set_envelope_shape(t, value & 15)
                    self.channelB.set_envelope_shape(t, value & 15)
                    self.channelC.set_envelope_shape(t, value & 15)

            self.registers[reg] = value
        else:
            # Registers 14 and 15 are the same register.
            self.registers[14] = value
            self.registers[15] = value

    def mute(self, val):
        self.muted = val

    def mute_channel(self, channel, val):
        if channel == 0:
            self.channelA.muted = val
        elif channel == 1:
            self.channelB.muted = val
        elif channel == 2:
            self.channelC.muted = val

    # Stops the player.
    def stop(self):
        self.mixer.stop()

    def set_stereo(self, val):
        self.stereo = val
        if self.stereo:
            self.stereo_on()
        else:
            self.stereo_off()

    # Turns on the stereo effect.
    def stereo_on(self):
        self.channelA.set_balance(self.stereo_high_volume, self.stereo_low_volume)
        self.channelB.set_balance(self.mono_volume, self.mono_volume)
        self.channelC.set_balance(self.stereo_low_volume, self.stereo_high_volume)

    # Turns off the stereo effect.
    # Set the left and right channels to the same volume.
    def stereo_off(self):
        self.channelA.set_balance(self.mono_volume, self.mono_volume)
        self.channelB.set_balance(self.mono_volume, self.mono_volume)
        self.channelC.set_balance(self.mono_volume, self.mono_volume)

    def set_frame_cycle_count(self, val):
        self.frame_t_state_count = val

    def run_frame_setup(self):
        pass

    def run_frame_end(self):
        play = 1 if self.cpu_frame_count == self.play_frame else 0
        if not self.muted:
            s0 = self.channelA.play_wave(play)
            s1 = self.channelB.play_wave(play)
            s2 = self.channelC.play_wave(play)
            if s0:
                self.mixer.Channel(0).queue(s0)
            if s1:
                self.mixer.Channel(1).queue(s1)
            if s2:
                self.mixer.Channel(2).queue(s2)

        self.cpu_frame_count = 1 if self.cpu_frame_count >= self.play_frame else self.cpu_frame_count + 1

    def log(self, text):
        if self.log_enabled:
            log = open('./tmp/ay.log', 'a')
            s = f'{time.monotonic()}: {text}\n'
            log.write(s)
            log.close
