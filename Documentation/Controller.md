# Loopy Controller

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

* `$0405d010`: ROW0+1
* `$0405d012`: ROW2+3
* `$0405d014`: ROW4+5

## Devices

### Controller

The Loopy controller has a D-Pad (↑↓←→), two triggers (LR), and five face buttons (Start+ABCD). These are connected in a matrix of rows and columns, similar to a [keyboard matrix][matrix]:

|      | COL0 | COL1 | COL2 | COL3 | COL4 | COL5 | COL6 | COL7 |
| ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- |
| ROW0 | P1 ? | P1 S | P1 L | P1 R | n/c  | n/c  | n/c  | n/c  |
| ROW1 | P1 A | P1 D | P1 C | P1 B | n/c  | n/c  | n/c  | n/c  |
| ROW2 | P1 ↑ | P1 ↓ | P1 ← | P1 → | n/c  | n/c  | n/c  | n/c  |
| ROW3 | n/c  | n/c  | n/c  | n/c  | n/c  | n/c  | n/c  | n/c  |
| ROW4 | n/c  | n/c  | n/c  | n/c  | n/c  | n/c  | n/c  | n/c  |
| ROW5 | n/c  | n/c  | n/c  | n/c  | n/c  | n/c  | n/c  | n/c  |

[matrix]: https://en.wikipedia.org/wiki/Keyboard_matrix_circuit

### Mouse

When a mouse is connected, it ignores the row pins and returns raw [quadrature][quad] data on the column pins:

|      | COL0 | COL1 | COL2 | COL3 | COL4 | COL5 | COL6 | COL7 |
| ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- |
| ALL  | X1   | X2   | Y1   | Y2   | LB   | n/c  | RB   | M?   |

[quad]: https://en.wikipedia.org/wiki/Quadrature_encoder

### Multi-tap

Although no such device was ever released, the Loopy also supports a theoretical four-port [multitap][multitap]. Each of the controllers is assigned to one of the four quadrants of the controller matrix:

|      | COL0 | COL1 | COL2 | COL3 | COL4 | COL5 | COL6 | COL7 |
| ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- |
| ROW0 | P1 ? | P1 S | P1 L | P1 R | P2 ? | P2 S | P2 L | P2 R |
| ROW1 | P1 A | P1 D | P1 C | P1 B | P2 A | P2 D | P2 C | P2 B |
| ROW2 | P1 ↑ | P1 ↓ | P1 ← | P1 → | P2 ↑ | P2 ↓ | P2 ← | P2 → |
| ROW3 | P3 ? | P3 S | P3 L | P3 R | P4 ? | P4 S | P4 L | P4 R |
| ROW4 | P3 A | P3 D | P3 C | P3 B | P4 A | P4 D | P4 C | P4 B |
| ROW5 | P3 ↑ | P3 ↓ | P3 ← | P3 → | P4 ↑ | P4 ↓ | P4 ← | P4 → |

[multitap]: https://en.wikipedia.org/wiki/Multitap
