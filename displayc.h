// header for displayc.c
#ifdef WIN32
#define EXPORTED __declspec(dllexport)
#define CDECL __cdecl
#else
#define EXPORTED extern
#define CDECL
#endif
EXPORTED int CDECL set_frame_p8(char * bitmap, char * vram, int screen_addr, int attrib_addr, int flash_phase);
EXPORTED int CDECL set_frame_rgb(char * bitmap, char * vram, int screen_addr, int attrib_addr, int flash_phase);
EXPORTED int CDECL set_resize_frame_rgb(char * bitmap, char * vram, int screen_addr, int attrib_addr, int flash_phase, int zoom);

