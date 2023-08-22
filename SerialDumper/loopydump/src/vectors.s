    .globl vector_table

    .section .vectors

vector_table:
v_PowerOnReset:
    .long halt
    .long halt
v_ManualReset:
    .long halt
    .long halt
v_GeneralIllegalInstruction:
    .long halt
    .long reserved
v_IllegalSlotInstruction:
    .long halt
    .long reserved
    .long reserved
v_CPUAddressError:
    .long halt
v_DMAAddressError:
    .long halt
v_NMI:
    .long doNothing
v_UserBreak:
    .long halt
    .long reserved
    .long reserved
    .long reserved
    .long reserved
    .long reserved
    .long reserved
    .long reserved
    .long reserved
    .long reserved
    .long reserved
    .long reserved
    .long reserved
    .long reserved
    .long reserved
    .long reserved
    .long reserved
    .long reserved
    .long reserved
    .long reserved
v_Trap_32_63:
    .long halt
    .long halt
    .long halt
    .long halt
    .long halt
    .long halt
    .long halt
    .long halt
    .long halt
    .long halt
    .long halt
    .long halt
    .long halt
    .long halt
    .long halt
    .long halt
    .long halt
    .long halt
    .long halt
    .long halt
    .long halt
    .long halt
    .long halt
    .long halt
    .long halt
    .long halt
    .long halt
    .long halt
    .long halt
    .long halt
    .long halt
    .long halt
v_IRQ0:
    .long doNothing
v_IRQ1:
    .long halt
v_IRQ2:
    .long halt
v_IRQ3:
    .long halt
v_IRQ4:
    .long halt
v_IRQ5:
    .long halt
v_IRQ6:
    .long halt
v_IRQ7:
    .long halt
v_DMAC0:
    .long halt
    .long reserved
v_DMAC1:
    .long halt
    .long reserved
v_DMAC2:
    .long halt
    .long reserved
v_DMAC3:
    .long halt
    .long reserved
v_ITU0:
    .long doNothing
    .long halt
    .long halt
    .long reserved
v_ITU1:
    .long halt
    .long halt
    .long halt
    .long reserved
v_ITU2:
    .long halt
    .long halt
    .long halt
    .long reserved
v_ITU3:
    .long halt
    .long halt
    .long halt
    .long reserved
v_ITU4:
    .long halt
    .long halt
    .long halt
    .long reserved
v_SCI0:
    .long halt
    .long halt
    .long halt
    .long halt
v_SCI1:
    .long halt
    .long halt
    .long halt
    .long halt
v_PRT:
    .long halt
    .long reserved
    .long reserved
    .long reserved
v_WDT:
    .long halt
v_REF:
    .long halt
    .long reserved
    .long reserved

    .section .vector_functions

reserved:
halt:
    mov.l r3, @-r15
    mov.l r0, @-r15
    stc sr, r0
    or #0xf0, r0
    ldc r0, sr
halt_loop:
    bra halt_loop
    nop

doNothing:
    rte
    nop
