import struct
from util import check_files
from lzss_ww import decompress

ROM_BASE = 0x0E000000
RESOURCES_COUNT_PTR = 0x0E070000
RESOURCES_TABLE_PTR = 0x0E070004
MAX_RAW_SIZE = 1<<16

def _get_resource(rom, index, size=None):
	# Get total resource count and verify index
	rom.seek(RESOURCES_COUNT_PTR - ROM_BASE)
	num_resources = struct.unpack(">I", rom.read(4))[0]
	if index < 0 or index >= num_resources:
		print(f"Resource {index} out of range")
		return None
	
	# Load resource table
	rom.seek(RESOURCES_TABLE_PTR - ROM_BASE)
	res_tbl = struct.unpack(f">{num_resources}I", rom.read(4*num_resources))
	
	# Get resource pointer
	res_ptr = res_tbl[index]
	if res_ptr < ROM_BASE:
		print(f"Resource {index} is null")
		return None
	
	# Estimate resource size if not given
	if size == None or size <= 0:
		next_ptr = min([p for p in res_tbl if p > res_ptr], default=None)
		if not next_ptr:
			# Last one has no "next", do max size
			print(f"Warning: resource {index} is last entry, reading max size")
			size = MAX_RAW_SIZE
		else:
			# Assume this one ends where the next one starts
			# This may include some padding bytes which the decoder should ignore
			size = min(next_ptr - res_ptr, MAX_RAW_SIZE)
	
	# Read the resource data
	rom.seek(res_ptr - ROM_BASE)
	res_data = rom.read(size)
	#print(f"Resource {index} size <= {len(res_data)} bytes")
	return res_data

def cmd_extract(args):
	# Parse and verify command arguments
	rom_in = args.path_rom_in
	res_out = args.path_res_out
	rindex = args.res_index
	rsize = args.res_size
	comp = args.compressed
	if not check_files(exist=[rom_in], noexist=[res_out]):
		return
	if rsize != None:
		if rsize <= 0:
			print("Invalid size")
			return
	
	# Read input data
	with open(rom_in, "rb") as rom:
		res_data = _get_resource(rom, rindex, rsize)
	
	# Decompress if requested
	if comp:
		res_data = decompress(res_data)
		if not res_data:
			return
		print(f"Decompressed {len(res_data)} bytes")
	
	# Write output data
	with open(res_out, "wb") as res:
		res.write(res_data)
		print(f"Saved resource {rindex} to {res_out}")
