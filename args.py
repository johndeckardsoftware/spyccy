
class Args:
    def __init__(self, *args):
        # tzxtools parameters
        self.file = None
        self.short = False #True
        self.verbose = True
        self.block = None           # 'block number to cat'
        self.to = './out.tmp'       # 'target file, stdout if omitted'
        self.skip = 0               # 'skip the given number of bytes before output'
        self.length = 999999        # 'limit output to the given number of bytes'
        self.text = False           # 'convert ZX Spectrum text to plain text'
        self.basic = False          # 'convert ZX Spectrum BASIC to plain text'
        self.assembler = False      # 'disassemble Z80 code'
        self.screen = False         # 'convert a ZX Spectrum SCREEN$ to PNG'
        self.dump = False           # 'convert to a hex dump'
        self.org = 0x8000           # 'base address for disassembled code'
