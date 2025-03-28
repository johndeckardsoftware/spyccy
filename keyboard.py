import tkinter as tk
from tkinter import ttk
import tkinter.font as tkFont
import app_globals

# Spectrum keyboard matrix
SPECCY = {
    'ONE': {'row': 3, 'mask': 0x01},
    'TWO': {'row': 3, 'mask': 0x02},
    'THREE': {'row': 3, 'mask': 0x04},
    'FOUR': {'row': 3, 'mask': 0x08},
    'FIVE': {'row': 3, 'mask': 0x10},
    'SIX': {'row': 4, 'mask': 0x10},
    'SEVEN': {'row': 4, 'mask': 0x08},
    'EIGHT': {'row': 4, 'mask': 0x04},
    'NINE': {'row': 4, 'mask': 0x02},
    'ZERO': {'row': 4, 'mask': 0x01},

    'Q': {'row': 2, 'mask': 0x01},
    'W': {'row': 2, 'mask': 0x02},
    'E': {'row': 2, 'mask': 0x04},
    'R': {'row': 2, 'mask': 0x08},
    'T': {'row': 2, 'mask': 0x10},
    'Y': {'row': 5, 'mask': 0x10},
    'U': {'row': 5, 'mask': 0x08},
    'I': {'row': 5, 'mask': 0x04},
    'O': {'row': 5, 'mask': 0x02},
    'P': {'row': 5, 'mask': 0x01},

    'A': {'row': 1, 'mask': 0x01},
    'S': {'row': 1, 'mask': 0x02},
    'D': {'row': 1, 'mask': 0x04},
    'F': {'row': 1, 'mask': 0x08},
    'G': {'row': 1, 'mask': 0x10},
    'H': {'row': 6, 'mask': 0x10},
    'J': {'row': 6, 'mask': 0x08},
    'K': {'row': 6, 'mask': 0x04},
    'L': {'row': 6, 'mask': 0x02},
    'ENTER': {'row': 6, 'mask': 0x01},

    'CAPS_SHIFT': {'row': 0, 'mask': 0x01, 'isCaps': True},
    'Z': {'row': 0, 'mask': 0x02},
    'X': {'row': 0, 'mask': 0x04},
    'C': {'row': 0, 'mask': 0x08},
    'V': {'row': 0, 'mask': 0x10},
    'B': {'row': 7, 'mask': 0x10},
    'N': {'row': 7, 'mask': 0x08},
    'M': {'row': 7, 'mask': 0x04},
    'SYMBOL_SHIFT': {'row': 7, 'mask': 0x02, 'isSymbol': True},
    'BREAK_SPACE': {'row': 7, 'mask': 0x01},
}

def sym(speccy_key):
    # patch key definition to indicate that symbol shift should be activated
    #return {...speccy_key, sym: true}
    d = dict(speccy_key)
    d['sym'] = True
    return d

def caps(speccy_key):
    # patch key definition to indicate that caps shift should be activated
    #return {...speccy_key, caps: True}
    d = dict(speccy_key)
    d['caps'] = True
    return d

# Mapping from system key codes to Spectrum key definitions
KEY_CODES = {
    49: SPECCY['ONE'],
    50: SPECCY['TWO'],
    51: SPECCY['THREE'],
    52: SPECCY['FOUR'],
    53: SPECCY['FIVE'],
    54: SPECCY['SIX'],
    55: SPECCY['SEVEN'],
    56: SPECCY['EIGHT'],
    57: SPECCY['NINE'],
    48: SPECCY['ZERO'],

    81: SPECCY['Q'],
    87: SPECCY['W'],
    69: SPECCY['E'],
    82: SPECCY['R'],
    84: SPECCY['T'],
    89: SPECCY['Y'],
    85: SPECCY['U'],
    73: SPECCY['I'],
    79: SPECCY['O'],
    80: SPECCY['P'],

    65: SPECCY['A'],
    83: SPECCY['S'],
    68: SPECCY['D'],
    70: SPECCY['F'],
    71: SPECCY['G'],
    72: SPECCY['H'],
    74: SPECCY['J'],
    75: SPECCY['K'],
    76: SPECCY['L'],
    13: SPECCY['ENTER'],

    16: SPECCY['CAPS_SHIFT'], # right shift, left shift is for 'symbol keys' defined down
    90: SPECCY['Z'],
    88: SPECCY['X'],
    67: SPECCY['C'],
    86: SPECCY['V'],
    66: SPECCY['B'],
    78: SPECCY['N'],
    77: SPECCY['M'],
    17: SPECCY['SYMBOL_SHIFT'],
    32: SPECCY['BREAK_SPACE'],

    # shifted combinations
    8: caps(SPECCY['ZERO']), # backspace
    37: caps(SPECCY['FIVE']), # left arrow
    38: caps(SPECCY['SEVEN']), # up arrow
    39: caps(SPECCY['EIGHT']), # right arrow
    40: caps(SPECCY['SIX']), # down arrow
    20: caps(SPECCY['TWO']), # caps lock
    112: caps(SPECCY['ONE']), # F1 > edit
    114: caps(SPECCY['THREE']), # F3 > true video
    115: caps(SPECCY['FOUR']), # F4 > inv. video
    120: caps(SPECCY['NINE']), # F9 > graphics

    # symbol keys
    '-': sym(SPECCY['J']),
    '_': sym(SPECCY['ZERO']),
    '=': sym(SPECCY['L']),
    '+': sym(SPECCY['K']),
    ';': sym(SPECCY['O']),
    ':': sym(SPECCY['Z']),
    '\'': sym(SPECCY['SEVEN']),
    '"': sym(SPECCY['P']),
    ',': sym(SPECCY['N']),
    '<': sym(SPECCY['R']),
    '.': sym(SPECCY['M']),
    '>': sym(SPECCY['T']),
    '/': sym(SPECCY['V']),
    '?': sym(SPECCY['C']),
    '*': sym(SPECCY['B']),
    '@': sym(SPECCY['TWO']),
    '#': sym(SPECCY['THREE']),
}
KEY_CODES['\x2264'] = sym(SPECCY['Q']); # LESS_THAN_EQUAL symbol (≤)
KEY_CODES['\x2265'] = sym(SPECCY['E']); # GREATER_THAN_EQUAL symbol (≥)
KEY_CODES['\x2260'] = sym(SPECCY['W']); # NOT_EQUAL symbol (≠)

