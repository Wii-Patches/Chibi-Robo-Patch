# hook: the `bl DECODE` that decodes a sample's extension data into the channel state
# (r3 = the channel's KPAD state, r4 = the sample).  For a Nunchuk it reads the stick as
# two signed bytes at +0x30 / +0x31 (centre 0, dead zone 15, full scale 71).
# With a Classic Controller or GameCube pad on the channel the sample is shown to DECODE as
# a Nunchuk's, with that stick, and put back afterwards (KPAD compares the sample's real
# extension type with its own bookkeeping on every call, so the sample must stay as it was).
#
# Classic Controller sticks are centred shorts (dead zone 60, full scale 308): /4 matches.
# A GameCube stick is 128 +/- ~100: minus 128 matches.
    stwu    1, -0x40(1)
    mflr    0
    stw     0, 0x44(1)
    stw     3, 0x08(1)
    stw     4, 0x0c(1)
    CHANNEL 9, 3
    GETPAD  9
    li      11, 0
    cmpwi   10, 0
    beq     nopad
    rlwinm  8, 10, 24, 24, 31           # stick X
    addi    8, 8, -128
    rlwinm  9, 10, 0, 24, 31            # stick Y
    addi    9, 9, -128
    li      11, 1
nopad:
    lwz     4, 0x0c(1)
    lbz     5, 0x28(4)                  # sample's extension type
    cmpwi   5, 2
    bne     nocl
    cmpwi   11, 0
    bne     nocl                        # a pad wins over the Classic Controller
    lha     8, 0x2c(4)
    srawi   8, 8, 2
    lha     9, 0x2e(4)
    srawi   9, 9, 2
    li      11, 1
nocl:
    cmpwi   11, 0
    beq     call
    CLAMP   8
    CLAMP   9
    lbz     5, 0x28(4)                  # save what we are about to change
    stw     5, 0x10(1)
    lbz     5, 0x36(4)
    stw     5, 0x14(1)
    lhz     5, 0x2a(4)
    stw     5, 0x18(1)
    lhz     5, 0x2c(4)
    stw     5, 0x1c(1)
    lhz     5, 0x2e(4)
    stw     5, 0x20(1)
    lhz     5, 0x30(4)
    stw     5, 0x24(1)
    li      0, 1
    stb     0, 0x28(4)                  # extension type := Nunchuk
    lbz     5, 0x36(4)                  # data format: core 0-2 / Classic 6-8 -> Nunchuk 3-5
    cmplwi  5, 3
    bge     1f
    addi    5, 5, 3
    b       3f
1:  cmplwi  5, 6
    blt     3f
    cmplwi  5, 8
    bgt     3f
    addi    5, 5, -3
3:  stb     5, 0x36(4)
    li      0, 0
    sth     0, 0x2a(4)                  # Nunchuk accelerometer: neutral
    sth     0, 0x2c(4)
    sth     0, 0x2e(4)
    stb     8, 0x30(4)                  # stick X, Y
    stb     9, 0x31(4)
call:
    stw     11, 0x28(1)                 # (the call below clobbers r11)
    lwz     3, 0x08(1)
    lwz     4, 0x0c(1)
    lis     12, DECODE@ha
    addi    12, 12, DECODE@l
    mtctr   12
    bctrl                               # displaced instruction: bl DECODE
    lwz     11, 0x28(1)
.ifdef DBG
    lwz     3, 0x08(1)
    lwz     4, 0x0c(1)
    lis     9, 0x8000
    stw     11, 0x3F1C(9)
    lwz     5, 0x60(3)
    stw     5, 0x3F14(9)
    lwz     5, 0x64(3)
    stw     5, 0x3F18(9)
    lhz     5, 0x28(4)
    stw     5, 0x3F20(9)
    lhz     5, 0x30(4)
    stw     5, 0x3F24(9)
    lbz     5, 0x36(4)
    stw     5, 0x3F28(9)
    lwz     5, 0x3F2C(9)
    addi    5, 5, 1
    stw     5, 0x3F2C(9)
.endif
    cmpwi   11, 0
    beq     out
    lwz     4, 0x0c(1)                  # put the sample back
    lwz     5, 0x10(1)
    stb     5, 0x28(4)
    lwz     5, 0x14(1)
    stb     5, 0x36(4)
    lwz     5, 0x18(1)
    sth     5, 0x2a(4)
    lwz     5, 0x1c(1)
    sth     5, 0x2c(4)
    lwz     5, 0x20(1)
    sth     5, 0x2e(4)
    lwz     5, 0x24(1)
    sth     5, 0x30(4)
out:
    lwz     0, 0x44(1)
    mtlr    0
    addi    1, 1, 0x40
end:
