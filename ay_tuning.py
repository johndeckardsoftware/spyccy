import tkinter as tk
from tkinter import ttk
import app_globals
from config import Config

# https://tkdocs.com/tutorial/grid.html
# https://coderslegacy.com/python/list-of-tkinter-widgets/
class AYTuning():
    def __init__(self, parent, machine):
        self.window = parent
        self.machine = machine
        self.controller = self.machine.AY
        self.window.title('SPYCCY - AY Tuning')
        self.window.geometry(Config.get('app.aytuning.geometry', '555x480'))
        #self.window.resizable(False, False)
        self.window.bind('<Configure>', self.configure_callback)
        self.window.iconphoto(False, app_globals.APP_ICON)

        self.var_channel = tk.IntVar()
        self.var_a_mute = tk.IntVar()
        self.var_b_mute = tk.IntVar()
        self.var_c_mute = tk.IntVar()
        self.var_ay_freq = tk.IntVar()
        self.var_abc_ord = tk.StringVar()
        self.var_lvolume = [tk.DoubleVar(), tk.DoubleVar(), tk.DoubleVar()]
        self.var_rvolume = [tk.DoubleVar(), tk.DoubleVar(), tk.DoubleVar()]
        self.var_ay_freq = [tk.IntVar(), tk.IntVar(), tk.IntVar()]
        self.var_freq_adj = [tk.IntVar(), tk.IntVar(), tk.IntVar()]
        self.var_play_int = [tk.IntVar(), tk.IntVar(), tk.IntVar()]
        self.var_fps = [tk.IntVar(), tk.IntVar(), tk.IntVar()]

        self.AY_clock_frequency = self.controller.AY_clock_frequency

        self.chaname = ['a', 'b', 'c']
        self.chanord = [0, 1, 2]
        self.channel = 0
        self.channels = self.controller.channels

        self.frame = tk.Frame(self.window, width=680, height=320)
        font = ('TkSmallCaptionFont', 8)

        panel1 = tk.LabelFrame(self.frame, text="Controller:")
        self.panel1 = panel1

        self.lbl_abc_ord = tk.Label(panel1, text='Channel Order')
        self.abc_ord = ["ABC", "BAC", "BCA", "ACB", "CAB", "CBA"]
        self.cb_abc_ord = ttk.Combobox(panel1, values=self.abc_ord, textvariable=self.var_abc_ord)
        self.cb_abc_ord.bind('<<ComboboxSelected>>', self.update_abc_ord)
        abc = self.get_ord()
        self.cb_abc_ord.set(abc)

        self.ck_a_mute = ttk.Checkbutton(panel1, text="Mute A", variable=self.var_a_mute, onvalue=1, offvalue=0, command=self.mute_a)
        self.ck_b_mute = ttk.Checkbutton(panel1, text="Mute B", variable=self.var_b_mute, onvalue=1, offvalue=0, command=self.mute_b)
        self.ck_c_mute = ttk.Checkbutton(panel1, text="Mute C", variable=self.var_c_mute, onvalue=1, offvalue=0, command=self.mute_c)

        self.rb_chan_a = ttk.Radiobutton(panel1, text="Channel A", variable=self.var_channel, value=0, command=self.select_abc)
        self.rb_chan_b = ttk.Radiobutton(panel1, text="Channel B", variable=self.var_channel, value=1, command=self.select_abc)
        self.rb_chan_c = ttk.Radiobutton(panel1, text="Channel C", variable=self.var_channel, value=2, command=self.select_abc)

        panel2 = tk.LabelFrame(self.frame, text="Channel")
        self.panel2 = panel2

        self.lbl_lvolume = tk.Label(panel2, text='Left Volume:')
        self.scale_lvolume = tk.Scale(panel2, from_=0.0, to=1.0, resolution=0.05, length=400, orient=tk.HORIZONTAL, font=font,
                                        variable=self.var_lvolume[self.channel], command=self.update_lvolume, tickinterval=0.2)

        self.lbl_rvolume = tk.Label(panel2, text='Right Volume:')
        self.scale_rvolume = tk.Scale(panel2, from_=0.0, to=1.0, resolution=0.05, length=400, orient=tk.HORIZONTAL, font=font,
                                        variable=self.var_rvolume[self.channel], command=self.update_rvolume, tickinterval=0.2)

        self.lbl_ay_freq = tk.Label(panel2, text='AY frequency:')
        #self.scale_freq = tk.Scale(panel1, from_=-100, to=100, length=400, orient=tk.HORIZONTAL, variable=self.var_freq, command=self.update_freq)
        self.scale_ay_freq = tk.Scale(panel2, from_=1000000, to=2000000, resolution=10000, length=400, orient=tk.HORIZONTAL, variable=self.var_ay_freq[self.channel],
                                    command=self.update_ay_freq, font=font)

        self.lbl_freq_adj = tk.Label(panel2, text='AY frequency adjuster:')
        self.scale_freq_adj = tk.Scale(panel2, from_=1, to=100, length=400, orient=tk.HORIZONTAL, font=font,
                                        variable=self.var_freq_adj[self.channel], command=self.update_freq_adj, tickinterval=99)

        self.lbl_play_int = tk.Label(panel2, text='Play every cpu frame:')
        self.scale_play_frame = tk.Scale(panel2, from_=1, to=50, orient=tk.HORIZONTAL, variable=self.var_play_int[self.channel], font=font,
                                        command=self.update_play_frame, tickinterval=49)

        self.lbl_fps = tk.Label(panel2, text='t samples:')
        self.scale_t_samples = tk.Scale(panel2, from_=1, to=120, length=200, orient=tk.HORIZONTAL, variable=self.var_fps[self.channel], font=font,
                                   command=self.update_t_samples, tickinterval=119)

        row = 0
        self.frame.grid(column=0, row=0)
        self.panel1.grid(column=0, row=0, padx=5, pady=5)
        self.panel2.grid(column=0, row=1, padx=5, pady=5)

        self.lbl_abc_ord.mygrid(0, row)
        self.cb_abc_ord.mygrid(1, row, columnspan=2)
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

        self.lbl_ay_freq.mygrid(0, row)
        self.scale_ay_freq.mygrid(1, row, columnspan=4)
        row += 1

        self.lbl_freq_adj.mygrid(0, row)
        self.scale_freq_adj.mygrid(1, row, columnspan=4)
        row += 1

        self.lbl_play_int.mygrid(0, row)
        self.scale_play_frame.mygrid(1, row, columnspan=4)
        row += 1

        self.lbl_fps.mygrid(0, row)
        self.scale_t_samples.mygrid(1, row, columnspan=4)
        row += 1

        self.select_abc()

    def select_abc(self):
        self.channel = self.var_channel.get()
        name = f"Channel {self.chaname[self.channel].upper()}"
        self.panel2.configure(text=name)
        self.scale_lvolume.set(self.channels[self.channel].left_volume)
        self.scale_rvolume.set(self.channels[self.channel].right_volume)
        self.scale_ay_freq.set(self.channels[self.channel].AY_clock_frequency)
        self.scale_freq_adj.set(self.channels[self.channel].frequency_adjuster)
        self.scale_play_frame.set(self.controller.play_frame)
        self.scale_t_samples.set(self.channels[self.channel].wave_tstate_samples)
        self.var_a_mute.set(self.channels[0].muted)
        self.var_b_mute.set(self.channels[1].muted)
        self.var_c_mute.set(self.channels[2].muted)

    def configure_callback(self, event):
        Config.set('app.aytuning.geometry', self.window.geometry())

    def get_ord(self):
        abc = self.chaname[Config.get('ay.py.a.ord', 0)] + self.chaname[Config.get('ay.py.b.ord', 1)] + self.chaname[Config.get('ay.py.c.ord', 2)]
        return abc.upper()

    def update_abc_ord(self, event):
        abc = self.cb_abc_ord.get()
        i = 0
        for x in abc:
            key = f"ay.py.{x}.ord".lower()
            Config.set(key, i)
            i += 1
        abc = [' ', ' ', ' ']
        i = Config.get('ay.py.a.ord', 0)
        abc[i] = 'A'
        i = Config.get('ay.py.b.ord', 1)
        abc[i] = 'B'
        i = Config.get('ay.py.c.ord', 2)
        abc[i] = 'C'

    def update_lvolume(self, val):
        self.channels[self.channel].left_volume = self.scale_lvolume.get()
        Config.set(f'ay.py.{self.chaname[self.channel]}.lvolume', self.scale_lvolume.get())

    def update_rvolume(self, val):
        self.channels[self.channel].right_volume = self.scale_rvolume.get()
        Config.set(f'ay.py.{self.chaname[self.channel]}.rvolume', self.scale_rvolume.get())

    def update_ay_freq(self, val):
        #self.controller.AY_clock_frequency = self.AY_clock_frequency + (self.scale_freq.get() * 10000)
        self.channels[self.channel].AY_clock_frequency = self.scale_ay_freq.get()

    def update_freq_adj(self, val):
        self.channels[self.channel].frequency_adjuster = self.scale_freq_adj.get()

    def update_play_frame(self, val):
        self.controller.play_frame = self.scale_play_frame.get()

    def update_t_samples(self, val):
        self.channels[self.channel].wave_tstate_samples = self.scale_t_samples.get()

    def mute_a(self):
        print(self.var_a_mute.get())
        self.channels[0].mute(self.var_a_mute.get())
        Config.set(f'ay.py.a.muted', self.var_a_mute.get())

    def mute_b(self):
        self.channels[1].mute(self.var_b_mute.get())
        Config.set(f'ay.py.b.muted', self.var_b_mute.get())

    def mute_c(self):
        self.channels[2].mute(self.var_c_mute.get())
        Config.set(f'ay.py.c.muted', self.var_c_mute.get())

def mygrid(self, column, row, padx=(2,2), pady=(2,2), sticky="w", **kw):
    self.grid(row=row, column=column, padx=padx, pady=pady, sticky=sticky, **kw)

setattr(tk.Widget, 'mygrid', mygrid)

def main():
    root = tk.Tk()
    AYTuning(root, None)
    root.mainloop()