# Extended Mapping from system key codes to Spectrum key definitions
KEY_CODES_EX = {
    '1': SPECCY['ONE'],
    '2': SPECCY['TWO'],
    '3': SPECCY['THREE'],
    '4': SPECCY['FOUR'],
    '5': SPECCY['FIVE'],
    '6': SPECCY['SIX'],
    '7': SPECCY['SEVEN'],
    '8': SPECCY['EIGHT'],
    '9': SPECCY['NINE'],
    '0': SPECCY['ZERO'],

    'q': SPECCY['Q'],
    'w': SPECCY['W'],
    'e': SPECCY['E'],
    'r': SPECCY['R'],
    't': SPECCY['T'],
    'y': SPECCY['Y'],
    'u': SPECCY['U'],
    'i': SPECCY['I'],
    'o': SPECCY['O'],
    'p': SPECCY['P'],

    'a': SPECCY['A'],
    's': SPECCY['S'],
    'd': SPECCY['D'],
    'f': SPECCY['F'],
    'g': SPECCY['G'],
    'h': SPECCY['H'],
    'j': SPECCY['J'],
    'k': SPECCY['K'],
    'l': SPECCY['L'],
    'return': SPECCY['ENTER'],

    'shift_l': SPECCY['CAPS_SHIFT'],
    'shift_r': SPECCY['CAPS_SHIFT'],
    'z': SPECCY['Z'],
    'x': SPECCY['X'],
    'c': SPECCY['C'],
    'v': SPECCY['V'],
    'b': SPECCY['B'],
    'n': SPECCY['N'],
    'm': SPECCY['M'],
    'control_l': SPECCY['SYMBOL_SHIFT'],
    'control_r': SPECCY['SYMBOL_SHIFT'],
    'space': SPECCY['BREAK_SPACE'],

    # shifted combinations
    'backspace': caps(SPECCY['ZERO']), # backspace
    'left': caps(SPECCY['FIVE']), # left arrow
    'up': caps(SPECCY['SEVEN']), # up arrow
    'right': caps(SPECCY['EIGHT']), # right arrow
    'down': caps(SPECCY['SIX']), # down arrow
    'caps_lock': caps(SPECCY['TWO']), # caps lock
    'f1': caps(SPECCY['ONE']), # F1 > edit
    'f3': caps(SPECCY['THREE']), # F3 > true video
    'f4': caps(SPECCY['FOUR']), # F4 > inv. video
    'f9': caps(SPECCY['NINE']), # F9 > graphics

    # symbol keys
    'exclam': sym(SPECCY['ONE']),
    'quotedbl': sym(SPECCY['P']),
    'sterling': sym(SPECCY['X']),
    'dollar': sym(SPECCY['FOUR']),
    'ampersand': sym(SPECCY['FOUR']),
    'percen': sym(SPECCY['FIVE']),
    'ampersand': sym(SPECCY['SIX']),
    'slash': sym(SPECCY['V']),
    'parenleft': sym(SPECCY['EIGHT']),
    'parenright': sym(SPECCY['NINE']),
    'equal': sym(SPECCY['L']),
    'question': sym(SPECCY['C']),
    'apostrophe': sym(SPECCY['SEVEN']),
    'less': sym(SPECCY['R']),
    'greater': sym(SPECCY['T']),
    'comma': sym(SPECCY['N']),
    'semicolon': sym(SPECCY['O']),
    'period': sym(SPECCY['M']),
    'colon': sym(SPECCY['Z']),
    'minus': sym(SPECCY['J']),
    'underscore': sym(SPECCY['ZERO']),
    'plus': sym(SPECCY['K']),
    'asterisk': sym(SPECCY['B']),
    'ograve': sym(SPECCY['TWO']),
    'agrave': sym(SPECCY['THREE']),

    # (App key for E mode) + shift combinations
    'ugrave': caps(SPECCY['F']),             # {
    'igrave': caps(SPECCY['G']),             # }
    'egrave': caps(SPECCY['Y']),             # [
    'eacute': caps(SPECCY['U']),             # ]
    'ccedilla': caps(SPECCY['P']),           # copyright
    'degree': caps(SPECCY['A']),             # tilde
    'bar': caps(SPECCY['S']),                # |
    'backslash': caps(SPECCY['D']),          # \
}

