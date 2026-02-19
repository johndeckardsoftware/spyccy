import time, platform
from cffi import FFI
import tkinter as tk
from PIL import Image, ImagePalette
from PIL import ImageTk as itk
from config import *
import app_globals

# Screen specifications: 
# 32 x 24 chars     256 x 192 pixels    border:
# absolute pointers:
# screen: 0x4000 - 0x47ff first 8 rows, 0x4800 - 0x4fff second 8 rows, 0x5000 0x57ff last 8 rows
# attrib: 0x5800 - 0x5aff  
# relative pointers:
# screen: 0x0000 - 0x07ff first 8 rows, 0x0800 - 0x0fff second 8 rows, 0x1000 0x17ff last 8 rows
# attrib: 0x1800 - 0x1aff  

class TkScreenRenderer:
    def __init__(self, window, mmu):
        self.mmu = mmu
        self.canvas_width = 640 if window.winfo_width() == 1 else window.winfo_width() #:-O
        self.canvas_height = 500 if window.winfo_height() == 1 else window.winfo_height() #:-O
        self.canvas = tk.Canvas(window, width=self.canvas_width, height=self.canvas_height, bg='#d0d0d0')
        self.canvas.pack(anchor=tk.CENTER, fill="both", expand=True)
        self.left = 0
        self.top = 0
        self.width = 256
        self.height = 192
        self.zoom = Config.get('display.zoom', 2)
        self.resize = (self.width * self.zoom, self.height * self.zoom)
        self.screen_pixels_p = bytearray(self.width * self.height * 1)           # cols * rows * palette index (P)
        self.screen_pixels_rgb = bytearray(self.resize[0] * self.resize[1] * 3)  # cols * rows * RGB
        self.actual_screen_frame = None
        self.image_id = 0
        self.flash_phase = 0
        self.current_border_color = -1
        self.set_zoom(self.zoom)
        self.palette = [
                [0x00, 0x00, 0x00], # black
                [0x00, 0x00, 0xc0], # blue
                [0xc0, 0x00, 0x00], # red
                [0xc0, 0x00, 0xc0], # magenta
                [0x00, 0xc0, 0x00], # green
                [0x00, 0xc0, 0xc0], # cyan
                [0xc0, 0xc0, 0x00], # yellow
                [0xd0, 0xd0, 0xd0], # white
                [0x00, 0x00, 0x00],
                [0x00, 0x00, 0xff],
                [0xff, 0x00, 0x00],
                [0xff, 0x00, 0xff],
                [0x00, 0xff, 0x00],
                [0x00, 0xff, 0xff],
                [0xff, 0xff, 0x00],
                [0xff, 0xff, 0xff],
            ]
        self.image_palette = ImagePalette.ImagePalette("RGB", [
                0x00, 0x00, 0x00, # black
                0x00, 0x00, 0xc0, # blue
                0xc0, 0x00, 0x00, # red
                0xc0, 0x00, 0xc0, # magenta
                0x00, 0xc0, 0x00, # green
                0x00, 0xc0, 0xc0, # cyan
                0xc0, 0xc0, 0x00, # yellow
                0xd0, 0xd0, 0xd0, # white
                0x00, 0x00, 0x00,
                0x00, 0x00, 0xff,
                0xff, 0x00, 0x00,
                0xff, 0x00, 0xff,
                0x00, 0xff, 0x00,
                0x00, 0xff, 0xff,
                0xff, 0xff, 0x00,
                0xff, 0xff, 0xff,
            ])
        # check library to boost pixels handling
        _os_ = platform.system().lower()
        arch = platform.machine().lower()
        libname = os.path.join(os.path.dirname(__file__), f"displayc_{_os_}_{arch}.lib")
        if os.path.exists(libname):
            self.use_c_code = True
            self.ffi = FFI()
            self.displayc = self.ffi.dlopen(libname)
            self.ffi.cdef("int set_frame_p8(char *, char *, int, int, int);")
            self.ffi.cdef("int set_frame_rgb(char *, char *, int, int, int);")
            self.ffi.cdef("int set_resize_frame_rgb(char *, char *, int, int, int, int);")
        else:
            self.use_c_code = False
            print(f"'{libname}' not found, screen optimizations disabled")

    def set_zoom(self, zoom):
        self.zoom = zoom
        self.resize = (self.width * self.zoom, self.height * self.zoom)
        self.left = (self.canvas_width - (self.width * self.zoom)) // 2
        self.top = (self.canvas_height - (self.height * self.zoom)) // 2

    #
    # screen bitmap created using color palette index as pixel (tkinter 'P' mode)
    # resize to actual screen size done with tkinter   
    #
    def show_frame(self):
        bitmap = self.screen_pixels_p
        flash_phase = self.flash_phase
        border_color = app_globals.border_color
        if border_color != self.current_border_color:
            self.current_border_color = border_color
            bc = self.palette[border_color]
            c = f"#{''.join(format(x, '02x') for x in bc)}"
            self.canvas.configure(bg=c)

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

        png = Image.frombytes('P', (self.width, self.height), bytes(bitmap))
        png.putpalette(self.image_palette)
        im = itk.PhotoImage(png.resize(self.resize, Image.Resampling.NEAREST))

        prev_image_id = self.image_id
        self.image_id = self.canvas.create_image(self.left, self.top, image=im, anchor="nw")
        self.actual_screen_frame = im
        if prev_image_id: self.canvas.delete(prev_image_id)

        self.flash_phase = (self.flash_phase + 1) & 0x1f
    
    #
    # screen bitmap with RGB format (tkinter 'RGB' mode)
    # resize to actual screen size done at the same of bitmap generation   
    #
    def show_frame_rgb_resize(self):

        bitmap = self.screen_pixels_rgb
        palette = self.palette
        flash_phase = self.flash_phase
        border_color = app_globals.border_color
        if border_color != self.current_border_color:
            self.current_border_color = border_color
            bc = self.palette[border_color]
            c = f"#{''.join(format(x, '02x') for x in bc)}"
            self.canvas.configure(bg=c)

        vram, screen_addr, attrib_addr = self.mmu.get_video_ram()

        if self.use_c_code:
            self.displayc.set_resize_frame_rgb(self.ffi.from_buffer(bitmap), self.ffi.from_buffer(vram), screen_addr, attrib_addr, flash_phase, self.zoom)
        else:
            COLS = 32
            zoom = self.zoom
            pixel_colors = 3
            char_width_pixels_size = 8 * zoom
            char_width_size = char_width_pixels_size * pixel_colors
            char_height_pixels_size = 8 * zoom
            char_height_size = char_height_pixels_size * pixel_colors

            col_size = COLS * char_width_size
            row_size = COLS * char_width_pixels_size * char_height_pixels_size * pixel_colors

            row = col = 0
            char_bitmap_ptr = 0

            char_attrib_ptr = attrib_addr
            for rows_block_addr in range(0, 0x1800, 0x800):
                char_first_byte = screen_addr + rows_block_addr
                for _ in range(0, 8):
                    for col in range(0, COLS):
                        attr = vram[char_attrib_ptr]
                        if (attr & 0x80) and (flash_phase & 0x10):
                            # reverse ink and paper
                            paper = palette[((attr & 0x40) >> 3) | (attr & 0x07)]
                            ink = palette[(attr & 0x78) >> 3]
                        else:
                            ink = palette[((attr & 0x40) >> 3) | (attr & 0x07)]
                            paper = palette[(attr & 0x78) >> 3]

                        char_bitmap_ptr = ((row * row_size) + (col * char_width_size))
                        for char_other_bytes_offset in range(0, 0x800, 0x100):
                            char_pixels = vram[char_first_byte + char_other_bytes_offset]

                            ptr = char_bitmap_ptr
                            for _ in range(0, 8):
                                red, green, blue = ink if char_pixels & 0x80 else paper
                                for _ in range(0, zoom):
                                    bitmap[ptr] = red
                                    bitmap[ptr+1] = green
                                    bitmap[ptr+2] = blue
                                    if zoom > 1:
                                        ptr2 = ptr + col_size
                                        bitmap[ptr2] = red
                                        bitmap[ptr2+1] = green
                                        bitmap[ptr2+2] = blue
                                    ptr += 3
                                char_pixels <<= 1

                            char_bitmap_ptr += col_size * zoom 

                        char_attrib_ptr += 1
                        char_first_byte += 1

                    row = row + 1

        im = itk.PhotoImage(Image.frombytes('RGB', self.resize, bytes(bitmap)))
        prev_image_id = self.image_id
        self.image_id = self.canvas.create_image(self.left, self.top, image=im, anchor="nw")
        self.actual_screen_frame = im
        if prev_image_id: self.canvas.delete(prev_image_id)

        self.flash_phase = (self.flash_phase + 1) & 0x1f
    
    #
    # screen bitmap with RGB format (tkinter 'RGB' mode)
    # resize to actual screen size done by tkinter   
    #
    def show_frame_rgb(self):
        bitmap = self.screen_pixels_rgb
        palette = self.palette
        flash_phase = self.flash_phase
        border_color = app_globals.border_color
        if border_color != self.current_border_color:
            self.current_border_color = border_color
            bc = self.palette[border_color]
            c = f"#{''.join(format(x, '02x') for x in bc)}"
            self.canvas.configure(bg=c)

        vram, screen_addr, attrib_addr = self.mmu.get_video_ram()

        if self.use_c_code:
            self.displayc.set_frame_rgb(self.ffi.from_buffer(bitmap), self.ffi.from_buffer(vram), screen_addr, attrib_addr, flash_phase)
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
                            paper_r, paper_g, paper_b = palette[((attr & 0x40) >> 3) | (attr & 0x07)]
                            ink_r, ink_g, ink_b = palette[(attr & 0x78) >> 3]
                        else:
                            ink_r, ink_g, ink_b = palette[((attr & 0x40) >> 3) | (attr & 0x07)]
                            paper_r, paper_g, paper_b = palette[(attr & 0x78) >> 3]

                        bitmap_ptr = row * 6144 + col * 24 # (32 * 8 * 3) * 8, 8 * 3
                        for char_other_bytes_offset in range(0, 0x800, 0x100):
                            char_pixels = vram[char_first_byte + char_other_bytes_offset]

                            ptr = bitmap_ptr
                            for _ in range(0, 8):
                                if (char_pixels & 0x80):
                                    bitmap[ptr] = ink_r
                                    bitmap[ptr+1] = ink_g
                                    bitmap[ptr+2] = ink_b
                                else:
                                    bitmap[ptr] = paper_r
                                    bitmap[ptr+1] = paper_g
                                    bitmap[ptr+2] = paper_b
                                ptr += 3
                                char_pixels <<= 1
                            bitmap_ptr += 768 # 32 * 8 * 3

                        char_attrib_ptr += 1
                        char_first_byte += 1
                    row = row + 1

        im = itk.PhotoImage(Image.frombytes('RGB', (self.width, self.height), bytes(bitmap)).resize(self.resize, Image.Resampling.NEAREST))
        prev_image_id = self.image_id
        self.image_id = self.canvas.create_image(self.left, self.top, image=im, anchor="nw")
        self.actual_video_frame = im
        if prev_image_id: self.canvas.delete(prev_image_id)

        self.flash_phase = (self.flash_phase + 1) & 0x1f

    def show_frame_old(self):
        pixels = self.screen_pixels_rgb
        palette = self.palette
        flash_phase = self.flash_phase
        border_color = app_globals.border_color
        if border_color != self.current_border_color:
            self.current_border_color = border_color
            bc = self.palette[border_color]
            c = f"#{''.join(format(x, '02x') for x in bc)}"
            self.canvas.configure(bg=c)

        vram, screen_addr, attrib_addr = self.mmu.get_video_ram()
        screen_ptr = attrib_ptr = pixel_ptr = 0x0

        if self.use_c_code:
            self.displayc.set_frame_rgb(self.ffi.from_buffer(pixels), self.ffi.from_buffer(vram), screen_addr, attrib_addr, flash_phase)
        else:
            ink = paper = 0
            attrib_ptr = attrib_addr
            for rows_block_addr in range(0, 0x1800, 0x800):
                screen_ptr = screen_addr + rows_block_addr
                for char in range(0, 0x100, 0x20):
                    for char_bytes_offset in range(0, 0x800, 0x100):
                        for i in range(0, 32):
                            bitmap = vram[screen_ptr + char + char_bytes_offset + i]
                            attr = vram[attrib_ptr + i]
                            if ((attr & 0x80) and (flash_phase & 0x10)):
                                # reverse ink and paper
                                paper = palette[((attr & 0x40) >> 3) | (attr & 0x07)]
                                ink = palette[(attr & 0x78) >> 3]
                            else:
                                ink = palette[((attr & 0x40) >> 3) | (attr & 0x07)]
                                paper = palette[(attr & 0x78) >> 3]
                            for _ in range(0, 8):
                                color = ink if (bitmap & 0x80) else paper
                                pixels[pixel_ptr] = color[0]
                                pixels[pixel_ptr+1] = color[1]
                                pixels[pixel_ptr+2] = color[2]
                                pixel_ptr += 3
                                bitmap <<= 1
                    attrib_ptr += 32

        im = itk.PhotoImage(Image.frombytes('RGB', (self.width, self.height), bytes(pixels)).resize(self.resize, Image.Resampling.NEAREST))
        prev_image_id = self.image_id
        self.image_id = self.canvas.create_image(self.left, self.top, image=im, anchor="nw")
        self.actual_screen_frame = im
        if prev_image_id: self.canvas.delete(prev_image_id)

        self.flash_phase = (self.flash_phase + 1) & 0x1f

    def stop(self):
        self.canvas.destroy()
