from array import array
from tkinter import messagebox
from tkinter import filedialog
from dataview import DataView
from config import *
from snapshot import parseZ80File, parseSZXFile
import app_globals

def extract(data, offset, len): return data[offset: offset + len]

class ToneSegment :
    def __init__(self, pulseLength, pulseCount):
        self.pulseLength = pulseLength
        self.pulseCount = pulseCount
        self.pulsesGenerated = 0

    def isFinished(self):
        return self.pulsesGenerated == self.pulseCount

    def getNextPulseLength(self):
        self.pulsesGenerated += 1
        return self.pulseLength

class PulseSequenceSegment :
    def __init__(self, pulses):
        self.pulses = pulses
        self.index = 0

    def isFinished(self,):
        return self.index == len(self.pulses)

    def getNextPulseLength(self):
        i = self.pulses[self.index]
        self.index += 1
        return i

class DataSegment :
    def __init__(self, data, zeroPulseLength, onePulseLength, lastByteBits):
        self.data = data
        self.zeroPulseLength = zeroPulseLength
        self.onePulseLength = onePulseLength
        self.bitCount = (len(self.data) - 1) * 8 + lastByteBits
        self.pulsesOutput = 0
        self.lastPulseLength = None

    def isFinished(self,):
        return self.pulsesOutput == self.bitCount * 2

    def getNextPulseLength(self):
        if (self.pulsesOutput & 0x01):
            self.pulsesOutput += 1
            return self.lastPulseLength
        else:
            bitIndex = self.pulsesOutput >> 1
            byteIndex = bitIndex >> 3
            bitMask = 1 << (7 - (bitIndex & 0x07))
            self.lastPulseLength = self.onePulseLength if (self.data[byteIndex] & bitMask) else self.zeroPulseLength
            self.pulsesOutput += 1
            return self.lastPulseLength

class PauseSegment :
    def __init__(self, duration):
        self.duration = duration
        self.emitted = False

    def isFinished(self):
        return self.emitted

    def getNextPulseLength(self):
        # TODO: take level back down to 0 after 1ms if it's currently high
        self.emitted = True
        return self.duration * 3500

class PulseGenerator :
    def __init__(self, getSegments):
        self.segments = []
        self.getSegments = getSegments
        self.level = 0x0000
        self.tapeIsFinished = False;  # if True, don't call getSegments again
        self.pendingCycles = 0

    def addSegment(self, segment):
        self.segments.append(segment)

    def emitPulses(self, buffer, startIndex, cycleCount):
        cyclesEmitted = 0
        index = startIndex
        isFinished = False
        while cyclesEmitted < cycleCount:
            if self.pendingCycles > 0:
                if self.pendingCycles >= 0x8000:
                    # emit a pulse of length 0x7fff
                    buffer[index] = self.level | 0x7fff
                    index += 1
                    cyclesEmitted += 0x7fff
                    self.pendingCycles -= 0x7fff
                else:
                    # emit a the remainder of self.pulse in full
                    buffer[index] = self.level | self.pendingCycles
                    index += 1
                    cyclesEmitted += self.pendingCycles
                    self.pendingCycles = 0

            elif len(self.segments) == 0:
                if self.tapeIsFinished:
                    # mark end of tape
                    isFinished = True
                    break
                else:
                    # get more segments
                    self.tapeIsFinished = not self.getSegments(self)

            elif self.segments[0].isFinished():
                # discard finished segment
                self.segments.pop(0)
            else:
                # new pulse
                self.pendingCycles = self.segments[0].getNextPulseLength()
                self.level ^= 0x8000

        return [index, cyclesEmitted, isFinished]

