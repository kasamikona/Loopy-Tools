import struct
from util import check_files, make_dirs_for_file
from lzss_ww import decompress

ROM_BASE = 0x0E000000
RESOURCES_SECTION_PTR = 0x70000
RESOURCES_SECTION_MAX_SIZE = 0x200000-0x70000

def get_res_count_table(sec_data):
	# Load count and table, ensure input is sane
	if len(sec_data) < 4:
		print("Size too small, can't read resource count")
		return None
	res_count = struct.unpack(">I", sec_data[:4])[0]
	if 4+(res_count*4) > len(sec_data):
		print("Size too small, can't read resource table")
		return None
	res_table = struct.unpack(f">{res_count}I", sec_data[4:4+(res_count*4)])
	
	# Validate input size contains at least the start address for all resources
	max_ptr = max(0, max(res_table)-ROM_BASE-RESOURCES_SECTION_PTR)
	if max_ptr >= len(sec_data):
		print("Size too small, some pointers are excluded")
		return None
	
	return (res_count, res_table)

def read_one_resource(sec_data, res_count, res_table, res_index):
	# Get resource pointer
	if res_index < 0 or res_index >= res_count:
		print(f"Resource {res_index} out of range (0-{res_count-1})")
		return None
	res_ptr = res_table[res_index]
	if res_ptr == 0 or res_ptr < ROM_BASE+RESOURCES_SECTION_PTR:
		print(f"Resource {res_index} is null")
		return None
	res_offset = res_ptr - (ROM_BASE+RESOURCES_SECTION_PTR)
	
	# Calculate resource size
	next_ptr = min([p for p in res_table if p > res_ptr], default=None)
	if not next_ptr:
		size = len(sec_data) - res_offset
	else:
		size = next_ptr - res_ptr
	
	# Read the resource data
	res_data = sec_data[res_offset:res_offset+size]
	return res_data

def cmd_extract_sec(args):
	# Parse and verify command arguments
	rom_in = args.path_rom_in
	sec_out = args.path_sec_out
	sec_size = args.sec_size
	if not check_files(exist=[rom_in], noexist=[sec_out]):
		return
	if sec_size <= 0:
		print("Invalid size")
		return
	
	# Read input data
	with open(rom_in, "rb") as rom:
		rom.seek(RESOURCES_SECTION_PTR)
		sec_data = rom.read(sec_size)
		post_data = rom.read(RESOURCES_SECTION_MAX_SIZE-sec_size)
	
	# Validate that the remaining data contains only FF
	for b in post_data:
		if b != 0xFF:
			print("Size too small, some data after end")
			return
	
	# Warn if the data has too many FFs at the end
	check_ff_count = 5
	for i in range(check_ff_count):
		if sec_data[-1-i] != 0xFF:
			break
		if i+1 == check_ff_count:
			print(f"Warning: data ends with at least {check_ff_count} \"FF\" bytes, size may be too large")
	
	# Load section data for validation
	res_count_table = get_res_count_table(sec_data)
	if res_count_table == None:
		return
	
	# Write output data
	make_dirs_for_file(sec_out)
	with open(sec_out, "wb") as sec:
		sec.write(sec_data)
		print(f"Saved resources section to {sec_out}")

def cmd_extract_res(args):
	# Parse and verify command arguments
	sec_in = args.path_sec_in
	res_out = args.path_res_out
	res_index = args.res_index
	comp = args.compressed
	if not check_files(exist=[sec_in], noexist=[res_out]):
		return
	
	# Read input data
	with open(sec_in, "rb") as sec:
		sec_data = sec.read()
	
	# Load and validate section data
	res_count_table = get_res_count_table(sec_data)
	if res_count_table == None:
		return
	res_count, res_table = res_count_table
	
	# Read resource and decompress if requested
	res_data = read_one_resource(sec_data, res_count, res_table, res_index)
	if comp:
		res_data = decompress(res_data)
		if not res_data:
			return
		print(f"Decompressed {len(res_data)} bytes")
	
	# Write output data
	make_dirs_for_file(res_out)
	with open(res_out, "wb") as res:
		res.write(res_data)
		print(f"Saved resource {res_index} to {res_out}")
