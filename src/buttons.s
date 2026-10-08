# hook: the `bl FACA0` that turns the raw buttons of a sample into hold / trig / release
# (KPAD's button processing; called from both read loops of KPADRead).
#   r3 = the channel's KPAD state   r4 = extension type of the sample (1 Nunchuk, 2 Classic)
#   r5 = sample count   r6 = Wii Remote buttons   r7 = Nunchuk buttons (Z 0x2000, C 0x4000)
#   r8 = Classic Controller buttons
# With a Classic Controller or a GameCube pad on the channel, its buttons are mapped onto
# the Wii Remote / Nunchuk bits the game reads, and the sample is presented as a Nunchuk's
# so the Z and C bits are honoured.  The edge detection (trig / release) runs on the result.
    stwu    1, -0x20(1)
    mflr    0
    stw     0, 0x24(1)
    stw     3, 0x08(1)
    stw     4, 0x0c(1)
    stw     5, 0x10(1)
    stw     6, 0x14(1)
    stw     7, 0x18(1)
    stw     8, 0x1c(1)
    CHANNEL 9, 3
    GETPAD  9
    li      9, 0                        # r9 = the buttons to add
    li      11, 0                       # r11 = 1: present the sample as a Nunchuk's
    bl      here
here:
    mflr    12
    cmpwi   10, 0
    beq     nopad
    srwi    4, 10, 16
    andi.   4, 4, 0x1f7f
    addi    5, 12, tbl_gc - here
    bl      map
    or      9, 9, 6
    li      11, 1
nopad:
    lwz     4, 0x0c(1)
    cmpwi   4, 2
    bne     nocl
    lwz     4, 0x1c(1)
    addi    5, 12, tbl_cl - here
    bl      map
    or      9, 9, 6
    li      11, 1
nocl:
    cmpwi   11, 0
    beq     call
    li      0, 1
    stw     0, 0x0c(1)                  # type := Nunchuk
    andi.   0, 9, 0x9fff
    lwz     4, 0x14(1)
    or      4, 4, 0
    stw     4, 0x14(1)                  # Wii Remote buttons
    lwz     4, 0x18(1)
    or      4, 4, 9
    stw     4, 0x18(1)                  # Nunchuk buttons
call:
    lwz     3, 0x08(1)
    lwz     4, 0x0c(1)
    lwz     5, 0x10(1)
    lwz     6, 0x14(1)
    lwz     7, 0x18(1)
    lwz     8, 0x1c(1)
    lis     12, FACA0@ha
    addi    12, 12, FACA0@l
    mtctr   12
    bctrl                               # displaced instruction: bl FACA0
    lwz     0, 0x24(1)
    mtlr    0
    addi    1, 1, 0x20
    b       end

# r4 = buttons, r5 = table of (mask, bits) halfword pairs ending in a zero mask
# -> r6 = the OR of the bits of every mask that is set   (clobbers r0, r5, r7)
map:
    li      6, 0
1:  lhz     7, 0(5)
    cmplwi  7, 0
    beqlr
    and.    0, 4, 7
    beq     2f
    lhz     0, 2(5)
    or      6, 6, 0
2:  addi    5, 5, 4
    b       1b

# GameCube pad -> Wii Remote (A 0x800  B 0x400  + 0x10  - 0x1000  1 0x200  2 0x100
#                             Home 0x8000  Nunchuk Z 0x2000  C 0x4000  D-pad 8 4 2 1)
tbl_gc:
    .short  0x0100, 0x0800              # A
    .short  0x0200, 0x0400              # B
    .short  0x0400, 0x0200              # X -> 1
    .short  0x0800, 0x4000              # Y -> C
    .short  0x1000, 0x0010              # Start -> +
    .short  0x0040, 0x2000              # L -> Z
    .short  0x0020, 0x0100              # R -> 2
    .short  0x0010, 0x1000              # Z -> -
    .short  0x0008, 0x0008              # D-pad up
    .short  0x0004, 0x0004              # down
    .short  0x0002, 0x0002              # right
    .short  0x0001, 0x0001              # left
    .short  0, 0
# Classic Controller -> Wii Remote
tbl_cl:
    .short  0x0010, 0x0800              # A
    .short  0x0040, 0x0400              # B
    .short  0x0008, 0x0200              # X -> 1
    .short  0x0020, 0x4000              # Y -> C
    .short  0x0400, 0x0010              # + 
    .short  0x1000, 0x1000              # -
    .short  0x0800, 0x8000              # HOME
    .short  0x0080, 0x2000              # ZL -> Z
    .short  0x2000, 0x2000              # L  -> Z
    .short  0x0004, 0x0100              # ZR -> 2
    .short  0x0200, 0x0100              # R  -> 2
    .short  0x0001, 0x0008              # D-pad up
    .short  0x4000, 0x0004              # down
    .short  0x8000, 0x0002              # right
    .short  0x0002, 0x0001              # left
    .short  0, 0
end:
