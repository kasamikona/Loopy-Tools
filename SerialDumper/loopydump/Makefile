ROMSIZE = 2M
SRAMSIZE = 8K
ROMPADDING = 0
ROMSWAP = 1

CC  = sh-elf-gcc
CXX = sh-elf-g++
AS  = sh-elf-as
LD  = sh-elf-ld
AR  = sh-elf-ar
OBJ = sh-elf-objcopy
NM  = sh-elf-nm

ARFLAGS   = rv
ASFLAGS   = -big
CFLAGS    = -m1 -fomit-frame-pointer -fno-exceptions -fno-asynchronous-unwind-tables -fno-unwind-tables -nostartfiles -Wl,-T casloopy.ld
CXX_FLAGS = -std=c++17 $(CFLAGS)

MEMSIZE_LD = "\
ROMSIZE = $(ROMSIZE); \
SRAMSIZE = $(SRAMSIZE);"

all: src/vectors.s src/header.s src/crt0.s src/main.cpp
	echo $(MEMSIZE_LD) >memsize.ld
	# $(CXX) $(CXX_FLAGS) src/main.cpp -S -fverbose-asm -o rom.out.S
	$(CXX) $(CXX_FLAGS) $^ -o rom.out
	$(OBJ) -R .stack -O binary rom.out rom.bin
ifeq ($(ROMPADDING), 1)
	mv rom.bin rom_source.bin
	dd if=/dev/zero ibs=$(ROMSIZE) count=1 | tr "\000" "\377" >rom.bin
	dd if=rom_source.bin of=rom.bin conv=notrunc status=none
	rm rom_source.bin
endif
ifeq ($(ROMSWAP), 1)
	dd if=rom.bin of=rom.swap.bin conv=swab status=none
endif
		

.PHONY: clean
clean:
	$(RM) rom.out rom.bin rom.swap.bin memsize.ld
