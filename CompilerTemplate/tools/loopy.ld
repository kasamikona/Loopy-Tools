/* Import ROMSIZE, SRAMSIZE, STACKSIZE, ROMPADDING(bool) */
/* ROMPADDING value is just used to build header properly */

OUTPUT_FORMAT("elf32-sh", "elf32-sh", "elf32-sh")
OUTPUT_ARCH(sh)

MEMORY {
    /* Console side */
    RAM (rwx) : ORIGIN = 0x09000000, LENGTH = 512K - STACKSIZE
    /* Cartridge side */
    ROM (rwx) : ORIGIN = 0x0E000000, LENGTH = ROMSIZE
    SRAM (rwx) : ORIGIN = 0x02000000, LENGTH = SRAMSIZE
}

SECTIONS {
  . = ORIGIN(ROM);

  .header : {
    KEEP(*(.header.pointers))
    KEEP(*(.header.copyright))

    . = 0x80;
  } >ROM =0xFF
  
  .vectors ALIGN(4) : SUBALIGN(4) {
    KEEP(*(.vectors))

    . = 0x1D0;

    /* 560 bytes spare in vectable, put small functions here */
    KEEP(*(.lowfunc))
    KEEP(*(.smallfunc))
  } >ROM =0xFF

  . = ORIGIN(ROM) + 0x480;

  .text ALIGN(4) : SUBALIGN(4)
  {
    *(.text.startup)
    *(.text)
    *(.text.*)

  } >ROM =0xFF

  __text_link_start = ADDR(.text);
  __text_link_end = ADDR(.text) + SIZEOF(.text);

  .rodata ALIGN(4) : SUBALIGN(4) {
    *(.rodata)
    *(.rodata.*)
  } >ROM

  __rodata_link_start = ADDR(.rodata);
  __rodata_link_end = ADDR(.rodata) + SIZEOF(.rodata);

  .ctors ALIGN(4) : SUBALIGN(4)
  {
    KEEP(*(.ctors))
    KEEP(*(.ctors.*))
  } >ROM

    . = ALIGN(4096);

  __ctors_link_start = ADDR(.ctors);
  __ctors_link_end = ADDR(.ctors) + SIZEOF(.ctors);

  /* reserve 256 bytes at the beginning of RAM for the BIOS */
  . = ORIGIN(RAM) + 0x100;

  .data ALIGN(4) : SUBALIGN(4) {
    *(.data)
    *(.data.*)

    KEEP(*(.ramtext))
    KEEP(*(.ramfunc))
  } >RAM AT> ROM

  __data_link_start = ADDR(.data);
  __data_link_end = ADDR(.data) + SIZEOF(.data);
  __data_load_start = LOADADDR(.data);

  .bss ALIGN(4) (NOLOAD) : SUBALIGN(4) {
    *(.bss)
    *(.bss.*)
    *(COMMON)
  } >RAM

  __bss_link_start = ADDR(.bss);
  __bss_link_end = ADDR(.bss) + SIZEOF(.bss);

  INCLUDE "tools/debug.ld"
}

__clheader_romfirst = ADDR(.vectors);
__clheader_romlast = LOADADDR(.data) + SIZEOF(.data) - 2;
__clheader_sramfirst = ORIGIN(SRAM);
__clheader_sramlast = ORIGIN(SRAM) + LENGTH(SRAM) - 1;

__stack_end = ORIGIN(RAM) + LENGTH(RAM) + STACKSIZE;

__vbr_link_start = ADDR(.vectors);

ENTRY(start);
