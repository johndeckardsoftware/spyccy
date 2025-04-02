import os
import json
from enum import Enum

TAPE_LOADERS_BY_MACHINE = {
    '48':  {'default': './support/tapeloaders/Load48.z80', 'usr0': './support/tapeloaders/tape_48.szx'},
    '128': {'default': './support/tapeloaders/tape_128.szx', 'usr0': './support/tapeloaders/tape_128_usr0.szx'}
}

class MACHINE(Enum):
    STOPPED = 0
    RUNNING = 1
    PAUSED = 2
    RESUMED = 3

class STYLE_TAG(Enum):
    TOKEN = "TOKEN"
    NUMBER = "NUMBER"
    STRING = "STRING"
    COMMENT = "COMMENT"

class Config(object):

    config = {}
    config_file = 'config.json'
    if os.path.exists(config_file):
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)

    machine = {} # selected machine configuration
    _vars = {}

    @staticmethod
    def set_machine(type='current', vars=None) -> str:
        if vars:
            Config.save(vars)
            Config._vars = vars

        active = ''
        if 'active' in Config.config:
            active = Config.config['active']
        else:
            active = '48a'
            Config.config['active'] = active
            Config.config[active] = {
                "machine": {
                    "type": "48a",
                    "auto_start": 0,
                    "status": "stop"
                }
            }

        if type == 'current':
            Config.machine = Config.config[active]
        elif type in Config.config:
            active = type
            Config.machine = Config.config[active]
            Config.config['active'] = active
        else:
            active = type
            Config.config['active'] = active
            Config.config[active] = {
                "machine": {
                    "type": active
                }
            }
            Config.machine = Config.config[active]

        # set vars for ui
        if vars:
            vars['machine.type'].set(Config.get('machine.type', '48a'))
            if active == '48a' or active == '48b':
                vars['machine.rom0'].set(Config.get('machine.rom0', './support/roms/48.rom'))
                vars['machine.rom1'].set('--')
            else:
                vars['machine.rom0'].set(Config.get('machine.rom0', './support/roms/128-0.rom'))  
                vars['machine.rom1'].set(Config.get('machine.rom1', './support/roms/128-1.rom'))  

            vars['machine.auto_start'].set(Config.get('machine.auto_start', 1))
            if Config.get('machine.auto_start', 0):
                vars['machine.status'].set('start')

            vars['machine.constrain'].set(Config.get('machine.constrain', 1))
            vars['machine.background'].set(Config.get('machine.background', 0))
            vars['tape.enabled'].set(Config.get('tape.enabled', True))
            vars['tape.auto_load'].set(Config.get('tape.auto_load', True))
            vars['tape.block'].set(Config.get('tape.block', -1))
            vars['tape.converter'].set(Config.get('tape.converter', 'basic'))
            vars['display.zoom'].set(Config.get('display.zoom', '2'))
            vars['display.renderer'].set(Config.get('display.renderer', 'tk'))
            vars['keyboard.type'].set(Config.get('keyboard.type', 'standard'))
            vars['joystick.enabled'].set(Config.get('joystick.enabled', 0))
            vars['joystick.type'].set(Config.get('joystick.type', 1))
            vars['joystick.left'].set(Config.get('joystick.left', 'Q'))
            vars['joystick.right'].set(Config.get('joystick.right', 'A'))
            vars['joystick.up'].set(Config.get('joystick.up', 'O'))
            vars['joystick.down'].set(Config.get('joystick.down', 'P'))
            vars['joystick.fire'].set(Config.get('joystick.fire', 'BREAK_SPACE'))
            vars['beeper.muted'].set(Config.get('beeper.muted', 0))
            vars['beeper.stereo'].set(Config.get('beeper.stereo', 1))
            vars['ay.muted'].set(Config.get('ay.muted', 0))
            vars['ay.a.muted'].set(Config.get('ay.a.muted', 0))
            vars['ay.b.muted'].set(Config.get('ay.b.muted', 0))
            vars['ay.c.muted'].set(Config.get('ay.c.muted', 0))
            vars['ay.stereo'].set(Config.get('ay.stereo', 1))
            vars['usource.enabled'].set(Config.get('usource.enabled', 0))
            vars['usource.rom'].set(Config.get('usource.rom', './support/roms/usource.rom'))
            vars['betadisk.enabled'].set(Config.get('betadisk.enabled', 0))
            vars['betadisk.rom'].set(Config.get('betadisk.rom', './support/roms/trdos.rom'))
            vars['cartridge.enabled'].set(Config.get('cartridge.enabled', 0))

        return active

    @staticmethod
    def get(key: str, _default: any) -> any:
        s = key.split('.')
        c = Config.machine
        r = True
        for k in s:
            if k in c:
                c = c[k]
            else:
                r = False
                break
        if r:
            return c
        else:
            return _default

    @staticmethod
    def set(key: str, value: any) -> any:
        s = key.split('.')
        c = Config.machine
        r = True
        for k in s:
            if k in c:
                pc = c
                c = c[k]
            else:
                c[k] = {}
                pc = c
                c = c[k]
        if r:
            pc[k] = value

        if key in Config._vars:
            Config._vars[key].set(value)

    @staticmethod
    def update(vars: dict):
        for var in vars:
            if var != 'machine.type':
                Config.set(var, vars[var].get())

    @staticmethod
    def save(vars: dict):
        for var in vars:
            if var != 'machine.type':
                Config.set(var, vars[var].get())
                #print(var, vars[var].get())

        with open(Config.config_file, "w", encoding="utf-8") as f:
            json.dump(Config.config, f, indent=2)