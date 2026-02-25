from array import array
from dataview import DataView
import zlib
import app_globals

# https:#stackoverflow.com/questions/1089662/python-inflate-and-deflate-implementations
# https:#stackoverflow.com/questions/3943149/reading-and-interpreting-data-from-a-binary-file-in-python

def extract(data, offset, len):
    tmp = data[offset: offset + len]
    return tmp

def extractMemoryBlock(data, fileOffset, isCompressed, unpackedLength):
    if not isCompressed:
        # uncompressed; extract a byte array directly from data """
        return array('B', extract(data, fileOffset, unpackedLength))
    else:
        # compressed
        #fileBytes = new Uint8Array(data, fileOffset);
        fileBytes = data
        memoryBytes = array('B', [0] * unpackedLength)
        #filePtr = 0
        filePtr = fileOffset 
        memoryPtr = 0
        while memoryPtr < unpackedLength:
            # check for coded ED ED nn bb sequence
            if ( # at least two bytes left to unpack
                unpackedLength - memoryPtr >= 2 and 
                fileBytes[filePtr] == 0xed and
                fileBytes[filePtr + 1] == 0xed
            ):
                # coded sequence
                count = fileBytes[filePtr + 2]
                value = fileBytes[filePtr + 3]
                for i in range(0, count):
                    memoryBytes[memoryPtr] = value
                    memoryPtr += 1
                filePtr += 4
            else: # plain byte
                memoryBytes[memoryPtr] = fileBytes[filePtr]
                memoryPtr += 1
                filePtr += 1

        return memoryBytes

# https://worldofspectrum.org/faq/reference/z80format.htm
def parseZ80File(data):
    file = DataView(data)

    iReg = file.getUint8(10)
    byte12 = file.getUint8(12)
    rReg = (file.getUint8(11) & 0x7f) | ((byte12 & 0x01) << 7)
    byte29 = file.getUint8(29)

    snapshot = {
        'registers': {
            'AF': file.getUint16(0, False), # NB Big-endian
            'BC': file.getUint16(2, True),
            'HL': file.getUint16(4, True),
            'PC': file.getUint16(6, True),
            'SP': file.getUint16(8, True),
            'IR': (iReg << 8) | rReg,
            'DE': file.getUint16(13, True),
            'BC_': file.getUint16(15, True),
            'DE_': file.getUint16(17, True),
            'HL_': file.getUint16(19, True),
            'AF_': file.getUint16(21, False), # Big-endian
            'IY': file.getUint16(23, True),
            'IX': file.getUint16(25, True),
            'iff1': not not file.getUint8(27),
            'iff2': not not file.getUint8(28),
            'im': byte29 & 0x03
        },
        'ulaState': {
            'borderColour': (byte12 & 0x0e) >> 1
        },
        'memoryPages': {},
    }

    if (snapshot['registers']['PC'] != 0):
        # a non-zero value for PC at offset 6 indicates a version 1 file
        snapshot['model'] = 48
        memory = extractMemoryBlock(data, 30, byte12 & 0x20, 0xc000)

        # construct byte arrays of length 0x4000 at the appropriate offsets into the data stream
        snapshot['memoryPages'][1] = extract(memory, 0, 0x4000)
        snapshot['memoryPages'][2] = extract(memory, 0x4000, 0x4000)
        snapshot['memoryPages'][3] = extract(memory, 0x8000, 0x4000)

        snapshot['tstates'] = 0
    else:
        # version 2-3 snapshot
        additionalHeaderLength = file.getUint16(30, True)
        isVersion2 = (additionalHeaderLength == 23)
        snapshot['registers']['PC'] = file.getUint16(32, True)
        machineId = file.getUint8(34)
        is48K = machineId < 3 if isVersion2 else machineId < 4
        snapshot['model'] = 48 if is48K else 128
        if (not is48K):
            snapshot['ulaState']['pagingFlags'] = file.getUint8(35)
        
        tstateChunkSize = int((69888 if is48K else 70908) / 4)
        snapshot['tstates'] = (
            (((file.getUint8(57) + 1) % 4) + 1) * tstateChunkSize
            - (file.getUint16(55, True) + 1)
        )
        if (snapshot['tstates'] >= tstateChunkSize * 4): snapshot['tstates'] = 0

        offset = 32 + additionalHeaderLength

        # translation table from the IDs Z80 assigns to pages, to the page numbers they
        # actually get loaded into
        pageIdToNumber = None
        if (is48K):
            pageIdToNumber = {
                4: 2,
                5: 3,
                8: 1
            }
        else:
            pageIdToNumber = {
                3: 0,
                4: 1,
                5: 2,
                6: 3,
                7: 4,
                8: 5,
                9: 6,
                10: 7
            }
        tmp = data.buffer_info()
        while offset < data.buffer_info()[1]:
            compressedLength = file.getUint16(offset, True)
            isCompressed = True
            if compressedLength == 0xffff:
                compressedLength = 0x4000
                isCompressed = False

            pageId = file.getUint8(offset + 2)
            if pageId in pageIdToNumber:
                pageNumber = pageIdToNumber[pageId]
                pageData = extractMemoryBlock(data, offset + 3, isCompressed, 0x4000)
                snapshot['memoryPages'][pageNumber] = pageData

            offset += compressedLength + 3

    return snapshot

