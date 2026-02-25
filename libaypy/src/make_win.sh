#  https://github.com/skeeto/w64devkit/ for an easy to install and run gcc compiler
gcc -o ay_emu_windows_amd64.lib mman.c ay8912.c lh5dec_old.c vtxfile.c -I ../include -O3 -DWIN32 -fPIC -Wall -shared
