# hook: the `bl IRPROC` that processes a sample's pointer (IR) data (r3 = the channel's KPAD
# state, r4 = the sample).  It leaves the pointer position at state+0x20 / +0x24 (x right,
# y down, +/-1 and +/-0.75 at the screen edges) and its validity at +0x5e.
# With a GameCube pad or a Classic Controller on the channel the IR step is skipped and the
# pointer is steered by the Classic Controller's right stick / the pad's C-stick instead: each
# sample moves it a little, in proportion to the stick, and it is reported valid.  Nothing is
# stored anywhere but the pointer itself.
    stwu    1, -0x50(1)
    mflr    0
    stw     0, 0x54(1)
    stw     3, 0x08(1)
    stw     4, 0x0c(1)
    CHANNEL 9, 3
    cmplwi  9, 3
    bgt     nogc
    mulli   11, 9, 12
    lis     12, 0xCD00
    add     12, 12, 11
    lwz     6, 0x6404(12)
    cmpwi   6, 0
    blt     nogc
    andis.  0, 6, 0x0080
    beq     nogc
    lwz     6, 0x6408(12)               # SICnINBUFL: C-stick X [31:24], C-stick Y [23:16]
    rlwinm  8, 6, 8, 24, 31
    addi    8, 8, -128
    rlwinm  10, 6, 16, 24, 31
    addi    10, 10, -128
    b       have
nogc:
    lbz     0, 0x28(4)
    cmpwi   0, 2
    beq     cl
    lis     12, IRPROC@ha               # no pad, no Classic Controller: the remote's own pointer
    addi    12, 12, IRPROC@l
    mtctr   12
    bctrl                               # displaced instruction: bl IRPROC
    b       out
cl:
    lha     8, 0x30(4)                  # right stick, centred shorts (about +/-500)
    srawi   8, 8, 2
    lha     10, 0x32(4)
    srawi   10, 10, 2
have:
    lwz     3, 0x08(1)
.ifdef DBG
    lis     9, 0x8000
    stw     8, 0x3F40(9)
    stw     10, 0x3F44(9)
    stw     6, 0x3F48(9)
    lwz     5, 0x3F4C(9)
    addi    5, 5, 1
    stw     5, 0x3F4C(9)
.endif
    NORM    8
    NORM    10
    neg     10, 10                      # stick up = pointer up = y smaller
    lis     0, 0x3b80
    stw     0, 0x30(1)
    lfs     12, 0x30(1)                 # 1/256
    lis     0, 0xbc45
    ori     0, 0, 0x9ba6
    stw     0, 0x34(1)
    lfs     3, 0x34(1)                  # -0.012 per sample at full tilt (the game's pointer runs against the stick)
    lis     0, 0x3f80
    stw     0, 0x38(1)
    lfs     4, 0x38(1)                  # x limit 1.0
    lis     0, 0x3f40
    stw     0, 0x3c(1)
    lfs     5, 0x3c(1)                  # y limit 0.75
    lis     0, 0x4330
    stw     0, 0x40(1)
    stw     0, 0x48(1)
    lis     0, 0x8000
    stw     0, 0x4c(1)
    lfd     13, 0x48(1)                 # 2^52 + 2^31, to turn ints into doubles
    xoris   8, 8, 0x8000
    stw     8, 0x44(1)
    lfd     1, 0x40(1)
    fsub    1, 1, 13
    fmul    1, 1, 12                    # stick X in -1..1
    xoris   10, 10, 0x8000
    stw     10, 0x44(1)
    lfd     2, 0x40(1)
    fsub    2, 2, 13
    fmul    2, 2, 12                    # stick Y in -1..1 (already inverted)
    lfs     0, 0x20(3)
    fmadd   0, 1, 3, 0
    fmr     1, 4
    bl      clamp
    stfs    0, 0x20(3)                  # pos.x
    lfs     0, 0x24(3)
    fmadd   0, 2, 3, 0
    fmr     1, 5
    bl      clamp
    stfs    0, 0x24(3)                  # pos.y
    li      0, 2
    stb     0, 0x5e(3)                  # pointer valid
out:
    lwz     0, 0x54(1)
    mtlr    0
    addi    1, 1, 0x50
    b       end

# f0 = clamp(f0, -f1, f1)   (clobbers f1, f6)
clamp:
    fcmpu   0, 0, 1
    blt     1f
    fmr     0, 1
    blr
1:  fneg    6, 1
    fcmpu   0, 0, 6
    bgt     2f
    fmr     0, 6
2:  blr
end:
