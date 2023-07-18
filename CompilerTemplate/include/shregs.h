#ifndef _INC_SHREGS_H_
#define _INC_SHREGS_H_

#include <stdint.h>

#define _REG8(ADDR) (*((volatile uint8_t*) ADDR))
#define _REG16(ADDR) (*((volatile uint16_t*) ADDR))
#define _REG32(ADDR) (*((volatile uint32_t*) ADDR))

/*
NOTE both ITU and DMAC modules have "TCR" registers.
This file prefixes them with ITU_ and DMA_ to disambiguate.
If you want shorter names, create your own defines e.g.
#define TCR0 ITU_TCR0
*/

// Serial Communication Interface (SCI)
#define SMR0 _REG8(0x5FFFEC0)
#define BRR0 _REG8(0x5FFFEC1)
#define SCR0 _REG8(0x5FFFEC2)
#define TDR0 _REG8(0x5FFFEC3)
#define SSR0 _REG8(0x5FFFEC4)
#define RDR0 _REG8(0x5FFFEC5)
#define SMR1 _REG8(0x5FFFEC8)
#define BRR1 _REG8(0x5FFFEC9)
#define SCR1 _REG8(0x5FFFECA)
#define TDR1 _REG8(0x5FFFECB)
#define SSR1 _REG8(0x5FFFECC)
#define RDR1 _REG8(0x5FFFECD)

// Integrated-Timer Pulse Unit (ITU)
#define TSTR _REG8(0x5FFFF00)
#define TSNC _REG8(0x5FFFF01)
#define TMDR _REG8(0x5FFFF02)
#define TFCR _REG8(0x5FFFF03)
#define ITU_TCR0 _REG8(0x5FFFF04)
#define TIOR0 _REG8(0x5FFFF05)
#define TIER0 _REG8(0x5FFFF06)
#define TSR0 _REG8(0x5FFFF07)
#define TCNT0 _REG16(0x5FFFF08)
#define GRA0 _REG16(0x5FFFF0A)
#define GRB0 _REG16(0x5FFFF0C)
#define ITU_TCR1 _REG8(0x5FFFF0E)
#define TIOR1 _REG8(0x5FFFF0F)
#define TIER1 _REG8(0x5FFFF10)
#define TSR1 _REG8(0x5FFFF11)
#define TCNT1 _REG16(0x5FFFF12)
#define GRA1 _REG16(0x5FFFF14)
#define GRB1 _REG16(0x5FFFF16)
#define ITU_TCR2 _REG8(0x5FFFF18)
#define TIOR2 _REG8(0x5FFFF19)
#define TIER2 _REG8(0x5FFFF1A)
#define TSR2 _REG8(0x5FFFF1B)
#define TCNT2 _REG16(0x5FFFF1C)
#define GRA2 _REG16(0x5FFFF1E)
#define GRB2 _REG16(0x5FFFF20)
#define ITU_TCR3 _REG8(0x5FFFF22)
#define TIOR3 _REG8(0x5FFFF23)
#define TIER3 _REG8(0x5FFFF24)
#define TSR3 _REG8(0x5FFFF25)
#define TCNT3 _REG16(0x5FFFF26)
#define GRA3 _REG16(0x5FFFF28)
#define GRB3 _REG16(0x5FFFF2A)
#define BRA3 _REG16(0x5FFFF2C)
#define BRB3 _REG16(0x5FFFF2E)
#define TOCR _REG8(0x5FFFF31)
#define ITU_TCR4 _REG8(0x5FFFF32)
#define TIOR4 _REG8(0x5FFFF33)
#define TIER4 _REG8(0x5FFFF34)
#define TSR4 _REG8(0x5FFFF35)
#define TCNT4 _REG16(0x5FFFF36)
#define GRA4 _REG16(0x5FFFF38)
#define GRB4 _REG16(0x5FFFF3A)
#define BRA4 _REG16(0x5FFFF3C)
#define BRB4 _REG16(0x5FFFF3E)

