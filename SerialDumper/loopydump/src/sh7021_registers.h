#include <stdint.h>

#define SMR0 (*((volatile uint8_t*) 0x05FFFEC0))
#define BRR0 (*((volatile uint8_t*) 0x05FFFEC1))
#define SCR0 (*((volatile uint8_t*) 0x05FFFEC2))
#define TDR0 (*((volatile uint8_t*) 0x05FFFEC3))
#define SSR0 (*((volatile uint8_t*) 0x05FFFEC4))
#define RDR0 (*((volatile uint8_t*) 0x05FFFEC5))
#define SMR1 (*((volatile uint8_t*) 0x05FFFEC8))
#define BRR1 (*((volatile uint8_t*) 0x05FFFEC9))
#define SCR1 (*((volatile uint8_t*) 0x05FFFECA))
#define TDR1 (*((volatile uint8_t*) 0x05FFFECB))
#define SSR1 (*((volatile uint8_t*) 0x05FFFECC))
#define RDR1 (*((volatile uint8_t*) 0x05FFFECD))

#define PBCR1 (*((volatile uint16_t*) 0x05FFFFCC))

#define IPRA (*((volatile uint16_t*) 0x05FFFF84))
#define IPRB (*((volatile uint16_t*) 0x05FFFF86))
#define IPRC (*((volatile uint16_t*) 0x05FFFF88))
#define IPRD (*((volatile uint16_t*) 0x05FFFF8A))
#define IPRE (*((volatile uint16_t*) 0x05FFFF8C))
#define ICR (*((volatile uint16_t*) 0x05FFFF8E))
