#!/usr/bin/env python3

import struct, sys, os

ROM_BASE = 0x0E000000

def check(data):
	check_start, check_end, check_expect = struct.unpack(">LLL", data[0:12])
	check_start -= ROM_BASE
	check_end -= ROM_BASE
	if check_start < 0 or check_start >= len(data):
		print("Invalid start address")
		return False
	if check_end < 0 or check_end >= len(data):
		print("Invalid end address")
		return False
	if check_end < check_start or (check_start&1) != 0 or (check_end&1) != 0:
		print("Invalid range")
	#print("Expected checksum: {0:08X}".format(check_expect))
	s = 0
	for i in range(check_start, check_end+1, 2):
		s = (s+struct.unpack(">H", data[i:i+2])[0])&0xFFFFFFFF
	print("Computed checksum: {0:08X} ({1})".format(s, "Match" if s == check_expect else "MISMATCH"))
	return s == check_expect

if __name__ == "__main__":
	if len(sys.argv) == 2:
		if os.path.exists(sys.argv[1]):
			with open(sys.argv[1], "rb") as f:
				data = f.read()
				print("Checking", f.name)
			if check(data):
				print("ROM is valid!")
			else:
				print("ROM is INVALID!")
		else:
			print("File not found")
	else:
		print(sys.argv[0], "<rom file>")
	print()
	