# Shared by every routine.  The routines are self-contained: they call game code through
# absolute addresses and hold no variables of their own, so a Gecko code handler can put
# them anywhere.
#
# The SI hardware polls the GameCube pads on its own and mirrors the answer into
# SICnINBUFH (0xCD006404 + 12*port): [31] error, [23] always 1 in a real pad's reply,
# [29:16] the PAD button word (A 0x100 B 0x200 X 0x400 Y 0x800 Start 0x1000 L 0x40
# R 0x20 Z 0x10 Up 8 Down 4 Right 2 Left 1), [15:8] stick X, [7:0] stick Y (128 = centre).

# r10 = the pad word of the port in \ch, or 0 when no pad answers (clobbers r10-r12)
.macro GETPAD ch
    li      10, 0
    cmplwi  \ch, 3
    bgt     9f
    mulli   11, \ch, 12
    lis     12, 0xCD00
    add     12, 12, 11
    lwz     11, 0x6404(12)
    cmpwi   11, 0
    blt     9f                          # error / no pad
    andis.  12, 11, 0x0080
    beq     9f                          # not a pad's reply
    mr      10, 11
9:
.endm

# r<dst> = KPAD channel of the channel state pointer in r<src> (clobbers r10)
.macro CHANNEL dst, src
    lis     \dst, KBASE@ha
    addi    \dst, \dst, KBASE@l
    subf    \dst, \dst, \src
    li      10, 0x5c0
    divwu   \dst, \dst, 10
.endm

# clamp r<x> to [-127, 127]
.macro CLAMP x
    cmpwi   \x, 127
    ble     8f
    li      \x, 127
8:  cmpwi   \x, -127
    bge     7f
    li      \x, -127
7:
.endm

# Keep the SI hardware polling all four pads.  The game probes the ports once at boot (which
# is why a pad's reply is sitting in the registers) but never keeps the polling running.
# Command 0x00400300 = "poll, analog mode 3, motor off".  Idempotent; clobbers r0, r10-r12.
.macro POLLER
    lis     12, 0xCD00
    lis     10, 0x0040
    ori     10, 10, 0x0300
    lwz     11, 0x6400(12)
    cmpw    11, 10
    beq     6f
    stw     10, 0x6400(12)
6:  lwz     11, 0x640C(12)
    cmpw    11, 10
    beq     6f
    stw     10, 0x640C(12)
6:  lwz     11, 0x6418(12)
    cmpw    11, 10
    beq     6f
    stw     10, 0x6418(12)
6:  lwz     11, 0x6424(12)
    cmpw    11, 10
    beq     6f
    stw     10, 0x6424(12)
6:  lwz     11, 0x6430(12)              # SIPOLL: enable bits 7..4, polls per frame 15..8, lines 25..16
    andi.   0, 11, 0x00F0
    cmpwi   0, 0x00F0
    beq     6f
    ori     11, 11, 0x00F0
    rlwinm. 0, 11, 0, 6, 23
    bne     5f
    oris    11, 11, 0x00F7
    ori     11, 11, 0x0200
5:  stw     11, 0x6430(12)
6:
.endm

# r<x> = the stick value in r<x> (centred, +/-~100) through a dead zone of DEAD and a full
# scale at DEAD + 80, as -256..256 (clobbers r0, r11)
.macro NORM x
    srawi   11, \x, 31
    xor     0, \x, 11
    subf    0, 11, 0                    # |x|
    cmpwi   0, DEAD
    ble     5f
    addi    0, 0, -DEAD
    mulli   0, 0, KMUL
    srawi   0, 0, 6
    cmpwi   0, 256
    ble     4f
    li      0, 256
4:  xor     0, 0, 11
    subf    0, 11, 0
    mr      \x, 0
    b       3f
5:  li      \x, 0
3:
.endm
