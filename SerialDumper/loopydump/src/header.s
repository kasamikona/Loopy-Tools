    .section .header

header_start:
    .long vector_table
    .long _header_romlast
    .long 0xA5A5A5A5 ! Checksum placeholder
    .long 0xFFFFFFFF
    .long _header_sramfirst
    .long _header_sramlast
    .long 0xFFFFFFFE
