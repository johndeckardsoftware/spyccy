# SPYCCY

Just another ZXSpectrum emulator completely written in Python.

## Features

* Emulates the Spectrum 48K and 128K machines
* Handles all Z80 instructions, documented and undocumented
* Beeper and AY-8912 chip audio
* Loads SZX, Z80 and SNA snapshots
* Save Z80 snapshots
* Loads TZX and TAP tape images
* Save TAP tape images
* Run BASIC programs edited from spyccy editor (manages zmakebas syntax) 
* TR-DOS rom extension
* Read and write Floppy TRD and SCL format
* Original and Standard keyboard
* Joystick (Sinclair, Kempston, Programmable, Cursor, Fuller)
* Currah µSource rom extension
* Sinclair Zx2 interface cartridge

## Requirements

All the code is written in Python.

required libraries:

* tkinter   ("pip install" tk or "apt-get install python3-tk")
* pygame    ("pip install pygame" or "apt-get install python3-pygame")
* cffi      ("pip install cffi" or "apt-get install python3-cffi")
* numpy     ("pip install numpy")
* pillow    ("pip install pilllow" or "apt-get install python3-pil python3-pil.imagetk")
* zxbasic   [optional] ("pip install zxbasic")

## Run

1. Clone the repository to your local machine:

   ```bash
   git clone https://github.com/johndeckardsoftware/spyccy.git
   ```

2. Navigate to the project directory:

   ```bash
   cd spyccy
   ```

3. Run the application:

   ```bash
   python spyccy
   ```

## Contributions

These days, releasing open source code tends to come with an unspoken social contract, so I'd like to set some expectations...

This is a personal project, created for my own enjoyment, and my act of publishing the code does not come with any commitment to provide technical support or assistance. I'm always happy to hear of other people getting similar enjoyment from hacking on the code, and pull requests are welcome, but I can't promise to review them or shepherd them into an "official" release on any sort of timescale. 


## License

_SPYCCY_ is open source software. The source code is distributed under the terms of [GNU General Public License (GPLv3)](https://www.gnu.org/licenses/gpl-3.0.html).


## Acknowledgements

This software is inspired, or derive code from the following open source projects:

* fuse emulator (http://fuse-emulator.sourceforge.net/)
* EightyOne Sinclair Emulator (https://sourceforge.net/projects/eightyone-sinclair-emulator/)
* SoftSpectrum48 (https://softspectrum48.weebly.com/)
* PyZXSpectrum (https://github.com/folkertvanheusden/PyZXSpectrum)
* tzxtools - a collection for processing tzx files (https://github.com/shred/tzxtools)
* Russell Marks zmakebas.c (https://github.com/z00m128/zmakebas)
