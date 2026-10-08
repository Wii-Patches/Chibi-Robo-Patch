# hook: the game's own `bl PROBE` (r3 = channel, r4 = where to put the extension type; returns
# a status in r3).  The game reads the extension type from here -- not from KPAD's samples --
# to decide whether a Nunchuk is connected ("Connect a Nunchuk to the Wiimote").
# A Classic Controller (type 2) or a GameCube pad on the channel is reported as a Nunchuk (1).
    stwu    1, -0x20(1)
    mflr    0
    stw     0, 0x24(1)
    stw     3, 0x08(1)
    stw     4, 0x0c(1)
    lis     12, PROBE@ha
    addi    12, 12, PROBE@l
    mtctr   12
    bctrl                               # displaced instruction: bl PROBE
    POLLER
    lwz     4, 0x0c(1)
    lwz     5, 0(4)
    cmpwi   5, 2
    beq     conv
    lwz     9, 0x08(1)
    GETPAD  9
    cmpwi   10, 0
    beq     out
conv:
    li      5, 1
    stw     5, 0(4)
out:
    lwz     0, 0x24(1)
    mtlr    0
    addi    1, 1, 0x20
end:
