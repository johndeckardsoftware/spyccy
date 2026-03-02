from array import array
from dataview import DataView
import zlib
import app_globals

# https:#stackoverflow.com/questions/1089662/python-inflate-and-deflate-implementations
# https:#stackoverflow.com/questions/3943149/reading-and-interpreting-data-from-a-binary-file-in-python

def extract(data, offset, len):
    tmp = data[offset: offset + len]
    return tmp

def extract_memory_block(data, file_offset, is_compressed, unpacked_length):
    if not is_compressed:
        # uncompressed; extract a byte array directly from data """
        return array('B', extract(data, file_offset, unpacked_length))
    else:
        # compressed
        file_bytes = data
        memory_bytes = array('B', [0] * unpacked_length)
        file_ptr = file_offset
        memory_ptr = 0
        while memory_ptr < unpacked_length:
            # check for coded ED ED nn bb sequence
            if ( # at least two bytes left to unpack
                unpacked_length - memory_ptr >= 2 and
                file_bytes[file_ptr] == 0xed and
                file_bytes[file_ptr + 1] == 0xed
            ):
                # coded sequence
                count = file_bytes[file_ptr + 2]
                value = file_bytes[file_ptr + 3]
                for i in range(0, count):
                    memory_bytes[memory_ptr] = value
                    memory_ptr += 1
                file_ptr += 4
            else: # plain byte
                memory_bytes[memory_ptr] = file_bytes[file_ptr]
                memory_ptr += 1
                file_ptr += 1

        return memory_bytes