# Mapping from Basic token to key
BASIC_TO_KEY = {
    'ENTER': {'text': 'ENTER', 'ks': ['return']},
    'BREAK': {'text': 'Caps Shift and SPACE', 'ks': ['cs_mode','SPACE']},
    'CAPS LOCK': {'text': 'CS 2 or capslock', 'ks': ['cs_mode','2']},
    'DELETE': {'text': 'CS 0 or backspace', 'ks': ['cs_mode','0','g','0']},
    'EDIT': {'text': 'CS 1 or F1', 'ks': ['cs_mode','1']},
    'GRAPHICS': {'text': 'CS 9 or F9', 'ks': ['cs_mode','9']},
    'TRUE VID': {'text': 'CS 3 or F3', 'ks': ['cs_mode','3']},
    'INV VID': {'text': 'CS 4 or F4', 'ks': ['cs_mode','4']},
    'BRIGHT': {'text': 'E, 9', 'ks': ['e_mode','9']},
    'UNBRIGHT': {'text': 'E, 8', 'ks': ['e_mode','8']},

    'Left': {'text': 'CS 5 or left', 'ks': ['cs_mode','5']},
    'Down': {'text': 'CS 6 or down', 'ks': ['cs_mode','6']},
    'Up': {'text': 'CS 7 or up', 'ks': ['cs_mode','7']},
    'Right': {'text': 'CS 8 or right', 'ks': ['cs_mode','8']},

    ',': {'text': 'K, L or C, Symbol Shift N', 'ks': ['ss_mode','n']},
    '.': {'text': 'K, L or C, Symbol Shift M', 'ks': ['ss_mode','m']},
    ':': {'text': 'K, L or C, Symbol Shift Z', 'ks': ['ss_mode','z']},
    ';': {'text': 'K, L or C, Symbol Shift O', 'ks': ['ss_mode','o']},
    '!': {'text': 'K, L or C, Symbol Shift 1', 'ks': ['ss_mode','1']},
    '?': {'text': 'K, L or C, Symbol Shift C', 'ks': ['ss_mode','c']},
    '"': {'text': 'K, L or C, Symbol Shift P', 'ks': ['ss_mode','p']},
    '\'': {'text': 'K, L or C, Symbol Shift 7', 'ks': ['ss_mode','7']},
    '#': {'text': 'K, L or C, Symbol Shift 3', 'ks': ['ss_mode','3']},
    '$': {'text': 'K, L or C, Symbol Shift 4', 'ks': ['ss_mode','4']},
    '£': {'text': 'K, L or C, Symbol Shift X', 'ks': ['ss_mode','x']},
    '%': {'text': 'K, L or C, Symbol Shift 5', 'ks': ['ss_mode','5']},
    '&': {'text': 'K, L or C, Symbol Shift 6', 'ks': ['ss_mode','6']},
    '@': {'text': 'K, L or C, Symbol Shift 2', 'ks': ['ss_mode','2']},
    '©': {'text': 'E, Symbol Shift P', 'ks': ['e_mode','ss_mode','p']},
    '+': {'text': 'K, L or C, Symbol Shift K', 'ks': ['ss_mode','k']},
    '-': {'text': 'K, L or C, Symbol Shift J', 'ks': ['ss_mode','j']},
    '*': {'text': 'K, L or C, Symbol Shift B', 'ks': ['ss_mode','b']},
    '/': {'text': 'K, L or C, Symbol Shift V', 'ks': ['ss_mode','v']},
    '|': {'text': 'E, Symbol Shift S', 'ks': ['e_mode','ss_mode','s']},
    '\\': {'text': 'E, Symbol Shift D', 'ks': ['e_mode','ss_mode','d']},
    '(': {'text': 'K, L or C, Symbol Shift 8', 'ks': ['ss_mode','8']},
    ')': {'text': 'K, L or C, Symbol Shift 9', 'ks': ['ss_mode','9']},
    '[': {'text': 'E, Symbol Shift Y', 'ks': ['e_mode','ss_mode','y']},
    ']': {'text': 'E, Symbol Shift U', 'ks': ['e_mode','ss_mode','u']},
    '{': {'text': 'E, Symbol Shift F', 'ks': ['e_mode','ss_mode','f']},
    '}': {'text': 'E, Symbol Shift G', 'ks': ['e_mode','ss_mode','g']},
    '<': {'text': 'K, L or C, Symbol Shift R', 'ks': ['ss_mode','r']},
    '>': {'text': 'K, L or C, Symbol Shift T', 'ks': ['ss_mode','t']},
    '=': {'text': 'K, L or C, Symbol Shift L', 'ks': ['ss_mode','l']},
    '<=': {'text': 'K, L or C, Symbol Shift Q', 'ks': ['ss_mode','q']},
    '>=': {'text': 'K, L or C, Symbol Shift E', 'ks': ['ss_mode','e']},
    '<>': {'text': 'K, L or C, Symbol Shift W', 'ks': ['ss_mode','w']},
    '^': {'text': 'K, L or C, Symbol Shift H', 'ks': ['ss_mode','h']},
    '_': {'text': 'K, L or C, Symbol Shift 0', 'ks': ['ss_mode','0']},
    '~': {'text': 'E, Symbol Shift A', 'ks': ['e_mode','ss_mode','a']},
    'ABS': {'text': 'E, G', 'ks': ['e_mode','g']},
    'ACS': {'text': 'E, Symbol Shift W', 'ks': ['e_mode','ss_mode','w']},
    'AND': {'text': 'K, L or C, Symbol Shift Y', 'ks': ['ss_mode','y']},
    'ASN': {'text': 'E, Symbol Shift Q', 'ks': ['e_mode','ss_mode','q']},
    'AT': {'text': 'K, L or C, Symbol Shift I', 'ks': ['ss_mode','i']},
    'ATN': {'text': 'E, Symbol Shift E', 'ks': ['e_mode','ss_mode','e']},
    'ATTR': {'text': 'E, Symbol Shift L', 'ks': ['e_mode','ss_mode','l']},
    'BEEP': {'text': 'E, Symbol Shift Z', 'ks': ['e_mode','ss_mode','z']},
    'BIN': {'text': 'E, B', 'ks': ['e_mode','b']},
    'BORDER': {'text': 'K, B', 'ks': ['b']},
    'BRIGHT': {'text': 'E, Symbol Shift B', 'ks': ['e_mode','ss_mode','b']},
    'CAT': {'text': 'E, Symbol Shift 9', 'ks': ['e_mode','ss_mode','9']},
    'CHR$': {'text': 'E, U', 'ks': ['e_mode','u']},
    'CIRCLE': {'text': 'E, Symbol Shift H', 'ks': ['e_mode','ss_mode','h']},
    'CLEAR': {'text': 'K, X', 'ks': ['x']},
    'CLOSE #': {'text': 'E, Symbol Shift 5', 'ks': ['e_mode','ss_mode','5']},
    'CLS': {'text': 'K, V', 'ks': ['v']},
    'CODE': {'text': 'E, I', 'ks': ['e_mode','i']},
    'CONTINUE': {'text': 'K, C', 'ks': ['c']},
    'COPY': {'text': 'K, Z', 'ks': ['z']},
    'COS': {'text': 'E, W', 'ks': ['e_mode','w']},
    'DATA': {'text': 'E, D', 'ks': ['e_mode','d']},
    'DEF FN': {'text': 'E, Symbol Shift 1', 'ks': ['e_mode','ss_mode','1']},
    'DIM': {'text': 'K, D', 'ks': ['d']},
    'DRAW': {'text': 'K, W', 'ks': ['w']},
    'ERASE': {'text': 'E, Symbol Shift 7', 'ks': ['e_mode','ss_mode','7']},
    'EXP': {'text': 'E, X', 'ks': ['e_mode','x']},
    'FLASH': {'text': 'E, Symbol Shift V', 'ks': ['e_mode','ss_mode','v']},
    'FN': {'text': 'E, Symbol Shift 2', 'ks': ['e_mode','ss_mode','2']},
    'FOR': {'text': 'K, F', 'ks': ['f']},
    'FORMAT': {'text': 'E, Symbol Shift 0', 'ks': ['e_mode','ss_mode','0']},
    'GO SUB': {'text': 'K, H', 'ks': ['h']},
    'GO TO': {'text': 'K, G', 'ks': ['g']},
    'IF': {'text': 'K, U', 'ks': ['u']},
    'IN': {'text': 'E, Symbol Shift I', 'ks': ['e_mode','ss_mode','i']},
    'INK': {'text': 'E, Symbol Shift X', 'ks': ['e_mode','ss_mode','x']},
    'INKEY$': {'text': 'E, N', 'ks': ['e_mode','n']},
    'INPUT': {'text': 'K, I', 'ks': ['i']},
    'INT': {'text': 'E, R', 'ks': ['e_mode','r']},
    'INVERSE': {'text': 'E, Symbol Shift M', 'ks': ['e_mode','ss_mode','m']},
    'LEN': {'text': 'E, K', 'ks': ['e_mode','k']},
    'LET': {'text': 'K, L', 'ks': ['l']},
    'LINE': {'text': 'E, Symbol Shift 3', 'ks': ['e_mode','ss_mode','3']},
    'LIST': {'text': 'K, K', 'ks': ['k']},
    'LLIST': {'text': 'E, V', 'ks': ['e_mode','v']},
    'LN': {'text': 'E, Z', 'ks': ['e_mode','z']},
    'LOAD': {'text': 'K, J', 'ks': ['j']},
    'LPRINT': {'text': 'E, C', 'ks': ['e_mode','c']},
    'MERGE': {'text': 'E, Symbol Shift T', 'ks': ['e_mode','ss_mode','t']},
    'MOVE': {'text': 'E, Symbol Shift 6', 'ks': ['e_mode','ss_mode','6']},
    'NEW': {'text': 'K, A', 'ks': ['a']},
    'NEXT': {'text': 'K, N', 'ks': ['n']},
    'NOT': {'text': 'K, L or C, Symbol Shift S', 'ks': ['ss_mode','s']},
    'OPEN #': {'text': 'E, Symbol Shift 4', 'ks': ['e_mode','ss_mode','4']},
    'OR': {'text': 'K, L or C, Symbol Shift U', 'ks': ['ss_mode','u']},
    'OUT': {'text': 'E, Symbol Shift O', 'ks': ['e_mode','ss_mode','o']},
    'OVER': {'text': 'E, Symbol Shift N', 'ks': ['e_mode','ss_mode','n']},
    'PAPER': {'text': 'E, Symbol Shift C', 'ks': ['e_mode','ss_mode','c']},
    'PAUSE': {'text': 'K, M', 'ks': ['m']},
    'PEEK': {'text': 'E, O', 'ks': ['e_mode','o']},
    'PI': {'text': 'E, M', 'ks': ['e_mode','m']},
    'PLOT': {'text': 'K, Q', 'ks': ['q']},
    'POINT': {'text': 'E, Symbol Shift 8', 'ks': ['e_mode','ss_mode','8']},
    'POKE': {'text': 'K, O', 'ks': ['o']},
    'PRINT': {'text': 'K, P', 'ks': ['p']},
    'RANDOMIZE': {'text': 'K, T', 'ks': ['t']},
    'READ': {'text': 'E, A', 'ks': ['e_mode','a']},
    'REM': {'text': 'K, E', 'ks': ['e']},
    'RESTORE': {'text': 'E, S', 'ks': ['e_mode','s']},
    'RETURN': {'text': 'K, Y', 'ks': ['y']},
    'RND': {'text': 'E, T', 'ks': ['e_mode','t']},
    'RUN': {'text': 'K, R', 'ks': ['r']},
    'SAVE': {'text': 'K, S', 'ks': ['s']},
    'SCREEN$': {'text': 'E, Symbol Shift K', 'ks': ['e_mode','ss_mode','k']},
    'SGN': {'text': 'E, F', 'ks': ['e_mode','f']},
    'SIN': {'text': 'E, Q', 'ks': ['e_mode','q']},
    'SQR': {'text': 'E, H', 'ks': ['e_mode','h']},
    'STEP': {'text': 'K, L or C, Symbol Shift D', 'ks': ['ss_mode','d']},
    'STOP': {'text': 'K, L or C, Symbol Shift A', 'ks': ['ss_mode','a']},
    'STR$': {'text': 'E, Y', 'ks': ['e_mode','y']},
    'TAB': {'text': 'E, P', 'ks': ['e_mode','p']},
    'TAN': {'text': 'E, E', 'ks': ['e_mode','e']},
    'THEN': {'text': 'K, L or C, Symbol Shift G', 'ks': ['ss_mode','g']},
    'TO': {'text': 'K, L or C, Symbol Shift F', 'ks': ['ss_mode','f']},
    'USR': {'text': 'E, L', 'ks': ['e_mode','l']},
    'VAL': {'text': 'E, J', 'ks': ['e_mode','j']},
    'VAL$': {'text': 'E, Symbol Shift J', 'ks': ['e_mode','ss_mode','j']},
    'VERIFY': {'text': 'E, Symbol Shift R', 'ks': ['e_mode','ss_mode','r']},
}