# https://github.com/tslabs/zx-evo/blob/master/pentevo/docs/Formats/sna.txt
# for zx48, spyccy banks configuration is: 0 rom; 1,2,3 ram; 4 rom write; 5 usource rom; 6 tr-dos rom, 7 if2 cartridge 
def parseSNAFile(data):
    mode128 = False
    snapshot = None
    size = len(data)
    sna = None
    HEADER_SIZE = 27

    match size:
        case 131103 | 147487:
            mode128 = True
        case 49179:
            # sna = new DataView(data, 0, mode128 ? 49182 : len);
            if mode128: sna = data[0: 0xc01e]
            else: tmp = data
            sna = DataView(tmp)
            snapshot = {
                'model': 128 if mode128 else 48,
                'registers': {},
                'ulaState': {},
                'memoryPages': {},
                'tstates': 0,
            }

            if mode128:
                snapshot['memoryPages'][5] = extract(data, 0x0000 + HEADER_SIZE, 0x4000)
                snapshot['memoryPages'][2] = extract(data, 0x4000 + HEADER_SIZE, 0x4000)
            else:
                snapshot['memoryPages'][1] = extract(data, 0x0000 + HEADER_SIZE, 0x4000)
                snapshot['memoryPages'][2] = extract(data, 0x4000 + HEADER_SIZE, 0x4000)
                snapshot['memoryPages'][3] = extract(data, 0x8000 + HEADER_SIZE, 0x4000)

            if mode128:
                page = (sna.getUint8(49181) & 7)
                snapshot['memoryPages'][page] = extract(data, 0x8000 + HEADER_SIZE, 0x4000)

                ptr = 49183
                for i in range(0, 8):
                    if i not in snapshot['memoryPages']:
                        snapshot['memoryPages'][i] = extract(data, ptr, 0x4000)
                        ptr += 0x4000
            #else:
            #    snapshot['memoryPages'][0] = extract(data, 0x8000 + HEADER_SIZE, 0x4000)

            snapshot['registers']['IR'] = (sna.getUint8(0) << 8) | sna.getUint8(20)
            snapshot['registers']['HL_'] = sna.getUint16(1, True)
            snapshot['registers']['DE_'] = sna.getUint16(3, True)
            snapshot['registers']['BC_'] = sna.getUint16(5, True)
            snapshot['registers']['AF_'] = sna.getUint16(7, True)
            snapshot['registers']['HL'] = sna.getUint16(9, True)
            snapshot['registers']['DE'] = sna.getUint16(11, True)
            snapshot['registers']['BC'] = sna.getUint16(13, True)
            snapshot['registers']['IY'] = sna.getUint16(15, True)
            snapshot['registers']['IX'] = sna.getUint16(17, True)
            snapshot['registers']['iff1'] = (sna.getUint8(19) & 0x04) >> 2
            snapshot['registers']['iff2'] = (sna.getUint8(19) & 0x04) >> 2
            snapshot['registers']['AF'] = sna.getUint16(21, True)

            if mode128:
                snapshot['registers']['SP'] = sna.getUint16(23, True)
                snapshot['registers']['PC'] = sna.getUint16(49179, True)
                snapshot['ulaState']['pagingFlags'] = sna.getUint8(49181)
            else:
                # peek memory at SP to get proper value of PC
                sp = sna.getUint16(23, True)
                l = sna.getUint8(sp - 16384 + HEADER_SIZE)
                sp = (sp + 1) & 0xffff
                h = sna.getUint8(sp - 16384 + HEADER_SIZE)
                sp = (sp + 1) & 0xffff
                snapshot['registers']['PC'] = (h << 8) | l
                snapshot['registers']['SP'] = sp

            snapshot['registers']['im'] = sna.getUint8(25)
            snapshot['ulaState']['borderColour'] = sna.getUint8(26)

        case default:
            raise Exception(f"Cannot handle SNA snapshots of length {size}")

    return snapshot

