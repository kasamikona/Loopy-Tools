# Casio Loopy Compiler Template

**Please do not use my tools for creating controversial or offensive content.**  
I feel that the demographic of the Loopy including the modern community is not a suitable place for this.
I can't stop you from doing anything, but I will blacklist you and certainly won't provide support if you do so.
You may contact me privately if you want more of an explanation of why this notice is here.  
This does not constitute a further licensing restriction, but a moral expectation and a polite request.
You may still "use this software for any purpose" as far as the (zlib) license is concerned.

---

The code here produces a basic graphical output that responds to controller input, prints a message on the debug serial port,
and plays a musical jingle taken from the boot screen of original games.
While the header files etc do technically provide full hardware access, the code is far from a comprehensive demonstration of features.
The code structure is also currently a mess of incomplete files and not laid out like a proper SDK.
It mostly exists as a barebones template project to replace an older template that only printed a serial message.

Info on how to use the hardware, with architecture and register descriptions etc, is being collected in
[this document](https://docs.google.com/document/d/1pdENQW1TpfwI13OxSud_IjoWcnCqHppCCFDhUVSScKc/edit?usp=sharing).
This info will hopefully become a wiki eventually, alongside this code project developing into something more like an SDK.
There is currently no complete listing of BIOS functions, but some basic ones are listed in the code.

Disclaimers: This is by no means a robust setup. Things will probably break.
Feel free to let me know through issues, make minor PRs etc.
I'm unlikely to accept major PRs like project restructuring at the moment.
C++ support may be flaky and is currently disabled in the makefile.
My priority is to get everything working *well* for C, and deal with C++ further down the road.
I have no plans to port this project to other languages outside of C/C++.

## Prerequisites

You first need to set up a SuperH GCC toolchain. For Linux:
1. Install the [Wonderful Toolchain wf-pacman](https://wonderful.asie.pl/docs/getting-started/)
2. `wf-pacman -S toolchain-gcc-sh-elf`
3. `export PATH=/opt/wonderful/toolchain/gcc-sh-elf/bin:$PATH`

If you're on Windows I suggest using a Linux VM or WSL2 as Wonderful Toolchain's gcc-sh currently only works on Linux.

You also need Python 3 installed for the checksum fixer script to run.
It will run automatically as part of compilation.

## Building

Once everything is set up, you can build a Loopy ROM by just running `make` in this directory.
It will produce a `rom.bin` file which is ready for direct use on a flash cart or emulator.
To ensure a clean build after modifications you should use `make clean && make`.

The recommended flash cart to run ROMs on real hardware is the [Floopy Drive](https://github.com/partlyhuman/loopycart).
For emulation I recommend (and test against) this [LoopyMSE fork](https://github.com/partlyhuman/LoopyMSE),
which is mostly feature-complete and currently being actively developed to improve accuracy.
There is also limited support in MAME, but I haven't tested it and can't speak for its accuracy or completeness.

Congratulations, you've just compiled and run a new program for the Casio Loopy.
Now go have fun poking around with the code.
