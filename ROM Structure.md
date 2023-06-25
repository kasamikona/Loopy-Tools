Offset in bytes. ROM base is `0E000000`. Example values taken from "Dream Change" XK-403 dump.  

|Offset|Purpose|Example|
|--|--|--|
|`000000`|Pointer to first word after header, normally vector table start|`0E000080`|
|`000004`|Pointer to last word of ROM|`0E1FFFFE`|
|`000008`|Checksum; a 32bit sum of unsigned 16bit words from end of header to last word of ROM, inclusive, according to the above pointers|`F6D41645`|
|`00000C`|Padding|`FFFFFFFF`|
|`000010`|Pointer to first byte of SRAM|`02000000`|
|`000014`|Pointer to last byte of SRAM|`02001FFF`|
|`000018`|Header end marker?|`FFFFFFFE`|
|`00001C-00007F`|Padding (sometimes contains copyright text)|`FFFFFFFF...`|
|`000080-00024F`|Vector table, seemingly not required to be here as the ROM itself is responsible for setting VBR?|`0E000AC0...`|
|`000250-00047F`|Padding / free space, sometimes contains small vector code|`FFFFFFFF...`|
|`000480-ROMEND`|Entry point and rest of ROM code/data; BIOS jumps to `0E000480` to begin execution|(code)

The checksum is not critical as games boot regardless, but any debug menus that check it (e.g PC Collection) will obviously fail.
Dumpers can easily use the checksum to validate a clean dump.
A tool `romintegrity.py` is included here which does this.
The same is run automatically by the serial dumper `loopydump.py` on completion.

Note: all data is stored as **big-endian** on SuperH architecture, and dumps should ideally preserve this!
For example a raw dump .bin should start with `0E 00 ..`, not `00 0E ..`.
Many ROM reader tools in 16bit mode will output little-endian, so old online dumps are byte-swapped, beware.
SuperH compiler toolchains should output big-endian code (gcc-sh does).  

If you need to swap endianness for some reason, a quick way is `dd if=input.bin of=output.bin conv=swab`,
but if you'd rather not use `dd` there seem to be plenty of other tools out there.  
