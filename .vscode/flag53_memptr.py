        self.set_flag_53(val)


bit 
        self.set_flag_53(self.memptr >> 8)


    def set_flag_53(self, value : int) -> None:
        assert value >= 0 and value <= 255
        self.f &= ~0x28
        self.f |= value & 0x28