# https://worldofspectrum.org/faq/reference/z80format.htm
def parse_z80_file(data):
    file = DataView(data)

    i_reg = file.get_uint8(10)
    byte12 = file.get_uint8(12)
    r_reg = (file.get_uint8(11) & 0x7f) | ((byte12 & 0x01) << 7)
    byte29 = file.get_uint8(29)

    snapshot = {
        'registers': {
            'AF': file.get_uint16(0, False), # NB Big-endian
            'BC': file.get_uint16(2, True),
            'HL': file.get_uint16(4, True),
            'PC': file.get_uint16(6, True),
            'SP': file.get_uint16(8, True),
            'IR': (i_reg << 8) | r_reg,
            'DE': file.get_uint16(13, True),
            'BC_': file.get_uint16(15, True),
            'DE_': file.get_uint16(17, True),
            'HL_': file.get_uint16(19, True),
            'AF_': file.get_uint16(21, False), # Big-endian
            'IY': file.get_uint16(23, True),
            'IX': file.get_uint16(25, True),
            'iff1': not not file.get_uint8(27),
            'iff2': not not file.get_uint8(28),
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
        memory = extract_memory_block(data, 30, byte12 & 0x20, 0xc000)

        # construct byte arrays of length 0x4000 at the appropriate offsets into the data stream
        snapshot['memoryPages'][1] = extract(memory, 0, 0x4000)
        snapshot['memoryPages'][2] = extract(memory, 0x4000, 0x4000)
        snapshot['memoryPages'][3] = extract(memory, 0x8000, 0x4000)

        snapshot['tstates'] = 0
    else:
        # version 2-3 snapshot
        additional_header_length = file.get_uint16(30, True)
        isVersion2 = (additional_header_length == 23)
        snapshot['registers']['PC'] = file.get_uint16(32, True)
        machineId = file.get_uint8(34)
        is48K = machineId < 3 if isVersion2 else machineId < 4
        snapshot['model'] = 48 if is48K else 128
        if (not is48K):
            snapshot['ulaState']['pagingFlags'] = file.get_uint8(35)

        tstate_chunk_size = int((69888 if is48K else 70908) / 4)
        snapshot['tstates'] = (
            (((file.get_uint8(57) + 1) % 4) + 1) * tstate_chunk_size
            - (file.get_uint16(55, True) + 1)
        )
        if (snapshot['tstates'] >= tstate_chunk_size * 4): snapshot['tstates'] = 0

        offset = 32 + additional_header_length

        # translation table from the IDs Z80 assigns to pages, to the page numbers they
        # actually get loaded into
        page_id_to_number = None
        if (is48K):
            page_id_to_number = {
                4: 2,
                5: 3,
                8: 1
            }
        else:
            page_id_to_number = {
                3: 0,
                4: 1,
                5: 2,
                6: 3,
                7: 4,
                8: 5,
                9: 6,
                10: 7
            }
        data_length = data.buffer_info()[1]
        while offset < data_length:
            compressed_length = file.get_uint16(offset, True)
            is_compressed = True
            if compressed_length == 0xffff:
                compressed_length = 0x4000
                is_compressed = False

            page_id = file.get_uint8(offset + 2)
            if page_id in page_id_to_number:
                page_number = page_id_to_number[page_id]
                page_data = extract_memory_block(data, offset + 3, is_compressed, 0x4000)
                snapshot['memoryPages'][page_number] = page_data

            offset += compressed_length + 3

    return snapshot

# https://github.com/tslabs/zx-evo/blob/master/pentevo/docs/Formats/sna.txt
# for zx48, spyccy banks configuration is: 0 rom; 1,2,3 ram; 4 rom write; 5 usource rom; 6 tr-dos rom, 7 if2 cartridge
def parse_sna_file(data):
    mode128 = False
    snapshot = None
    size = len(data)
    sna = None
    HEADER_SIZE = 27

    if size == 131103 or size == 147487:
        mode128 = True
    elif size == 49179:
        mode128 = False
    else:
        raise Exception(f"parse_sna_file: Cannot handle SNA snapshots of length {size}")

    if mode128:
        sna = data[0: 49182]
    else:
        sna = data
    sna = DataView(sna)

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
        page = (sna.get_uint8(49181) & 7)
        snapshot['memoryPages'][page] = extract(data, 0x8000 + HEADER_SIZE, 0x4000)

        ptr = 49183
        for i in range(0, 8):
            if i not in snapshot['memoryPages']:
                snapshot['memoryPages'][i] = extract(data, ptr, 0x4000)
                ptr += 0x4000

    snapshot['registers']['IR'] = (sna.get_uint8(0) << 8) | sna.get_uint8(20)
    snapshot['registers']['HL_'] = sna.get_uint16(1, True)
    snapshot['registers']['DE_'] = sna.get_uint16(3, True)
    snapshot['registers']['BC_'] = sna.get_uint16(5, True)
    snapshot['registers']['AF_'] = sna.get_uint16(7, True)
    snapshot['registers']['HL'] = sna.get_uint16(9, True)
    snapshot['registers']['DE'] = sna.get_uint16(11, True)
    snapshot['registers']['BC'] = sna.get_uint16(13, True)
    snapshot['registers']['IY'] = sna.get_uint16(15, True)
    snapshot['registers']['IX'] = sna.get_uint16(17, True)
    snapshot['registers']['iff1'] = (sna.get_uint8(19) & 0x04) >> 2
    snapshot['registers']['iff2'] = (sna.get_uint8(19) & 0x04) >> 2
    snapshot['registers']['AF'] = sna.get_uint16(21, True)

    if mode128:
        snapshot['registers']['SP'] = sna.get_uint16(23, True)
        snapshot['registers']['PC'] = sna.get_uint16(49179, True)
        snapshot['ulaState']['pagingFlags'] = sna.get_uint8(49181)
    else:
        # peek memory at SP to get proper value of PC
        sp = sna.get_uint16(23, True)
        l = sna.get_uint8(sp - 16384 + HEADER_SIZE)
        sp = (sp + 1) & 0xffff
        h = sna.get_uint8(sp - 16384 + HEADER_SIZE)
        sp = (sp + 1) & 0xffff
        snapshot['registers']['PC'] = (h << 8) | l
        snapshot['registers']['SP'] = sp

    snapshot['registers']['im'] = sna.get_uint8(25)
    snapshot['ulaState']['borderColour'] = sna.get_uint8(26)

    return snapshot

def get_szx_id_string(file: DataView, offset):
    ascii = []
    ascii.append(file.get_uint8(offset))
    ascii.append(file.get_uint8(offset+1))
    ascii.append(file.get_uint8(offset+2))
    ascii.append(file.get_uint8(offset+3))
    return ''.join(map(chr, ascii))

def parse_szx_file(data):
    file = DataView(data)
    fileLen = len(data)
    snapshot = {
        'memoryPages': {}
    }

    if get_szx_id_string(file, 0) != 'ZXST':
        raise Exception("Not a valid SZX file")

    machine_id = file.get_uint8(6)
    match machine_id:
        case 1:
            snapshot['model'] = 48
        case 2 | 3:
            snapshot['model'] = 128
        case 7:
            snapshot['model'] = 5
        case _:
            raise Exception(f"parse_szx_file: unsupported machine type: {machine_id}")

    offset = 8
    while offset < fileLen:
        block_id = get_szx_id_string(file, offset)
        block_len = file.get_uint32(offset + 4, True)
        offset += 8

        match block_id:
            case 'Z80R':
                snapshot['registers'] = {
                    'AF': file.get_uint16(offset + 0, True),
                    'BC': file.get_uint16(offset + 2, True),
                    'DE': file.get_uint16(offset + 4, True),
                    'HL': file.get_uint16(offset + 6, True),
                    'AF_': file.get_uint16(offset + 8, True),
                    'BC_': file.get_uint16(offset + 10, True),
                    'DE_': file.get_uint16(offset + 12, True),
                    'HL_': file.get_uint16(offset + 14, True),
                    'IX': file.get_uint16(offset + 16, True),
                    'IY': file.get_uint16(offset + 18, True),
                    'SP': file.get_uint16(offset + 20, True),
                    'PC': file.get_uint16(offset + 22, True),
                    'IR': file.get_uint16(offset + 24, False),
                    'iff1': not not file.get_uint8(offset + 26),
                    'iff2': not not file.get_uint8(offset + 27),
                    'im': file.get_uint8(offset + 28),
                }
                snapshot['tstates'] = file.get_uint32(offset + 29, True)
                snapshot['halted'] = not not (file.get_uint8(offset + 37) & 0x02)
                # currently ignored:
                # chHoldIntReqCycles, eilast, memptr

            case 'SPCR':
                snapshot['ulaState'] = {
                    'borderColour': file.get_uint8(offset + 0),
                    'pagingFlags': file.get_uint8(offset + 1),
                }
                # currently ignored:
                # ch1ffd, chEff7, chFe

            case 'RAMP':
                is_compressed = file.get_uint16(offset + 0, True) & 0x0001
                pageNumber = file.get_uint8(offset + 2)
                if is_compressed:
                    compressedLength = block_len - 3
                    compressed = extract(data, offset + 3, compressedLength)
                    pageData = zlib.decompress(compressed)
                    #pageData = pako.inflate(compressed)
                    snapshot['memoryPages'][pageNumber] = pageData
                else:
                    pageData = extract(data, offset + 3, 0x4000)
                    snapshot['memoryPages'][pageNumber] = pageData

            case _:
                print(f'parse_szx_file: skipping block: {block_id}')

        offset += block_len

    return snapshot

def create_snapshot(board, cpu, mmu, ports, AY):
    page_size = mmu.get_page_size()

    # Compress the content of a memory bank into a byte array.
    def  compress_data():
        nonlocal page_size, previous_byte_single_ED, bank_pos

        content = bank_data[bank_pos]
        data = None

        # Every byte directly following a single ED is not taken into a block.
        if (previous_byte_single_ED == True and content != 0xED):
            data = array('B', [0])
            data[0] = content
            previous_byte_single_ED = False
            bank_pos += 1
        else:
            # Calculate how many times the content at the current position is repeated.
            repeats = 1
            if (bank_pos < page_size - 1):
                while ((bank_data[bank_pos + repeats] == content) and repeats < 0xFF and bank_pos + repeats < page_size - 1):
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
                previous_byte_single_ED = True
            else:
                previous_byte_single_ED = False

            bank_pos += repeats

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
        snapshot[39] = AY.read_register(0)
        snapshot[40] = AY.read_register(1)
        snapshot[41] = AY.read_register(2)
        snapshot[42] = AY.read_register(3)
        snapshot[43] = AY.read_register(4)
        snapshot[44] = AY.read_register(5)
        snapshot[45] = AY.read_register(6)
        snapshot[46] = AY.read_register(7)
        snapshot[47] = AY.read_register(8)
        snapshot[48] = AY.read_register(9)
        snapshot[49] = AY.read_register(10)
        snapshot[50] = AY.read_register(11)
        snapshot[51] = AY.read_register(12)
        snapshot[52] = AY.read_register(13)
        snapshot[53] = AY.read_register(14)
        snapshot[54] = AY.read_register(15)

    # Store the _memory data.
    # We now need to step through the Spectrum RAM starting at byte 16384.
    # The memory bytes will be stored in the Snapshot array, compressed when needed.
    bank_pos = 0
    store_pos = 30 + snapshot[30] + 2
    previous_byte_single_ED = False
    bank_data = None

    bank_to_page_map = array('B', [99, 99, 99, 99, 99, 99, 99, 99])

    if (board.type == 48):
        # Spectrum 48K
        bank_to_page_map[2] = 4
        bank_to_page_map[3] = 5
        bank_to_page_map[1] = 8
    else:
        # Spectrum 128K
        bank_to_page_map[0] = 3
        bank_to_page_map[1] = 4
        bank_to_page_map[2] = 5
        bank_to_page_map[3] = 6
        bank_to_page_map[4] = 7
        bank_to_page_map[5] = 8
        bank_to_page_map[6] = 9
        bank_to_page_map[7] = 10

    # Loop through the memory banks and save the data pages.
    for i in range(0, 8):
        if bank_to_page_map[i] != 99:
            bank_data = mmu.get_page_ram(i)
            previous_byte_single_ED = False
            pageData = array('B', [0] *18000)
            bank_pos = 0
            pagePos = 0
            j = 0
            while True:
                # Analyze the data at the current ram position and return an array to store in the Snapshot array.
                compressedData = compress_data()
                # Append the returned array to the Snapshot array.
                for j in range(0, len(compressedData)):
                    pageData[pagePos + j] = compressedData[j]
                # Move the current position in the Snapshot array forward.
                pagePos += j + 1

                if bank_pos >= page_size:
                    break

            # Store the compressed bank in the main array.
            snapshot[store_pos] = pagePos & 0xff
            snapshot[store_pos + 1] = (pagePos >> 8) & 0xff
            snapshot[store_pos + 2] = bank_to_page_map[i]

            for k in range(0, pagePos):
                snapshot[store_pos + 3 + k] = pageData[k]

            store_pos = store_pos + 3 + pagePos

    return snapshot, store_pos


