import tkinter as tk
from tkinter import Menu
from tkinter import messagebox
from tkinter import filedialog
import webbrowser
import string
import app_globals
from config import *
from editor import Editor
from args import Args
from tzxtools import tzxls, tzxcat
import basic2tape
import joystick
from ay_tuning import AYTuning

class StatusBar(tk.Frame):
    def __init__(self, master, color):
        tk.Frame.__init__(self, master, background = color)

        font = ('TkSmallCaptionFont', 8)

        self.machine = tk.Label(self, width=15, text='', fg='white', bg=color, anchor='w', relief="ridge", font=font)
        self.machine.pack(side=tk.LEFT, fill='none')
        self.status_var = tk.StringVar()
        self.status = tk.Label(self, width=9, text='', fg='white', bg=color, anchor='w', relief="ridge", font=font)
        self.status.pack(side=tk.LEFT, fill='none')
        self.tape = tk.Label(self, width=21, text='', fg='white', bg=color, anchor='w', relief="ridge", font=font)
        self.tape.pack(side=tk.LEFT, fill='none')
        self.diska = tk.Label(self, width=16, text='', fg='white', bg=color, anchor='w', relief="ridge", font=font)
        self.diska.pack(side=tk.LEFT, fill='none')
        self.diskb = tk.Label(self, width=16, text='', fg='white', bg=color, anchor='w', relief="ridge", font=font)
        self.diskb.pack(side=tk.LEFT, fill='none')
        self.lfps = tk.Label(self, width=3, text='fps:', fg='white', bg=color, anchor='w', relief="ridge", font=font)
        self.lfps.pack(side=tk.LEFT, fill='none')
        self.fps = tk.Label(self, width=6, text='', fg='white', bg=color, anchor='w', relief="ridge", font=font)
        self.fps.pack(side=tk.LEFT, fill='none')
        self.cpu_fps = tk.Label(self, width=6, text='', fg='white', bg=color, anchor='w', relief="ridge", font=font)
        self.cpu_fps.pack(side=tk.LEFT, fill='none')
        self.video_fps = tk.Label(self, width=6, text='', fg='white', bg=color, anchor='w', relief="ridge", font=font)
        self.video_fps.pack(side=tk.LEFT, fill='none')
        #self.tk_fps = tk.Label(self, width=6, text='', fg='white', bg=color, anchor='w', relief="ridge")
        #self.tk_fps.pack(side=tk.LEFT, fill='none')
        self.pack(fill=tk.X, side=tk.BOTTOM)

    def set_machine(self, text):
        self.machine.configure(text=text)

    def set_status(self, text):
        self.status.configure(text=text)
        self.status_var.set(text)

    def set_tape(self, text):
        self.tape.configure(text=text)

    def set_cpu_fps(self, text):
        self.cpu_fps.configure(text=text)

    def set_video_fps(self, text):
        self.video_fps.configure(text=text)

    def set_fps(self, text):
        self.fps.configure(text=text)

    def set_tk_fps(self, text):
        self.tk_fps.configure(text=text)

    def set_disk(self, drive, text):
        if drive == 0:
            self.diska.configure(text='A:'+text)
        elif drive == 1:
            self.diskb.configure(text='B:'+text)

    def set_diska(self, text):
        self.diska.configure(text=text)

    def set_diskb(self, text):
        self.diskb.configure(text=text)