class BaseKeyboardHandler :
    def __init__(self, window, machine):
        self.window = window  # where we attach keyboard event listeners
        self.machine = machine
        self.eventsAreBound = False
        self.keyStates = bytearray([0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff])
        # if True, the real symbol shift key is being held (as opposed to being active through a
        # virtual key combination)
        self.symbolIsShifted = False
        # if True, the real caps shift key is being held (as opposed to being active through a
        # virtual key combination)
        self.capsIsShifted = False
        self.kempston_state = 0

    def start(self):
        self.eventsAreBound = True

    def stop(self):
        self.eventsAreBound = False

    def vkey_down(self, row, mask):
        self.keyStates[row] = (self.keyStates[row] & (~ mask))

    def vkey_up(self, row, mask):
        self.keyStates[row] = (self.keyStates[row] | mask)

    def send_key(self, row, mask, down):
        if down: self.vkey_down(row, mask)
        else:    self.vkey_up(row, mask)
        #self.log(f'{row}, {hex(mask)}, {"down" if down else "up"}')

    def poll(self, addr):
        result = 0xbf
        for row in range(0, 8):
            if (not (addr & (1 << row))):
                result &= self.keyStates[row]   # scan this keyboard row
        return result

    def key_to_kempston(self, row, mask):
        #Handle Kempston joystick via the keyboard.
        match (row, mask):
            case "Up":
                self.kempston_state |= 8
                KeyToPort(ZXKeyboardPortMap.Key("7"), True)
            case "Down":
                self.kempston_state |= 4
                KeyToPort(ZXKeyboardPortMap.Key("6"), True)
            case "Left":
                self.kempston_state |= 2
                KeyToPort(ZXKeyboardPortMap.Key("5"), True)
            case "Right":
                self.kempston_state |= 1
                KeyToPort(ZXKeyboardPortMap.Key("8"), True)
            case "B":
                self.kempston_state |= 16
            case "B1":
                self.kempston_state |= 16
            case "N":
                self.kempston_state |= 32
            case "B2":
                self.kempston_state |= 32

    def log(self, text):
        log = open('./tmp/keyboard.log', 'a')
        log.write(text)
        log.write("\n")
        log.close