# https://sinclair.wiki.zxnet.co.uk/wiki/TAP_format
class TAPFile:
    def __init__(self, data):
        if data:
            self.data = data
        else:
            self.data = array("B")
        self.blocks = self.get_blocks(self.data)
        self.next_block_index = 0
        #self.pulseGenerator = PulseGenerator(self._generator)

    def get_blocks(self, data):
        tap = DataView(data)
        blocks = []
        i = 0
        while (i+1) < len(data):
            block_length = tap.getUint16(i, True)
            i += 2
            blocks.append(extract(data, i, block_length))
            i += block_length
        return blocks

    def getNextLoadableBlock(self):
        if (len(self.blocks) == 0):
            return None
        block = self.blocks[self.next_block_index]
        self.next_block_index = (self.next_block_index + 1) % len(self.blocks)
        return block

    @staticmethod
    def is_valid(data):
        # test whether the given ArrayBuffer is a valid TAP file, i.e. EOF is consistent with the
        # block lengths we read from the file
        pos = 0
        tap = DataView(data)
        while pos < len(data):
            if pos + 1 >= len(data):
                return False # EOF in the middle of a length word
            blockLength = tap.getUint16(pos, True)
            pos += blockLength + 2

        return (pos == len(data)) # file is a valid TAP if pos is exactly at EOF and no further

    def _generator(self, generator):
        if len(self.blocks) == 0:
            return False

        block = self.blocks[self.next_block_index]
        self.next_block_index = (self.next_block_index + 1) % len(self.blocks)

        if block[0] & 0x80:
            # add short leader tone for data block
            generator.addSegment(ToneSegment(2168, 3223))
        else:
            # add long leader tone for header block
            generator.addSegment(ToneSegment(2168, 8063))

        generator.addSegment(PulseSequenceSegment([667, 735]))
        generator.addSegment(DataSegment(block, 855, 1710, 8))
        generator.addSegment(PauseSegment(1000))

        # return False if tape has ended
        return self.next_block_index != 0

