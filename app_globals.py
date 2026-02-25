#
# globals vars
#
APP_NAME = "SPYCCY - ZXSpectrum emulator"
APP_ICON = None
TAPE_PLAYING = [" ●", "  "]
border_color = 7            # white
floating_bus_value = 0xff
frames_count = 0
frame_fps = 0.0
cpu_fps = 0.0
video_fps = 0.0
tk_fps = 0.0

import os, platform
try:
    from cffi import FFI
    _os_ = platform.system().lower()
    arch = platform.machine().lower()
    #
    lib_ay_emu = os.path.join(os.path.dirname(__file__), f"ay_emu_{_os_}_{arch}.lib")
    if os.path.exists(lib_ay_emu):
        pass
    else:
        print(f"'{lib_ay_emu}' not found, AY audio optimizations disabled")
        lib_ay_emu = None
    #
    lib_displayc = os.path.join(os.path.dirname(__file__), f"displayc_{_os_}_{arch}.lib")
    if os.path.exists(lib_displayc):
        pass
    else:
        print(f"'{lib_displayc}' not found, screen optimizations disabled")
        lib_displayc = None
except:
    lib_ay_emu = None
    lib_displayc = None
    print(f"'cffi' module not found, audio optimizations disabled")
