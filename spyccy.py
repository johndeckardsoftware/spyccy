# coding=utf-8
#
# spyccy - zxspectrum 48/128 emulator
#
# Copyright (C) 2025 John Deckard
#   https://github.com/johndeckardsoftware
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import asyncio
import threading
import tkinter as tk
import app_globals
from config import *
from ui import MainWindow
from zxs48a import ZXSpectrum48a
from zxs128a import ZXSpectrum128a
import z80profile2


class Emulator(tk.Frame):
    def __init__(self, root=None):
        super().__init__()
        self.tk_root = root
        self.window = MainWindow(self, root)
        self.thread = None
        self.machine = None

    def start(self):
        mt = Config.get('machine.type', '48a')
        if mt == '48a':
            self.machine = ZXSpectrum48a(self.tk_root, self.window)
        else:
            self.machine = ZXSpectrum128a(self.tk_root, self.window)
        self.thread = threading.Thread(target=asyncio.run, args=[self.machine.main_runner()], daemon=True)
        self.thread.start()
        self.window.status_bar.set_status('running')

    def stop(self):
        if self.machine and self.machine.status != MACHINE.STOPPED:
            # uncomment to enable profile
            #z80profile2.save()
            #z80profile2.clear()
            self.window.status_bar.set_status('stopping...')
            self.tk_root.update()
            self.machine.stop()
            self.thread.join(2)
            self.thread = None
            self.machine = None
            self.window.status_bar.set_status('stopped')
            self.window.status_bar.set_tape('')
            self.window.status_bar.set_diska('')
            self.window.status_bar.set_diskb('')
            self.window.status_bar.set_cpu_fps('')
            self.window.status_bar.set_video_fps('')

    def pause(self, wait_eof=False):
        #z80profile2.save()
        if self.machine:
            self.machine.pause(wait_eof)
            self.window.status_bar.set_status('paused')

    def resume(self):
        if self.machine:
            self.machine.resume()
            self.window.status_bar.set_status('resumed')

    def reset(self):
        if self.machine:
            return self.machine.reset(pc=0)

    def restart(self):
        self.stop()
        self.start()

    def exit(self):
        Config.save(self.window.vars)
        self.stop()
        self.tk_root.quit()

    def load_disk(self, drive, filename):
        if self.machine:
            return self.machine.load_disk(drive, filename)

    def save_disk(self, drive, filename=None):
        if self.machine:
            return self.machine.save_disk(drive, filename)

    def eject_disk(self, drive):
        if self.machine:
            ret = self.machine.eject_disk(drive)
            if ret: self.window.status_bar.set_disk(drive, '')
            return ret

    def usource_enable(self, val):
        if self.machine:
            self.machine.usource_enable(val)

    def insert_cartridge(self):
        self.pause(wait_eof=True)
        self.restart()

    def eject_cartridge(self):
        if self.machine:
            self.machine.eject_cartridge()

    def tape_enable(self, val):
        if self.machine:
            self.machine.tapedeck.set_traps(val)

    def set_tape_auto_load(self, val):
        if self.machine:
            self.machine.tapedeck.auto_load = val

    def tape_load(self, file):
        if self.machine:
            if self.machine.tapedeck.load(file):
                self.machine.tapedeck.play()

    def tape_play(self):
        if self.machine:
            self.machine.tapedeck.play()

    def tape_stop(self):
        if self.machine:
            self.machine.tapedeck.stop()
            self.window.status_bar.set_tape('')

    def tape_save(self):
        if self.machine:
            self.machine.tapedeck.save()

    def process_snapshot(self, file):
        if self.machine:
            self.machine.process_snapshot(file)

    def save_snapshot(self, file):
        if self.machine:
            self.machine.save_snapshot(file)

    def display_zoom(self, zoom):
        if self.machine:
            self.machine.set_zoom(zoom)

    def keyboard_type(self, type):
        if self.machine:
            self.machine.keyboard_type(type)

    def key_sequence(self, key_sequence_id):
        if self.machine:
            self.machine.key_sequence(key_sequence_id)

    def keyboard_help(self):
        if self.machine:
            self.machine.keyboard_help()

    def set_sound(self, what, val):
        if self.machine:
            self.machine.set_sound(what, val)

    def joystick_type(self, type):
        if self.machine:
            self.machine.joystick_type(type)

#
# main
#
if not os.path.isdir('./tmp'):
    os.mkdir('./tmp')

root = tk.Tk()
print(f"{tk.TkVersion=}, {tk.TclVersion=}")
app_globals.APP_ICON = tk.PhotoImage(file='./support/icon.png')
emulator = Emulator(root)

if Config.get('machine.auto_start', True):
    emulator.start()

root.mainloop()
