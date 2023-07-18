#include "loopy.h"
#include "serial.h"

#define PORT_SERIALMOD 0

char* message = "\r\n\r\n\
 ;xKNXK00kc.       ,oO0xoc,.\r\n\
dNW0c'..'l0k'     .xWKl,coxkxdl;'.\r\n\
NMK,      ,0k,':clkNWk.    .':ldkkxo:.\r\n\
WMK;       c0Oxdo0WXKK0c.        .;lx0d'\r\n\
OWWx.       ..  'OO,.:KWd.           cX0\r\n\
,KMNl          .xK:  .xWX;           '0W\r\n\
 lNMK;         oKl...cKMK,.ooc,.    'xWX\r\n\
 .xWMO.       ;KXxd0XNMXc.xWMMWXOxxOXWKc\r\n\
  '0MWd. .':oxKWMMWXKOo'.lNMXxdOKXK0kc.\r\n\
   :XMNOOKNMWNKXWXd,....oXMNl   ....\r\n\
   .oWWWXOxl;'.'dKX0OO0XWW0:\r\n\
    'xxc'.       ;xXNWWN0l.\r\n\
\r\n\
      Casio Loopy says hello world\r\n\
  Example code by kasamikona July 2023\r\n\
\r\n\
Echoing received data: \
";

static void arbDelay(int loops) {
    // Rough arbitrary delay function
    for(int i = 0; i < loops; i++) {
        asm volatile ("nop");
    }
}

int main() {
    maskInterrupts(0);
    serialBegin(9600);
    arbDelay(1000);
    serialPrint(message);
    
    while(1) {
        if(serialAvailable()) serialWrite(serialRead());
    }
}
