/*
Linux
(arm):  gcc -o displayc_linux_aarch64.lib displayc.c -O3 -Wall -Wextra -Wredundant-decls -shared
(x64):  gcc -o displayc_linux_x86_64.lib displayc.c -O3 -Wall -Wextra -Wredundant-decls -shared

Windows:
        gcc -o displayc_windows_amd64.lib displayc.c -O3 -DWIN32 -Wall -Wextra -Wredundant-decls -shared
        https://github.com/skeeto/w64devkit/ for an easy to instal and run gcc compiler

Others: gcc -o displayc_xxx_yyy.lib displayc.c -DWIN32 -Wall -Wextra -Wredundant-decls -shared
        where xxx is the system and yyy is the cpu architecture
        or check the error message to view the expected file name
*/

#include "displayc.h"

// set screen pixels bitmap using the palette color index
int set_frame_p8(char * bitmap, char * vram, int screen_addr, int attrib_addr, int flash_phase)
{
    int row = 0, col = 0;
    int bitmap_ptr = 0;
    int char_attrib_ptr = attrib_addr;
    unsigned char paper = 0, ink = 0;
    unsigned char flash_phase_ = (unsigned char)flash_phase;

    for (int rows_block_addr = 0; rows_block_addr < 0x1800; rows_block_addr+=0x800) {
        int char_first_byte = screen_addr + rows_block_addr;
        for (int i = 0; i < 8; i++) {
            for (col = 0; col < 32; col++) {
                unsigned char attr = vram[char_attrib_ptr];
                if ((attr & 0x80) && (flash_phase_ & 0x10)) {
                    // reverse ink and paper
                    paper = ((attr & 0x40) >> 3) | (attr & 0x07);
                    ink = (attr & 0x78) >> 3;
                } else {
                    ink = ((attr & 0x40) >> 3) | (attr & 0x07);
                    paper = (attr & 0x78) >> 3;
                }
                bitmap_ptr = row * 2048 + col * 8; // (32 * 8 * 1) * 8, 8 * 1
                for (int char_other_bytes_offset = 0; char_other_bytes_offset < 0x800; char_other_bytes_offset += 0x100) {
                    unsigned char char_pixels = vram[char_first_byte + char_other_bytes_offset];
                    int ptr = bitmap_ptr;
                    for (int j = 0; j < 8; j++) {
                        if (char_pixels & 0x80)
                            bitmap[ptr] = ink;
                        else
                            bitmap[ptr] = paper;
                        ptr += 1;
                        char_pixels <<= 1;
                    }
                    bitmap_ptr += 256; // 32 * 8 * 1
                }
                char_attrib_ptr++;
                char_first_byte++;
            }
            row++;
        }
    }

    return row;
}

int set_frame_rgb(char * bitmap, char * vram, int screen_addr, int attrib_addr, int flash_phase)
{
    int row = 0, col = 0;
    int bitmap_ptr = 0;
    int char_attrib_ptr = attrib_addr;
    unsigned char paper = 0, ink = 0;
    unsigned char flash_phase_ = (unsigned char)flash_phase;
    unsigned char palette[16][3] = {
                {0x00, 0x00, 0x00}, // black
                {0x00, 0x00, 0xc0}, // blue
                {0xc0, 0x00, 0x00}, // red
                {0xc0, 0x00, 0xc0}, // magenta
                {0x00, 0xc0, 0x00}, // green
                {0x00, 0xc0, 0xc0}, // cyan
                {0xc0, 0xc0, 0x00}, // yellow
                {0xd0, 0xd0, 0xd0}, // white
                {0x00, 0x00, 0x00},
                {0x00, 0x00, 0xff},
                {0xff, 0x00, 0x00},
                {0xff, 0x00, 0xff},
                {0x00, 0xff, 0x00},
                {0x00, 0xff, 0xff},
                {0xff, 0xff, 0x00},
                {0xff, 0xff, 0xff},
    };

    for (int rows_block_addr = 0; rows_block_addr < 0x1800; rows_block_addr+=0x800) {
        int char_first_byte = screen_addr + rows_block_addr;
        for (int i = 0; i < 8; i++) {
            for (col = 0; col < 32; col++) {
                unsigned char attr = vram[char_attrib_ptr];
                if ((attr & 0x80) && (flash_phase_ & 0x10)) {
                    // reverse ink and paper
                    paper = ((attr & 0x40) >> 3) | (attr & 0x07);
                    ink = (attr & 0x78) >> 3;
                } else {
                    ink = ((attr & 0x40) >> 3) | (attr & 0x07);
                    paper = (attr & 0x78) >> 3;
                }
                bitmap_ptr = row * 6144 + col * 24; // row * (32 * 8 * 3) * 8 + (8 * 3) ; 3 = number of pixels
                for (int char_other_bytes_offset = 0; char_other_bytes_offset < 0x800; char_other_bytes_offset += 0x100) {
                    unsigned char char_pixels = vram[char_first_byte + char_other_bytes_offset];
                    int ptr = bitmap_ptr;
                    for (int j = 0; j < 8; j++) {
                        if (char_pixels & 0x80) {
                            bitmap[ptr++] = palette[ink][0];
                            bitmap[ptr++] = palette[ink][1];
                            bitmap[ptr++] = palette[ink][2];
                        } else {
                            bitmap[ptr++] = palette[paper][0];
                            bitmap[ptr++] = palette[paper][1];
                            bitmap[ptr++] = palette[paper][2];
                        }
                        char_pixels <<= 1;
                    }
                    bitmap_ptr += 768; // 32 * 8 * 3
                }
                char_attrib_ptr++;
                char_first_byte++;
            }
            row++;
        }
    }

    return row;
}