class MainWindow():
    def __init__(self, emulator, root):
        self.emulator = emulator
        self.window = root
        self.status_bar = None

        # Create a dictionary to store Variable for each menu that require it
        self.vars = {}
        self.vars['machine.type'] = tk.StringVar()
        self.vars['machine.rom0'] = tk.StringVar()
        self.vars['machine.rom1'] = tk.StringVar()
        self.vars['machine.auto_start'] = tk.IntVar()
        self.vars['machine.status'] = tk.StringVar()
        self.vars['machine.constrain'] = tk.IntVar()
        self.vars['machine.background'] = tk.IntVar()
        self.vars['tape.enabled'] = tk.BooleanVar()
        self.vars['tape.auto_load'] = tk.BooleanVar()
        self.vars['tape.block'] = tk.IntVar()
        self.vars['tape.converter'] = tk.StringVar()
        self.vars['display.zoom'] = tk.IntVar()
        self.vars['display.renderer'] = tk.StringVar()
        self.vars['keyboard.type'] = tk.StringVar()
        self.vars['joystick.detected'] = tk.IntVar()
        self.vars['joystick.enabled'] = tk.IntVar()
        self.vars['joystick.type'] = tk.IntVar()
        self.vars['joystick.left'] = tk.StringVar()
        self.vars['joystick.right'] = tk.StringVar()
        self.vars['joystick.up'] = tk.StringVar()
        self.vars['joystick.down'] = tk.StringVar()
        self.vars['joystick.fire'] = tk.StringVar()
        self.vars['beeper.muted'] = tk.IntVar()
        self.vars['beeper.stereo'] = tk.IntVar()
        self.vars['beeper.mode'] = tk.StringVar()
        self.vars['ay.muted'] = tk.IntVar()
        self.vars['ay.a.muted'] = tk.IntVar()
        self.vars['ay.b.muted'] = tk.IntVar()
        self.vars['ay.c.muted'] = tk.IntVar()
        self.vars['ay.stereo'] = tk.IntVar()
        self.vars['usource.enabled'] = tk.IntVar()
        self.vars['usource.rom'] = tk.StringVar()
        self.vars['betadisk.enabled'] = tk.IntVar()
        self.vars['betadisk.rom'] = tk.StringVar()
        self.vars['cartridge.enabled'] = tk.IntVar()
        self.vars['cartridge.rom'] = tk.StringVar()

        self.active = Config.set_machine('current', vars=self.vars)

        self.title = Config.get('app.title', app_globals.APP_NAME)
        self.window.title(self.title)
        self.window.geometry(Config.get('app.window.geometry', '640x520'))
        self.window.configure(bg=Config.get('app.bg', 'black'))
        self.window.resizable(False, False)
        self.window.bind('<Configure>', self.configure_callback)

        self.window.iconphoto(False, app_globals.APP_ICON)

        self.editor = None
        self.info_tape_file = None
        self.loaded_tape_file = None
        self.info_tape_blocks = 0

        self.window.protocol('WM_DELETE_WINDOW', self.emulator.exit)
        #
        # user interface
        #
        # machine
        #
        menubar = Menu(self.window)

        machine_menu = tk.Menu(menubar, tearoff=0)
        machine_menu.add_radiobutton(label='48', variable=self.vars['machine.type'], value='48a',
                                      command=lambda: self.set_machine(type='48a', vars=self.vars))
        machine_menu.add_radiobutton(label='128', variable=self.vars['machine.type'], value='128',
                                      command=lambda: self.set_machine(type='128', vars=self.vars))
        machine_menu.add_separator()
        machine_menu.add_checkbutton(label='Auto start', onvalue=1, offvalue=0, variable=self.vars['machine.auto_start'])
        machine_menu.add_separator()
        machine_menu.add_radiobutton(label='Start', variable=self.vars['machine.status'], value='start', command=self.emulator.start)
        machine_menu.add_radiobutton(label='Pause', variable=self.vars['machine.status'], value='pause', command=self.emulator.pause)
        machine_menu.add_command(label='Resume', command=self.set_resume)
        machine_menu.add_command(label='Reset', command=self.emulator.reset)
        machine_menu.add_command(label='Restart', command=self.emulator.restart)
        machine_menu.add_radiobutton(label='Stop', variable=self.vars['machine.status'], value='stop', command=self.emulator.stop)
        machine_menu.add_separator()
        machine_menu.add_command(label='Load snapshot...', command=self.open_snapshot_dialog)
        machine_menu.add_command(label='Save snapshot...', command=self.save_snapshot_dialog)
        machine_menu.add_separator()
        machine_menu.add_command(label='Exit', command=self.emulator.exit)
        self.machine_menu = machine_menu
        menubar.add_cascade(label='Machine', menu=machine_menu, underline=0)

        #
        # tape
        #
        tape_menu = Menu(menubar, tearoff=0)
        tape_menu.add_checkbutton(label='Enabled', onvalue=True, offvalue=False, variable=self.vars['tape.enabled'],
                                  command=self.set_tape_entries)
        tape_menu.add_checkbutton(label='Auto Load', onvalue=True, offvalue=False, variable=self.vars['tape.auto_load'],
                                  command=lambda: self.emulator.set_tape_auto_load(self.vars['tape.enabled'].get()))
        tape_menu.add_separator()
        tape_menu.add_command(label='Load...', command=self.open_tape_dialog)
        tape_menu.add_command(label='Play', command=self.emulator.tape_play)
        tape_menu.add_command(label='Eject', command=self.tape_stop)
        tape_menu.add_command(label='Save', command=self.emulator.tape_save)
        tape_menu.add_separator()
        tape_menu.add_command(label='Tape info...', command=self.tape_info)
        tape_block = tk.Menu(tape_menu, tearoff=0)
        tape_block.add_radiobutton(label='All', variable=self.vars['tape.block'], value=-1)
        for x in range(self.info_tape_blocks):
            tape_block.add_radiobutton(label=str(x), variable=self.vars['tape.block'], value=x)
        self.tape_block = tape_block
        tape_conv = tk.Menu(tape_menu, tearoff=0)
        tape_conv.add_radiobutton(label='BASIC', variable=self.vars['tape.converter'], value='basic')
        tape_conv.add_radiobutton(label='Text', variable=self.vars['tape.converter'], value='text')
        tape_conv.add_radiobutton(label='Assembler', variable=self.vars['tape.converter'], value='assembler')
        tape_conv.add_radiobutton(label='Screen', variable=self.vars['tape.converter'], value='screen')
        tape_conv.add_radiobutton(label='Dump', variable=self.vars['tape.converter'], value='dump')
        tape_menu.add_cascade(label='Select block', menu=tape_block, underline=0)
        tape_menu.add_cascade(label='Select converter', menu=tape_conv, underline=0)
        tape_menu.add_command(label='Tape cat', command=self.tape_cat)
        tape_menu.add_separator()
        tape_menu.add_command(label='BASIC to tap...', command=self.basic_to_tape)
        self.tape_menu = tape_menu
        menubar.add_cascade(label='Tape', menu=tape_menu, underline=0)

        #
        # disk
        #
        disk_menu = Menu(menubar, tearoff=0)
        disk_menu.add_checkbutton(label='Enabled', onvalue=1, offvalue=0, variable=self.vars['betadisk.enabled'],
                                  command=self.set_disk_entries)
        disk_menu.add_command(label='Enter TR-DOS', command=lambda: self.emulator.key_sequence(0), state=self.disk_state())
        disk_menu.add_command(label='Back to SOS', command=lambda: self.emulator.key_sequence(1), state=self.disk_state())
        disk_menu.add_separator()
        diska_menu = tk.Menu(disk_menu, tearoff=0)
        diska_menu.add_command(label='Load disk', command=lambda: self.select_disk_dialog(0))
        diska_menu.add_command(label='Save disk', command=lambda: self.emulator.save_disk(0))
        diska_menu.add_command(label='Eject disk', command=lambda: self.emulator.eject_disk(0))
        diska_menu.add_command(label='Empty disk', command=lambda: self.emulator.load_disk(0, None))
        disk_menu.add_cascade(label='Drive A', menu=diska_menu, underline=0, state=self.disk_state())

        diskb_menu = tk.Menu(disk_menu, tearoff=0)
        diskb_menu.add_command(label='Load disk', command=lambda: self.select_disk_dialog(1))
        diskb_menu.add_command(label='Save disk', command=lambda: self.emulator.save_disk(1))
        diskb_menu.add_command(label='Eject disk', command=lambda: self.emulator.eject_disk(1))
        diskb_menu.add_command(label='Empty disk', command=lambda: self.emulator.load_disk(1, None))
        disk_menu.add_cascade(label='Drive B', menu=diskb_menu, state=self.disk_state())
        self.disk_menu = disk_menu
        menubar.add_cascade(label='Disk', menu=disk_menu, underline=0)

        #
        # display
        #
        display_menu = tk.Menu(menubar, tearoff=0)
        display_menu.add_radiobutton(label='Zoom x 1', variable=self.vars['display.zoom'], value=1,
                                      command=lambda: self.emulator.display_zoom(self.vars['display.zoom'].get()))
        display_menu.add_radiobutton(label='Zoom x 2', variable=self.vars['display.zoom'], value=2,
                                      command=lambda: self.emulator.display_zoom(self.vars['display.zoom'].get()))
        display_menu.add_separator()
        display_menu.add_radiobutton(label='Renderer: Tk canvas', variable=self.vars['display.renderer'], value='tk',
                                      command=self.set_display_renderer)
        display_menu.add_radiobutton(label='Renderer: pygame (Windows only)', variable=self.vars['display.renderer'], value='sdl',
                                      command=self.set_display_renderer)
        menubar.add_cascade(label='Display', menu=display_menu, underline=0)

        #
        # keyboard
        #
        keyboard_menu = tk.Menu(menubar, tearoff=0)
        keyboard_menu.add_radiobutton(label='Original', variable=self.vars['keyboard.type'], value='original',
                                       command=lambda: self.emulator.keyboard_type(self.vars['keyboard.type'].get()))
        keyboard_menu.add_radiobutton(label='Standard', variable=self.vars['keyboard.type'], value='standard',
                                       command=lambda: self.emulator.keyboard_type(self.vars['keyboard.type'].get()))
        keyboard_menu.add_radiobutton(label='Gamer', variable=self.vars['keyboard.type'], value='gamer',
                                       command=lambda: self.emulator.keyboard_type(self.vars['keyboard.type'].get()))
        keyboard_menu.add_command(label='Basic Token to Key', command=self.emulator.keyboard_help)
        keyboard_menu.add_command(label='Layout 48', command=lambda: self.layout48())
        menubar.add_cascade(label='Keyboard', menu=keyboard_menu, underline=0)

        #
        # joystick
        #
        joystick_menu = tk.Menu(menubar, tearoff=0)
        joystick_menu.add_checkbutton(label='Enabled', onvalue=1, offvalue=0, variable=self.vars['joystick.enabled'], command=self.set_joystick_entries)
        joystick_menu.add_separator()
        joystick_menu.add_radiobutton(label='Sinclair 1&2', variable=self.vars['joystick.type'], value=joystick.SINCLAIR,
                                       command=lambda: self.emulator.joystick_type(self.vars['joystick.type'].get()))
        joystick_menu.add_radiobutton(label='Sinclair 1 (left)', variable=self.vars['joystick.type'], value=joystick.SINCLAIR_LEFT,
                                       command=lambda: self.emulator.joystick_type(self.vars['joystick.type'].get()))
        joystick_menu.add_radiobutton(label='Sinclair 2 (right)', variable=self.vars['joystick.type'], value=joystick.SINCLAIR_RIGHT,
                                       command=lambda: self.emulator.joystick_type(self.vars['joystick.type'].get()))
        joystick_menu.add_radiobutton(label='Kempston', variable=self.vars['joystick.type'], value=joystick.KEMPSTON,
                                       command=lambda: self.emulator.joystick_type(self.vars['joystick.type'].get()))
        joystick_menu.add_radiobutton(label='Cursor', variable=self.vars['joystick.type'], value=joystick.CURSOR,
                                       command=lambda: self.emulator.joystick_type(self.vars['joystick.type'].get()))
        joystick_menu.add_radiobutton(label='Fuller', variable=self.vars['joystick.type'], value=joystick.FULLER,
                                       command=lambda: self.emulator.joystick_type(self.vars['joystick.type'].get()))
        joystick_menu.add_separator()
        joystick_menu.add_radiobutton(label='Programmable', variable=self.vars['joystick.type'], value=joystick.PROGRAMMABLE,
                                       command=lambda: self.emulator.joystick_type(self.vars['joystick.type'].get()))

        joyprog_conf = tk.Menu(joystick_menu, tearoff=0)
        joyprog_left = tk.Menu(joyprog_conf, tearoff=0)
        joyprog_left.add_radiobutton(label='space', variable=self.vars['joystick.left'], value=' ')
        for x in string.ascii_uppercase:
            joyprog_left.add_radiobutton(label=x, variable=self.vars['joystick.left'], value=x)

        joyprog_up = tk.Menu(joyprog_conf, tearoff=0)
        joyprog_up.add_radiobutton(label='space', variable=self.vars['joystick.up'], value=' ')
        for x in string.ascii_uppercase:
            joyprog_up.add_radiobutton(label=x, variable=self.vars['joystick.up'], value=x)

        joyprog_right = tk.Menu(joyprog_conf, tearoff=0)
        joyprog_right.add_radiobutton(label='space', variable=self.vars['joystick.right'], value=' ')
        for x in string.ascii_uppercase:
            joyprog_right.add_radiobutton(label=x, variable=self.vars['joystick.right'], value=x)

        joyprog_down = tk.Menu(joyprog_conf, tearoff=0)
        joyprog_down.add_radiobutton(label='space', variable=self.vars['joystick.down'], value=' ')
        for x in string.ascii_uppercase:
            joyprog_down.add_radiobutton(label=x, variable=self.vars['joystick.down'], value=x)

        joyprog_fire = tk.Menu(joyprog_conf, tearoff=0)
        joyprog_fire.add_radiobutton(label='space', variable=self.vars['joystick.fire'], value='BREAK_SPACE')
        for x in string.ascii_uppercase:
            joyprog_fire.add_radiobutton(label=x, variable=self.vars['joystick.fire'], value=x)

        joyprog_conf.add_cascade(label='Left', menu=joyprog_left, underline=0)
        joyprog_conf.add_cascade(label='Up', menu=joyprog_up, underline=0)
        joyprog_conf.add_cascade(label='Right', menu=joyprog_right, underline=0)
        joyprog_conf.add_cascade(label='Down', menu=joyprog_down, underline=0)
        joyprog_conf.add_cascade(label='Fire', menu=joyprog_fire, underline=0)
        joystick_menu.add_cascade(label='Configure', menu=joyprog_conf, underline=0)

        self.joystick_menu = joystick_menu
        menubar.add_cascade(label='Joystick', menu=joystick_menu, underline=0)

        #
        # sound
        #
        sound_menu = tk.Menu(menubar, tearoff=0)
        sound_menu.add_checkbutton(label='Beeper stereo', onvalue=1, offvalue=0, variable=self.vars['beeper.stereo'],
                                     command=lambda: self.emulator.set_sound(1, self.vars['beeper.stereo'].get()))
        sound_menu.add_checkbutton(label='Beeper muted', onvalue=1, offvalue=0, variable=self.vars['beeper.muted'],
                                     command=lambda: self.emulator.set_sound(0, self.vars['beeper.muted'].get()))
        sound_menu.add_separator()
        sound_menu.add_checkbutton(label='AY stereo', onvalue=1, offvalue=0, variable=self.vars['ay.stereo'],
                                     command=lambda: self.emulator.set_sound(32, self.vars['ay.stereo'].get()))
        sound_menu.add_checkbutton(label='AY muted', onvalue=1, offvalue=0, variable=self.vars['ay.muted'],
                                     command=lambda: self.emulator.set_sound(16, self.vars['ay.muted'].get()))
        sound_menu.add_command(label='AY Tuning', command=self.ay_tuning)
        self.sound_menu = sound_menu
        menubar.add_cascade(label='Sound', menu=sound_menu)

        #
        # options
        #
        options_menu = tk.Menu(menubar, tearoff=0)
        options_menu.add_command(label=self.label_menu_rom(0), command=lambda: self.select_rom_dialog(0))
        options_menu.add_command(label=self.label_menu_rom(1), command=lambda: self.select_rom_dialog(1))
        options_menu.add_separator()
        options_menu.add_checkbutton(label='µSource', onvalue=1, offvalue=0, variable=self.vars['usource.enabled'],
                                     command=lambda: self.emulator.usource_enable(self.vars['usource.enabled'].get()))
        options_menu.add_separator()
        cartridge_menu = tk.Menu(options_menu, tearoff=0)
        cartridge_menu.add_checkbutton(label='Enabled', onvalue=1, offvalue=0, variable=self.vars['cartridge.enabled'], command=self.set_cartridge_entries)

        cartridge_menu.add_command(label='Insert...', command=lambda: self.select_cartridge_dialog())
        cartridge_menu.add_command(label='Eject', command=lambda: self.eject_cartridge(), state=self.cartridge_state())
        self.cartridge_menu = cartridge_menu
        options_menu.add_cascade(label='Cartridge', menu=cartridge_menu, underline=0)

        options_menu.add_separator()
        options_menu.add_checkbutton(label="Constrain 50 fps", onvalue=1, offvalue=0, variable=self.vars['machine.constrain'], command=self.constrain_50_fps)

        options_menu.add_separator()
        options_menu.add_command(label="Editor", command=lambda: self.show_editor())

        options_menu.add_separator()
        options_menu.add_command(label="Save configuration", command=lambda: Config.save(self.vars))

        self.options_menu = options_menu
        menubar.add_cascade(label='Options', menu=options_menu)

        #
        # about
        #
        about_menu = Menu(menubar, tearoff=0)
        credits_menu = tk.Menu(about_menu, tearoff=0)
        credits_menu.add_command(label='fuse emulator', command=lambda: webbrowser.open('http://fuse-emulator.sourceforge.net/'))
        credits_menu.add_command(label='EightyOne Sinclair Emulator', command=lambda: webbrowser.open('https://sourceforge.net/projects/eightyone-sinclair-emulator/'))
        credits_menu.add_command(label='SoftSpectrum48', command=lambda: webbrowser.open('https://softspectrum48.weebly.com/'))
        credits_menu.add_command(label='PyZXSpectrum', command=lambda: webbrowser.open('https://github.com/folkertvanheusden/PyZXSpectrum'))
        credits_menu.add_command(label='tzxtools - a collection for processing tzx files', command=lambda: webbrowser.open('https://github.com/shred/tzxtools'))
        credits_menu.add_command(label='Russell Marks zmakebas.c', command=lambda: webbrowser.open('https://github.com/z00m128/zmakebas'))

        about_menu.add_cascade(label='Credits', menu=credits_menu, underline=0)

        info_menu = tk.Menu(about_menu, tearoff=0)
        info_menu.add_command(label='ZXSpectrum 48 User Manual', command=lambda: webbrowser.open('https://worldofspectrum.org/ZXBasicManual/'))
        info_menu.add_command(label='ZXSpectrum 128 User Manual', command=lambda: webbrowser.open('https://worldofspectrum.org/ZXSpectrum128Manual/'))
        info_menu.add_command(label='worldofspectrum.net', command=lambda: webbrowser.open('https://worldofspectrum.net/pub/sinclair/'))
        info_menu.add_command(label='spectrumcomputing', command=lambda: webbrowser.open('https://spectrumcomputing.co.uk/'))
        info_menu.add_command(label='SoftSpectrum48', command=lambda: webbrowser.open('https://softspectrum48.weebly.com/notes'))
        info_menu.add_command(label='prettybasic', command=lambda: webbrowser.open('https://github.com/reclaimed/prettybasic'))
        info_menu.add_command(label='z88dk', command=lambda: webbrowser.open('https://z88dk.org/site/'))

        about_menu.add_cascade(label='Documentation', menu=info_menu, underline=0)
        about_menu.add_separator()
        about_menu.add_command(label='speccy ver. 1.0')
        menubar.add_cascade(label='About', menu=about_menu, underline=0)

        menubar.bind('<<MenuSelect>>', self.update_menu)
        self.window.configure(menu=menubar)

        self.set_tape_entries()
        self.set_disk_entries()
        self.set_joystick_entries()
        #self.set_sound_entries()       # AY-8912 configured also for 48
        self.set_cartridge_entries()

        self.status_bar = StatusBar(self.window, 'blue')

    def set_machine(self, type, vars):
        Config.set_machine(type=type, vars=vars)

    def configure_callback(self, event):
        Config.set('app.window.geometry', f'640x520+{self.window.winfo_x()}+{self.window.winfo_y()}')

    def update_menu(self, event):
        Config.update(self.vars)
        self.options_menu.entryconfigure(0, label=self.label_menu_rom(0))
        self.options_menu.entryconfigure(1, label=self.label_menu_rom(1))

    def set_tape_entries(self):
        if self.status_bar:
            self.emulator.tape_enable(self.vars['tape.enabled'].get()) 
        self.tape_menu.entryconfigure('Load...', state=self.tape_state())
        self.tape_menu.entryconfigure('Play', state=self.tape_state())
        self.tape_menu.entryconfigure('Eject', state=self.tape_state())
        self.tape_menu.entryconfigure('Save', state=self.tape_state())

    def set_disk_entries(self):
        Config.save(self.vars)
        self.disk_menu.entryconfigure('Enter TR-DOS', state=self.disk_state())
        self.disk_menu.entryconfigure('Back to SOS', state=self.disk_state())
        self.disk_menu.entryconfigure('Drive B', state=self.disk_state())
        self.disk_menu.entryconfigure('Drive A', state=self.disk_state())

    def set_joystick_entries(self):
        #self.joystick_menu.entryconfigure('Enabled', state=self.joystick_detected())
        self.joystick_menu.entryconfigure('Sinclair 1&2', state=self.joystick_state())
        self.joystick_menu.entryconfigure('Sinclair 1 (left)', state=self.joystick_state())
        self.joystick_menu.entryconfigure('Sinclair 2 (right)', state=self.joystick_state())
        self.joystick_menu.entryconfigure('Kempston', state=self.joystick_state())
        self.joystick_menu.entryconfigure('Cursor', state=self.joystick_state())
        self.joystick_menu.entryconfigure('Fuller', state=self.joystick_state())
        self.joystick_menu.entryconfigure('Programmable', state=self.joystick_state())

    def set_sound_entries(self):
        self.sound_menu.entryconfigure('AY stereo', state=self.sound_state())
        self.sound_menu.entryconfigure('AY muted', state=self.sound_state())
        self.sound_menu.entryconfigure('AY Tuning', state=self.sound_state())

    def set_cartridge_entries(self):
        self.cartridge_menu.entryconfig('Insert...', state=self.cartridge_state())
        self.cartridge_menu.entryconfig('Eject', state=self.cartridge_state())

    def label_menu_rom(self, id):
        fn = self.vars[f'machine.rom{id}'].get()
        pf = os.path.split(fn)
        return f"rom{id}: {pf[1]}"

    def tape_state(self):
        return 'normal' if self.vars['tape.enabled'].get() else 'disabled'

    def disk_state(self):
        return 'normal' if self.vars['betadisk.enabled'].get() else 'disabled'

    def cartridge_state(self):
        return 'normal' if self.vars['cartridge.enabled'].get() else 'disabled'

    def joystick_detected(self):
        return 'normal' if self.vars['joystick.detected'].get() else 'disabled'

    def joystick_state(self):
        return 'normal' if self.vars['joystick.detected'].get() and self.vars['joystick.enabled'].get() else 'disabled'

    def sound_state(self):
        return 'normal' if self.vars['machine.type'].get() == "128" else 'disabled'

    def show_editor(self, file=None, text=None):
        if self.editor:
            if file:
                self.editor.open_file(file_dir=file)
            elif text:
                self.editor.open_text(text=text)
        else:
            child_window = tk.Toplevel(self.window)
            self.editor = Editor(child_window, self, file, text)
        self.editor.frame.focus_force()

    def open_tape_dialog(self):
        if not self.vars['tape.enabled'].get(): return
        file_path = filedialog.askopenfilename(title='Select a file', filetypes=[('Tape', '*.tap'), ('Tape', '*.tzx'), ('All files', '*.*')])
        if file_path:
            self.loaded_tape_file = file_path
            self.emulator.tape_load(file_path)

    def tape_stop(self):
        if not self.vars['tape.enabled'].get(): return
        self.loaded_tape_file = None
        self.emulator.tape_stop()

    def tape_info(self):
        file_path = filedialog.askopenfilename(title='Select a tape', filetypes=[('Tape', '*.tap'), ('Tape', '*.tzx'), ('All files', '*.*')])
        if file_path:
            self.info_tape_file = file_path
            args = Args()
            setattr(args, 'file', [file_path])
            info, num_blocks = tzxls.main(args)
            x = self.info_tape_blocks
            while x > 0:
                self.tape_block.delete(x)
                x -= 1
            self.info_tape_blocks = num_blocks
            for x in range(self.info_tape_blocks):
                self.tape_block.add_radiobutton(label=str(x), variable=self.vars['tape.block'], value=x)
            self.show_editor(text=info)

    def tape_cat(self):
        if self.info_tape_file:
            file_path = self.info_tape_file
        elif self.loaded_tape_file:
            file_path = self.loaded_tape_file
        else:
            file_path = filedialog.askopenfilename(title='Select a tape', filetypes=[('Tape', '*.tap'), ('Tape', '*.tzx'), ('All files', '*.*')])
        if file_path:
            args = Args()
            setattr(args, 'file', file_path)
            setattr(args, self.vars['tape.converter'].get(), self.vars['tape.converter'].get())
            if self.vars['tape.block'].get() != -1:
                setattr(args, 'block', self.vars['tape.block'].get())
            info = tzxcat.main(args)

            self.show_editor(text=info)

    def basic_to_tape(self):
        file_path = filedialog.askopenfilename(title='Select a file', filetypes=[('Basic', '*.bas'), ('All files', '*.*')])
        if file_path:
            #basic2tape.zmakebas(file_path, file_path+'.tap', "./tmp/zmakebas.log")
            basic2tape.zmakebas(file_path, file_path+'.tap', None)

    def open_snapshot_dialog(self):
        file_path = filedialog.askopenfilename(title='Select a file', filetypes=[('Snapshot', '*.z80 *.szx *.sna'), ('All files', '*.*')])
        if file_path:
            self.emulator.process_snapshot(file_path)

    def save_snapshot_dialog(self):
        file_path = filedialog.asksaveasfilename(title='Select a file', filetypes=[('Snapshot', '*.z80'), ('All files', '*.*')])
        if file_path:
            if not file_path.endswith(".z80"):
                file_path = file_path + ".z80"
            self.emulator.save_snapshot(file_path)

    def select_rom_dialog(self, id):
        file_path = filedialog.askopenfilename(title='Select a file', filetypes=[('ROM', '*.rom *.bin'), ('All files', '*.*')])
        if file_path:
            self.vars[f'machine.rom{id}'].set(file_path)
            self.options_menu.entryconfigure(id+2, label=self.label_menu_rom(id))

    def select_cartridge_dialog(self):
        file_path = filedialog.askopenfilename(title='Select a cartridge file', filetypes=[('ROM', '*.rom *.bin'), ('All files', '*.*')])
        if file_path:
            self.vars['cartridge.rom'].set(file_path)
            Config.update(self.vars)
            self.emulator.insert_cartridge()

    def eject_cartridge(self):
        self.vars['cartridge.rom'].set('')
        Config.update(self.vars)
        self.emulator.eject_cartridge()

    def select_disk_dialog(self, drive):
        file_path = filedialog.askopenfilename(title='Select a Disk', filetypes=[('Floppy Disk', '*.trd *.scl'), ('All files', '*.*')])
        if file_path:
            ret = self.emulator.load_disk(drive, file_path)
            if ret:
                pf = os.path.split(file_path)
                self.status_bar.set_disk(drive, pf[1])
            else:
                self.status_bar.set_disk(drive, '')

    def on_radio_select(self, submenu_name):
        selected_option = self.vars[submenu_name].get()
        print(f'{submenu_name}: Selected option - {selected_option}')

    def set_display_renderer(self):
        r = self.vars['display.renderer'].get()
        if r == 'sdl':
            self.vars['machine.auto_start'].set(0)
            Config.update(self.vars)
        pass

    def set_resume(self):
        self.vars['machine.status'].set('start')
        self.emulator.resume()

    def layout48(self):
        self.image_window = ImageWindow(tk.Toplevel(self.window), self, "./support/zx48keyboard.png", "ZXSpectrum 48 keyboard layout")

    def constrain_50_fps(self):
        if self.emulator.machine:
            self.emulator.machine.constrain_50_fps = self.vars['machine.constrain']

    def ay_tuning(self):
        if self.emulator.machine and self.emulator.machine.AY:
            self.ay_tuning_window = AYTuning(tk.Toplevel(self.window), self.emulator.machine)

    def msgbox(self, text):
        messagebox.showerror(self.title, text)

class ImageWindow():

    def __init__(self, top_level, parent, file, title):
        self.master = top_level
        self.master.title(title)
        self.master.geometry(Config.get('app.image.geometry', '804x507'))
        self.master.configure(bg='black')
        self.parent = parent
        self.img = tk.PhotoImage(file=file)
        self.label = tk.Label(top_level, image=self.img, width=self.img.width(), height=self.img.height(), bg='black')
        self.label.pack()
        self.master.bind('<Configure>', self.configure_callback)
        self.master.iconphoto(False, app_globals.APP_ICON)

    def configure_callback(self, event):
        Config.set('app.image.geometry', self.master.geometry())