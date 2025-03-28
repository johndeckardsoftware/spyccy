# clock program

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
#!prog_name = "CLOCK"
#!use_labels = 1
#!auto_start_line = 1

REM First we draw the clock face 
CLS
FOR n=1 TO 12 
PRINT AT 10-10*COS (n/6*PI),16+10*SIN (n/6*PI);n 
NEXT n 

DEF FN m(x,y)=(x+y+ABS (x-y))/2: REM the larger of x and y 
DEF FN u()=(65536*PEEK 23674+256*PEEK 23673+PEEK 23672)/50: REM time, may be wrong
DEF FN t()=FN m(FN u(), FN u()): REM time, right

@LOOP:
REM Now we start the clock
LET t1=FN t()
LET a=t1/30*PI: REM a is the angle of the second hand in radians
LET sx=72*SIN a: LET sy=72*COS a
PLOT 131,91: DRAW OVER 1;sx,sy: REM draw hand

@WAIT_ONE:
REM WAIT UNTIL TIME FOR NEXT HAND
LET t=FN t()
IF t<=t1 THEN GOTO @WAIT_ONE

REM RUB OUT OLD HAND
PLOT 131,91
DRAW OVER 1;SX,SY
GOTO @LOOP



