#
# only windows and very instable
#
import platform
from cffi import FFI
import pygame
import tkinter as tk
from config import *
import app_globals

class SDLScreenRenderer:
    def __init__(self, window, mmu):
        self.window = window
        self.mmu = mmu
        self.canvas_width = window.winfo_width()
        self.canvas_height = window.winfo_height()
        self.width = 256
        self.height = 192
        self.left = 0
        self.top = 0
        self.zoom = Config.get('display.zoom', 2)
        self.resize = (self.width * self.zoom, self.height * self.zoom)
        self.flash_phase = 0
        self.current_border_color = -1
        self.set_zoom(self.zoom)
        self.canvas = tk.Frame(window, width=self.resize[0], height=self.resize[1])
        self.canvas.pack(anchor=tk.CENTER, fill="both", expand=True)
        self.palette = [
            (0x00, 0x00, 0x00), # black
            (0x00, 0x00, 0xc0), # blue
            (0xc0, 0x00, 0x00), # red
            (0xc0, 0x00, 0xc0), # magenta
            (0x00, 0xc0, 0x00), # green
            (0x00, 0xc0, 0xc0), # cyan
            (0xc0, 0xc0, 0x00), # yellow
            (0xd0, 0xd0, 0xd0), # white
            (0x00, 0x00, 0x00),
            (0x00, 0x00, 0xff),
            (0xff, 0x00, 0x00),
            (0xff, 0x00, 0xff),
            (0x00, 0xff, 0x00),
            (0x00, 0xff, 0xff),
            (0xff, 0xff, 0x00),
            (0xff, 0xff, 0xff),
        ]
        # check library to boost pixels handling
        _os_ = platform.system().lower()
        arch = platform.machine().lower()
        libname = os.path.join(os.path.dirname(__file__), f"displayc_{_os_}_{arch}.lib")
        if os.path.exists(libname):
            self.use_c_code = True
            self.ffi = FFI()
            self.displayc = self.ffi.dlopen(libname)
            self.ffi.cdef("int set_frame_p8(char *, char *, int, int, int);")
        else:
            self.use_c_code = False
            print(f"'{libname}' not found, screen optimizations disabled")

        # trick to embed pygame screen into tkinter canvas 
        os.environ['SDL_WINDOWID'] = str(self.canvas.winfo_id())
        os.environ['SDL_VIDEODRIVER'] = 'windib'
        self.init_display = True

    def display_init(self):
        pygame.display.init()
        self.zx_screen = pygame.surface.Surface((self.width, self.height), depth=8)
        self.zx_screen.set_palette(self.palette)
        self.zx_screen_with_zoom = pygame.surface.Surface(self.resize, depth=8)
        self.zx_screen_with_zoom.set_palette(self.palette)
        self.screen_pixels = self.zx_screen.get_buffer()
        self.screen_pixels_p = bytearray(self.width * self.height * 1) # using palette index, so only one byte per pixel
        self.screen = pygame.display.set_mode(size=self.resize, flags=pygame.NOFRAME)
        print(pygame.display.Info())
        pygame.display.flip()

    def set_zoom(self, zoom):
        self.zoom = zoom
        self.resize = (self.width * self.zoom, self.height * self.zoom)
        self.left = (self.canvas_width - (self.width * self.zoom)) // 2
        self.top = (self.canvas_height - (self.height * self.zoom)) // 2

    def show_frame(self):
        if self.init_display:
            self.display_init()
            self.init_display = False

        bitmap = self.screen_pixels_p
        flash_phase = self.flash_phase
        border_color = app_globals.border_color
        if border_color != self.current_border_color:
            self.current_border_color = border_color
            bc = self.rgb(self.palette[border_color])
            self.screen.fill(bc)

        vram, screen_addr, attrib_addr = self.mmu.get_video_ram()

        if self.use_c_code:
            self.displayc.set_frame_p8(self.ffi.from_buffer(bitmap), self.ffi.from_buffer(vram), screen_addr, attrib_addr, flash_phase)
        else:
            row = col = 0
            bitmap_ptr = 0
            char_attrib_ptr = attrib_addr
            for rows_block_addr in range(0, 0x1800, 0x800):
                char_first_byte = screen_addr + rows_block_addr
                for _ in range(0, 8):
                    for col in range(0, 32):
                        attr = vram[char_attrib_ptr]
                        if (attr & 0x80) and (flash_phase & 0x10):
                            # reverse ink and paper
                            paper = ((attr & 0x40) >> 3) | (attr & 0x07)
                            ink = (attr & 0x78) >> 3
                        else:
                            ink = ((attr & 0x40) >> 3) | (attr & 0x07)
                            paper = (attr & 0x78) >> 3

                        bitmap_ptr = row * 2048 + col * 8 # (32 * 8 * 1) * 8, 8 * 1
                        for char_other_bytes_offset in range(0, 0x800, 0x100):
                            char_pixels = vram[char_first_byte + char_other_bytes_offset]

                            ptr = bitmap_ptr
                            for _ in range(0, 8):
                                if (char_pixels & 0x80):
                                    bitmap[ptr] = ink
                                else:
                                    bitmap[ptr] = paper
                                ptr += 1
                                char_pixels <<= 1
                            bitmap_ptr += 256 # 32 * 8 * 1

                        char_attrib_ptr += 1
                        char_first_byte += 1
                    row = row + 1

        self.screen_pixels.write(bytes(self.screen_pixels_p), 0)
        pygame.transform.scale(self.zx_screen, self.resize, self.zx_screen_with_zoom)
        self.screen.blit(self.zx_screen_with_zoom, (self.left, self.top))
        pygame.display.flip()

        self.flash_phase = (self.flash_phase + 1) & 0x1f

    def rgb(self, rgb):
        return (rgb[0] << 16) | (rgb[1] << 8) | rgb[2]

    def stop(self):
        del os.environ['SDL_WINDOWID']
        pygame.display.quit()
        self.canvas.destroy()
