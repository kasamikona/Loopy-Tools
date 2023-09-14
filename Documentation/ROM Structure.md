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
|`00001C-⁠00007F`|Padding (sometimes contains copyright text)|`FFFFFFFF...`|
|`000080-⁠00024F`|Vector table, seemingly not required to be here as the ROM itself is responsible for setting VBR?|`0E000AC0...`|
|`000250-⁠00047F`|Padding / free space, sometimes contains small vector code|`FFFFFFFF...`|
|`000480-⁠ROMEND`|Entry point and rest of ROM code/data; BIOS jumps to `0E000480` to begin execution|(code)

If SRAM first/last is outside the range `02000000-02FFFFFF`, or if last <= first, there is no SRAM.
Otherwise physical SRAM size in bytes = `last + 1 - first`.
Addresses should be mapped modulo size to match hardware mirroring, i.e. `02000003` is always mapped to SRAM+3 regardless of start.  

Note: the Magical Shop addon does not have a header, but otherwise behaves as a normal cart and follows normal structure.
Treat this as the exception, not the rule. All other originally-released software uses this header format and you should too.
If you require a suitable header for Magical Shop (1MiB ROM, valid checksum, no SRAM), overwrite the first 28 bytes with
`0E000080 0E0FFFFE 40F54DD7 FFFFFFFF 02FFFFFF 02FFFFFE FFFFFFFE`  

The checksum is not critical as games boot regardless, but any debug menus that check it (e.g PC Collection) will obviously fail.
Dumpers can easily use the checksum to validate a clean dump.
A tool `romintegrity.py` is included here which does this.
The same is run automatically by the serial dumper `loopydump.py` on completion.  

Note: all data is stored as **big-endian** on SuperH architecture, and dumps should ideally preserve this!
For example a raw dump .bin should start with `0E000080`, **not** `000E8000`.
Many ROM reader tools in 16bit mode will output little-endian, so old dumps shared online are byte-swapped, beware.
SuperH compiler toolchains should output big-endian code (gcc-sh does).  

If you need to swap endianness for some reason, a quick way is `dd if=input.bin of=output.bin conv=swab`,
but if you'd rather not use `dd` there are plenty of other capable tools out there.
Recent versions of the Xgpro EPROM programmer tool include a byte-swapping function.  
