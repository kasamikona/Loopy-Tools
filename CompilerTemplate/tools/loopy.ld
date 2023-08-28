/* Import ROMSIZE, SRAMSIZE, STACKSIZE, ROMPADDING(bool) */
/* ROMPADDING value is just used to build header properly */

OUTPUT_ARCH(sh)
OUTPUT_FORMAT("binary")

MEMORY {
    /* Console side */
    RAM (rwx) : ORIGIN = 0x09000000, LENGTH = 512K
    /* Cartridge side */
    ROM (rwx) : ORIGIN = 0x0E000000, LENGTH = ROMSIZE
    SRAM (rwx) : ORIGIN = 0x02000000, LENGTH = SRAMSIZE
}

SECTIONS {
  .clheader : {
    LONG(__clheader_romfirst)
    LONG(__clheader_romlast)
    LONG(0xA5A5A5A5) /* Placeholder checksum */
    LONG(-1)
    LONG(__clheader_sramfirst)
    LONG(__clheader_sramlast)
    LONG(-2)
    KEEP(*(.copyright))
    . = 0x80;
  } >ROM =0xFF
  
  .vectors : ALIGN(4) {
    KEEP(*(.vectors))
    . = 0x1D0;
    /* 560 bytes spare in vectable, put small functions here */
    KEEP(*(.lowfunc))
    KEEP(*(.smallfunc))
    . = 0x400;
  } >ROM =0xFF
  
  .text : {
    __text_start = .;
    *(.text.startup)
    *(.text .text.*)
    *(.rodata .rodata.*)
    . = ALIGN(4);
    __text_end = .;
  } >ROM =0xFF
  
  .bss (NOLOAD) : {
    /* Reserve low RAM for BIOS */
    . = 0x100;
    __bss_start = . ;
    *(.bss .bss.*)
    *(COMMON)
    . = ALIGN(4);
    __bss_end = . ;
  } >RAM
  
  .init : AT(__text_end) {
    . = ALIGN(4);
    __data_start = .;
    *(.data*)
    KEEP(*(.ramtext))
    KEEP(*(.ramfunc))
    . = ALIGN(4);
    __data_end = .;
  } >RAM
  
  .stack : {
    . = ORIGIN(RAM)+LENGTH(RAM)-STACKSIZE;
    /*__stack_start = .;*/
    . = . + STACKSIZE;
    __stack_end = .;
  } >RAM
}

__vbr_start = ADDR(.vectors);
__clheader_romfirst = __vbr_start;
__clheader_romlast = (ROMPADDING ? ORIGIN(ROM) + LENGTH(ROM) : __text_end + SIZEOF(.init)) - 2;
__clheader_sramfirst = ORIGIN(SRAM);
__clheader_sramlast = ORIGIN(SRAM) + LENGTH(SRAM) - 1;

ENTRY(__text_start);
