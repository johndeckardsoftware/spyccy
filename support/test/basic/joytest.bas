# (for Emacs) -*- indented-text -*-

# joystick test program

# SPYCCY options syntax:
#!option = value
#
# options:
#  prog_name = 10 char 
#  use_labels = 0, 1  	(default: 1)
#  auto_start_line = n 	(run line number. default: 0x8000 no auto run)
#  auto_inc = n			(line number increment when use_labels = 1. default: 2)
#  first_line = n		(first line number when use_labels = 1. default: 2) 
#
#!prog_name = "JOY TEST"
#!use_labels = 1
#!auto_start_line = 1

rem joystick test program

gosub @init
gosub @header
gosub @seljoy
stop

@init:
for f=usr "a"+7 to usr "u"+7 step 8
poke f,255
next f
let iszx=1

# init all attrs just in case
border 7:paper 7:ink 7:bright 0:flash 0:cls

# check for 48k speccy or 48k mode. This is a pretty nasty way to do
# it, but seems to be the most sane way (from Basic at least).
print "\t"
if screen$(0,0) = "S" then let iszx = 0
ink 0:print at 0,0;
return

@header:
print ink 5;"\..\..\..\..\..\..\..\..\..\..\..\..\..\..\..\..";\
            "\..\..\..\..\..\..\..\..\..\..\..\..\..\..\..\.."
print paper 5; "         Joystick  Test         "
print ink 5;"\''\''\''\''\''\''\''\''\''\''\''\''\''\''\''\''";\
	    "\''\''\''\''\''\''\''\''\''\''\''\''\''\''\''\''"
return

@seljoy:
print at 6,2;"Select joystick type:"
print at 8,3;"'0' Sinclair, programmable, Cursor"
print at 10,3;"'1' Kempston"
print at 12,3;"'2' Fuller"
print at 16,0;"                               " 
input "'x' to exit", j$
if j$ = "0" then gosub @keymap
if j$ = "1" then gosub @kempston
if j$ = "2" then gosub @fuller
if j$ = "x" then return
goto @seljoy


@keymap:
rem if inkey$ <> "" then goto @keymap 
rem if inkey$ = "" then goto @keymap
pause 0
let k$ = inkey$
if k$ = "x" then return  
print at 16,2;"pressed key: '";k$;"'   " 
goto @keymap


@kempston:
let a = in 31: rem kempston
print at 16,2;"button pressed: '";a;"'   " 
if inkey$ = "x" then return
goto @kempston


@fuller:
let a = in 127: rem fuller
print at 16,2;"button pressed: '";a;"'   " 
if inkey$ = "x" then return
goto @fuller


