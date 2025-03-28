

class MemoryManager:
    def __init__(self, page_size, pages, cpu):
        self.page_size = page_size
        self.page_count = pages
        self.ram = [bytearray(page_size) for _ in range(pages)]
        self.size = self.page_size * self.page_count
        self.page_read_map = [0, 1, 2, 3]
        self.page_write_map = [0, 1, 2, 3]
        self.screen_page = 1
        self.paging_locked = 0
        self.get_t_state = cpu.get_t_state if cpu else None
        self.add_t_state = cpu.add_t_state if cpu else None
        self.SYS_ROM0_BANK = -1
        self.SYS_ROM0_PAGE = -1
        self.SYS_ROM1_BANK = -1
        self.SYS_ROM1_PAGE = -1
        self.SYS_ROM0_WRITE_PAGE = -1 # to keep rom readonly
        self.prev_active_rom0_page = -1
        # betadisk
        self.TRDOS_ROM_PAGE = -1
        self.TRDOS_ROM_BANK = -1
        self.betadisk_active = 0
        # usource
        self.USOURCE_ROM_PAGE = -1
        self.USOURCE_ROM_BANK = -1
        self.uSource = 0
        self.uSource_paged = 0
        # usource
        self.CARTRIDGE_ROM_PAGE = -1
        self.CARTRIDGE_ROM_BANK = -1

    def set_page_read_map(self, map):
        self.page_read_map = [i for i in map]

    def set_page_write_map(self, map):
        self.page_write_map = [i for i in map]

    def read(self, addr:int):
        self.add_t_state(3)
        if self.uSource_paged and addr < 0x4000:
            return self.ram[self.USOURCE_ROM_PAGE][addr & 0x1fff]
        return self.ram[self.page_read_map[(addr >> 14)]][addr & 0x3fff]

    def read16(self, addr:int)->int:
        if self.uSource_paged and addr < 0x4000:
            lo = self.ram[self.USOURCE_ROM_PAGE][addr & 0x1fff]
            hi = self.ram[self.USOURCE_ROM_PAGE][addr+1 & 0x1fff]
            self.add_t_state(6)
            return hi << 8 | lo

        lo = self.ram[self.page_read_map[(addr >> 14)]][addr & 0x3fff]
        addr = (addr + 1) & 0xffff
        hi = self.ram[self.page_read_map[(addr >> 14)]][addr & 0x3fff]
        self.add_t_state(6)
        return hi << 8 | lo

    def read_nn(self, addr:int):
        if self.uSource_paged and addr < 0x4000:
            lo = self.ram[self.USOURCE_ROM_PAGE][addr & 0x1fff]
            addr = (addr + 1) & 0xffff
            hi = self.ram[self.USOURCE_ROM_PAGE][addr & 0x1fff]
            addr = (addr + 1) & 0xffff
            self.add_t_state(6)
            return addr, hi << 8 | lo

        lo = self.ram[self.page_read_map[(addr >> 14)]][addr & 0x3fff]
        addr = (addr + 1) & 0xffff
        hi = self.ram[self.page_read_map[(addr >> 14)]][addr & 0x3fff]
        addr = (addr + 1) & 0xffff
        self.add_t_state(6)
        return addr, hi << 8 | lo

    def write(self, addr:int, val:int):
        self.ram[self.page_write_map[(addr >> 14)]][addr & 0x3fff] = val
        self.add_t_state(3)

    def push(self, addr:int, hi:int, lo:int)->int:
        addr = (addr - 1) & 0xffff
        self.ram[self.page_write_map[(addr >> 14)]][addr & 0x3fff] = hi
        addr = (addr - 1) & 0xffff
        self.ram[self.page_write_map[(addr >> 14)]][addr & 0x3fff] = lo
        self.add_t_state(7)
        return addr

    def push16(self, addr:int, u16:int)->int:
        hi = (u16 >> 8) & 0xff; lo = u16 & 0xff
        addr = (addr - 1) & 0xffff
        self.ram[self.page_write_map[(addr >> 14)]][addr & 0x3fff] = hi
        addr = (addr - 1) & 0xffff
        self.ram[self.page_write_map[(addr >> 14)]][addr & 0x3fff] = lo
        self.add_t_state(7)
        return addr

    def pop(self, addr:int):
        lo = self.ram[self.page_read_map[(addr >> 14)]][addr & 0x3fff]
        addr = (addr + 1) & 0xffff
        hi = self.ram[self.page_read_map[(addr >> 14)]][addr & 0x3fff]
        addr = (addr + 1) & 0xffff
        self.add_t_state(6)
        return addr, hi, lo

    def pop16(self, addr:int):
        lo = self.ram[self.page_read_map[(addr >> 14)]][addr & 0x3fff]
        addr = (addr + 1) & 0xffff
        hi = self.ram[self.page_read_map[(addr >> 14)]][addr & 0x3fff]
        addr = (addr + 1) & 0xffff
        self.add_t_state(6)
        return addr, (hi << 8) | lo

    def call(self, pc:int, sp:int)->int:
        lo = self.ram[self.page_read_map[(pc >> 14)]][pc & 0x3fff]
        pc = (pc + 1) & 0xffff
        hi = self.ram[self.page_read_map[(pc >> 14)]][pc & 0x3fff]
        pc = (pc + 1) & 0xffff
        #sp = self.push16(sp, pc)
        sp = (sp - 1) & 0xffff
        self.ram[self.page_write_map[(sp >> 14)]][sp & 0x3fff] = (pc >> 8) & 0xff
        sp = (sp - 1) & 0xffff
        self.ram[self.page_write_map[(sp >> 14)]][sp & 0x3fff] = pc & 0xff
        self.add_t_state(13)
        return  (hi << 8) | lo, sp

    def ret(self, sp:int)->int:
        lo = self.ram[self.page_read_map[(sp >> 14)]][sp & 0x3fff]
        sp = (sp + 1) & 0xffff
        hi = self.ram[self.page_read_map[(sp >> 14)]][sp & 0x3fff]
        sp = (sp + 1) & 0xffff
        self.add_t_state(6)
        return  (hi << 8) | lo, sp

    def poke(self, addr:int, v:int):
        self.ram[self.page_write_map[(addr >> 14)]][addr & 0x3fff] = v

    def peek(self, addr:int)->int:
        if self.uSource_paged and addr < 0x4000:
            return self.ram[self.USOURCE_ROM_PAGE][addr & 0x1fff]
        return self.ram[self.page_read_map[(addr >> 14)]][addr & 0x3fff]

    def poke16(self, addr:int, v:int):
        self.ram[self.page_write_map[(addr >> 14)]][addr & 0x3fff] = v & 0xff
        self.ram[self.page_write_map[(((addr+1) & 0xffff) >> 14)]][(addr+1) & 0x3fff] = (v >> 8) & 0xff

    def peek16(self, addr:int)->int:
        lo = self.ram[self.page_read_map[(addr >> 14)]][addr & 0x3fff]
        hi = self.ram[self.page_read_map[(((addr+1) & 0xffff) >> 14)]][(addr+1) & 0x3fff]
        return lo | hi << 8

    def write_block(self, dest, dest_offset, source:bytearray, source_offset:int, size:int)->int:
        if isinstance(dest, int):
            for i in range(dest_offset, dest_offset+size):
                self.ram[dest][i] = source[source_offset+i]
        else:
            for i in range(dest_offset, dest_offset+size):
                dest[i] = source[source_offset+i]

    def set_paging_locked(self, paging_locked): #128
        self.paging_locked = paging_locked

    def switch_in_ram(self, page):     #128
        self.page_read_map[3] = page
        self.page_write_map[3] = page

    def switch_in_rom(self, page):      #128
        self.page_read_map[0] = page
        self.page_write_map[0] = page+2 # readonly

    def switch_in_trdos(self):
        if self.TRDOS_ROM_PAGE != -1:
            self.prev_active_rom0_page = self.page_read_map[self.SYS_ROM0_BANK]
            self.page_read_map[self.SYS_ROM0_BANK] = self.TRDOS_ROM_PAGE

    def switch_out_trdos(self):
        self.page_read_map[self.SYS_ROM0_BANK] = self.prev_active_rom0_page #self.SYS_ROM0_PAGE

    def switch_in_cartridge(self):
        if self.CARTRIDGE_ROM_PAGE != -1:
            self.prev_active_rom0_page = self.page_read_map[self.SYS_ROM0_BANK]
            self.page_read_map[self.SYS_ROM0_BANK] = self.CARTRIDGE_ROM_PAGE

    def switch_out_cartridge(self):
        self.page_read_map[self.SYS_ROM0_BANK] = self.prev_active_rom0_page

    def set_screen_page(self, value):
        self.screen_page = value

    def get_screen_page(self):
        return self.screen_page

    def get_write_page(self, addr):
        return self.page_write_map[(addr >> 14)]

    def get_read_page(self, addr):
        return self.page_read_map[(addr >> 14)]

    def get_page_ram(self, page):
        return self.ram[page]

    def get_ram(self):
        return self.ram

    def get_ram_size(self):
        return self.size

    def get_page_size(self):
        return self.page_size

    def get_page_count(self):
        return self.page_count

    def get_video_ram(self):
        return self.ram[self.screen_page], 0x0000, 0x1800