class TZXFile :
    @staticmethod
    def is_valid(data):
        tzx = DataView(data)
        signature = list(b"ZXTape!\x1A")
        for (i, b) in enumerate(signature):
            if b != tzx.getUint8(i):
                return False
        return True

    def __init__(self, data):
        self.blocks = []
        tzx = DataView(data)

        offset = 0x0a

        while (offset < len(data)):
            block_type = tzx.getUint8(offset)
            offset += 1
            match block_type:
                case 0x10:
                    pause = tzx.getUint16(offset, True)
                    offset += 2
                    dataLength = tzx.getUint16(offset, True)
                    offset += 2
                    blockData = extract(data, offset, dataLength)
                    tmp = {
                        'type': 'StandardSpeedData',
                        'pause': pause,
                        'data': blockData,
                        'generatePulses': None
                    }
                    self.blocks.append(tmp)
                    offset += dataLength

                case 0x11:
                    pilotPulseLength = tzx.getUint16(offset, True); offset += 2
                    syncPulse1Length = tzx.getUint16(offset, True); offset += 2
                    syncPulse2Length = tzx.getUint16(offset, True); offset += 2
                    zeroBitLength = tzx.getUint16(offset, True); offset += 2
                    oneBitLength = tzx.getUint16(offset, True); offset += 2
                    pilotPulseCount = tzx.getUint16(offset, True); offset += 2
                    lastByteMask = tzx.getUint8(offset); offset += 1
                    pause = tzx.getUint16(offset, True); offset += 2
                    dataLength = tzx.getUint16(offset, True) | (tzx.getUint8(offset+2) << 16); offset += 3
                    blockData = extract(data, offset, dataLength)
                    tmp = {
                        'type': 'TurboSpeedData',
                        'pilotPulseLength': pilotPulseLength,
                        'syncPulse1Length': syncPulse1Length,
                        'syncPulse2Length': syncPulse2Length,
                        'zeroBitLength': zeroBitLength,
                        'oneBitLength': oneBitLength,
                        'pilotPulseCount': pilotPulseCount,
                        'lastByteMask': lastByteMask,
                        'pause': pause,
                        'data': blockData,
                        'generatePulses': None
                    }
                    self.blocks.append(tmp)
                    offset += dataLength

                case 0x12:
                    pulseLength = tzx.getUint16(offset, True); offset += 2
                    pulseCount = tzx.getUint16(offset, True); offset += 2
                    tmp = {
                        'type': 'PureTone',
                        'pulseLength': pulseLength,
                        'pulseCount': pulseCount,
                        'generatePulses': None
                    }
                    self.blocks.append(tmp)

                case 0x13:
                    pulseCount = tzx.getUint8(offset); offset += 1
                    pulseLengths = []
                    for i in range(0, pulseCount):
                        pulseLengths[i] = tzx.getUint16(offset + i*2, True)
                    tmp = {
                        'type': 'PulseSequence',
                        'pulseLengths': pulseLengths,
                        'generatePulses': None
                    }
                    self.blocks.append(tmp)
                    offset += (pulseCount * 2)

                case 0x14:
                    zeroBitLength = tzx.getUint16(offset, True); offset += 2
                    oneBitLength = tzx.getUint16(offset, True); offset += 2
                    lastByteMask = tzx.getUint8(offset); offset += 1
                    pause = tzx.getUint16(offset, True); offset += 2
                    dataLength = tzx.getUint16(offset, True) | (tzx.getUint8(offset+2) << 16); offset += 3
                    blockData = extract(data, offset, dataLength)
                    tmp = {
                        'type': 'PureData',
                        'zeroBitLength': zeroBitLength,
                        'oneBitLength': oneBitLength,
                        'lastByteMask': lastByteMask,
                        'pause': pause,
                        'data': blockData,
                        'generatePulses': None
                    }
                    self.blocks.append(tmp)
                    offset += dataLength

                case 0x15:
                    tstatesPerSample = tzx.getUint16(offset, True); offset += 2
                    pause = tzx.getUint16(offset, True); offset += 2
                    lastByteMask = tzx.getUint8(offset); offset += 1
                    dataLength = tzx.getUint16(offset, True) | (tzx.getUint8(offset+2) << 16); offset += 3
                    tmp = {
                        'type': 'DirectRecording',
                        'tstatesPerSample': tstatesPerSample,
                        'lastByteMask': lastByteMask,
                        'pause': pause,
                        'data': extract(data, offset, dataLength)
                    }
                    self.blocks.append(tmp)
                    offset += dataLength

                case 0x20:
                    # TODO: handle pause length of 0 (= stop tape)
                    pause = tzx.getUint16(offset, True); offset += 2
                    tmp = {
                        'type': 'Pause',
                        'pause': pause,
                        'generatePulses': None
                    }
                    self.blocks.append(tmp)

                case 0x21:
                    nameLength = tzx.getUint8(offset); offset += 1
                    nameBytes = extract(data, offset, dataLength)
                    offset += nameLength
                    name = bytes(nameBytes).decode("utf-8")
                    tmp = {
                        'type': 'GroupStart',
                        'name': name
                    }
                    self.blocks.append(tmp)

                case 0x22:
                    tmp = {
                        'type': 'GroupEnd'
                    }
                    self.blocks.append(tmp)

                case 0x23:
                    jumpOffset = tzx.getUint16(offset, True); offset += 2
                    tmp = {
                        'type': 'JumpToBlock',
                        'offset': jumpOffset
                    }
                    self.blocks.append(tmp)

                case 0x24:
                    repeatCount = tzx.getUint16(offset, True); offset += 2
                    tmp = {
                        'type': 'LoopStart',
                        'repeatCount': repeatCount
                    }
                    self.blocks.append(tmp)

                case 0x25:
                    tmp = {
                        'type': 'LoopEnd'
                    }
                    self.blocks.append(tmp)

                case 0x26:
                    callCount = tzx.getUint16(offset, True); offset += 2
                    offsets = []
                    for i in range(0, callCount):
                        offsets[i] = tzx.getUint16(offset + i*2, True)

                    tmp = {
                        'type': 'CallSequence',
                        'offsets': offsets
                    }
                    offset += (callCount * 2)
                    self.blocks.append(tmp)
                    break
                case 0x27:
                    tmp = {
                        'type': 'ReturnFromSequence'
                    }
                    self.blocks.append(tmp)

                case 0x28:
                    blockLength = tzx.getUint16(offset, True); offset += 2
                    # This is a silly block. Don't bother parsing it further.
                    tmp = {
                        'type': 'Select',
                        'data': extract(data, offset, blockLength)
                    }
                    offset += blockLength
                    self.blocks.append(tmp)

                case 0x30:
                    textLength = tzx.getUint8(offset); offset += 1
                    textBytes = extract(data, offset, textLength)
                    offset += textLength
                    text = bytes(textBytes).decode("utf-8")
                    tmp = {
                        'type': 'TextDescription',
                        'text': text
                    }
                    self.blocks.append(tmp)
                case 0x31:
                    displayTime = tzx.getUint8(offset); offset += 1
                    textLength = tzx.getUint8(offset); offset += 1
                    textBytes = extract(data, offset, textLength)
                    offset += textLength
                    text = bytes(textBytes).decode("utf-8")
                    tmp = {
                        'type': 'MessageBlock',
                        'displayTime': displayTime,
                        'text': text
                    }
                    self.blocks.append(tmp)

                case 0x32:
                    blockLength = tzx.getUint16(offset, True); offset += 2
                    tmp = {
                        'type': 'ArchiveInfo',
                        'data': extract(data, offset, blockLength)
                    }
                    offset += blockLength
                    self.blocks.append(tmp)
                case 0x33:
                    blockLength = tzx.getUint8(offset) * 3; offset += 1
                    tmp = {
                        'type': 'HardwareType',
                        'data': extract(data, offset, blockLength)
                    }
                    offset += blockLength
                    self.blocks.append(tmp)

                case 0x35:
                    identifierBytes = extract(data, offset, 10)
                    offset += 10
                    identifier = bytes(identifierBytes).decode("utf-8")
                    dataLength = tzx.getUint32(offset, True)
                    tmp = {
                        'type': 'CustomInfo',
                        'identifier': identifier,
                        'data': extract(data, offset, dataLength)
                    }
                    offset += dataLength
                    self.blocks.append(tmp)

                case 0x5A:
                    offset += 9
                    tmp = {
                        'type': 'Glue'
                    }
                    self.blocks.append(tmp)

                case default:
                    # follow extension rule: next 4 bytes = length of block
                    blockLength = tzx.getUint32(offset, True)
                    offset += 4
                    tmp = {
                        'type': 'unknown',
                        'data': extract(data, offset, blockLength)
                    }
                    offset += blockLength
                    self.blocks.append(tmp)

        self.nextBlockIndex = 0
        self.loopToBlockIndex = 0
        self.repeatCount = 0
        self.callStack = []
        self.pulseGenerator = None #PulseGenerator()

    def getNextMeaningfulBlock(self,wrapAtEnd):
        startedAtZero = (self.nextBlockIndex == 0)
        while True:
            if (self.nextBlockIndex >= len(self.blocks)):
                if (startedAtZero or not wrapAtEnd): return None; # have looped around; quit now
                self.nextBlockIndex = 0
                startedAtZero = True

            block = self.blocks[self.nextBlockIndex]
            match block['type']:
                case 'StandardSpeedData' | 'TurboSpeedData' | 'TurboSpeedData' | 'PureTone' | 'PulseSequence' | 'PureData' | 'DirectRecording' | 'Pause':
                    # found a meaningful block
                    self.nextBlockIndex += 1
                    return block
                case 'JumpToBlock':
                    self.nextBlockIndex += block['offset']

                case 'LoopStart':
                    self.loopToBlockIndex = self.nextBlockIndex + 1
                    self.repeatCount = block['repeatCount']
                    self.nextBlockIndex += 1

                case 'LoopEnd':
                    self.repeatCount -= 1
                    if (self.repeatCount > 0):
                        self.nextBlockIndex = self.loopToBlockIndex
                    else:
                        self.nextBlockIndex += 1

                case 'CallSequence':
                    # push the future destinations (where to go on reaching a ReturnFromSequence block)
                    #    onto the call stack in reverse order, starting with the block immediately
                    #    after the CallSequence (which we go to when leaving the sequence)
                    self.callStack.unshift(self.nextBlockIndex+1)
                    i = len(block['offsets']) - 1
                    while i >= 0:
                        self.callStack.unshift(self.nextBlockIndex + block['offsets'][i])
                        i -= 1
                    # now visit the first destination on the list
                    self.nextBlockIndex = self.callStack.shift()

                case 'ReturnFromSequence':
                    self.nextBlockIndex = self.callStack.shift()

                case default:
                    # not one of the types we care about; skip past it
                    self.nextBlockIndex += 1

    def getNextLoadableBlock(self,):
        while True:
            block = self.getNextMeaningfulBlock(True)
            if (not block): return None
            if (block['type'] == 'StandardSpeedData' or block['type'] == 'TurboSpeedData'):
                return block['data']

            # FIXME: avoid infinite loop if the TZX file consists only of meaningful but non-loadable blocks

