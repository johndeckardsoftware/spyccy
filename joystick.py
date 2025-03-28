#
# https://worldofspectrum.org/faq/reference/peripherals.htm#Miscellaneous
#
import pygame
from pygame.locals import *
from config import Config
import keyboard

SINCLAIR = 1
SINCLAIR_LEFT = 2
SINCLAIR_RIGHT = 3
CURSOR = 4
PROGRAMMABLE = 5
KEMPSTON = 6
FULLER = 7

KB_ROW_PORT = [0xfefe, 0xfdfe, 0xfbfe, 0xf7fe, 0xeffe, 0xdffe, 0xbffe, 0x7ffe]

class JoysticksController():

    def __init__(self, type):
        self.type = type
        self.key_mapping = 0 if type == KEMPSTON or type == FULLER else 1

        pygame.joystick.init()
        self.joycount = pygame.joystick.get_count()
        if self.joycount == 0:
            print("No joysticks were detected.")
            Config.set('joystick.detected', 0)
        else:
            Config.set('joystick.detected', 1)

        if self.type == SINCLAIR and self.joycount == 1:
            self.type = SINCLAIR_RIGHT

        self.joysticks = [pygame.joystick.Joystick(x) for x in range(self.joycount)]
        for joy in self.joysticks:
            joy.init()

        self.p1_left = self.get_port_mask(Config.get('joystick.left', 'Q'))
        self.p1_right = self.get_port_mask(Config.get('joystick.right', 'A'))
        self.p1_up = self.get_port_mask(Config.get('joystick.up', 'O'))
        self.p1_down = self.get_port_mask(Config.get('joystick.down', 'P'))
        self.p1_fire = self.get_port_mask(Config.get('joystick.fire', 'BREAK_SPACE'))

    def set_type(self, type):
        self.type = type
        if self.type == SINCLAIR and self.joycount == 1:
            self.type = SINCLAIR_RIGHT
        self.key_mapping = 0 if type == KEMPSTON or type == FULLER else 1

    def get_port_mask(self, key):
        speccy = keyboard.SPECCY[key]
        port = KB_ROW_PORT[speccy['row']]
        mask = ~speccy['mask'] & 0xbf
        return (port, mask)

