/* Import ROMSIZE & SRAMSIZE */
INCLUDE memsize.ld

STACK_SIZE = 0x1000; /* 4KB */

MEMORY {
    /* Console side */
    RAM (rwx) : ORIGIN = 0x09000000, LENGTH = 512K
    /* Cartridge side */
    ROM (rwx) : ORIGIN = 0x0E000000, LENGTH = ROMSIZE
    SRAM (rwx) : ORIGIN = 0x02000000, LENGTH = SRAMSIZE
}

SECTIONS
{
  .header_vectors : {
    KEEP(*(.header))
    . = 0x80;
    KEEP(*(.vectors))
    . = 0x250;
    KEEP(*(.vector_functions))
    . = 0x480;
  } >ROM =0xFF
  
  .text : {
    __text_start = .;
    *(.text .text.*)
    *(.rodata .rodata.*)
    __text_end = .;
  } >ROM =0xFF
  
  .bss (NOLOAD) : {
    . = ALIGN(4);
    __bss_start = . ;
    *(.bss .bss.*)
    *(COMMON)
    __bss_end = . ;
  } >RAM
  
  .init : AT(__text_end) {
    . = ALIGN(4);
    __data_start = .;
    *(.data .data.*)
    . = ALIGN(4);
    KEEP(*(.ramtext .ramtext.*))
    __data_end = .;
  } >RAM
  
  .stack (NOLOAD): {
    . = ALIGN(4);
    __stack_start = .;
    . = . + STACK_SIZE;
    __stack_end = .;
  } >RAM
  
  .romfill : {
    /* . = ROMPADDING ? (ORIGIN(ROM) + LENGTH(ROM) - 1) : .; */
    /* BYTE(0xFF); */
    . = ALIGN(2);
  } >ROM =0xFF
}

_header_romlast = ORIGIN(ROM) + LENGTH(ROM) - 2;
_header_sramfirst = ORIGIN(SRAM);
_header_sramlast = ORIGIN(SRAM) + LENGTH(SRAM) - 1;

ENTRY(__text_start);
