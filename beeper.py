from array import array
import app_globals
from config import *
import wave 

try:
    from pygame import mixer as mixer
except Exception as e:
    from audio_null import mixer

#
# tpf (tone pulse frequency) to note f
# (cpu clock (3.500.000) / minimum t state length (4)) / (tpf / 2)
# tpf = 6688 > (3500000 / 4) / (6688 / 2) = 261,66
#
#    freq = int(875000 / (tpf / 2))
# http://www.breakintoprogram.co.uk/hardware/computers/zx-spectrum/sound
# https://softspectrum48.weebly.com/notes/category/beeper
class BeeperController:
    def __init__(self, sample_rate, stereo, muted, frame_cycle_count):
        self.sample_rate = sample_rate
        self.stereo = stereo
        self.muted = muted
        self.frame_cycle_count = frame_cycle_count
        self.is_active = True
        self.last_write_t = 0
        self.last_write_frame_count = app_globals.frames_count
        self.t_samples = 56 #80
        self.dtt = 0
        #self.lowest_frequency = 107022 #freq=16 Hz  C0
        self.lowest_frequency = 50506 #freq=34 Hz C1
        self.highest_frequency = 206 #freq=8495 Hz B8
        self.t_span_real = 500		# real t state duration in ns
        self.t_span_emul = 500 // 4.1   # here
        self.cpu_freq = 3500000	#MHz
        # Initalize player
        self.mixer = mixer
        self.mixer.init(buffer=512*1)
        self.mixer_channel = self.mixer.Channel(0)
        self.wave = array('h', [0] * (self.sample_rate * (self.stereo+1)))
        self.wave_pos = 0
        self.wave_prog = 0
        self.out_mode = 1
        self.amplitude_factor = 0.5
        self.left_volume = 0.4
        self.right_volume =  0.7
        self.mono_volume =  0.6
        self.amplitude = 16384 #32767

        # log
        self.log_enabled = 1  # 0 = no log, 1 = log, 2 = full log 
        self.log_last_text = ""
        self.log_same_as_last_count = 0

    def stop(self):
        self.mixer.stop()

    def set_frame_cycle_count(self, val):
        self.frame_cycle_count = val

    def mute(self, val):
        self.muted = val

    def set_stereo(self, val):
        self.stereo = val

    def write(self, state, t):
        if state:
            self.last_write_frame_count = app_globals.frames_count
            self.last_write_t = t
            return
        else:
            fc = app_globals.frames_count
            if fc > self.last_write_frame_count:
                self.dtt = ((fc - self.last_write_frame_count) * self.frame_cycle_count) + t - self.last_write_t
                self.last_write_frame_count = fc
                self.last_write_t = t
            else:
                self.dtt = t - self.last_write_t
                self.last_write_t = t

            #self.log(f"{self.dtt=} freq={int(875000 / (self.dtt / 2))}")

            if self.dtt >= self.highest_frequency and self.dtt <= self.lowest_frequency:
                samples = int(self.dtt / self.t_samples)
                if self.stereo:
                    signal_left = int(1 * self.left_volume * self.amplitude_factor * self.amplitude)
                    signal_right = int(1 * self.right_volume * self.amplitude_factor * self.amplitude)
                    for _ in range(samples):
                        self.wave[self.wave_pos] = signal_left
                        self.wave_pos += 1
                        self.wave[self.wave_pos] = signal_right
                        self.wave_pos += 1
                    signal_left *= -1 #int(-1 * self.left_volume * self.amplitude_factor * self.amplitude)
                    signal_right *= -1 #int(-1 * self.right_volume * self.amplitude_factor * self.amplitude)
                    for _ in range(samples):
                        self.wave[self.wave_pos] = signal_left
                        self.wave_pos += 1
                        self.wave[self.wave_pos] = signal_right
                        self.wave_pos += 1
                else:
                    signal_mono = int(1 * self.mono_volume * self.amplitude_factor * self.amplitude)
                    for _ in range(samples):
                        self.wave[self.wave_pos] = signal_mono
                        self.wave_pos += 1
                    signal_mono *= -1 #int(-1 * self.mono_volume * self.amplitude_factor * self.amplitude)
                    for _ in range(samples):
                        self.wave[self.wave_pos] = signal_mono
                        self.wave_pos += 1
            else:
                self.dtt = 0

    def run_frame_end(self):
        # output current bufferd sound
        if not self.muted and self.wave_pos:
            if self.out_mode == 0:
                sound = self.mixer.Sound(self.wave[0:self.wave_pos]).play()
            else:
                sound = self.mixer.Sound(self.wave[0:self.wave_pos])
                self.mixer_channel.queue(sound)
                #self.save_wave(sound)

        self.wave_pos = 0

    def save_wave(self, snd):
        sfile = wave.open(f'./tmp/wave{self.wave_prog}.wav', 'w')
        # set the parameters
        sfile.setframerate(self.sample_rate)
        sfile.setnchannels(self.stereo+1)
        sfile.setsampwidth(2)
        # write raw PyGame sound buffer to wave file
        sfile.writeframesraw(snd.get_raw())
        sfile.close()
        self.wave_prog += 1

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

        log = open('./tmp/audio.log', 'a')
        log.write(s)
        log.close
