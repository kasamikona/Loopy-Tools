#include <stdint.h>
#include "sh7021_registers.h"

#define SERIAL_BUFFER_SIZE 256

void* ramvt[116];
uint8_t serialBuffer[SERIAL_BUFFER_SIZE];
int serialBufferWrite = 0;
int serialBufferRead = 0;

void serialBegin() {
    // Set up for 38400 baud 8N1 full duplex
    PBCR1 = (PBCR1 & 0xFFF0) | 0x000A;
    SMR0 = 0x00;
    BRR0 = 0x0C;
    // Enable transmit, receive, receive interrupts
    SCR0 = 0x70;
    
    // Clear all flags except TDRE
    SSR0;
    SSR0 = 0x80;
    
    // Set nonzero priority
    IPRD = (IPRD & 0xFFF0) | 0x000F;
}

__attribute__((section (".ramtext")))
void serialWrite(uint8_t b) {
    while(!(SSR0 & 0x80)); // Wait for serial ready
    TDR0 = b; // Set serial data
    SSR0 &= 0x7F; // Send data
}

__attribute__((section (".ramtext")))
uint32_t serialAvailable() {
    return (SERIAL_BUFFER_SIZE + serialBufferWrite - serialBufferRead) % SERIAL_BUFFER_SIZE;
}

__attribute__((section (".ramtext")))
uint8_t serialRead() {
    if(serialBufferWrite == serialBufferRead) return 0;
    uint8_t c = serialBuffer[serialBufferRead];
    serialBufferRead = (serialBufferRead+1) % SERIAL_BUFFER_SIZE;
    return c;
}

__attribute__((section (".ramtext")))
void delay(uint32_t loops) {
    for(uint32_t i = 0; i < loops; i++) {
        asm volatile ("nop");
    }
}

__attribute__((section (".ramtext")))
uint32_t crc32(const uint8_t* data, uint32_t length, uint32_t previousCrc32 = 0) { 
     uint32_t crc = ~previousCrc32; // same as previousCrc32 ^ 0xFFFFFFFF 
     while (length--) { 
         crc ^= *data++; 
         for (unsigned int j = 0; j < 8; j++) {
             if (crc & 1) 
                 crc = (crc >> 1) ^ 0xEDB88320; 
             else 
                 crc = crc >> 1; 
         }

     } 
     return ~crc; // same as crc ^ 0xFFFFFFFF 
}


/*
__attribute__((section (".ramtext")))
void printHex32(uint32_t h) {
    for(int i = 28; i >= 0; i-=4) {
        uint8_t c = (h>>i)&15;
        if(c > 9) c += 'A'-10;
        else c += '0';
        serialWrite(c);
    }
    serialWrite('\n');
}
*/

__attribute__((section (".ramtext")))
void ramMain() {
    delay(1000);
    while(true) {
        if(serialAvailable() >= 6) {
            uint32_t origin = 0;
            uint16_t length = 0;
            uint32_t checksum = 0;
            
            // Read header
            origin += serialRead()<<24;
            origin += serialRead()<<16;
            origin += serialRead()<<8;
            origin += serialRead()<<0;
            length += serialRead()<<8;
            length += serialRead()<<0;
            
            // Return header
            serialWrite((origin>>24)&0xFF);
            serialWrite((origin>>16)&0xFF);
            serialWrite((origin>>8)&0xFF);
            serialWrite((origin>>0)&0xFF);
            serialWrite((length>>8)&0xFF);
            serialWrite((length>>0)&0xFF);
            
            // Send requested data
            uint8_t *readFrom = (uint8_t*)origin;
            for(unsigned int i = 0; i < length; i++) {
                uint8_t readByte = *readFrom++;
                serialWrite(readByte);
            }
            
            // Send checksum
            // This serves as a double-read mechanism, hopefully mismatches on open bus
            checksum = crc32((uint8_t*)origin, length, 0);
            serialWrite((checksum>>24)&0xFF);
            serialWrite((checksum>>16)&0xFF);
            serialWrite((checksum>>8)&0xFF);
            serialWrite((checksum>>0)&0xFF);
        }
        delay(100);
    }
}

__attribute__((section (".ramtext")))
__attribute__((interrupt_handler))
void vectorDoNothing() {
    asm volatile ("nop"); 
}

__attribute__((section (".ramtext")))
__attribute__((interrupt_handler))
void vectorERI0() {
    SSR0; SSR0 &= 0xC7; // Clear error flags
}

__attribute__((section (".ramtext")))
__attribute__((interrupt_handler))
void vectorRxI0() {
    uint8_t c = RDR0;
    SSR0; SSR0 &= 0xBF; // Clear RDRF flag
    
    int serialBufferWriteNew = (serialBufferWrite+1) % SERIAL_BUFFER_SIZE;
    if(serialBufferWriteNew != serialBufferRead) {
        serialBuffer[serialBufferWrite] = c;
        serialBufferWrite = serialBufferWriteNew;
    }
}

int main() {
    serialBegin();

    void** vbr;
    uint32_t sr;
    for(int i = 0; i < 116; i++) {
        ramvt[i] = (void*) &vectorDoNothing;
    }
    ramvt[101] = (void*) &vectorRxI0;
    ramvt[102] = (void*) &vectorERI0;
    vbr = (void**)&ramvt;
    
    // Store VBR, read SR
    __asm__ __volatile__("LDC %0,VBR\n\t"
        : /* no output */
        : "r" (vbr)
        : /* no clobbers */ );
    
    // Read SR
    __asm__ __volatile__("STC SR,%0\n\t"
        : "=r" (sr)
        : /* no input */
        : /* no clobbers */ );
    
    // Clear interrupt mask
    sr &= 0xFFFFFF0F;
    
    // Write back SR
    __asm__ __volatile__("LDC %0,SR\n\t"
        : /* no output */
        : "r" (sr)
        : /* no clobbers */ );
    ramMain();
    return 0;
}
