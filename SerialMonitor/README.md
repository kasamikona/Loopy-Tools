# Casio Loopy Serial Memory Monitor

This is a research tool for interacting with the Loopy's hardware and memory space.
It consists of two parts; a Loopy ROM (monitor.bin) which runs on the console,
and the user interface in the form of a python script you run locally.
These communicate over the console's internal serial port.

The ROM implements low-level operations like directly reading/writing blocks of memory,
while the script exposes this and much more in the form of simple commands.
This allows for high-level operations like savestates and uploading local files,
and enables rapid iteration without having to recompile or reflash the ROM.
Currently the ROM is a standalone thing and can't be integrated into games, but maybe one day.

Operations that the python script is capable of (not exhaustive):
- Read/write single values directly
- Save/load memory areas with local files (dump/burst commands)
- Save/load multi-area state files using simple user-defined templates
- All memory accesses can be 8/16/32-bit (16-bit is most useful)
- Use raw memory addresses, or known labels e.g. `VDP.MODE`, `INTC_IPRD`
- Use relative addresses or array indexing e.g. `VDP.PALETTE+0x20`, `VDP.PALETTE[16]`
- Call BIOS functions from a known list with up to 8 numeric arguments
- Take screen captures using the built-in scanline capture system (slow)
- Change baud rate for faster but possibly less stable transfers

NOTE:
I haven't updated the ROM in a long time, and barely understood the VDP when I wrote it.
It boots to an ugly pinkish gradient and may set up some registers weirdly. This is normal.

## Requirements