def getSZXIDString(file, offset):
    ascii = []
    ascii.append(file.getUint8(offset))
    ascii.append(file.getUint8(offset+1))
    ascii.append(file.getUint8(offset+2))
    ascii.append(file.getUint8(offset+3))
    return ''.join(map(chr, ascii))

def parseSZXFile(data):
    file = DataView(data)
    fileLen = len(data)
    snapshot = {
        'memoryPages': {}
    }

    if getSZXIDString(file, 0) != 'ZXST':
        raise Exception("Not a valid SZX file")

    machineId = file.getUint8(6)
    match machineId:
        case 1:
            snapshot['model'] = 48
        case 2 | 3:
            snapshot['model'] = 128
        case 7:
            snapshot['model'] = 5
        case default:
            raise Exception("Unsupported machine type: " + machineId)

    offset = 8
    while offset < fileLen:
        blockId = getSZXIDString(file, offset)
        blockLen = file.getUint32(offset + 4, True)
        offset += 8

        match blockId:
            case 'Z80R':
                snapshot['registers'] = {
                    'AF': file.getUint16(offset + 0, True),
                    'BC': file.getUint16(offset + 2, True),
                    'DE': file.getUint16(offset + 4, True),
                    'HL': file.getUint16(offset + 6, True),
                    'AF_': file.getUint16(offset + 8, True),
                    'BC_': file.getUint16(offset + 10, True),
                    'DE_': file.getUint16(offset + 12, True),
                    'HL_': file.getUint16(offset + 14, True),
                    'IX': file.getUint16(offset + 16, True),
                    'IY': file.getUint16(offset + 18, True),
                    'SP': file.getUint16(offset + 20, True),
                    'PC': file.getUint16(offset + 22, True),
                    'IR': file.getUint16(offset + 24, False),
                    'iff1': not not file.getUint8(offset + 26),
                    'iff2': not not file.getUint8(offset + 27),
                    'im': file.getUint8(offset + 28),
                }
                snapshot['tstates'] = file.getUint32(offset + 29, True)
                snapshot['halted'] = not not (file.getUint8(offset + 37) & 0x02)
                # currently ignored:
                # chHoldIntReqCycles, eilast, memptr

            case 'SPCR':
                snapshot['ulaState'] = {
                    'borderColour': file.getUint8(offset + 0),
                    'pagingFlags': file.getUint8(offset + 1),
                }
                # currently ignored:
                # ch1ffd, chEff7, chFe

            case 'RAMP':
                isCompressed = file.getUint16(offset + 0, True) & 0x0001
                pageNumber = file.getUint8(offset + 2)
                if isCompressed:
                    compressedLength = blockLen - 3
                    compressed = extract(data, offset + 3, compressedLength)
                    pageData = zlib.decompress(compressed)
                    #pageData = pako.inflate(compressed)
                    snapshot['memoryPages'][pageNumber] = pageData
                else:
                    pageData = extract(data, offset + 3, 0x4000)
                    snapshot['memoryPages'][pageNumber] = pageData

            case default:
                #print('skipping block', blockId)
                pass

        offset += blockLen

    return snapshot