int set_resize_frame_rgb(char * bitmap, char * vram, int screen_addr, int attrib_addr, int flash_phase, int zoom)
{
    int COLS = 32;
    int pixel_colors = 3;
    int char_width_pixels_size = 8 * zoom;
    int char_width_size = char_width_pixels_size * pixel_colors;
    int char_height_pixels_size = 8 * zoom;
    //int char_height_size = char_height_pixels_size * pixel_colors;

    int col_size = COLS * char_width_size;
    int row_size = COLS * char_width_pixels_size * char_height_pixels_size * pixel_colors;

    int row = 0, col = 0;
    int char_bitmap_ptr = 0;
    int char_attrib_ptr = attrib_addr;
    unsigned char paper = 0, ink = 0;
    unsigned char flash_phase_ = (unsigned char)flash_phase;
    unsigned char palette[16][3] = {
                {0x00, 0x00, 0x00}, // black
                {0x00, 0x00, 0xc0}, // blue
                {0xc0, 0x00, 0x00}, // red
                {0xc0, 0x00, 0xc0}, // magenta
                {0x00, 0xc0, 0x00}, // green
                {0x00, 0xc0, 0xc0}, // cyan
                {0xc0, 0xc0, 0x00}, // yellow
                {0xd0, 0xd0, 0xd0}, // white
                {0x00, 0x00, 0x00},
                {0x00, 0x00, 0xff},
                {0xff, 0x00, 0x00},
                {0xff, 0x00, 0xff},
                {0x00, 0xff, 0x00},
                {0x00, 0xff, 0xff},
                {0xff, 0xff, 0x00},
                {0xff, 0xff, 0xff},
    };

    for (int rows_block_addr = 0; rows_block_addr < 0x1800; rows_block_addr += 0x800) {
        int char_first_byte = screen_addr + rows_block_addr;
        for (int r = 0; r < 8; r++) {
            for (col = 0; col < COLS; col++) {
                unsigned char attr = vram[char_attrib_ptr];
                if ((attr & 0x80) && (flash_phase_ & 0x10)) {
                    // reverse ink and paper
                    paper = ((attr & 0x40) >> 3) | (attr & 0x07);
                    ink = (attr & 0x78) >> 3;
                } else {
                    ink = ((attr & 0x40) >> 3) | (attr & 0x07);
                    paper = (attr & 0x78) >> 3;
                }
                char_bitmap_ptr = (row * row_size) + (col * char_width_size);
                for (int char_other_bytes_offset = 0; char_other_bytes_offset < 0x800; char_other_bytes_offset += 0x100) {
                    unsigned char char_pixels = vram[char_first_byte + char_other_bytes_offset];

                    int ptr = char_bitmap_ptr;
                    for (int bit = 0; bit < 8; bit++) {
                        int pi = char_pixels & 0x80 ? ink: paper;
                        for (int j = 0; j < zoom; j++) {
                            bitmap[ptr] = palette[pi][0];
                            bitmap[ptr + 1] = palette[pi][1];
                            bitmap[ptr + 2] = palette[pi][2];
                            if (zoom > 1) {
                                int ptr2 = ptr + col_size;
                                bitmap[ptr2] = palette[pi][0];
                                bitmap[ptr2 + 1] = palette[pi][1];
                                bitmap[ptr2 + 2] = palette[pi][2];
                            }
                            ptr += 3;
                        }
                        char_pixels <<= 1;
                    }
                    char_bitmap_ptr += col_size * zoom;
                }
                char_attrib_ptr++;
                char_first_byte++;
            }
            row++;
        }
    }

    return row;
}
