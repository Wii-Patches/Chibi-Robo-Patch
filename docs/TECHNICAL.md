# How the Chibi-Robo patch works

The game reads its controller through KPAD (`KPADRead`), and decides whether a
Nunchuk is connected from WPAD's probe, not from KPAD's samples. Four routines
(`src/*.s`) are hooked in, each at the `bl` that calls the SDK function:

| Source | Replaces the call to | Does |
|---|---|---|
| `buttons.s` | KPAD's raw-buttons -> hold/trig/release step | maps pad / Classic buttons onto Wii Remote and Nunchuk bits |
| `stick.s` | KPAD's extension decoder | feeds the pad's or Classic stick in as a Nunchuk stick |
| `pointer.s` | KPAD's IR processing | steers the pointer with the C-stick / right stick, reports it valid |
| `probe.s` | the game's `WPADProbe` call | reports a Classic Controller or pad as a Nunchuk, keeps SI polling on |

`KPADRead` has two read loops, so each hook is installed at two call sites
(8 hooks). GameCube pads are read straight from the SI hardware registers
(`0xCD006400`+), which `probe.s` keeps polling.

The routines are assembled with devkitPPC into `tools/prebuilt/pad_R24J01.json`;
the patcher adds them as a text section at `0x80001820` of `main.dol`, and
`riivolution/R24J01.xml` writes the same bytes as memory patches.