class TapeManager:
    def __init__(self, machine):
        self.machine = machine
        self.window = machine.window
        self.tape = TAPFile(None) # new tape
        self.type = "TAP"
        self.is_playing = False
        self.auto_load = Config.get('tape.auto_load', False)
        self.traps_enabled = 0
        self.name = ""
        self.filename = ""
        self.count = 1
        self.dirty = 0
        self.patched = 0

    def load(self, filename):
        try:
            with open(filename, 'rb') as file:
                pf = os.path.split(filename)
                tape_data = array("B")
                tape_data.fromfile(file, os.stat(filename).st_size)
                file_type = filename[-4:].lower()
                if file_type == '.tap':
                    if not TAPFile.is_valid(tape_data):
                        messagebox.showerror(app_globals.APP_NAME, f'{filename}: Invalid TAP file')
                    else:
                        self.type = "TAP"
                        self.name = pf[1]
                        self.filename = filename
                        self.window.status_bar.set_tape(self.name)
                        self.tape = TAPFile(tape_data)
                        self.is_playing = False

                elif file_type == '.tzx':
                    if not TZXFile.is_valid(tape_data):
                        messagebox.showerror(app_globals.APP_NAME, f'{filename}: Invalid TZX file')
                    else:
                        self.type = "TZX"
                        self.name = pf[1]
                        self.filename = filename
                        self.window.status_bar.set_tape(self.name)
                        self.tape = TZXFile(tape_data)
                        self.is_playing = False
                else:
                    messagebox.showerror(app_globals.APP_NAME, "Unmanaged tape format")
                    return 0
            return 1
        except Exception as e:
            messagebox.showerror(app_globals.APP_NAME, str(e))
            return 0

    def save(self):
        if not self.dirty:
            return 1

        if self.filename == "":
            title = f"{app_globals.APP_NAME} - Save {self.name}"
            filename = filedialog.asksaveasfilename(title=title, filetypes=[('Tape TAP Format', '*.tap'), ('All files', '*.*')])
            if not filename:
                return 0
        else:
            filename = self.filename

        # Save tape buffer
        with open(filename, 'wb') as file:
            self.tape.data.tofile(file)

        self.dirty = 0
        return 1

    def basic_load(self):
        if not self.tape: return
        block = self.tape.getNextLoadableBlock()
        if not block: return

        # get expected block type and load vs verify flag from AF'
        af_ = self.machine.cpu.get_af_()
        expected_block_type = af_ >> 8
        shouldLoad = af_ & 0x0001  # LOAD rather than VERIFY
        addr = self.machine.cpu.get_ix()
        requested_length = self.machine.cpu.get_de()
        actual_block_type = block[0]
        #print(f"{expected_block_type=}, {actual_block_type=}, {requested_length=}, {len(block)=}")
        success = True
        if expected_block_type != actual_block_type:
            success = False
        else:
            if shouldLoad:
                offset = 1
                loaded_bytes = 0
                checksum = actual_block_type
                while loaded_bytes < requested_length:
                    if (offset >= len(block)):
                        # have run out of bytes to load
                        success = False
                        break
                    byte = block[offset]
                    offset += 1
                    loaded_bytes += 1
                    self.machine.mmu.poke(addr, byte)
                    addr = (addr + 1) & 0xffff
                    checksum ^= byte

                # if loading is going right, we should still have a checksum byte left to read
                success &= (offset < len(block))
                if success:
                    expectedc_checksum = block[offset]
                    success = checksum == expectedc_checksum
                else:
                    # VERIFY. TODO: actually verify.
                    success = True
        if success:
            # set carry to indicate success
            self.machine.cpu.set_af(self.machine.cpu.get_de() | 0x0001)
        else:
            # reset carry to indicate failure
            self.machine.cpu.set_af(self.machine.cpu.get_af() | 0xfffe)

        self.machine.cpu.set_pc(0x05e2)  # address at which to exit the tape trap

    # This class extracts data to be saved to tape, when the ROM routine
    # SA-BYTES 0x04C2 has been reached and appends it to the currently opened TAP-file.
    def basic_save(self):
        tape_block_appended = False

        block_length = self.machine.cpu.get_de()
        block_start = self.machine.cpu.get_ix()
        block_type = (self.machine.cpu.get_af() >> 8) & 0xff

        block_data = bytearray([0] * (block_length + 4))

        # The first two bytes of the block contains the data length plus the flag byte and the checksum.
        block_data[0] = (block_length + 2) & 0xff
        block_data[1] = ((block_length + 2) >> 8) &0xff

        # The third byte is block type (flag byte).
        block_data[2] = block_type

        # The checksum is calculated by XOR the block data, includiung the block type.
        checksum = block_type

        # Get the block data from memory.
        addr = block_start
        for i in range(0, block_length):
            block_data[3 + i] = self.machine.mmu.peek(addr)
            checksum = checksum ^ block_data[3 + i]
            addr = (addr + 1) & 0xffff

        # Append the checksum.
        block_data[3 + block_length] = checksum

        if self.type == "TAP":
            # Append the block to the currently opened TAP data.
            self.tape.data.extend(block_data)
            # Refresh the tape player listing.
            self.tape.blocks = self.tape.get_blocks(self.tape.data)
            # Indicate that the process was successful.
            tape_block_appended = True
            self.dirty = 1
        #print(block_length, block_type, tape_block_appended)
        return tape_block_appended

    def play(self):
        if self.name:
            self.auto_load_tape()
            self.is_playing = True

    def auto_load_tape(self):
        if self.auto_load:
            filename = TAPE_LOADERS_BY_MACHINE[str(self.machine.type)]['default']
            with open(filename, 'rb') as file:
                loader = array("B")
                loader.fromfile(file, os.stat(filename).st_size)
                if filename.lower().endswith('.z80'):
                    snap = parseZ80File(loader)
                    return self.machine.load_snapshot(snap)
                if filename.lower().endswith('.szx'):
                    snap = parseSZXFile(loader)
                    return self.machine.load_snapshot(snap)

    def stop(self):
        self.dirty = 0
        self.type = ""
        self.name = ""
        self.filename = ""
        self.tape.data = array("B")     # blank tape
        self.is_playing = False

    def set_traps(self, val):
        self.traps_enabled = val
        self.patch()

    # rom patch with meta opcode ed cd and ed 02
    def patch(self):
        if self.machine.type == 48 or self.machine.type == 128:
            if self.machine.type == 48:
                rom_page = self.machine.SYS_ROM0_PAGE
            else:
                rom_page = self.machine.SYS_ROM1_PAGE
            ram = self.machine.mmu.get_page_ram(rom_page)
            if self.traps_enabled:
                # load
                ram[0x056b] = 0xed
                #ram[0x056c] = 0xcd  # luckily ed cd is not used
                # save
                ram[0x04c2] = 0xed
                ram[0x04c3] = 0x02
                self.patched = 1
            else:
                #restore original
                ram[0x056b] = 0xc0
                #ram[0x056c] = 0xcd
                ram[0x04c2] = 0x21
                ram[0x04c3] = 0x3f
                self.patched = 0

