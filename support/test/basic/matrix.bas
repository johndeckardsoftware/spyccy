10 CLEAR 61999
20 BORDER 0: POKE 23624,4: POKE 23693,0: CLS: REM easier than "bright 0: flash 0: ink 0: paper 0"
30 PRINT INK 4; FLASH 1;"Initialising": GO SUB 9000: LET m=USR 62000: CLS: REM set up and run machine code; USR is the call function
40 DIM s(32,2): REM current top and bottom of character sequence for each of the 32 spaces across the screen

50 FOR x=1 TO 32: REM main loop
60 IF s(x,1)=0 AND RND>.95 THEN LET s(x,1)=1: LET s(x,2)=2: GO SUB 4000: GO SUB 3000: GO TO 80: REM start a new column; decrease the .95 modifier for a busier - but slower - screen
70 IF s(x,2)>0 THEN GO SUB 1000
80 NEXT x
90 FOR l=1 TO 10: REM matrix code switches existing glyphs occasionally
100 LET x=INT (RND*22): LET y=INT (RND*32)
110 IF PEEK (22528+32*x+y)=0 THEN GO TO 140: REM no point updating a blank space
120 GO SUB 4000
130 PRINT AT x,y; INK 8; BRIGHT 8;CHR$ (33+RND*95): REM ink 8 and bright 8 tells it to keep the cell's existing ink and bright values
140 NEXT l
150 GO TO 50

999 REM continue an existing column
1000 LET s(x,2)=s(x,2)+1
1010 IF s(x,2)<21 THEN GO SUB 3000
1020 IF s(x,2)>12 THEN LET s(x,1)=s(x,1)+1
1030 LET k=2
1040 GO SUB 2000
1050 LET k=6
1060 GO SUB 2000
1070 LET k=12
1080 GO SUB 2000
1090 IF s(x,1)=22 THEN LET s(x,1)=0: LET s(x,2)=0
1100 RETURN 

1999 REM update colour
2000 LET a=22527+x+32*(s(x,2)-k)
2010 LET c=PEEK a
2020 IF c=4 THEN POKE a,0
2030 IF c=68 THEN POKE a,4
2040 IF c=71 THEN POKE a,68: REM this poke could be done with 'print at s(x,2)-k-1,x-1; ink 4; bright 1; over 1; " " ' but poking is FAR easier, especially considering the above pokes would be similar
2050 RETURN 

2999 REM new character at bottom of column
3000 PRINT AT s(x,2)-1,x-1; INK 7; BRIGHT 1;CHR$ (33+RND*95)
3010 RETURN 

3999 REM select character set
4000 POKE 23607,242+3*INT (RND*4): REM the spectrum character set is pointed to by the two-byte system value CHARS at 23606 and 23607, so repoking this selects a new character set - the machine code below has created four copies of the character set at suitable locations
4010 RETURN 

8999 REM machine code routine to create multiple character sets
9000 RESTORE 9800
9010 LET h$="0123456789ABCDEF"
9020 LET o=62000
9030 IF PEEK o=33 AND PEEK 62121=201 THEN RETURN: REM saves storing it all again if the machine code is already there
9040 READ a$
9050 IF a$="eof" THEN RETURN 
9060 FOR x=1 TO 8
9070 LET n=0
9080 LET s=(x*2)-1
9090 LET t=s+1
9100 FOR m=1 TO 16
9110 IF h$(m)=a$(s) THEN LET n=n+16*(m-1)
9120 IF h$(m)=a$(t) THEN LET n=n+m-1
9130 NEXT m
9140 POKE o,n
9150 LET o=o+1
9160 NEXT x
9170 GO TO 9040

9800 DATA "21003D1100F30100"
9810 DATA "03EDB02100F31100"
9820 DATA "F6010009EDB01100"
9830 DATA "F901FF051A6F0707"
9840 DATA "ADE6AAAD6F070707"
9850 DATA "CB0DADE666AD1213"
9860 DATA "0B78B120E721FFF5"
9870 DATA "010000E5CD8BF2E1"
9880 DATA "E5CD8BF2E1E5CD8B"
9890 DATA "F2E1CD8BF2232323"
9900 DATA "23AF470C79FEC0C2"
9910 DATA "6BF2C9E5D1043E09"
9920 DATA "90835F8A93577885"
9930 DATA "6F8C95671AE521AA"
9940 DATA "F277E17E123AAAF2"
9950 DATA "77C9000000000000"
9960 DATA "eof"

9999 POKE 23606,0: POKE 23607,60: INK 4: REM reset to default character set and colour if you get lost
