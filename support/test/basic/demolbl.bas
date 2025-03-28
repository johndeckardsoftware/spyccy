# (for Emacs) -*- indented-text -*-

# this is a label-using version of `demo.bas', which shows how much
# nicer it is not to have to deal with line numbers. :-)

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
#!prog_name = "ZMAKEBAS"
#!use_labels = 1
#!auto_start_line = 1

rem zmakebas demo

gosub @init
gosub @header
gosub @udgdem
gosub @blockdem
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
            "\..\..\..\..\..\..\..\..\..\..\..\..\..\..\.."
print paper 5; "  Non-ASCII chars in zmakebas  "
print ink 5;"\''\''\''\''\''\''\''\''\''\''\''\''\''\''\''\''";\
	    "\''\''\''\''\''\''\''\''\''\''\''\''\''\''\''"
return


@udgdem:
print "Here are the UDGs:"''
print ink 1;"\a\b\c\d\e\f\g\h\i\j\k\l\m\n\o\p\q\r\s";
if iszx then print ink 1;"\t\u";
print ''"(They should be underlined.)"
return


@blockdem:
#              01234567890123456789012345678901
print at 10,0;"The block graphics, first as"'\
	      "listed by a for..next loop, then"'\
	      "via zmakebas's escape sequences:"
ink 7
print at 15,0;
for f=128 to 143:print chr$(f);" ";:next f:print ''
print at 17,0;"\   \ ' \'  \'' \ . \ : \'. \': ";\
	      "\.  \.' \:  \:' \.. \.: \:. \::"
# draw boxes around them to make it look less confusing
ink 1
for y=0 to 1
for x=0 to 15
plot x*16,55-y*16:draw 7,0:draw 0,-7:draw -7,0:draw 0,7
next x
next y
ink 0
print at 19,0;"And finally here's the copyright symbol (";ink 1;"\*";ink 0;") and pound sign (";ink 1;"`";ink 0;")."
print TAB 15;"\{0x5e} ^"
return

