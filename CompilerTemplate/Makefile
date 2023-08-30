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
TOOLBIN = $(WONDERFUL_TOOLCHAIN)/toolchain/gcc-sh-elf/bin
CC  = $(TOOLBIN)/sh-elf-gcc
LD  = $(TOOLBIN)/sh-elf-ld
OBJ = $(TOOLBIN)/sh-elf-objcopy

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
LIBS = -lm

# Below here probably doesn't need to be touched

LDSCRIPT = ./tools/loopy.ld

# Source/object lists
SRCS_C  = $(wildcard $(SRCDIR)/*.c)
OBJS_C  = $(patsubst $(SRCDIR)/%.c,$(OBJDIR)/%.o,$(SRCS_C))
SRCS_S  = $(wildcard $(SRCDIR)/*.s)
OBJS_S  = $(patsubst $(SRCDIR)/%.s,$(OBJDIR)/%.o,$(SRCS_S))

SIZEDEFS  = -Wl,--defsym=ROMSIZE=$(ROMSIZE),--defsym=SRAMSIZE=$(SRAMSIZE),--defsym=STACKSIZE=$(STACKSIZE),--defsym=ROMPADDING=$(ROMPADDING)

CFLAGS  = -m1 -mrenesas $(OPTIMIZE) -fomit-frame-pointer -fno-exceptions -fno-asynchronous-unwind-tables -fno-unwind-tables -nostartfiles -Wstack-usage=$(shell numfmt --from=iec $(STACKSIZE)) -I$(INCDIR) -flto
LDFLAGS = $(SIZEDEFS) -Wl,-T $(LDSCRIPT) -nostartfiles $(LIBS)

.PHONY: clean rom swapped

all: rom

rom: $(ROM)
swapped: $(ROMSWP)

$(ROMSWP): $(ROM)
	$(OBJ) --reverse-bytes=2 -I binary -O binary $(ROM) $(ROMSWP)

$(ROM): $(OBJS_S) $(OBJS_C)
	$(CC) $(LDFLAGS) $^ -o $@
	$(FIXSUM) $(ROM)
ifeq ($(ROMPADDING), 1)
	$(OBJ) --pad-to=$(shell numfmt --from=iec $(ROMSIZE)) -I binary -O binary $(ROM)
endif

$(OBJDIR)/%.o: $(SRCDIR)/%.s | $(OBJDIR)
	$(CC) $(CFLAGS) -c $< -o $@
$(OBJDIR)/%.o: $(SRCDIR)/%.c | $(OBJDIR)
	$(CC) $(CFLAGS) -c $< -o $@
	
$(OBJDIR):
	$(MKDIR) $@

clean:
	$(RMDIR) $(OBJDIR)
	$(RM) $(ROM) $(ROMSWP)
