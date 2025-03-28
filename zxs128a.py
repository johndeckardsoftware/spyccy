#
# ZXSpectrum 128
#
from config import *
from display import TkScreenRenderer
from display2 import SDLScreenRenderer
from keyboard import OriginalKeyboardHandler, GamerKeyboardHandler, StandardKeyboardHandler
from beeper import BeeperController
from ay_controller import AYController
from mmu import MemoryManager
from ports import InOutManager
from zxs48a import ZXSpectrum48a
from beta_disk_controller import BetaDiskController as BetaDisk
import joystick
from joystick import JoysticksController
import pygame
from pygame.locals import *

class ZXSpectrum128a(ZXSpectrum48a):
    def __init__(self, frame, window):
        super().__init__( frame, window)
        self.name = 'ZXSpectrum 128'
        self.type = 128
        self.frame_cycle_count = 70908
        self.SYS_ROM0_BANK = 0
        self.SYS_ROM0_PAGE = 8
        self.SYS_ROM1_BANK = 0
        self.SYS_ROM1_PAGE = 9
        self.SYS_ROM0_WRITE_PAGE = 10 # to keep rom readonly

        #
        # additional roms mapping
        #
        # TR-DOS (beta disk 128)
        self.betadisk = None
        self.TRDOS_ROM_PAGE = 11
        self.TRDOS_ROM_BANK = self.SYS_ROM0_BANK    # when swapped in

    def setup(self):
        self.mmu = MemoryManager(0x4000, 12, self.cpu)  # 8, 9 rom; 5,2,0 ram; 10 rom write; 11 tr-dos rom
        self.mmu.SYS_ROM0_BANK = self.SYS_ROM0_BANK
        self.mmu.SYS_ROM0_PAGE = self.SYS_ROM0_PAGE
        self.mmu.SYS_ROM1_BANK = self.SYS_ROM1_BANK
        self.mmu.SYS_ROM1_PAGE = self.SYS_ROM1_PAGE
        self.mmu.SYS_ROM0_WRITE_PAGE = self.SYS_ROM0_WRITE_PAGE
        self.mmu.set_page_read_map([8, 5, 2, 0])
        self.mmu.set_page_write_map([10, 5, 2, 0])
        self.mmu.paging_locked = 0
        self.mmu.set_screen_page(5)
        self.load_rom(Config.get('machine.rom0', './support/roms/128-0.rom'), self.SYS_ROM0_PAGE)
        self.load_rom(Config.get('machine.rom1', './support/roms/128-1.rom'), self.SYS_ROM1_PAGE)
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
        self.AY = AYController(44100, Config.get('audio.stereo', 1), Config.get('audio.muted', 0), self.frame_cycle_count)

        # betadisk
        self.betadisk = BetaDisk(2)
        self.betadisk.enabled = Config.get('betadisk.enabled', 1)
        if self.betadisk.enabled:
            self.cpu.betadisk = self.betadisk.enabled
            self.mmu.TRDOS_ROM_PAGE = self.TRDOS_ROM_PAGE
            self.mmu.TRDOS_ROM_BANK = self.TRDOS_ROM_BANK
            self.load_rom(Config.get('betadisk.rom', './support/roms/trdos.rom'), self.TRDOS_ROM_PAGE)

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

    def reset(self, pc=0):
        self.pause(wait_eof=True)
        self.mmu.set_page_read_map([8, 5, 2, 0])
        self.mmu.set_page_write_map([10, 5, 2, 0])
        self.mmu.set_paging_locked(False)
        self.cpu.reset(pc)
        self.resume()