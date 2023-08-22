#ifndef _INC_LOOPY_H_
#define _INC_LOOPY_H_

#define F_CPU 16000000

#include "shregs.h"

static void maskInterrupts(int mask) {
    uint32_t sr;
    mask &= 0xF;
    mask <<= 4;
    __asm__ __volatile__("STC SR,%0\n\t" : "=r" (sr) : : );
    sr &= 0xFFFFFF0F;
    sr |= mask;
    __asm__ __volatile__("LDC %0,SR\n\t" : : "r" (sr) : );
}

#endif
