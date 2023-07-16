#ifndef _INC_SERIAL_H_
#define _INC_SERIAL_H_

void serialBegin(int baud);
void serialWrite(char c);
void serialPrint(char *s);
int serialAvailable();
char serialRead();

void midiBegin(int baud);
void midiWrite(char c);
void midiPrint(char *s);

void serial_RxI0();
void serial_ERI0();

#endif

