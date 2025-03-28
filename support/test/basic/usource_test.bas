10 REM TEST SCREEN HANDLING USING uSource
20 LET codeorg=32768
30 IF  PEEK (codeorg)=24 THEN  GOTO 640
40 LET assemble=1
50 REM !       OPT 2+4+64
60 REM !       ORG 8000h
70 REM !       jr start
80 REM !start  ld de, screen
90 REM !       ld c, 3 ; rows
100 REM !loopc  ld h, 8 ; char height
110 REM !       ld ix, mask
120 REM !looph  call random
130 REM !       ld b, 0 ; cols
140 REM !loopa  ld (de), a
150 REM !       inc de
160 REM !       call random
170 REM !       djnz loopa
180 REM !       inc ix
190 REM !       dec h
200 REM !       jr nz, looph
210 REM !       dec c
220 REM !       jr nz, loopc
230 REM !       ld de, attrib
240 REM !       ld c, 3
250 REM !moopc  call random
260 REM !       ld b, 0
270 REM !moopb  ld (de), a
280 REM !       inc de
290 REM !       call random
300 REM !       djnz moopb
310 REM !       dec c
320 REM !       jr nz, moopc
330 REM !exit   ret
340 REM ! ; Generate a random number
350 REM ! ; output a=answer 0<=a<=255
360 REM ! ; all registers are preserved except: af
370 REM !random push    hl
380 REM !       push    de
390 REM !       ld      hl,(rseed)
400 REM !       ld      a,r
410 REM !       ld      d,a
420 REM !       ld      e,(hl)
430 REM !       add     hl,de
440 REM !       add     a,l
450 REM !       xor     h
460 REM !       ld      (rseed),hl
470 REM !       pop     de
480 REM !       pop     hl
490 REM !       ret
500 REM !
510 REM !rseed  DEFW 1234h
520 REM !       
530 REM !mask   DEFB 255
540 REM !       DEFB 129
550 REM !       DEFB 129
560 REM !       DEFB 99h
570 REM !       DEFB 99h
580 REM !       DEFB 129
590 REM !       DEFB 129
600 REM !       DEFB 255
610 REM !screen EQU 4000h
620 REM !attrib EQU 5800h
630 REM !udg    EQU 0000h
640 CLS 
642 IF  PEEK (codeorg) <> 24 THEN GOTO 670
650 RANDOMIZE  USR codeorg
660 STOP 
670 POKE 32768,0
680 PRINT "uSource not configured"