class OriginalKeyboardHandler(BaseKeyboardHandler):
    def __init__(self, window, machine):
        super().__init__(window, machine)
        self.window.bind("<Key>", self.real_key_down)
        self.window.bind("<KeyRelease>", self.real_key_up)

    def real_key_down(self, event):
        if event.keycode in KEY_CODES:
            speccy_key = KEY_CODES[event.keycode]
            self.send_key(speccy_key['row'], speccy_key['mask'], True)
            if 'caps' in speccy_key or 'sym' in speccy_key:
                self.send_key(SPECCY['CAPS_SHIFT']['row'], SPECCY['CAPS_SHIFT']['mask'], 'caps' in speccy_key)
                self.send_key(SPECCY['SYMBOL_SHIFT']['row'], SPECCY['SYMBOL_SHIFT']['mask'], 'sym' in speccy_key)
            elif 'isCaps' in speccy_key:
                self.capsIsShifted = True
            elif 'isSymbol' in speccy_key:
                self.symbolIsShifted = True

    def real_key_up(self, event):
        if event.keycode in KEY_CODES:
            speccy_key = KEY_CODES[event.keycode]
            self.send_key(speccy_key['row'], speccy_key['mask'], False)
            if 'caps' in speccy_key or 'sym' in speccy_key:
                self.send_key(SPECCY['CAPS_SHIFT']['row'], SPECCY['CAPS_SHIFT']['mask'], self.capsIsShifted)
                self.send_key(SPECCY['SYMBOL_SHIFT']['row'], SPECCY['SYMBOL_SHIFT']['mask'], self.symbolIsShifted)
            elif 'isCaps' in speccy_key:
                self.capsIsShifted = False
            elif 'isSymbol' in speccy_key:
                self.symbolIsShifted = False

    def show_help(self):
        if not self.help:
            child_window = tk.Toplevel(self.window)
            self.help = ZXBasicToKey(self, child_window, self.window)
        self.help.window.focus_force()