To use this you will need a serial-capable flash cart with the monitor ROM on it,
such as a [Floopy Drive](https://github.com/partlyhuman/floopydrive) with up-to-date firmware,
or some other way to access the console's internal serial port.
If a Floopy Drive is connected via USB while in the console, it appears as a USB serial device.

The python script requires some libraries: `pyserial`, `pillow`, and `mido[ports-rtmidi]`.
You can install these all at once with `pip install -r requirements.txt`.
You may choose to run it in a python virtual environment (venv) but it is not usually necessary.
It should run on any major OS.

## Connection Setup

1. Load the `monitor.bin` ROM onto your flash cart, and insert it into the Loopy.
Prepare a USB cable to connect to the flash cart or serial adapter but don't connect it yet.

2. With serial disconnected, run the monitor.py script with `python`/`python3`
in a terminal or command prompt, e.g. `python monitor.py` or `./monitor.py`.
It will list the serial ports currently connected to your PC.

3. Connect the USB cable and turn on the Loopy.
If you have the AV output connected, you should see a pink gradient and hear a startup chime.

4. Run the script again and identify the newly connected port.
Add the name of that port to the command line, e.g. `python monitor.py COM11`
and you'll be in an interactive monitor prompt.

## First Time Use

As a connection/sanity check you can type `read16 0x1234` and should see value `0x00A1` printed.
The address `0x00001234` lies within the BIOS ROM so this value shouldn't change.
A shorter command you can use to test the connection is `read8 0`, which should print `0x00`.
Type `reset` and the console should reset itself. You should still be able to read the same values.

If at any point the connection times out or the console appears to have crashed, push the reset button.
If the baud rate was changed from the default, you then need to restart the script
or use the `reset` command to ensure the console and script are using the same baud rate.

The default baud rate is 38400. Try increasing it with `baud 250000`. If that doesn't work,
you may have to use 125000 or lower. Type `baud` without an argument to see valid rates.
If you're using a Floopy Drive, all valid rates are supported. Other adapters may have limited support,
as the higher rates are non-standard values derived from the Loopy's CPU clock.

Try dumping the BIOS with `dump16 BIOS * my_bios.bin`. At baud rate 250000 this should take 1-2 seconds.
Here, `BIOS` is a label pointing to address 0x0000 with size 0x8000.
The `*` is a special indicator to use the size specified by the label.
Use the `labels` command to list all labels and their sizes (the list is quite long).

Exit the monitor by typing `exit` or Ctrl-C.

## Command Usage

Commands accessing memory use a data size suffix, replacing `#` with `8`, `16` or `32`.
Memory is accessed with corresponding 8/16/32-bit instructions in the CPU,
but this usually maps to a 16-bit hardware access in some way.

Numbers can be specified in decimal (default) or hexadecimal (`0x` prefix or `h` suffix).

Addresses can be a number or a label. As a number, they are specified in bytes.
Addresses can be offset by some number of bytes e.g. `read16 RAM+1024`.
Alternatively they can be array-indexed according to the access size,
e.g. `read16 VDP.PALETTE[50]` reads the 50th 16-bit word at byte offset 100.
Offsets/indices are not range checked and can be negative.

Data must be a number, and is always printed in hexadecimal.
The Loopy uses a big-endian CPU, so a 16-bit value of 0x1234 is equivalent to
an 8-bit value of 0x12 followed by 0x34.
Data loaded/saved in files uses this ordering.

### Low-Level

The first few commands map directly to low-level features implemented in the ROM.

- `read# <address>`: Read a single address and print the value
- `write# <address> <value>` Write a value to a single address; **writes not verified!**
- `dump# <address> <length> <output.bin>`: Read a range of addresses and save the contents to a file
- `burst# <address> <input.bin>`: Load a file and write it to memory starting at the given address
- `call <func> [args...]`: Call a known function with up to 8 numeric arguments
- `midiport <midi port>`: Pass through a local MIDI input to the console
- `baud <rate>`: Change the baud rate (recommended for slow commands)
- `reset`: Attempt to hard-reset the console via software; reconfigures current baud after

The script tries to prevent invalid memory accesses or function calls that could crash,
but you should be prepared to reset or remove power if anything goes wrong,
especially if it involves running the printer.
If you manage to find any *interesting* crashes, please tell me!
I can then attempt to mitigate that while also potentially improving community knowledge.

### High-Level

These commands implement more complex actions built on the low-level functionality.

- `hist# <address> <count> <log.txt>`: Read a value repeatedly and log a histogram of its values over time (very slow)
- `savestate <template.txt> <output.state>`: Save a state file using a template (slow)
- `loadstate <input.state>`: Load a state file (slow)
- `screencap <capture mode> <output name>`: Capture the current screen contents using scanline capture (slow)
- `movemotor <steps>`: Directly control the printer motor (UNSAFE)

### Meta

- `help [command]`: Show a list of commands, or help for a given command
- `labels`: List labels (and sizes) for all commands taking memory addresses/ranges
- `listfuncs`: List known callable functions for the `call` command
- `exit`: 

Names for memory, registers and functions may change, but are named according to the unfinished
[hardware megadoc](https://docs.google.com/document/d/1pdENQW1TpfwI13OxSud_IjoWcnCqHppCCFDhUVSScKc/edit?usp=sharing)
(which should eventually become a wiki) and what is left in the older
[addresses & registers spreadsheet](https://docs.google.com/spreadsheets/d/1Y0LgEqUD9ecm6lZwzL1_wo04XM952WdqCpiu2WO141Q/edit?usp=sharing).

## Save States

The `savestate` and `loadstate` commands above allow the contents of multiple memory addresses and
regions to be stored in a single file in a custom format. The `savestate` command takes a
plain-text template file.

Each functional line in a template file defines a memory range to save,
and contains 3 items separated by any whitespace:
the address, the access size in bits, and the length in bytes.
The address and length are parsed the same way as in dump commands.
If the line has a 4th item, it is treated as a name and displayed when saving.
The name should be in quotes if it has spaces.

In the `example_data` directory, an example state file is provided.
When loaded, it should display 4 colored rectangles on a gray background.
In the same directory is an image from the `screencap` command showing the expected output,
and a template text file that was used to create the state.

If you wish to work with the binary state files directly, the current file format is as follows.
I will do my best to not break this format but may extend it if necessary.
- 8-byte header `LPSTATE\0`
- For each memory block:
    - UINT32 block start address, big endian
    - UINT32 block length in bytes, big endian
    - UINT32 access size in bytes (1/2/4)
    - Data (UINT8 \* length)
    - Padding to 4-byte alignment
- End of file