def create_snapshot(board, cpu, mmu, ports, ay):
    page_size = mmu.get_page_size()

    # Compress the content of a memory bank into a byte array.
    def  CompressData():
        nonlocal page_size, previousByteSingleED, bankPos

        content = bankData[bankPos]
        data = None

        # Every byte directly following a single ED is not taken into a block.
        if (previousByteSingleED == True and content != 0xED):
            data = array('B', [0])
            data[0] = content
            previousByteSingleED = False
            bankPos += 1
        else:
            # Calculate how many times the content at the current position is repeated.
            repeats = 1
            if (bankPos < page_size - 1):
                while ((bankData[bankPos + repeats] == content) and repeats < 0xFF and bankPos + repeats < page_size - 1):
                    repeats += 1

            # Check if the repeated content should be compressed.
            if (repeats >= 5 or (content == 0xED and repeats >= 2)):
                data = array('B', [0] * 4)
                data[0] = 0xED
                data[1] = 0xED
                data[2] = repeats
                data[3] = content
            else:
                data = array('B', [content] * repeats)

            # If the content is a single 0xED, self.will be taken into account on the next round.
            if (repeats == 1 and content == 0xED):
                previousByteSingleED = True
            else:
                previousByteSingleED = False

            bankPos += repeats

        return data

    cs = cpu.get_cpu_state()
    snapshot = array('B', [0] * (0x4000*8))
    # Store the first header block.
    snapshot[0] = cs['A']
    snapshot[1] = cs['F']
    snapshot[2] = cs['C']
    snapshot[3] = cs['B']
    snapshot[4] = cs['L']
    snapshot[5] = cs['H']

    # Byte 6-7 are zero to signal a version 2 or 3 file.
    snapshot[6] = 0
    snapshot[7] = 0
    snapshot[8] = cs['P']
    snapshot[9] = cs['S']
    snapshot[10] = cs['I']
    snapshot[11] = cs['R']
    snapshot[12] = (((cs['R'] & 0x80) >> 7) | (app_globals.border_color << 1))

    # Add bit 5 to indicate that the memory is compressed.
    snapshot[12] = (snapshot[12] | 0x20)
    snapshot[13] = cs['E']
    snapshot[14] = cs['D']
    snapshot[15] = cs['C_']
    snapshot[16] = cs['B_']
    snapshot[17] = cs['E_']
    snapshot[18] = cs['D_']
    snapshot[19] = cs['L_']
    snapshot[20] = cs['H_']
    snapshot[21] = cs['A_']
    snapshot[22] = cs['F_']
    snapshot[23] = cs['Y']
    snapshot[24] = cs['Iy']
    snapshot[25] = cs['X']
    snapshot[26] = cs['Ix']

    if (cs['iff1'] == False):
        snapshot[27] = 0
    else:
        snapshot[27] = 1

    if (cs['iff2'] == False):
        snapshot[28] = 0
    else:
        snapshot[28] = 1

    snapshot[29] = cs['im']

    snapshot[32] = cs['pc'] & 0xff
    snapshot[33] = (cs['pc'] >> 8) & 0xff

    # Hardware mode and memory paging.
    if (board.type == 48):
        # Hardware mode = Spectrum 48K.
        snapshot[30] = 54
        snapshot[34] = 0
        snapshot[35] = 0
    else:
        # Hardware mode = Spectrum 128.
        snapshot[30] = 54
        snapshot[34] = 4
        snapshot[35] = ports.last_paging_value

        snapshot[38] = ports.last_ay_register
        snapshot[39] = ay.read_register(0)
        snapshot[40] = ay.read_register(1)
        snapshot[41] = ay.read_register(2)
        snapshot[42] = ay.read_register(3)
        snapshot[43] = ay.read_register(4)
        snapshot[44] = ay.read_register(5)
        snapshot[45] = ay.read_register(6)
        snapshot[46] = ay.read_register(7)
        snapshot[47] = ay.read_register(8)
        snapshot[48] = ay.read_register(9)
        snapshot[49] = ay.read_register(10)
        snapshot[50] = ay.read_register(11)
        snapshot[51] = ay.read_register(12)
        snapshot[52] = ay.read_register(13)
        snapshot[53] = ay.read_register(14)
        snapshot[54] = ay.read_register(15)

    # Store the _memory data.
    # We now need to step through the Spectrum RAM starting at byte 16384.
    # The memory bytes will be stored in the Snapshot array, compressed when needed.
    bankPos = 0
    storePos = 30 + snapshot[30] + 2
    previousByteSingleED = False
    bankData = None

    bankToPageMap = array('B', [99, 99, 99, 99, 99, 99, 99, 99])

    if (board.type == 48):
        # Spectrum 48K
        bankToPageMap[2] = 4
        bankToPageMap[3] = 5
        bankToPageMap[1] = 8
    else:
        # Spectrum 128K
        bankToPageMap[0] = 3
        bankToPageMap[1] = 4
        bankToPageMap[2] = 5
        bankToPageMap[3] = 6
        bankToPageMap[4] = 7
        bankToPageMap[5] = 8
        bankToPageMap[6] = 9
        bankToPageMap[7] = 10

    # Loop through the memory banks and save the data pages.
    for i in range(0, 8):
        if bankToPageMap[i] != 99:
            bankData = mmu.get_page_ram(i)
            previousByteSingleED = False
            pageData = array('B', [0] *18000)
            bankPos = 0
            pagePos = 0
            j = 0
            while True:
                # Analyze the data at the current ram position and return an array to store in the Snapshot array.
                compressedData = CompressData()
                # Append the returned array to the Snapshot array.
                for j in range(0, len(compressedData)):
                    pageData[pagePos + j] = compressedData[j]
                # Move the current position in the Snapshot array forward.
                pagePos += j + 1

                if bankPos >= page_size:
                    break

            # Store the compressed bank in the main array.
            snapshot[storePos] = pagePos & 0xff
            snapshot[storePos + 1] = (pagePos >> 8) & 0xff
            snapshot[storePos + 2] = bankToPageMap[i]

            for k in range(0, pagePos):
                snapshot[storePos + 3 + k] = pageData[k]

            storePos = storePos + 3 + pagePos

    return snapshot, storePos