class StandardKeyboardHandler(BaseKeyboardHandler):
    def __init__(self, window, machine):
        super().__init__(window, machine)
        self.window.bind("<Key>", self.real_key_down)
        self.window.bind("<KeyRelease>", self.real_key_up)
        #self.window.bind("PRINT", lambda x: print("PRINT"))
        self.help = None
        self.key_events_stack = []
        self.list_key_sequence = [
            ['t', 'e_mode', 'l', '1', '5', '6', '1', '6', 'return'],
            ['y', 'return', 'v', 'return']
        ]

    def e_mode(self, down):
        self.send_key(SPECCY['CAPS_SHIFT']['row'], SPECCY['CAPS_SHIFT']['mask'], down)
        self.send_key(SPECCY['SYMBOL_SHIFT']['row'], SPECCY['SYMBOL_SHIFT']['mask'], down)

    def key_sequence(self, id):
        if type(id) == int:
            #self.log(">>"+",".join(self.list_key_sequence[id]))
            self.send_keys(self.list_key_sequence[id], 0)
        else:
            b2k = BASIC_TO_KEY[id]
            ks = b2k['ks']
            #self.log(">>"+",".join(ks))
            self.send_keys(ks, 0)

    def send_keys(self, keys, i):
        if i < len(keys):
            k = keys[i]
            if k == 'e_mode':
                self.window.after(0, self.e_mode, True)
                self.window.after(50, self.e_mode, False)
            elif k == 'cs_mode':
                self.window.after(0, self.send_key(SPECCY['CAPS_SHIFT']['row'], SPECCY['CAPS_SHIFT']['mask'], True))
                i += 1
                k = keys[i]
                speccy_key = KEY_CODES_EX[k]
                self.window.after(50, self.send_key, speccy_key['row'], speccy_key['mask'], True)
                self.window.after(100, self.send_key, speccy_key['row'], speccy_key['mask'], False)
                self.window.after(150, self.send_key, SPECCY['CAPS_SHIFT']['row'], SPECCY['CAPS_SHIFT']['mask'], False)
            elif k == 'ss_mode':
                self.window.after(0, self.send_key, SPECCY['SYMBOL_SHIFT']['row'], SPECCY['SYMBOL_SHIFT']['mask'], True)
                i += 1
                k = keys[i]
                speccy_key = KEY_CODES_EX[k]
                self.window.after(50, self.send_key, speccy_key['row'], speccy_key['mask'], True)
                self.window.after(100, self.send_key, speccy_key['row'], speccy_key['mask'], False)
                self.window.after(150, self.send_key, SPECCY['SYMBOL_SHIFT']['row'], SPECCY['SYMBOL_SHIFT']['mask'], False)
            else:
                speccy_key = KEY_CODES_EX[k]
                self.window.after(0, self.send_key, speccy_key['row'], speccy_key['mask'], True)
                self.window.after(50, self.send_key, speccy_key['row'], speccy_key['mask'], False)
            self.window.after(200, self.send_keys, keys, i + 1)

    def real_key_down(self, event):
        #self.log(str(event))
        keysym = event.keysym.lower()
        if keysym == 'app':
            self.window.after(0, self.e_mode, True)
            self.window.after(100, self.e_mode, False)

        elif keysym in KEY_CODES_EX:
            speccy_key = KEY_CODES_EX[keysym]
            #self.log(str(speccy_key))
            if 'caps' in speccy_key or 'sym' in speccy_key:
                self.send_key(SPECCY['CAPS_SHIFT']['row'], SPECCY['CAPS_SHIFT']['mask'], 'caps' in speccy_key)
                self.send_key(SPECCY['SYMBOL_SHIFT']['row'], SPECCY['SYMBOL_SHIFT']['mask'], 'sym' in speccy_key)
            elif 'isCaps' in speccy_key:
                self.capsIsShifted = True
            elif 'isSymbol' in speccy_key:
                self.symbolIsShifted = True

            self.send_key(speccy_key['row'], speccy_key['mask'], True)
            self.key_events_stack.append(speccy_key)

    def real_key_up(self, event):
        #self.log(str(event))
        while len(self.key_events_stack):
            speccy_key = self.key_events_stack.pop(0)
            #self.log(str(speccy_key))
            if 'caps' in speccy_key or 'sym' in speccy_key:
                self.send_key(SPECCY['CAPS_SHIFT']['row'], SPECCY['CAPS_SHIFT']['mask'], self.capsIsShifted)
                self.send_key(SPECCY['SYMBOL_SHIFT']['row'], SPECCY['SYMBOL_SHIFT']['mask'], self.symbolIsShifted)
            elif 'isCaps' in speccy_key:
                self.capsIsShifted = False
            elif 'isSymbol' in speccy_key:
                self.symbolIsShifted = False
            self.send_key(speccy_key['row'], speccy_key['mask'], False)

    def show_help(self):
        if not self.help:
            child_window = tk.Toplevel(self.window)
            self.help = ZXBasicToKey(self, child_window, self.window)
        self.help.window.focus_force()