// DMA Controller (DMAC)
// TCR registers prefixed with DMA to disambiguate
#define SAR0 _REG32(0x5FFFF40)
#define DAR0 _REG32(0x5FFFF44)
#define DMAOR _REG16(0x5FFFF48)
#define DMATCR0 _REG16(0x5FFFF4A)
#define CHCR0 _REG16(0x5FFFF4E)
#define SAR1 _REG32(0x5FFFF50)
#define DAR1 _REG32(0x5FFFF54)
#define DMATCR1 _REG16(0x5FFFF5A)
#define CHCR1 _REG16(0x5FFFF5E)
#define SAR2 _REG32(0x5FFFF60)
#define DAR2 _REG32(0x5FFFF64)
#define DMATCR2 _REG16(0x5FFFF6A)
#define CHCR2 _REG16(0x5FFFF6E)
#define SAR3 _REG32(0x5FFFF70)
#define DAR3 _REG32(0x5FFFF74)
#define DMATCR3 _REG16(0x5FFFF7A)
#define CHCR3 _REG16(0x5FFFF7E)

// Interrupt Controller (INTC)
#define IPRA _REG16(0x5FFFF84)
#define IPRB _REG16(0x5FFFF86)
#define IPRC _REG16(0x5FFFF88)
#define IPRD _REG16(0x5FFFF8A)
#define IPRE _REG16(0x5FFFF8C)
#define ICR _REG16(0x5FFFF8E)

// User Break Controller (UBC)
#define BARH _REG16(0x5FFFF90)
#define BARL _REG16(0x5FFFF92)
#define BAMRH _REG16(0x5FFFF94)
#define BAMRL _REG16(0x5FFFF96)
#define BBR _REG16(0x5FFFF98)

// Bus State Controller (BSC)
#define BCR _REG16(0x5FFFFA0)
#define WCR1 _REG16(0x5FFFFA2)
#define WCR2 _REG16(0x5FFFFA4)
#define WCR3 _REG16(0x5FFFFA6)
#define DCR _REG16(0x5FFFFA8)
#define PCR _REG16(0x5FFFFAA)
#define RCR _REG16(0x5FFFFAC)
#define RTCSR _REG16(0x5FFFFAE)
#define RTCNT _REG16(0x5FFFFB0)
#define RTCOR _REG16(0x5FFFFB2)

// Watchdog Timer (WDT)
// These are a *mess*, read the datasheet...
#define TCSR_TCNT_W _REG16(0x5FFFFB8)
#define TCSR_R _REG8(0x5FFFFB8)
#define TCNT_R _REG8(0x5FFFFB9)
#define RSTCSR_W _REG16(0x5FFFFBA)
#define RSTCSR_R _REG8(0x5FFFFBB)

// Power Control
#define SBYCR _REG8(0x5FFFFBC)

// Parallel I/O Ports
#define PADR _REG16(0x5FFFFC0)
#define PBDR _REG16(0x5FFFFC2)

// Pin Function Controller (PFC)
#define PAIOR _REG16(0x5FFFFC4)
#define PBIOR _REG16(0x5FFFFC6)
#define PACR1 _REG16(0x5FFFFC8)
#define PACR2 _REG16(0x5FFFFCA)
#define PBCR1 _REG16(0x5FFFFCC)
#define PBCR2 _REG16(0x5FFFFCE)
#define CASCR _REG16(0x5FFFFEE)

// Programmable Timing Pattern Controller (TPC)
// Module also uses PBDR, PBCR1, PBCR2
#define TPMR _REG8(0x05FFFFF0)
#define TPCR _REG8(0x05FFFFF1)
#define NDERB _REG8(0x05FFFFF2)
#define NDERA _REG8(0x05FFFFF3)
#define NDRB3 _REG8(0x05FFFFF4)
#define NDRA1 _REG8(0x05FFFFF5)
#define NDRB2 _REG8(0x05FFFFF6)
#define NDRA0 _REG8(0x05FFFFF7)
#define NDRB NDRB3
#define NDRA NDRA1

#endif
