#!/usr/bin/env python3

import struct, sys, os

ROM_BASE = 0x0E000000

def read_header(data):
	return struct.unpack(">LLL", data[0:12])

def calc_checksum(data, check_start, check_end):
	check_start -= ROM_BASE
	check_end -= ROM_BASE
	if check_start < 0 or check_start >= len(data):
		print("Invalid start address for check range")
		return None
	if check_end < 0 or check_end >= len(data):
		print("Invalid end address for check range")
		return None
	if check_end < check_start or (check_start&1) != 0 or (check_end&1) != 0:
		print("Invalid check range")
		return None
	s = 0
	for i in range(check_start, check_end+1, 2):
		s = (s+struct.unpack(">H", data[i:i+2])[0])&0xFFFFFFFF
	print(f"Computed checksum: {s:08X}")
	return s

def validate(f):
	print("Validating", f.name)
	data = f.read()
	check_start, check_end, checksum_expect = read_header(data)
	print(f"Expected checksum: {checksum_expect:08X}")
	checksum_actual = calc_checksum(data, check_start, check_end)
	valid = False
	if checksum_actual != None:
		valid = (checksum_actual == checksum_expect)
	print("ROM is valid!" if valid else "ROM is INVALID!")
	return valid

def update(f):
	print("Updating", f.name)
	data = f.read()
	check_start, check_end, _ = read_header(data)
	checksum = calc_checksum(data, check_start, check_end)
	if checksum == None:
		return False
	f.seek(8)
	f.write(struct.pack(">L", checksum))
	print(f"Updated checksum")
	return True

if __name__ == "__main__":
	print()
	nargs = len(sys.argv)
	success = False
	if nargs in [2,3]:
		if nargs == 3:
			do_update = (sys.argv[1] == "-u" or sys.argv[1] == "--update")
			fpath = sys.argv[2]
		else:
			do_update = False
			fpath = sys.argv[1]
		if os.path.exists(fpath):
			if do_update:
				with open(fpath, "rb+") as f:
					success = update(f)
			else:
				with open(fpath, "rb") as f:
					success = validate(f)
		else:
			print("File not found")
	else:
		print(sys.argv[0], "[-u/--update] <rom file>")
		print("If '--update' is used, writes the correct checksum in-place (overwrites file!)")
		print("Otherwise, verifies the checksum.")
	print()
	exit(0 if success else 1)