RECREATED_SPECTRUM_GAME_LAYER = {
    "ab": SPECCY['ONE'],
    "cd": SPECCY['TWO'],
    "ef": SPECCY['THREE'],
    "gh": SPECCY['FOUR'],
    "ij": SPECCY['FIVE'],
    "kl": SPECCY['SIX'],
    "mn": SPECCY['SEVEN'],
    "op": SPECCY['EIGHT'],
    "qr": SPECCY['NINE'],
    "st": SPECCY['ZERO'],

    "uv": SPECCY['Q'],
    "wx": SPECCY['W'],
    "yz": SPECCY['E'],
    "AB": SPECCY['R'],
    "CD": SPECCY['T'],
    "EF": SPECCY['Y'],
    "GH": SPECCY['U'],
    "IJ": SPECCY['I'],
    "KL": SPECCY['O'],
    "MN": SPECCY['P'],

    "OP": SPECCY['A'],
    "QR": SPECCY['S'],
    "ST": SPECCY['D'],
    "UV": SPECCY['F'],
    "WX": SPECCY['G'],
    "YZ": SPECCY['H'],
    "01": SPECCY['J'],
    "23": SPECCY['K'],
    "45": SPECCY['L'],
    "67": SPECCY['ENTER'],

    "89": SPECCY['CAPS_SHIFT'],
    "<>": SPECCY['Z'],
    "-=": SPECCY['X'],
    "[]": SPECCY['C'],
    ";:": SPECCY['V'],
    ",.": SPECCY['B'],
    "/?": SPECCY['N'],
    "{}": SPECCY['M'],
    "!$": SPECCY['SYMBOL_SHIFT'],
    "%^": SPECCY['BREAK_SPACE'],
}
recreatedUpDown = {}

