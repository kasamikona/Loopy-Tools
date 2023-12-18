    .section .header.pointers
    .long __clheader_romfirst
    .long __clheader_romlast
    .long 0xa5a5a5a5 /* Placeholder checksum */
    .long 0xffffffff
    .long __clheader_sramfirst
    .long __clheader_sramlast
    .long 0xfffffffe

    ! NOT REQUIRED, and you can put anything you want here.
    ! Can move to a separate .s file keeping the .section line.
    ! Example in the format of Wanwan header:
!    .section .header.copyright
!    .long 0
!    .asciz "(C)1995 GAZIO All right reserved."
!    .asciz "ver 5.51"


    .section .text.startup
    .globl start
start:
    ! Set up initial stack pointer
    mov.l stackaddr, r15
    mov #0, r0

    ! Initialize bss, data, and ctors
    mov.l crtinitaddr, r0
    jsr @r0
    nop

    ! Setup VBR
    mov.l vbraddr, r1
    ldc	r1, vbr

    ! Execute main program
    mov.l mainaddr, r0
    jsr @r0
    nop

    ! IF main program ever exits, halt
terminated:
    bra terminated
    nop

    .align 4
stackaddr:
    .long __stack_end
vbraddr:
    .long __vbr_link_start
crtinitaddr:
    .long _crt_init
mainaddr:
    .long _main

    .end
