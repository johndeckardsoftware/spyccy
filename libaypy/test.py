import os, platform, time
from array import array
from pygame import mixer as mixer
from cffi import FFI

AY = None

class ayemu:

    def __init__(self):
        # check and setup libayemu
        _os_ = platform.system().lower()
        arch = platform.machine().lower()
        #libname = os.path.join(os.path.dirname(__file__), f"displayc_{_os_}_{arch}.lib")
        libname = os.path.join(os.path.dirname(__file__), f"src/libayemu.a")
        if os.path.exists(libname):
            self.use_c_code = True
            self.ffi = FFI()
            self.libayemu = self.ffi.dlopen(libname)
            self.ffi.cdef("void ayemu_init();")
            self.ffi.cdef("void ayemu_reset();")
            self.ffi.cdef("int ayemu_set_chip_type(int chip, int *custom_table);")
            self.ffi.cdef("void ayemu_set_chip_freq(int chipfreq);")
            self.ffi.cdef("int ayemu_set_stereo(int stereo, int *custom_eq);")
            self.ffi.cdef("int ayemu_set_sound_format(int freq, int chans, int bits);")
            self.ffi.cdef("void ayemu_set_regs(unsigned char * regs);")
            self.ffi.cdef("void *ayemu_gen_sound(void *buf, size_t bufsize);")
            
            self.regs = bytearray(14)

            self.freq = 44100
            self.chans = 2; #/* 1=mono, 2=stereo */
            self.bits = 16; #/* 16 or 8 bit */
            
            self.audio_bufsize = int(self.freq * self.chans * (self.bits >> 3) / 50)
            self.audio_buf = self.wave = array('h', [0] * self.audio_bufsize)  # max 1 sec buffer

            self.mixer = mixer
            self.mixer.pre_init(size=-16, buffer=512, channels=self.chans)
            self.mixer.init()

        else:
            self.use_c_code = False
            print(f"'{libname}' not found, screen optimizations disabled")

    def init(self):
        self.libayemu.ayemu_init()

    def set_regs(self, regs):
        self.libayemu.ayemu_set_regs(self.ffi.from_buffer(regs))

    #def gen_sound(self, buffer, buffer_size):
    def gen_sound(self):
        self.libayemu.ayemu_gen_sound(self.ffi.from_buffer(self.audio_buf), self.audio_bufsize)
        return self.audio_buf

def gen_sound(tonea, toneb, tonec, noise, control, vola, volb, volc, envfreq, envstyle):

    regs = bytearray(14)

    #/* setup regs */
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

    #/* test setreg function: set from array and dump internal regs data */
    AY.set_regs(regs)

    #/* generate sound */
    for _ in range(0, 50):
        AY.gen_sound()
        sound = AY.mixer.Sound(AY.audio_buf)
        #print(AY.audio_buf.buffer_info())
        #sound.play()
        AY.mixer.Channel(0).queue(sound)
        time.sleep(0.02)

def test():
    global AY

    AY = ayemu()
    AY.init()

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
        gen_sound(tonea, toneb, tonec, noise, control, vola, volb, volc, envfreq, envstyle)


if __name__ == '__main__':
    test()

