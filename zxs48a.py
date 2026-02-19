#
# ZXSpectrum 48
#
import os, time, asyncio
from array import array
import app_globals
from config import *
import z80a5 as z80a
from mmu import MemoryManager
from display import TkScreenRenderer
from display2 import SDLScreenRenderer
from keyboard import OriginalKeyboardHandler, GamerKeyboardHandler, StandardKeyboardHandler
from tape import TapeManager
from snapshot import parseZ80File, parseSZXFile, parseSNAFile, create_snapshot
from beeper import BeeperController
from ay_controller import AYController
from ports import InOutManager
from beta_disk_controller import BetaDiskController as BetaDisk
import joystick
from joystick import JoysticksController
import pygame
from pygame.locals import *

class ZXSpectrum48a:
    def __init__(self, tk_root, window):
        self.tk_root = tk_root
        self.window = window
        self.name = 'ZXSpectrum 48'
        self.status = MACHINE.STOPPED
        self.tasks = []
        self.type = 48
        self.cpu = z80a
        self.cpu.machine = self
        self.frame_cycle_count = 69888
        self.SYS_ROM0_BANK = 0
        self.SYS_ROM0_PAGE = 0
        self.SYS_ROM0_WRITE_PAGE = 4
        self.beeper_process_frame = 5
        self.ay_process_frame = 1
        self.constrain_50_fps = Config.get('machine.constrain', 0)

        # tape
        self.tapedeck = TapeManager(self)

        #
        # additional roms mapping
        #
        # TR-DOS (beta disk 128)
        self.betadisk = None
        self.TRDOS_ROM_PAGE = 6
        self.TRDOS_ROM_BANK = self.SYS_ROM0_BANK    # when swapped in

        # µSource Currah
        self.uSource = 0
        self.USOURCE_ROM_PAGE = 5
        self.USOURCE_ROM_BANK = 5   # no swap

        # Inferface 2 cartridge
        self.cartridge = 0
        self.cartridge_file = None
        self.CARTRIDGE_ROM_PAGE = 7
        self.CARTRIDGE_ROM_BANK = self.SYS_ROM0_BANK # when swapped in

    def setup(self):
        self.mmu = MemoryManager(0x4000, 8, self.cpu) # 0 rom; 1,2,3 ram; 4 rom write; 5 usource rom; 6 tr-dos rom, 7 if2 cartridge
        self.mmu.SYS_ROM0_BANK = self.SYS_ROM0_BANK
        self.mmu.SYS_ROM0_PAGE = self.SYS_ROM0_PAGE
        self.mmu.SYS_ROM0_WRITE_PAGE = self.SYS_ROM0_WRITE_PAGE
        self.mmu.set_page_read_map([self.SYS_ROM0_PAGE, 1, 2, 3])
        self.mmu.set_page_write_map([self.SYS_ROM0_WRITE_PAGE, 1, 2, 3])
        self.mmu.paging_locked = 1
        self.load_rom(Config.get('machine.rom0', './support/roms/48.rom'), self.SYS_ROM0_PAGE)
        self.window.status_bar.set_machine(self.name)

        # tape
        self.tapedeck.set_traps(Config.get('tape.enabled', True))

        # cpu
        self.cpu.mmu = self.mmu
        self.cpu.reset()
        self.cpu.tape_traps_enabled = self.tapedeck.traps_enabled
        self.cpu.frame_cycle_count = self.frame_cycle_count

        # screen
        if Config.get('display.renderer', 'tk') == 'tk':
            self.video = TkScreenRenderer(self.tk_root, self.mmu)
        else:
            self.video = SDLScreenRenderer(self.tk_root, self.mmu)

        # keyboard
        kb = Config.get('keyboard.type', 'standard')
        if kb == 'standard':
            self.keyboard = StandardKeyboardHandler(self.tk_root, self)
        elif kb == 'original':
            self.keyboard = OriginalKeyboardHandler(self.tk_root, self)
        else:
            self.keyboard = GamerKeyboardHandler(self.tk_root, self)

        # audio
        self.beeper = BeeperController(44100, Config.get('audio.stereo', 1), Config.get('audio.muted', 0), self.frame_cycle_count)
        #self.AY = None
        self.AY = AYController(44100, Config.get('audio.stereo', 1), Config.get('audio.muted', 0), self.frame_cycle_count)

        # betadisk
        self.betadisk = BetaDisk(2)
        self.betadisk.enabled = Config.get('betadisk.enabled', 1)
        if self.betadisk.enabled:
            self.cpu.betadisk = self.betadisk.enabled
            self.mmu.TRDOS_ROM_PAGE = self.TRDOS_ROM_PAGE
            self.mmu.TRDOS_ROM_BANK = self.TRDOS_ROM_BANK
            self.load_rom(Config.get('betadisk.rom', './support/roms/trdos.rom'), self.TRDOS_ROM_PAGE)

        # µSource
        self.uSource = Config.get('usource.enabled', 0)
        if self.uSource:
            self.cpu.uSource = self.uSource
            self.mmu.uSource = self.uSource
            self.mmu.USOURCE_ROM_PAGE = self.USOURCE_ROM_PAGE
            self.mmu.USOURCE_ROM_BANK = self.USOURCE_ROM_BANK
            self.load_rom(Config.get('usource.rom', './support/roms/usource.rom'), self.USOURCE_ROM_PAGE)

        # if2 cartridge
        self.cartridge = Config.get('cartridge.enabled', 0)
        if self.cartridge:
            self.cartridge_file = Config.get('cartridge.rom', '')
            if self.cartridge_file:
                self.mmu.CARTRIDGE_ROM_PAGE = self.CARTRIDGE_ROM_PAGE
                self.mmu.CARTRIDGE_ROM_BANK = self.CARTRIDGE_ROM_BANK
                self.load_rom(self.cartridge_file, self.CARTRIDGE_ROM_PAGE)
                self.mmu.switch_in_cartridge()

        # joystick
        if Config.get('joystick.enabled', 0):
            pygame.display.init()   # events works only with display module initialized
            pygame.event.set_blocked((QUIT, KEYDOWN, KEYUP, MOUSEMOTION, MOUSEWHEEL, MOUSEBUTTONUP, MOUSEBUTTONDOWN))
            self.joystick = JoysticksController(Config.get('joystick.type', joystick.SINCLAIR))
            print(self.joystick.info(full=1))
            if self.joystick.joycount == 0:
                self.joystick = None
        else:
            self.joystick = None

        # in/out
        self.ports = InOutManager(self)
        self.ports.set_frame_cycle_count(self.frame_cycle_count)
        self.cpu.ports = self.ports

    def get_frame_cycle_count(self):
        return self.frame_cycle_count

    def pause(self, wait_eof=False):
        self.status = MACHINE.PAUSED
        if wait_eof:
            self.tk_root.wait_variable(self.window.status_bar.status_var)

    def resume(self):
        self.status = MACHINE.RESUMED

    def stop(self):
        self.status = MACHINE.STOPPED

    def reset(self, pc=0):
        self.pause(wait_eof=True)
        self.cpu.reset(pc)
        self.resume()

    async def main_runner(self):
        self.setup()
        self.status = MACHINE.RUNNING
        self.tasks = [
            asyncio.create_task(self.run_frame())
        ]
        try:
            ret = await asyncio.gather(*self.tasks)
            self.video.stop()
            self.beeper.stop()
            if self.AY:
                self.AY.stop()
            if self.joystick:
                self.joystick.stop()
                pygame.display.quit()

            print(self.status)
            print(ret)
        except asyncio.CancelledError as e:
            print(e)
        return True

    async def run_frame(self):
        while self.status != MACHINE.STOPPED:
            if self.status == MACHINE.PAUSED:
                self.window.status_bar.set_status('paused')
                if pygame.joystick.get_init():
                    pygame.event.pump()
                await asyncio.sleep(1)
                continue
            elif self.status == MACHINE.RESUMED:
                self.window.status_bar.set_status('running')
                self.status = MACHINE.RUNNING

            frame_ms_start = time_ms_start = time.monotonic()

            ret = self.cpu.runFrame()

            while ret:
                if ret == 1:
                    raise Exception("unrecognised opcode")
                elif ret == 2:
                    self.tapedeck.basic_load()
                else:
                    raise Exception(f"runFrame returned unexpected result: {ret}")
                ret = self.cpu.resumeFrame()

            t = self.cpu.get_t_state() - self.frame_cycle_count
            self.cpu.set_t_state(t)

            time_ms_end = time.monotonic()
            app_globals.cpu_fps = (app_globals.cpu_fps + (time_ms_end - time_ms_start)) / 2

            # refresh video
            fc = app_globals.frames_count
            if fc % 2 == 0:
                time_ms_start = time.monotonic()
                self.video.show_frame()
                time_ms_end = time.monotonic()
                app_globals.video_fps = (app_globals.video_fps + (time_ms_end - time_ms_start)) / 2

            # stream beeper buffered sound
            if fc % self.beeper_process_frame == 0:
                self.beeper.run_frame_end()

            # stream AY buffered sound
            if self.AY and fc % self.ay_process_frame == 0:
                self.AY.run_frame_end()

            if pygame.joystick.get_init():
                pygame.event.pump()

            if self.constrain_50_fps and app_globals.frame_fps < 0.02:
                await asyncio.sleep(0.028 - app_globals.frame_fps)

            app_globals.frame_fps = (app_globals.frame_fps + (time.monotonic() - frame_ms_start)) / 2
            if fc % 250 == 0:
                self.window.status_bar.set_cpu_fps(str(round(app_globals.cpu_fps, 3)))
                self.window.status_bar.set_video_fps(str(round(app_globals.video_fps, 4)))
                #self.window.status_bar.set_tk_fps(str(round(app_globals.tk_fps, 3)))
                self.window.status_bar.set_fps(str(int(1 / (app_globals.frame_fps))))
                if self.tapedeck.is_playing:
                    self.window.status_bar.set_tape(self.tapedeck.name + app_globals.TAPE_PLAYING[self.tapedeck.count])
                    self.tapedeck.count += 1
                    if self.tapedeck.count > 1: self.tapedeck.count = 0

            app_globals.frames_count += 1

        return True

    # to test small code frame
    def run(self):
        ret = self.cpu.runUntil(4)
        return ret

    #mmu
    def load_ram_page(self, page, data):
        self.mmu.write_block(page, 0, data, 0, len(data))

    def load_rom(self, romfile, dest):
        fh = open(romfile, "rb")
        rom = fh.read()
        fh.close()
        self.mmu.write_block(dest, 0, rom, 0, len(rom))

    # snapshot
    def load_snapshot(self, snapshot):
        self.pause(wait_eof=True)
        #self.setMachineType(snapshot['model'])
        for page in snapshot['memoryPages']:
            self.load_ram_page(page, snapshot['memoryPages'][page])

        self.cpu.set_cpu_state(snapshot)

        self.ports.write(0x00fe, snapshot['ulaState']['borderColour'])
        if snapshot['model'] != 48:
            self.ports.write(0x7ffd, snapshot['ulaState']['pagingFlags'])

        self.cpu.set_t_state(snapshot['tstates'])
        self.resume()

    def process_snapshot(self, filename):
        try:
            with open(filename, 'rb') as file:
                pf = os.path.split(filename)
                self.window.status_bar.set_tape(pf[1])
                arrayBuffer = array("B")
                arrayBuffer.fromfile(file, os.stat(filename).st_size)
                file_type = filename[-4:].lower()
                if file_type == '.z80':
                    z80file = parseZ80File(arrayBuffer)
                    return self.load_snapshot(z80file)

                elif file_type == '.szx':
                    szxfile = parseSZXFile(arrayBuffer)
                    return self.load_snapshot(szxfile)

                elif file_type == '.sna':
                    snafile = parseSNAFile(arrayBuffer)
                    return self.load_snapshot(snafile)

                else:
                    self.window.status_bar.set_tape("unknow format")
        except Exception as e:
            self.window.msgbox(str(e))

    def save_snapshot(self, file):
        self.pause(wait_eof=True)
        snap, size = create_snapshot(self, self.cpu, self.mmu, self.ports, self.AY)
        with open(file, 'wb') as file:
            snap[0:size].tofile(file)
        self.resume()

    # audio
    def set_sound(self, what, val):
        if self.beeper:
            if what == 0: self.beeper.mute(val)
            elif what == 1: self.beeper.stereo = val
            elif what == 2: self.beeper.out_mode = val
            elif what == 3: self.beeper_process_frame = val
        if self.AY:
            if what == 16: self.AY.mute(val)
            if what == 17: self.AY.mute_channel(0, val)
            if what == 18: self.AY.mute_channel(1, val)
            if what == 19: self.AY.mute_channel(2, val)
            elif what == 32: self.AY.set_stereo(val)

    # display
    def set_zoom(self, zoom):
        self.video.set_zoom(zoom)

    # additional roms
    def usource_enable(self, val):
        self.uSource = val
        self.mmu.uSource = val

    def load_disk(self, drive, filename):
        return self.betadisk.load_disk(drive, filename)

    def save_disk(self, drive, filename):
        return self.betadisk.save_disk(drive, filename)

    def eject_disk(self, drive):
        return self.betadisk.eject_disk(drive)

    def eject_cartridge(self):
        self.pause(wait_eof=True)
        self.mmu.switch_out_cartridge()
        self.cpu.reset()
        self.resume()

    def keyboard_type(self, type):
        if type == 'standard':
            self.keyboard = StandardKeyboardHandler(self.tk_root, self)
        elif type == 'original':
            self.keyboard = OriginalKeyboardHandler(self.tk_root, self)
        else:
            self.keyboard = GamerKeyboardHandler(self.tk_root, self)
        self.ports.keyboard = self.keyboard

    def key_sequence(self, key_sequence_id):
        self.keyboard.key_sequence(key_sequence_id)

    def keyboard_help(self):
        self.keyboard.show_help()

    def joystick_type(self, type):
        if self.joystick:
            self.joystick.set_type(type)

    def log(self, text):
        log = open('./tmp/zxs48a.log', 'a')
        log.write(text)
        log.write("\n")
        log.close
