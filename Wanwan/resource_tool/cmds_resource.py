import struct
from util import check_files, make_dirs_for_file, paths_equivalent
from lzss_ww import compress, decompress

ROM_BASE = 0x0E000000
RESOURCES_SECTION_PTR = 0x70000
RESOURCES_SECTION_DEFAULT_MAX = 0x200000-RESOURCES_SECTION_PTR
RESOURCES_SECTION_HARD_LIMIT = 0x400000-RESOURCES_SECTION_PTR

def _get_res_count_table(sec_data):
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

def _get_res_ptr_size(sec_data, res_count, res_table, res_index):
	# Get resource pointer
	if res_index < 0 or res_index >= res_count:
		print(f"Resource {res_index} out of range (0-{res_count-1})")
		return None
	res_ptr = res_table[res_index]
	if res_ptr < ROM_BASE+RESOURCES_SECTION_PTR:
		res_ptr = 0
	
	# Calculate resource size
	res_size = 0
	if res_ptr != 0:
		next_ptr = min([p for p in res_table if p > res_ptr], default=None)
		if not next_ptr:
			res_offset = res_ptr - (ROM_BASE+RESOURCES_SECTION_PTR)
			res_size = len(sec_data) - res_offset
		else:
			res_size = next_ptr - res_ptr
	
	return (res_ptr, res_size)

def _read_one_resource(sec_data, res_count, res_table, res_index):
	# Locate the resource
	res_ptr_size = _get_res_ptr_size(sec_data, res_count, res_table, res_index)
	if not res_ptr_size:
		return None
	res_ptr, res_size = res_ptr_size
	if res_ptr == 0:
		print(f"Resource {res_index} is null")
		return None
	# Read the data
	res_offset = res_ptr - (ROM_BASE+RESOURCES_SECTION_PTR)
	res_data = sec_data[res_offset:res_offset+size]
	return res_data

def _read_all_resources(sec_data, res_count, res_table):
	resources = [None]*res_count
	for res_index in range(res_count):
		# Locate the resource
		res_ptr, res_size = _get_res_ptr_size(sec_data, res_count, res_table, res_index)
		if res_ptr == 0:
			continue
		# Read the data
		res_offset = res_ptr - (ROM_BASE+RESOURCES_SECTION_PTR)
		res_data = sec_data[res_offset:res_offset+res_size]
		resources[res_index] = res_data
	return resources

def cmd_extract_sec(args):
	# Parse and verify command arguments
	rom_in = args.path_rom_in
	sec_out = args.path_sec_out
	sec_size = args.sec_size
	if not check_files(exist=[rom_in], noexist=[sec_out]):
		return False
	if sec_size <= 0:
		print("Invalid size")
		return False
	
	# Read input data
	with open(rom_in, "rb") as rom:
		rom.seek(RESOURCES_SECTION_PTR)
		sec_data = rom.read(sec_size)
		post_data = rom.read()
	
	# Validate that the remaining data contains only FF
	for b in post_data:
		if b != 0xFF:
			print("Size too small, some data after end")
			return False
	
	# Warn if the data has too many FFs at the end
	check_ff_count = 5
	for i in range(check_ff_count):
		if sec_data[-1-i] != 0xFF:
			break
		if i+1 == check_ff_count:
			print(f"Warning: data ends with at least {check_ff_count} \"FF\" bytes, size may be too large")
	
	# Load section data for validation
	res_count_table = _get_res_count_table(sec_data)
	if res_count_table == None:
		return False
	
	# Write output data
	make_dirs_for_file(sec_out)
	with open(sec_out, "wb") as sec:
		sec.write(sec_data)
		print(f"Saved resources section to {sec_out}")
	return True

def cmd_extract_res(args):
	# Parse and verify command arguments
	sec_in = args.path_sec_in
	res_out = args.path_res_out
	res_index = args.res_index
	comp = args.compressed
	if not check_files(exist=[sec_in], noexist=[res_out]):
		return False
	
	# Read input data
	with open(sec_in, "rb") as sec:
		sec_data = sec.read()
	
	# Load and validate section data
	res_count_table = _get_res_count_table(sec_data)
	if res_count_table == None:
		return False
	res_count, res_table = res_count_table
	
	# Read resource and decompress if requested
	res_data = _read_one_resource(sec_data, res_count, res_table, res_index)
	if comp:
		res_data = decompress(res_data)
		if not res_data:
			return False
		print(f"Decompressed {len(res_data)} bytes")
	
	# Write output data
	make_dirs_for_file(res_out)
	with open(res_out, "wb") as res:
		res.write(res_data)
		print(f"Saved resource {res_index} to {res_out}")
	return True

def cmd_inject_res(args):
	# Parse and verify command arguments
	sec_in = args.path_sec_in
	res_in = args.path_res_in
	res_index = args.res_index
	sec_out = args.path_sec_out
	max_size = args.max_size
	comp = args.compressed
	inplace = False
	if sec_out == "@":
		sec_out = sec_in
		inplace = True
	if not check_files(exist=[sec_in, res_in], noexist=[] if inplace else [sec_out]):
		if paths_equivalent(sec_in, sec_out):
			print("Specify \"@\" as the output file to inject in-place")
		return False
	if res_index < -1:
		print(f"Resource {res_index} out of range")
		return False
	if max_size == -1:
		max_size = RESOURCES_SECTION_DEFAULT_MAX
	elif max_size <= 0 or max_size > RESOURCES_SECTION_HARD_LIMIT:
		print(f"Max size out of range (0x000001-0x{RESOURCES_SECTION_HARD_LIMIT:06X})")
		return False
	
	# Read input data
	with open(sec_in, "rb") as sec:
		sec_data = sec.read()
	with open(res_in, "rb") as res:
		res_data = res.read()
	
	# Load and validate section data
	res_count_table = _get_res_count_table(sec_data)
	if res_count_table == None:
		return False
	res_count, res_table = res_count_table

	append = False
	if res_index == -1:
		append = True
	elif res_index < 0 or res_index >= res_count:
		print(f"Resource {res_index} out of range (0-{res_count-1})")
		return False
	
	# Read all existing resources
	print("Reading existing resources section")
	resources = _read_all_resources(sec_data, res_count, res_table)
	
	# Replace the target, compressing if requested
	print("Injecting new resource...")
	if comp:
		res_data = compress(res_data)
		if not res_data:
			return False
		print(f"Compressed {len(res_data)} bytes")
	if append:
		resources.append(res_data)
		print(f"Appended at resource {res_count}")
		res_count += 1
	else:
		resources[res_index] = res_data
		print(f"Replaced resource {res_index}")
	
	# Create new pointer table and padded data
	current_ptr = ROM_BASE+RESOURCES_SECTION_PTR+4+(res_count*4)
	res_table = [0]*res_count
	sec_data = bytearray()
	pad_value = b"\xFF"
	for i in range(res_count):
		if resources[i] == None or len(resources[i]) == 0:
			continue
		rdata = bytes(resources[i])
		rlen = len(rdata)
		if (rlen&3) != 0:
			pad = 4 - (rlen&3)
			rdata = rdata + pad_value*pad
			rlen += pad
		sec_data.extend(rdata)
		res_table[i] = current_ptr
		current_ptr += rlen
	if 4+(res_count*4)+len(sec_data) > max_size:
		print("Resources section exceeds max size!")
		return False
	
	# Write output data
	with open(sec_out, "wb") as sec:
		sec.write(struct.pack(">I", res_count))
		sec.write(struct.pack(f">{res_count}I", *res_table))
		sec.write(sec_data)
		print(f"Saved modified resources section to {sec_out}")
	return True
