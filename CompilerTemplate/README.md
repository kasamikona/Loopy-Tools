# Casio Loopy Compiler Template

### Please do not use my tools or materials here for creating NSFW or offensive content.
**The demographic of the Loopy including the modern community is not a suitable place for this.**
**I can't stop you from doing anything, but I will blacklist you and certainly won't provide support if you do so.** 

---

**NOTE: This code currently produces no graphics or audio.**  
We are working on reverse-engineering and documenting the rest of the hardware beyond the CPU,
and have successfully produced graphics and audio in small tests, but don't have a great interface for it yet.
With that said, this is *technically* a fully functional compiler setup,
and it is already being used to develop some small games.

The code provided was originally designed for testing with the serial mod described in the SerialDumper section of this repo,
but since then the awesome [Floopy Drive](https://github.com/partlyhuman/loopycart) flash cart project
has added direct serial connection through the cart.  

Additional disclaimers: This is by no means a robust setup. Things will probably break.
Feel free to let me know through issues, PRs etc.
C++ support may be flaky. It *should* work with the current setup but it's entirely untested on my end.
My priority is to get everything working *well* for C, and deal with C++ further down the road.

## Prerequisites

You first need to set up a SuperH GCC toolchain. For Linux:
1. Install the [Wonderful Toolchain wf-pacman](https://wonderful.asie.pl/docs/getting-started/)
2. `wf-pacman -S toolchain-gcc-sh-elf`
3. `export PATH=/opt/wonderful/toolchain/gcc-sh-elf/bin:$PATH`

If you're on Windows I suggest using a Linux VM or WSL2 as Wonderful Toolchain is currently Linux only.  

For the time being, you also need Python 3 installed if you want the checksum fixer script to run.
It will run automatically as part of compilation.
This will probably be replaced with a small self-contained C program soon.  

## Building

Once everything is set up, you can build a Loopy ROM by just running `make` in this directory.
It will produce a `rom.bin` file which is ready for direct use on a flash cart or emulator.  

To ensure a clean build after modifications you should use `make clean && make`.  

## Testing with the serial mod

Flash the resulting ROM file to a flash cart and put it in your Loopy.
Connect the serial mod adapter to your PC and open a terminal connection at 9600 baud.
When you power on the Loopy you should see an ASCII-art Loopy "LP" hearts logo and a hello world message.
Assuming you have a working bidirectional serial mod, you can start typing and the Loopy will echo your keypresses back to your terminal.  

![serialdemo.gif](serialdemo.gif)

Congratulations, you've just compiled and run new code on a Casio Loopy.
Now go have fun poking around with the code... when there's something more interesting to do.  

## What's in the files?

A basic rundown of the files is as follows:  
- Makefile: A makefile to compile for the Loopy. Some build options like stack size are configurable.
- loopy.ld: Linker script used by GCC to construct the ROM, including the header layout.
- fixsum.py: A post-compilation Python script that calculates and injects the checksum into the ROM header.
- src/startup.s, src/crt0.c: Initializes the system and C runtime, and calls main().
- src/main.c: The main program. Sets up a serial connection, prints to it, and then echoes anything it receives.
- src/vectors.c: Interrupt vector table and supporting functions. Unused vectors either do nothing or halt.
- src/serial.c, include/serial.h: Basic serial interface layer with blocking writes and buffered reads, similar to Arduino.
- include/loopy.h: Loopy-specific definitions, includes sh7021_peripherals.h.
- include/sh7021_peripherals.h: Definitions for SH7021 on-chip peripheral registers.