#   Using shift keys and a combination of modes the Spectrum 40-key keyboard
#   can be mapped to 256 input characters
# ---------------------------------------------------------------------------
#
#         0     1     2     3     4 -Bits-  4     3     2     1     0
# PORT                                                                    PORT
#
# F7FE  [ 1 ] [ 2 ] [ 3 ] [ 4 ] [ 5 ]  |  [ 6 ] [ 7 ] [ 8 ] [ 9 ] [ 0 ]   EFFE
#  ^                                   |                                   v
# FBFE  [ Q ] [ W ] [ E ] [ R ] [ T ]  |  [ Y ] [ U ] [ I ] [ O ] [ P ]   DFFE
#  ^                                   |                                   v
# FDFE  [ A ] [ S ] [ D ] [ F ] [ G ]  |  [ H ] [ J ] [ K ] [ L ] [ ENT ] BFFE
#  ^                                   |                                   v
# FEFE  [SHI] [ Z ] [ X ] [ C ] [ V ]  |  [ B ] [ N ] [ M ] [sym] [ SPC ] 7FFE
#  ^     $27                                                 $18           v
# Start                                                                   End
#        00100111                                            00011000
#
# ---------------------------------------------------------------------------
#   The above map may help in reading.
#   The neat arrangement of ports means that the B register need only be
#   rotated left to work up the left hand side and then down the right
#   hand side of the keyboard. When the reset bit drops into the carry
#   then all 8 half-rows have been read. Shift is the first key to be
#   read. The lower six bits of the shifts are unambiguous.

    def key_map(self, addr):
        result = 0xbf
        #self.log(self.info())
        #self.log(f"{hex(addr)} {hex(result)=}")
        if self.type == SINCLAIR or self.type == SINCLAIR_LEFT or self.type == SINCLAIR_RIGHT:
            if addr == 0xf7fe and (self.type == SINCLAIR or self.type == SINCLAIR_LEFT):    #port 0xf7fe 1, 2, 3, 4, 5
                value = self.joysticks[0].get_hat(0)
                if value[0] == -1:
                    result = 0xbe       #left 1
                elif value[0] == 1:
                    result = 0xbd       #right 2
                elif value[1] == 1:
                    result = 0xb7       #up 4
                elif value[1] == -1:
                    result = 0xbb       #down 3
                b4 = self.joysticks[0].get_button(4)
                b5 = self.joysticks[0].get_button(5)
                if b4 or b5:
                    result = 0xaf       #fire 5
            elif addr == 0xeffe and (self.type == SINCLAIR or self.type == SINCLAIR_RIGHT):  #port 0xeffe 6, 7, 8, 9, 0
                joy = 1 if self.type == SINCLAIR else 0
                value = self.joysticks[joy].get_hat(0)
                if value[0] == -1:
                    result = 0xaf       #left 6
                elif value[0] == 1:
                    result = 0xb7       #right 7
                elif value[1] == 1:
                    result = 0xbd       #up 9
                elif value[1] == -1:
                    result = 0xbb       #down 8
                b4 = self.joysticks[joy].get_button(4)
                b5 = self.joysticks[joy].get_button(5)
                if b4 or b5:
                    result = 0xbe       #fire 0

        elif self.type == CURSOR:
            if addr == 0xf7fe: #port 0xf7fe keys 5 (left)
                value = self.joysticks[0].get_hat(0)
                if value[0] == -1:
                    result = 0xaf #left 5
            elif addr == 0xeffe: #port 0xeffe keys 6 (down), 7 (up), 8 (right) and 0 (fire)
                value = self.joysticks[0].get_hat(0)
                if value[0] == 1:
                    result = 0xbb #right 8
                elif value[1] == 1:
                    result = 0xb7 #up 7
                elif value[1] == -1:
                    result = 0xaf #down 6
                b4 = self.joysticks[0].get_button(4)
                b5 = self.joysticks[0].get_button(5)
                if b4 or b5:
                    result = 0xbe       #fire 0

        elif self.type == PROGRAMMABLE:
            value = self.joysticks[0].get_hat(0)
            if addr == self.p1_left[0] and value[0] == -1:
                result = self.p1_left[1]
            elif addr == self.p1_right[0] and value[0] == 1:
                result = self.p1_right[1]
            elif addr == self.p1_up[0] and value[1] == 1:
                result = self.p1_up[1]
            elif addr == self.p1_down[0] and value[1] == -1:
                result = self.p1_down[1]
            elif addr == self.p1_fire[0]:
                b4 = self.joysticks[0].get_button(4)
                b5 = self.joysticks[0].get_button(5)
                if b4 or b5:
                    result = self.p1_fire[1]

        return result

    def poll(self):
        result = 0x00
        value = self.joysticks[0].get_hat(0)
        if self.type == KEMPSTON:
            if value[0] == -1:
                result |= 2 #left
            elif value[0] == 1:
                result |= 1 #right
            elif value[1] == 1:
                result |= 8 #up
            elif value[1] == -1:
                result |= 4 #down
            b4 = self.joysticks[0].get_button(4)
            b5 = self.joysticks[0].get_button(5)
            if b4 or b5:
                result |= 16 #fire

        #Results were obtained by reading from port 0x7f in the form F---RLDU, with active bits low.
        elif self.type == FULLER: #port 0xeffe 6, 7, 8, 9, 0
            if value[0] == -1:
                result |= 4 #left
            elif value[0] == 1:
                result |= 8 #right
            elif value[1] == 1:
                result |= 1 #up
            elif value[1] == -1:
                result |= 2 #down
            b4 = self.joysticks[0].get_button(4)
            b5 = self.joysticks[0].get_button(5)
            if b4 or b5:
                result |= 128 #fire

        if self.type == FULLER:
            result = ~result & 0xff
        return result

    def info(self, name=0, axes=0, balls=0, hats=1, buttons=1, full=0):
        if full:
            name = axes = balls = hats = buttons = 1
        s = ""
        for joy in self.joysticks:
            if name:
                s += f"{joy.get_name()} id={joy.get_id()} instance_id={joy.get_instance_id()}"
            if axes:
                s += f"\n{joy.get_numaxes()} axes:\n"
                for i in range(joy.get_numaxes()):
                    s += f"{joy.get_axis(i)} "
            if balls:
                s += f"\n{joy.get_numballs()} trackballs:\n"
                for i in range(joy.get_numballs()):
                    s += f"{joy.get_ball(i)} "
            if hats:
                s += f"\n{joy.get_numhats()} hats:\n"
                for i in range(joy.get_numhats()):
                    s += f"{joy.get_hat(i)} "
            if buttons:
                s += f"\n{joy.get_numbuttons()} buttons:\n"
                for i in range(joy.get_numbuttons()):
                    s += f"{joy.get_button(i)} "
        return s

    def stop(self):
        pygame.joystick.quit()

    def log(self, text):
        log = open('./tmp/joystick.log', 'a')
        log.write(text)
        log.write("\n")
        log.close

