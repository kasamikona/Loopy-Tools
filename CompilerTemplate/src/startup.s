    .globl start

    ! NOT REQUIRED, and you can put anything you want here.
    ! Can move to a separate .s file keeping the .section line.
    ! Example in the format of Wanwan header:
!    .section .copyright
!    .long 0
!    .asciz "(C)1995 GAZIO All right reserved."
!    .asciz "ver 5.51"


    .section .text.startup

start:
    ! Set up initial stack pointer
    mov.l stackaddr, r15
    mov #0, r0

    ! Clear .bss area in memory
    mov.l clear_bss_start, r1
    mov.l clear_bss_end, r2

clear_bss_loop:
    mov.w r0, @r1
    add #2, r1
    cmp/hs r2, r1
    bf clear_bss_loop

    ! Copy .data into memory
    mov.l copy_data_from, r1
    mov.l copy_data_to, r2
    mov.l copy_data_end, r3
    
copy_data_loop:
    mov.w @r1+, r0
    mov.w r0, @r2
    add #2, r2
    cmp/hs r3, r2
    bf copy_data_loop

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
clear_bss_start:
    .long __bss_start
clear_bss_end:
    .long __bss_end
copy_data_from:
    .long __text_end
copy_data_to:
    .long __data_start
copy_data_end:
    .long __data_end
stackaddr:
    .long __stack_end
vbraddr:
    .long __vbr_start
mainaddr:
    .long _main

    .end
