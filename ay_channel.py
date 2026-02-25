#
# Adapted from HOME OF SPECTRUM 48  https://softspectrum48.weebly.com/
#
# One AYChannel object is created by the AYController for each sound channel (A,B,C).
# The AYChannel holds the channel parameter states (volume, pitch etc.) and 
# the wave generator
#
import time
import math
from array import array
from config import Config

class AYChannel:

    def __init__(self, id, name, controller, mixer):
        self.id = id
        self.name = name
        self.controller = controller
        self.mixer = mixer
        self.stereo = controller.stereo # 0 == mono, 1 == stereo
        self.streams = controller.stereo + 1
        self.muted = 0

        # The AY clock frequency affects the tone and envelope frequencies.
        self.AY_clock_frequency = 1773400  # zx 1773400 MHz
        self.frame_t_state_count = controller.frame_t_state_count
        self.actual_fps = Config.get('ay.py.fps', 50)
        self.frequency_adjuster = Config.get('ay.py.freq_adj', 8)

        # General AY signal parameters.
        self.tone_period_low_byte = 0
        self.tone_period_high_byte = 0
        self.tone_pitch = 0
        self.current_tone_pitch = 0
        self.noise_pitch = 0
        self.current_noise_pitch = 0
        #self.tone_in_mix = False
        #self.noise_in_mix = False

        self.amplitude = 0
        self.max_amplitude = 16
        self.amplitude_factor = 0.5
        # The AY amplitude values (0-15) are translated to output volume according to a logarithmic function, approximated in the AmplitudeFactors array.
        # Values according to: http://forum.tslabs.info/viewtopic.php?f=6&t=539
        self.amplitude_factors = [0.0, 0.01, 0.014, 0.021, 0.031, 0.046, 0.064, 0.107, 0.127, 0.205, 0.292, 0.373, 0.493, 0.635, 0.806, 1.0]

        self.phase_angle_tone = 0
        self.phase_angle_noise = 0
        self.phase_angle_increment_tone = 0
        self.phase_angle_increment_noise = 0
        self.tone_signal_on = False
        self.noise_signal_on = False
        self.left_volume = Config.get(f'ay.py.{name.lower()}.lvolume', 0)
        self.right_volume = Config.get(f'ay.py.{name.lower()}.rvolume', 0)

        # Envelope variables
        self.envelope_period_low_byte = 0
        self.envelope_period_high_byte = 0
        self.initial_amplitude = 0
        self.envelope_amplitude = 0
        self.envelope_period = 0
        self.envelope_shape = 0
        self.envelope_step = 0
        self.envelope_on = False
        self.envelope_direction = 0

        # noise variables
        self.noise1 = 0
        self.noise2 = 0
        self.seed = 0x1FFFF

        # out signal
        self.last_write_t = 0
        self.wave_sample_rate = controller.sample_rate
        self.wave_frame_samples = self.wave_sample_rate
        self.wave_tstate_samples = int(self.frame_t_state_count / (self.wave_sample_rate / self.actual_fps)) # 8  
        #self.log(f"{self.name} >>> {self.wave_sample_rate=} {self.wave_frame_samples=} {self.wave_tstate_samples=}")

        # out wave buffer
        self.wave = array('h', [0] * (self.wave_sample_rate * (self.streams)))  # max 1 sec buffer
        self.wave_data_index = 0
        # wave_data_size = freq * chans * (bits / 8) / player_freq
        # freq=self.wave_sample_rate
        # chans=self.streams
        # (bits/8)='h'
        # player_freq=50Hz   
        self.wave_data_length = int(self.wave_sample_rate * self.controller.play_frame * self.streams / self.actual_fps) 

        # initalize player
        self.mixer = self.mixer
        self.mixer_channel = self.mixer.Channel(self.id)

        # log
        self.log_enabled = 0  # 0 = no log, 1 = log, 2 = full log
        self.log_last_text = ""
        self.log_same_as_last_count = 0

        self._2PI_ = 2 * math.pi

    def generate_wave(self, sample_count):

        if self.muted:
            return -1

        #self.log(f"{self.channel.name} generate_wave {sampleCount=} {self.wave_data_index=} {{self.wave_data_max=}}")
        out_signal = 0
        signal_tone = 0
        signal_noise = 0
        signal = 0

        stereo = self.stereo
        wave = self.wave
        wave_data_index = self.wave_data_index
        
        # Loop through every sample
        for _ in range(0, sample_count):
            out_signal = 0.0

            # Is the tone signal on or off?
            if self.tone_signal_on:
                if self.phase_angle_tone < math.pi:
                    signal_tone = 1
                else:
                    signal_tone = 0

            # Is the noise signal on or off?
            if self.noise_signal_on:
                if self.phase_angle_noise < math.pi:
                    signal_noise = self.noise1
                else:
                    signal_noise = self.noise2

            # Merge the tone and noise signals.
            # - If both signals are in the mix, they are AND:ed together.
            # - If both signals are off, a constant high signal is generated.
            if self.noise_signal_on and self.tone_signal_on:
                signal = signal_tone & signal_noise
            else:
                if not self.noise_signal_on and not self.tone_signal_on:
                    signal = 1
                else:
                    signal = signal_tone + signal_noise

            # Set the signal low level to -1 for a fuller sound.
            if signal == 0:
                signal = -1

            # Apply volume envelope if it is active.
            if self.envelope_on:
                # The integer amplitude value can be 0-15. The Floor method converts
                # a floating point value to the neareast highest integer.
                # This means that a saw tooth envelope will look like this:
                # 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0 0 1 ...
                # This is according to figure 6 in the AY-3-8910/8912 Manual.
                amplitude = int(math.floor(self.envelope_amplitude))
                self.amplitude = 0 if (amplitude < 0) else 15 if (amplitude > 15) else amplitude

            # Calculate the resulting buffer value.
            out_signal = signal * self.amplitude_factors[self.amplitude]

            # Adjust volume envelope.
            if self.envelope_on:
                self.envelope_amplitude += self.envelope_direction * self.envelope_step

                match self.envelope_shape:
                    case 0: # Shape: \__________
                        if self.envelope_amplitude < 0:
                            self.envelope_amplitude = 0
                            self.envelope_step = 0

                    case 1: # Shape: \__________
                        if self.envelope_amplitude < 0:
                            self.envelope_amplitude = 0
                            self.envelope_step = 0

                    case 2: # Shape: \__________
                        if self.envelope_amplitude < 0:
                            self.envelope_amplitude = 0
                            self.envelope_step = 0

                    case 3: # Shape: \__________
                        if self.envelope_amplitude < 0:
                            self.envelope_amplitude = 0
                            self.envelope_step = 0

                    case 4: # Shape: /|_________
                        if self.envelope_amplitude > self.max_amplitude:
                            self.envelope_amplitude = 0
                            self.envelope_step = 0

                    case 5: # Shape: /|_________
                        if self.envelope_amplitude > self.max_amplitude:
                            self.envelope_amplitude = 0
                            self.envelope_step = 0

                    case 6: # Shape: /|_________
                        if self.envelope_amplitude > self.max_amplitude:
                            self.envelope_amplitude = 0
                            self.envelope_step = 0

                    case 7: # Shape: /|_________
                        if self.envelope_amplitude > self.max_amplitude:
                            self.envelope_amplitude = 0
                            self.envelope_step = 0

                    case 8: # Shape: \|\|\|\|\|
                        if self.envelope_amplitude < 0:
                            self.envelope_amplitude = self.max_amplitude

                    case 9: # Shape: \__________
                        if self.envelope_amplitude < 0:
                            self.envelope_amplitude = 0
                            self.envelope_step = 0

                    case 10: # Shape: \/\/\/\/\/
                        if self.envelope_amplitude < 0 or self.envelope_amplitude > self.max_amplitude:
                            self.envelope_direction = -self.envelope_direction
                        self.envelope_amplitude = 12

                    case 11: # Shape: \|^^^^^
                        if self.envelope_amplitude < 0:
                            self.envelope_amplitude = self.max_amplitude
                            self.envelope_step = 0

                    case 12: # Shape: /|/|/|/|/|/
                        if self.envelope_amplitude > self.max_amplitude:
                            self.envelope_amplitude = 0

                    case 13: # Shape: /^^^^^
                        if self.envelope_amplitude > self.max_amplitude:
                            self.envelope_amplitude = self.max_amplitude
                            self.envelope_step = 0

                    case 14: # Shape: /\/\/\/\/\/
                        if self.envelope_amplitude < 0 or self.envelope_amplitude > self.max_amplitude:
                            self.envelope_direction = -self.envelope_direction

                    case 15: # Shape: /|_________
                        if self.envelope_amplitude > self.max_amplitude:
                            self.envelope_amplitude = 0
                            self.envelope_step = 0

            # Store the value in the left and right channel stream.
            wave[wave_data_index] = int(out_signal * self.left_volume * self.amplitude_factor * 32767)
            wave_data_index += 1
            if stereo:
                wave[wave_data_index] = int(out_signal * self.right_volume * self.amplitude_factor * 32767)
                wave_data_index += 1

            # Increase the tone phase angle.
            self.phase_angle_tone += self.phase_angle_increment_tone

            if self.phase_angle_tone >= self._2PI_:
                self.phase_angle_tone -= self._2PI_

            # Increase the noise phase angle.
            self.phase_angle_noise += self.phase_angle_increment_noise

            if self.phase_angle_noise >= self._2PI_:
                self.phase_angle_noise -= self._2PI_

                self.noise1 = self.next_noise_value()
                self.noise2 = self.next_noise_value()
        
        self.wave_data_index = wave_data_index
        #self.wave = wave
        return sample_count

    def get_tstate_samples(self, t):
        dt = t - self.last_write_t
        t_samples = dt // self.wave_tstate_samples
        self.last_write_t = t
        return t_samples

    # Mutes the signals.
    # The signals can still be in the mix, but the sound is muted.
    def mute(self, val):
        self.muted = val

    # Sets the tone and noise signal left-right balance.
    def set_balance(self, left_volume, right_volume):
        if self.left_volume == 0 and left_volume >= 0 and left_volume <= 1:
            self.left_volume = left_volume

        if self.right_volume == 0 and right_volume >= 0 and right_volume <= 1:
            self.right_volume = right_volume

    # Sets the high byte of the tone period and trigger a pitch change.
    def set_tone_period_high_byte(self, t, tone_period_high_byte):
        self.tone_period_high_byte = tone_period_high_byte
        t_samples = self.get_tstate_samples(t)
        self.set_tone_pitch(t_samples)

    # Sets the low byte of the tone period and trigger a pitch change.
    def set_tone_period_low_byte(self, t, tone_period_low_byte):
        self.tone_period_low_byte = tone_period_low_byte
        #t_samples = self.get_tstate_samples(t)
        #self.set_tone_pitch(t_samples)

    # Sets the noise period and update the signal generator frequency.
    def set_noise_period(self, t, noise_period):
        if noise_period != 0:
            self.noise_pitch = self.AY_clock_frequency / (self.frequency_adjuster * noise_period)
        else:
            self.noise_pitch = self.AY_clock_frequency / self.frequency_adjuster # Noise period = 0 equals 1.

        t_samples = self.get_tstate_samples(t)
        # The signal frequency is translated to a phase angle increment value,
        # which is the step size used when delivering values from the buffer to
        # the audio stream.
        if self.noise_pitch != self.current_noise_pitch:
            self.phase_angle_increment_noise = (self._2PI_ * self.noise_pitch) / self.wave_sample_rate
            self.current_noise_pitch = self.noise_pitch
            if t_samples:
                self.generate_wave(t_samples)

    # Sets the high byte of the envelope period.
    def set_envelope_period_high_byte(self, t, envelope_period_high_byte):
        self.envelope_period_high_byte = envelope_period_high_byte
        t_samples = self.get_tstate_samples(t)
        self.set_envelope_period(t_samples)

    # Sets the low byte of the envelope period.
    def set_envelope_period_low_byte(self, t, envelope_period_low_byte):
        self.envelope_period_low_byte = envelope_period_low_byte
        #t_samples = self.get_tstate_samples(t)
        #self.set_envelope_period(t_samples)

    # Sets the channel volume or envelope.
    def set_volume(self, t, volume):
        t_samples = self.get_tstate_samples(t)
        if volume & 0x10:
            # Bit 4 is set: Activate envelope.            
            if not self.envelope_on:
                self.envelope_on = True
                self.reset_envelope()
                if t_samples:
                    self.generate_wave(t_samples)            
        else:
            volume &= 0x0f
            # Bit 4 is reset: Deactivate envelope and set volume to bit 0-3.
            self.envelope_on = False
            self.amplitude = volume
            if t_samples:
                self.generate_wave(t_samples)

    # Turns the tone signal on or off.
    def set_tone_in_mix(self, t, in_mix):
        t_samples = self.get_tstate_samples(t)
        if in_mix:
            if not self.tone_signal_on:
                self.tone_signal_on = True
                self.reset_envelope()
                if t_samples:
                    self.generate_wave(t_samples)
        else:
            self.tone_signal_on = False
            if t_samples:
                self.generate_wave(t_samples)            

    # Turns the noise signal on or off.
    def set_noise_in_mix(self, t, in_mix):
        t_samples = self.get_tstate_samples(t)
        if in_mix:
            if not self.noise_signal_on:
                self.noise_signal_on = True
                self.reset_envelope()
                if t_samples:
                    self.generate_wave(t_samples)
        else:
            self.noise_signal_on = False
            if t_samples:
                self.generate_wave(t_samples)

    # Sets the envelope shape.
    def set_envelope_shape(self, t, shape):
        t_samples = self.get_tstate_samples(t)
        self.envelope_shape = shape & 0x0f
        self.reset_envelope()
        if t_samples:
            self.generate_wave(t_samples)

    # Sets the tone pitch and update the signal generator frequency.
    def set_tone_pitch(self, t_samples):
        tonePeriod = (self.tone_period_high_byte << 8) | self.tone_period_low_byte
        if tonePeriod != 0:
            self.tone_pitch = self.AY_clock_frequency / (self.frequency_adjuster * tonePeriod)
        else:
            self.tone_pitch = self.AY_clock_frequency / self.frequency_adjuster # Tone period = 0 equals 1.
        # The signal frequency is translated to a phase angle increment value,
        # which is the step size used when delivering values from the buffer to
        # the audio stream.
        if self.tone_pitch != self.current_tone_pitch:
            self.phase_angle_increment_tone = (self._2PI_ * self.tone_pitch) / self.wave_sample_rate
            self.current_tone_pitch = self.tone_pitch
            if t_samples:
                self.generate_wave(t_samples)

    # Sets the envelope period.
    def set_envelope_period(self, t_samples):
        envelope_period_value = (self.envelope_period_high_byte << 8) | self.envelope_period_low_byte
        if envelope_period_value == 0:
            envelope_period_value = 1
        self.envelope_period = (256 * envelope_period_value) / self.AY_clock_frequency
        self.update_envelope_period()
        if t_samples:              
            self.generate_wave(t_samples)

    # Update the envelope period.
    # The envelope is not restarted when the period is updated.
    def update_envelope_period(self):
        if self.envelope_period:
            self.envelope_step = float(self.max_amplitude) / (self.envelope_period * self.wave_sample_rate)
        else:
            self.envelope_step = 0

    # Reset envelope.
    def reset_envelope(self):
        self.update_envelope_period()

        match self.envelope_shape:
            case 0: # Shape: \__________
                self.initial_amplitude = self.max_amplitude
                self.envelope_direction = -1
            case 1: # Shape: \__________
                self.initial_amplitude = self.max_amplitude
                self.envelope_direction = -1
            case 2: # Shape: \__________
                self.initial_amplitude = self.max_amplitude
                self.envelope_direction = -1
            case 3: # Shape: \__________
                self.initial_amplitude = self.max_amplitude
                self.envelope_direction = -1
            case 4: # Shape: /|_________
                self.initial_amplitude = 0
                self.envelope_direction = 1
            case 5: # Shape: /|_________
                self.initial_amplitude = 0
                self.envelope_direction = 1
            case 6: # Shape: /|_________
                self.initial_amplitude = 0
                self.envelope_direction = 1
            case 7: # Shape: /|_________
                self.initial_amplitude = 0
                self.envelope_direction = 1
            case 8: # Shape: \|\|\|\|\|
                self.initial_amplitude = self.max_amplitude
                self.envelope_direction = -1
            case 9: # Shape: \__________
                self.initial_amplitude = self.max_amplitude
                self.envelope_direction = -1
            case 10: # Shape: \/\/\/\/\/
                self.initial_amplitude = self.max_amplitude
                self.envelope_direction = -1
            case 11: # Shape: \|^^^^^
                self.initial_amplitude = self.max_amplitude
                self.envelope_direction = -1
            case 12: # Shape: /|/|/|/|/|/
                self.initial_amplitude = 0
                self.envelope_direction = 1
            case 13: # Shape: /^^^^^
                self.initial_amplitude = 0
                self.envelope_direction = 1
            case 14: # Shape: /\/\/\/\/\/
                self.initial_amplitude = 0
                self.envelope_direction = 1
            case 15: # Shape: /|_________
                self.initial_amplitude = 0
                self.envelope_direction = 1

        self.envelope_amplitude = self.initial_amplitude

    # Gets the next on/off (0/1) value.
    # Returns a 0 for off or a 1 for on
    def next_noise_value(self):
        # The algorithm is explained in the Fuse source:
        # The Random Number Generator of the 8910 is a 17-bit shift
        # register. The input to the shift register is bit0 XOR bit3
        # (bit0 is the output). This was verified on AY-3-8910 and YM2149 chips.
        # The following is a fast way to compute bit17 = bit0^bit3
        # Instead of doing all the logic operations, we only check
        # bit0, relying on the fact that after three shifts of the
        # register, what now is bit3 will become bit0, and will
        # invert, if necessary, bit14, which previously was bit17
        if (self.seed & 1) == 1:
            self.seed ^= 0x24000

        self.seed >>= 1
        return self.seed & 1

    def play_wave(self, play):
        sound = None
        if not self.muted:
            if self.wave_data_index > 0 and play:
                fill_samples = self.wave_data_length - self.wave_data_index
                if fill_samples > 0:
                    self.generate_wave(fill_samples)
                    sound = self.mixer.Sound(self.wave[0:self.wave_data_index])
                    #self.mixer_channel.queue(sound)
                    self.wave_data_index = 0
        
        self.last_write_t = 0
        return sound
    
    def log(self, text):
        if self.log_enabled:
            s = f"{text}\n"
            if s == self.log_last_text:
                self.log_same_as_last_count += 1
                if self.log_same_as_last_count > 20000:
                    self.log_same_as_last_count = 0
                    s = f"(10000) {s}"
                else:
                    return
            else:
                if self.log_same_as_last_count:
                    s = f"({self.log_same_as_last_count}) {self.log_last_text}{s}"
                    self.log_same_as_last_count = 0
                self.log_last_text = s

            log = open('./tmp/ay.log', 'a')
            s = f'{time.monotonic()}: {text}\n'
            log.write(s)
            log.close