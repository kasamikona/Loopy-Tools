# Loopy Controller

Note: to avoid confusion, this documentation uses the term "gamepad" to refer specifically to the normal handheld controller, and "controller" refers both the gamepad and mouse more generally as they share the same interface.

## Connector

The Loopy controller connector appears to be a 16-pin [Hosiden][hosiden] connector, a variant of the 10-pin HGC0492 used in the [Apple Pippin][pippin] controller and [Game Gear][gamegear] ext port.

The pins of the controller socket are assigned as follows, facing the console:

```
 09   10   11   12   13   14   15   16
ROW1 COL0 COL3 COL4 COL5 ROW5 ROW3 GND
ROW0 ROW2 COL1 COL2 COL6 COL7 ROW4 VCC
 01   02   03   04   05   06   07   08
```

[hosiden]: https://en.wikipedia.org/wiki/Hosiden
[pippin]: https://en.wikipedia.org/wiki/Apple_Pippin
[gamegear]: https://en.wikipedia.org/wiki/Game_Gear

## Memory map

* `0x0C058000` (VDP_MODE): bit 4 enables gamepad scan, bit 3 enables mouse scan
* `0x0C05D010` (IO_GAMEPAD0): Data from rows 0 & 1
* `0x0C05D012` (IO_GAMEPAD1): Data from rows 2 & 3
* `0x0C05D014` (IO_GAMEPAD2): Data from rows 4 & 5
* `0x0C05D050` (IO_MOUSEX): Mouse-specific, see below
* `0x0C05D052` (IO_MOUSEY): Mouse-specific, see below

## Devices

### Gamepad

The Loopy gamepad has a D-Pad (↑↓←→), two triggers (LR), and five face buttons (Start+ABCD). These are connected in a matrix of rows and columns, similar to a [keyboard matrix][matrix]:

|      | COL0 | COL1 | COL2 | COL3 | COL4 | COL5 | COL6 | COL7 |
| ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- |
| ROW0 | P1 P | P1 S | P1 L | P1 R | n/c  | n/c  | n/c  | n/c  |
| ROW1 | P1 A | P1 D | P1 C | P1 B | n/c  | n/c  | n/c  | n/c  |
| ROW2 | P1 ↑ | P1 ↓ | P1 ← | P1 → | n/c  | n/c  | n/c  | n/c  |
| ROW3 | n/c  | n/c  | n/c  | n/c  | n/c  | n/c  | n/c  | n/c  |
| ROW4 | n/c  | n/c  | n/c  | n/c  | n/c  | n/c  | n/c  | n/c  |
| ROW5 | n/c  | n/c  | n/c  | n/c  | n/c  | n/c  | n/c  | n/c  |

P is a presence detect signal. It is permanently connected in the gamepad, and is used to determine if a gamepad is plugged in.
The n/c locations are not normally used, but are scanned to facilitate a 4-gamepad multitap (see below).

When gamepad scanning is enabled, the ROW output signals are activated and the gamepad returns data on the COL input signals.
The full matrix is scanned once per frame.

Column data from rows 0 & 1 appear in the low and high byte of the IO_GAMEPAD0 register respectively.
Column 0 appears in bit 0 (or 8), and column 7 appears in bit 7 (or 15).
Rows 2 & 3 appear in IO_GAMEPAD1 and rows 4 & 5 appear in IO_GAMEPAD2 in the same manner.

[matrix]: https://en.wikipedia.org/wiki/Keyboard_matrix_circuit

### Mouse

When a mouse is connected, it ignores the row pins and returns raw [quadrature][quad] data on the column pins:

|      | COL0 | COL1 | COL2 | COL3 | COL4 | COL5 | COL6 | COL7 |
| ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- |
| ALL  | X1   | X2   | Y1   | Y2   | LB   | n/c  | RB   | P    |

This appears in all lower and upper bytes of the IO_GAMEPADn registers, even if gamepad and mouse scanning are disabled.
The P (presence) bit is used to determine if a mouse is plugged in, and must be checked with gamepad scanning disabled.

The quadrature position bits are not used directly, but sent to internal 12-bit delta position counters when mouse scanning is enabled.
The X counter appears in the IO_MOUSEX register, along with LB in bit 12 and RB in bit 14. The Y counter appears in the IO_MOUSEY register.
Reading each register resets the corresponding counter.
The LB and RB bits are preferably read from the IO_MOUSEX register as this may provide more reliable triggering.

[quad]: https://en.wikipedia.org/wiki/Quadrature_encoder

### Multi-tap

Although no such device was ever released, the Loopy also supports a theoretical four-port [multitap][multitap] for gamepads. Each of the gamepads is assigned to one of the four quadrants of the controller matrix:

|      | COL0 | COL1 | COL2 | COL3 | COL4 | COL5 | COL6 | COL7 |
| ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- |
| ROW0 | P1 P | P1 S | P1 L | P1 R | P2 P | P2 S | P2 L | P2 R |
| ROW1 | P1 A | P1 D | P1 C | P1 B | P2 A | P2 D | P2 C | P2 B |
| ROW2 | P1 ↑ | P1 ↓ | P1 ← | P1 → | P2 ↑ | P2 ↓ | P2 ← | P2 → |
| ROW3 | P3 P | P3 S | P3 L | P3 R | P4 P | P4 S | P4 L | P4 R |
| ROW4 | P3 A | P3 D | P3 C | P3 B | P4 A | P4 D | P4 C | P4 B |
| ROW5 | P3 ↑ | P3 ↓ | P3 ← | P3 → | P4 ↑ | P4 ↓ | P4 ← | P4 → |

The first gamepad "P1" is in the same location as the standalone gamepad, and the numbering of P2-P4 is derived from "PC Collection" controller initialization code.

A mouse cannot be used with a passive multitap setup as it ignores the row signals.
A more advanced active multitap could in theory allow this by buffering the mouse signals until no rows are active, and compensating for false counts from buttons.

[multitap]: https://en.wikipedia.org/wiki/Multitap

## Controller initialization routine

Note that some of the original games that were not designed to use the mouse generally do not check for it, and further some games may not check gamepads in P2-P4 positions.
This routine is mainly provided as an example of what to do in homebrew software, and to give a clearer understanding of how the presence bits work.

A general controller initialization may work as follows:

* Disable gamepad scanning and wait at least one whole frame, or assume disabled at boot
* If bit 7 (mouse presence) is high in any gamepad register, a mouse is connected
  * Enable mouse scanning in the VDP Mode register
  * Start game in mouse mode
* Otherwise, assume gamepads are connected
  * Enable gamepad scanning in the VDP Mode register
  * Wait at least one whole frame for scanning
  * Evaluate presence bits for all 4 gamepads
  * Determine primary gamepad
    * If nothing is connected, show an error or default to P1
  * Start game in gamepad mode
