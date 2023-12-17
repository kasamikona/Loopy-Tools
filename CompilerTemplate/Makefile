# Early makefile for Casio Loopy (Kasami, August 2023)
# Based on Wonderful Toolchain package for SuperH

# Normal use: "make clean && make"
# Generate byteswapped ROM for bad flashers: "make clean && make swapped"
# Memory sizes; should use K/M suffix or decimal integer
# Cart rom, maximum 4MB addressable
ROMSIZE = 4M
# Cart save RAM, most have at least 8K if any
SRAMSIZE = 8K
# Allocated stack size, increase if necessary
STACKSIZE = 2K

# ROMPADDING
# 0: no padding, ROMSIZE is a limit
# 1: pad to ROMSIZE
ROMPADDING = 0

# Toolchain programs
WONDERFUL_TOOLCHAIN ?= /opt/wonderful
TOOLBIN ?= $(WONDERFUL_TOOLCHAIN)/toolchain/gcc-sh-elf/bin
#TOOLBIN = /usr/local/bin
PREFIX ?= sh-elf-
#PREFIX = sh1-none-elf-
CC  = $(TOOLBIN)/$(PREFIX)gcc
CXX = $(TOOLBIN)/$(PREFIX)g++
LD  = $(TOOLBIN)/$(PREFIX)ld
OBJ = $(TOOLBIN)/$(PREFIX)objcopy

# File manipulation progs
MV     = mv
MKDIR  = mkdir -p
RMDIR  = rm -rf
FIXSUM = /usr/bin/env python3 ./tools/fixsum.py

# File/dir locations
SRCDIR = ./src
INCDIR = ./include
OBJDIR = ./obj
ROM    = ./rom.bin
ROMSWP = ./rom.nib

# Basic compile options
OPTIMIZE = -Os
LIBS =

# Below here probably doesn't need to be touched

LDSCRIPT = ./tools/loopy.ld

# Source/object lists
SRCS_C  = $(wildcard $(SRCDIR)/*.c)
OBJS_C  = $(patsubst $(SRCDIR)/%.c,$(OBJDIR)/%.o,$(SRCS_C))
SRCS_S  = $(wildcard $(SRCDIR)/*.s)
OBJS_S  = $(patsubst $(SRCDIR)/%.s,$(OBJDIR)/%.o,$(SRCS_S))

CFLAGS   = $(OPTIMIZE) -g -gdwarf-4
CFLAGS  += -m1 -mrenesas
CFLAGS  += -ffreestanding
CFLAGS  += -falign-functions=4 -ffunction-sections -fdata-sections
CFLAGS  += -fomit-frame-pointer -fno-asynchronous-unwind-tables -fno-unwind-tables
CFLAGS  += -Wstack-usage=$(shell numfmt --from=iec $(STACKSIZE)) -I$(INCDIR)

CXXFLAGS  = -std=c++23 -fno-exceptions -fno-non-call-exceptions -fno-rtti -fno-threadsafe-statics

SIZEDEFS  = -Wl,--defsym=ROMSIZE=$(ROMSIZE)
SIZEDEFS += -Wl,--defsym=SRAMSIZE=$(SRAMSIZE)
SIZEDEFS += -Wl,--defsym=STACKSIZE=$(STACKSIZE)

LDFLAGS  = -nostartfiles -nolibc -Wl,--gc-sections -Wl,--no-warn-rwx-segment -Wl,--orphan-handling=error -Wl,--print-memory-usage
LDFLAGS += $(SIZEDEFS) -Wl,-T $(LDSCRIPT) $(LIBS)

.PHONY: clean rom swapped

all: rom

rom: $(ROM)
swapped: $(ROMSWP)

$(ROMSWP): $(ROM)
	$(OBJ) --reverse-bytes=2 -I binary -O binary $(ROM) $(ROMSWP)

%.elf:
	$(CC) $(LDFLAGS) $^ -o $@

%.bin: %.elf
	$(OBJ) -O binary $< $@
	$(FIXSUM) $(ROM)
# pad the rom to an even multiple of 4096 bytes; this is to work
# around a bug in map_pagetable in LoopyMSE. If that bug is fixed,
# this can be removed.
	truncate -s%4096 $(ROM)

rom.elf: $(OBJS_S) $(OBJS_C)

$(OBJDIR)/%.o: $(SRCDIR)/%.s | $(OBJDIR)
	$(CC) $(CFLAGS) -c $< -o $@
$(OBJDIR)/%.o: $(SRCDIR)/%.c | $(OBJDIR)
	$(CC) $(CFLAGS) -c $< -o $@
$(OBJDIR)/%.o: $(SRCDIR)/%.cpp | $(OBJDIR)
	$(CXX) $(CFLAGS) $(CXXFLAGS) -c $< -o $@

$(OBJDIR):
	$(MKDIR) $@

clean:
	$(RMDIR) $(OBJDIR)
	$(RM) $(ROM) $(ROMSWP)
