import tkinter as tk
from tkinter import ttk
import app_globals
from config import Config

# https://tkdocs.com/tutorial/grid.html
# https://coderslegacy.com/python/list-of-tkinter-widgets/
class AYTuningEmu():
    def __init__(self, parent, machine):
        self.window = parent
        self.machine = machine
        self.controller = machine.AY
        self.window.title('SPYCCY - AY Tuning emu')
        self.window.geometry(Config.get('app.ay_emu_tuning.geometry', '313x325'))
        #self.window.resizable(False, False)
        self.window.bind('<Configure>', self.configure_callback)
        self.window.iconphoto(False, app_globals.APP_ICON)

        self.var_fps = tk.IntVar()
        self.var_list_abc = tk.StringVar()
        self.var_channel = tk.IntVar()
        self.var_a_mute = tk.IntVar()
        self.var_b_mute = tk.IntVar()
        self.var_c_mute = tk.IntVar()
        self.var_lvolume = [tk.DoubleVar(), tk.DoubleVar(), tk.DoubleVar()]
        self.var_rvolume = [tk.DoubleVar(), tk.DoubleVar(), tk.DoubleVar()]

        self.var_ay_freq = tk.IntVar()
        self.var_ay_freq = [tk.IntVar(), tk.IntVar(), tk.IntVar()]
        self.var_freq_adj = [tk.IntVar(), tk.IntVar(), tk.IntVar()]
        self.var_play_int = [tk.IntVar(), tk.IntVar(), tk.IntVar()]

        #self.AY_clock_frequency = self.controller.AY_clock_frequency

        self.chaname = ['a', 'b', 'c']
        self.chanord = [0, 1, 2]
        self.channel = 0
        self.channels = self.controller.channels

        self.frame = tk.Frame(self.window, width=680, height=320)
        font = ('TkSmallCaptionFont', 8)

        panel1 = tk.LabelFrame(self.frame, text="Controller:")
        self.panel1 = panel1

        self.var_fps.set(self.controller.audio_fps)
        self.lbl_fps = tk.Label(panel1, text='fps samples:')
        self.scale_fps = tk.Scale(panel1, from_=10, to=100, length=200, orient=tk.HORIZONTAL, variable=self.var_fps, font=font,
                                   command=self.update_fps, tickinterval=20)
        self.lbl_list_abc = tk.Label(panel1, text='Channel Order')
        self.list_abc = ["Mono", "ABC", "ACB", "BAC", "BCA", "CAB", "CBA"]
        self.var_list_abc.set(self.list_abc[self.controller.audio_abc_index])
        self.cb_list_abc = ttk.Combobox(panel1, values=self.list_abc, textvariable=self.var_list_abc)
        self.cb_list_abc.bind('<<ComboboxSelected>>', self.update_list_abc)

        self.var_a_mute.set(self.channels[0]['muted'])
        self.ck_a_mute = ttk.Checkbutton(panel1, text="Mute A", variable=self.var_a_mute, onvalue=1, offvalue=0, command=self.mute_a)
        self.var_b_mute.set(self.channels[1]['muted'])
        self.ck_b_mute = ttk.Checkbutton(panel1, text="Mute B", variable=self.var_b_mute, onvalue=1, offvalue=0, command=self.mute_b)
        self.var_c_mute.set(self.channels[2]['muted'])
        self.ck_c_mute = ttk.Checkbutton(panel1, text="Mute C", variable=self.var_c_mute, onvalue=1, offvalue=0, command=self.mute_c)

        self.rb_chan_a = ttk.Radiobutton(panel1, text="Channel A", variable=self.var_channel, value=0, command=self.select_abc)
        self.rb_chan_b = ttk.Radiobutton(panel1, text="Channel B", variable=self.var_channel, value=1, command=self.select_abc)
        self.rb_chan_c = ttk.Radiobutton(panel1, text="Channel C", variable=self.var_channel, value=2, command=self.select_abc)

        panel2 = tk.LabelFrame(self.frame, text="Channel")
        self.panel2 = panel2

        self.lbl_lvolume = tk.Label(panel2, text='Left Volume:')
        self.var_c_mute.set(self.channels[self.channel]['lvolume'])
        self.scale_lvolume = tk.Scale(panel2, from_=0, to=15, resolution=1, length=200, orient=tk.HORIZONTAL, font=font,
                                        variable=self.var_lvolume[self.channel], command=self.update_lvolume, tickinterval=2)

        self.lbl_rvolume = tk.Label(panel2, text='Right Volume:')
        self.var_c_mute.set(self.channels[self.channel]['rvolume'])
        self.scale_rvolume = tk.Scale(panel2, from_=0, to=15, resolution=1, length=200, orient=tk.HORIZONTAL, font=font,
                                        variable=self.var_rvolume[self.channel], command=self.update_rvolume, tickinterval=2)


        row = 0
        self.frame.grid(column=0, row=0)
        self.panel1.grid(column=0, row=0, padx=5, pady=5)
        self.panel2.grid(column=0, row=1, padx=5, pady=5)

        self.lbl_fps.mygrid(0, row)
        self.scale_fps.mygrid(1, row, columnspan=3)
        row += 1

        self.lbl_list_abc.mygrid(0, row)
        self.cb_list_abc.mygrid(1, row, columnspan=2)
        row += 1

        self.ck_a_mute.mygrid(0, row)
        self.ck_b_mute.mygrid(1, row)
        self.ck_c_mute.mygrid(2, row)
        row += 1

        self.rb_chan_a.mygrid(0, row)
        self.rb_chan_b.mygrid(1, row)
        self.rb_chan_c.mygrid(2, row)
        row += 1

        self.lbl_lvolume.mygrid(0, row)
        self.scale_lvolume.mygrid(1, row, columnspan=4)
        row += 1

        self.lbl_rvolume.mygrid(0, row)
        self.scale_rvolume.mygrid(1, row, columnspan=4)
        row += 1

        self.select_abc()

    def cname(self):
        return self.chaname[self.channel]

    def select_abc(self):
        self.channel = self.var_channel.get()
        name = f"Channel {self.chaname[self.channel].upper()}"
        self.panel2.configure(text=name)
        self.scale_lvolume.set(self.channels[self.channel]['lvolume'])
        self.scale_rvolume.set(self.channels[self.channel]['rvolume'])
        self.var_a_mute.set(self.channels[0]['muted'])
        self.var_b_mute.set(self.channels[1]['muted'])
        self.var_c_mute.set(self.channels[2]['muted'])

    def configure_callback(self, event):
        Config.set('app.ay_emu_tuning.geometry', self.window.geometry())

    def update_list_abc(self, event):
        abc = self.cb_list_abc.get()
        i = self.list_abc.index(abc)
        self.controller.set_abc_order(i)
        Config.set('ay.c.abc', i)

    def update_lvolume(self, val):
        self.channels[self.channel]['lvolume'] = self.scale_lvolume.get()
        Config.set(f'ay.c.{self.cname()}.lvolume', self.scale_lvolume.get())

    def update_rvolume(self, val):
        self.channels[self.channel]['rvolume'] = self.scale_rvolume.get()
        Config.set(f'ay.c.{self.cname()}.rvolume', self.scale_rvolume.get())

    def update_fps(self, val):
        self.controller.audio_fps = self.scale_fps.get()
        self.controller.set_audio_buffers()
        Config.set(f'ay.c.fps', self.scale_fps.get())

    def mute_a(self):
        print(f"a muted: {self.var_a_mute.get()}")
        self.channels[0]['muted'] = self.var_a_mute.get()
        Config.set(f'ay.c.a.muted', self.var_a_mute.get())

    def mute_b(self):
        print(f"b muted: {self.var_a_mute.get()}")
        self.channels[1]['muted'] = self.var_b_mute.get()
        Config.set(f'ay.c.b.muted', self.var_b_mute.get())

    def mute_c(self):
        print(f"c muted: {self.var_a_mute.get()}")
        self.channels[2]['muted'] = self.var_c_mute.get()
        Config.set(f'ay.c.c.muted', self.var_c_mute.get())

def mygrid(self, column, row, padx=(2,2), pady=(2,2), sticky="w", **kw):
    self.grid(row=row, column=column, padx=padx, pady=pady, sticky=sticky, **kw)

setattr(tk.Widget, 'mygrid', mygrid)

def main():
    root = tk.Tk()
    AYTuningEmu(root, None)
    root.mainloop()