for pair, key in RECREATED_SPECTRUM_GAME_LAYER.items():
    d = dict(key); d['message'] = "keyDown"
    recreatedUpDown[pair[0]] = d
    d = dict(key); d['message'] = "keyUp"
    recreatedUpDown[pair[1]] = d

class GamerKeyboardHandler(BaseKeyboardHandler):
    def __init__(self, window, machine):
        super().__init__(window, machine)
        self.window.bind("<Key>", self.real_key_down)

    def real_key_down(self, event):
        if event.char in recreatedUpDown:
            specialCode = recreatedUpDown[event.char]
            if specialCode['message'] == 'keyDown':
                self.send_key(specialCode['row'], specialCode['mask'], True)
            else:
                self.send_key(specialCode['row'], specialCode['mask'], False)

class ZXBasicToKey(StandardKeyboardHandler):
    def __init__(self, caller, top_window, emu_window):
        self.caller = caller
        self.window = top_window
        self.emu_window = emu_window

        w = 1324
        h = 390
        ws = top_window.winfo_screenwidth() # width of the screen
        hs = top_window.winfo_screenheight() # height of the screen
        x = int((ws/2) - (w/2))
        y = (hs - h - 48)
        self.window.geometry(f'{w}x{h}+{x}+{y}')
        self.window.title('SPYCCY - BASIC tokens to Key')
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        self.window.iconphoto(False, app_globals.APP_ICON)

        self.style = ttk.Style()
        self.style.configure("Treeview.Heading", font=(None, 7))
        self.style.configure("Treeview", font=(None, 7))

        # define columns
        columns = ('c0', 'c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'c7')
        self.tree = ttk.Treeview(self.window, columns=columns, show='headings', selectmode='browse')
        # define headings
        for i in range(8):
            self.tree.heading(f'c{i}', text='Statement >> keys')
            self.tree.column(f'c{i}', width=166, stretch=False)

        self.tree.tag_configure('oddrow', background='LightCyan1')
        self.tree.tag_configure('evenrow', background='LightCyan2')

        # add data to the treeview
        tag = "evenrow"
        i = 1
        lsk = []
        for key, value in BASIC_TO_KEY.items():
            lsk.append(f"{key} >> {value['text']}")
            i += 1
            if i > 8:
                self.tree.insert('', tk.END, values=lsk, tags=(tag))
                i = 1
                lsk.clear()
                tag = "oddrow" if tag == 'evenrow' else "evenrow"
        if i > 1:
            while i <= 8: lsk.append("--"); i+= 1
            self.tree.insert('', tk.END, values=lsk, tags=(tag))

        self.tree.bind('<ButtonRelease-1>', self.item_selected)
        self.tree.grid(row=0, column=0, sticky='nsew', padx=0, pady=0)

    def item_selected(self, event):
        for selected_item in self.tree.selection():
            item = self.tree.item(selected_item)
            col = self.tree.identify_column(event.x)
            col = int(col[1:]) - 1
            value = item['values'][col]
            i = value.find(">>")
            if i != 1:
                b2k = value[0:i-1].rstrip()
                self.caller.key_sequence(b2k)
        self.emu_window.focus_force()

