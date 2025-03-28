 10 FOR y=0 TO 23
 20 FOR x=0 TO 31
 30 PRINT #FN s(); AT FN y(),x; "*"
 40 NEXT x
 50 NEXT y
100 DEF FN s()=(1+(y<22))
110 DEF FN y()=(y-(22*(y>21)))
