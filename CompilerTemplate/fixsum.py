import struct, sys, os
ROM_BASE = 0x0E000000
with open(sys.argv[1],"r+b") as f:
	check_start, check_end = struct.unpack(">LL", f.read(8))
	f.seek(check_start-ROM_BASE)
	check_data = f.read(check_end+2-check_start)
	s = 0
	for i in range(0, len(check_data), 2):
		s = (s+struct.unpack(">H", check_data[i:i+2])[0])&0xFFFFFFFF
	f.seek(8)
	f.write(struct.pack(">L", s))

