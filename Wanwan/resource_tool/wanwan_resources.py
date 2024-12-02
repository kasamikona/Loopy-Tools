import sys, os, struct
from PIL import Image
from wanwan_lzss import decompress
import argparse

ROM_BASE = 0x0E000000
RESOURCES_COUNT_PTR = 0x0E070000
RESOURCES_TABLE_PTR = 0x0E070004
MAX_RAW_SIZE = 1<<16

def parsenum(x):
	x = x.lower()
	try:
		if x.startswith("0x"):
			a = int(x[2:], 16)
		elif x.endswith("h"):
			a = int(x[:-1], 16)
		else:
			a = int(x, 10)
		return a
	except ValueError as e:
		raise e

def parsebool(s):
	s = s.lower()
	if s in ["true", "1", "t", "y", "yes"]:
		return True
	if s in ["false", "0", "f", "n", "no"]:
		return False
	raise ValueError

def col2rgb(c):
	r = (c>>10)&31
	g = (c>>5)&31
	b = c&31
	return ((r*255)//31,(g*255)//31,(b*255)//31)

def rgbhex(rgb):
	return f"#{rgb[0]&255:02X}{rgb[1]&255:02X}{rgb[2]&255:02X}"

def load_palette(palette_data, use_transp, do_print=False):
	if len(palette_data) < 2:
		if do_print:
			print("Palette data incomplete")
		return None
	palette_size = struct.unpack(">H", palette_data[:2])[0]
	palette_data = palette_data[2:]
	if palette_size > len(palette_data):
		if do_print:
			print("Palette data incomplete")
		return None
	palette_values = struct.unpack(f">{palette_size}H", palette_data[:palette_size*2])
	palette_rgba = [0]*palette_size
	if do_print:
		print("Palette:")
	for i in range(palette_size):
		crgb = col2rgb(palette_values[i])
		if do_print:
			chex = rgbhex(crgb) if (i > 0 or not use_transp) else "Transp."
			if i&3 == 3 or i == palette_size-1:
				print(chex)
			else:
				print(chex.ljust(12), end="")
		crgba = (*crgb, 0 if (i == 0 and use_transp) else 255)
		palette_rgba[i] = crgba
	if do_print:
		for i in range(palette_size):
			for j in range(0, i):
				if palette_values[i] == palette_values[j]:
					print(f"Warning: color {i} is a duplicate of {j}")
					break
	return (palette_rgba, palette_size)

def check_files(exist, noexist):
	for f in exist:
		if not os.path.exists(f):
			print("Can't open file: "+f)
			return False
	for f in noexist:
		if os.path.exists(f):
			print("File already exists: "+f)
			return False
	return True

def get_resource(rom, index, size=None):
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
		res_data = get_resource(rom, rindex, rsize)
	
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

def cmd_decode_image(args):
	# Parse and verify command arguments
	res_im_in = args.path_res_im_in
	res_pal_in = args.path_res_pal_in
	im_out = args.path_image_out
	transp = args.transparent
	comp = args.compressed
	if not check_files(exist=[res_im_in, res_pal_in], noexist=[im_out]):
		return
	print("Transparent: " + ("YES" if transp else "NO"))
	print("Compressed: " + ("YES" if comp else "NO"))
	
	# Read input data
	with open(res_im_in, "rb") as f:
		data_image = f.read()
	with open(res_pal_in, "rb") as f:
		data_palette = f.read()
	
	# Load palette
	palette = load_palette(data_palette, transp, do_print=True)
	if not palette:
		return
	palette_rgba, palette_size = palette
	
	# Decompress image data if necessary
	if comp:
		data_image = decompress(data_image)
		if data_image == None:
			return
		print(f"Decompressed {len(data_image)} bytes")
	#comp_uncomp_other = "uncompressed" if comp else "compressed"
	comp_uncomp_other = "compressed = false" if comp else "compressed = true"
	
	# Load and verify image dimensions
	header_fmt = "BB"
	header_size = struct.calcsize(header_fmt)
	if len(data_image) < header_size:
		print(f"Data too short, try {comp_uncomp_other}.")
		return
	img_width, img_height = struct.unpack(header_fmt, data_image[:header_size])
	data_image = data_image[header_size:]
	img_width = img_width or 256
	img_height = img_height or 256
	print(f"Image dimensions {img_width}x{img_height}")
	if len(data_image) != img_width*img_height:
		print(f"Data size mismatch, try {comp_uncomp_other}.")
		return
	
	# Write output image
	img = Image.new("RGBA", (img_width, img_height), color = (0,0,0,0))
	pix = img.load()
	for x in range(img_width):
		for y in range(img_height):
			ci = data_image[y*img_width+x]
			if ci >= palette_size:
				print(f"Invalid color {ci} at {x},{y}")
				continue
			pix[x,y] = palette_rgba[ci]
	print(f"Saving to {im_out}")
	img.save(im_out)

def cmd_decode_tiles(args):
	# Parse and verify command arguments
	res_ts_in = args.path_res_tiles_in
	res_pal_in = args.path_res_pal_in
	im_out = args.path_image_out
	transp = args.transparent
	comp = args.compressed
	if not check_files(exist=[res_ts_in, res_pal_in], noexist=[im_out]):
		return
	print("Transparent: " + ("YES" if transp else "NO"))
	print("Compressed: " + ("YES" if comp else "NO"))
	
	# Read input data
	with open(res_ts_in, "rb") as f:
		data_tiles = f.read()
	with open(res_pal_in, "rb") as f:
		data_palette = f.read()
	
	# Load palette
	palette = load_palette(data_palette, transp, do_print=True)
	if not palette:
		return
	palette_rgba, palette_size = palette
	
	# Decompress tilesheet data if necessary
	if comp:
		data_tiles = decompress(data_tiles)
		if data_tiles == None:
			return
		print(f"Decompressed {len(data_tiles)} bytes")
	#comp_uncomp_other = "uncompressed" if comp else "compressed"
	comp_uncomp_other = "compressed = false" if comp else "compressed = true"
	
	# Load and verify tile count
	header_fmt = ">H"
	header_size = struct.calcsize(header_fmt)
	if len(data_tiles) < header_size:
		print(f"Data too short, try {comp_uncomp_other}.")
		return
	num_tiles = struct.unpack(header_fmt, data_tiles[:header_size])[0]
	data_tiles = data_tiles[header_size:]
	if num_tiles == 0:
		print("No tiles")
		return
	if len(data_tiles) != num_tiles*32:
		print(f"Data size mismatch, try {comp_uncomp_other}.")
		return
	
	# Compute output image dimensions
	img_width = 64
	img_height = ((num_tiles+7)//8) * 8
	print(f"Sheet contains {num_tiles} tiles, output in {img_width}x{img_height} image")

	# Write output image
	img = Image.new("RGBA", (img_width, img_height), color = (0,0,0,0))
	pix = img.load()
	for t in range(num_tiles):
		for tx in range(8):
			for ty in range(8):
				ci = data_tiles[t*32 + ty*4 + tx//2]
				if tx & 1 == 0:
					ci >>= 4
				ci &= 15
				if ci >= palette_size:
					print(f"Invalid color {ci} at T{t}:{tx},{ty}")
					continue
				ix = (t&7)*8 + tx
				iy = (t//8)*8 + ty
				pix[ix,iy] = palette_rgba[ci]
	print(f"Saving to {im_out}")
	img.save(im_out)

class ArgParserHelpOnError(argparse.ArgumentParser):
	def error(self, message):
		self.print_help()
		print()
		print(f"ERROR: {message}")
		#sys.exit(2)

def main(args):
	progname = os.path.basename(args.pop(0))
	
	parser = ArgParserHelpOnError(prog=progname, epilog="Select an action for more help.")
	globalopts = ""
	subparsers = parser.add_subparsers(required=True, metavar="action")
	
	aname = "extract"
	ahelp = "Extract a raw or compressed resource"
	afunc = cmd_extract
	parser_extract = subparsers.add_parser(aname, prog=f"{progname} {aname}", help=ahelp)
	parser_extract.add_argument("path_rom_in", metavar="rom.bin", help="Source ROM input path")
	parser_extract.add_argument("res_index", metavar="res_index", help="Resource number to extract", type=parsenum)
	parser_extract.add_argument("path_res_out", metavar="output.bin", help="Resource output path")
	parser_extract.add_argument("-s", "--size", metavar="res_size", dest="res_size", help="Size of the source data", type=parsenum)
	parser_extract.add_argument("-c", "--compressed", metavar="true/false", help="Decompress resource on extraction (default false)", type=parsebool, default=False)
	parser_extract.set_defaults(action=afunc)
	
	aname = "decode-image"
	ahelp = "Decode an 8bpp image"
	afunc = cmd_decode_image
	parser_dec_image = subparsers.add_parser(aname, prog=f"{progname} {aname}", help=ahelp)
	parser_dec_image.add_argument("path_res_im_in", metavar="res_image.bin", help="Image resource file path")
	parser_dec_image.add_argument("path_res_pal_in", metavar="res_palette.bin", help="Palette resource file path")
	parser_dec_image.add_argument("path_image_out", metavar="output.png", help="Image output path")
	parser_dec_image.add_argument("-t", "--transparent", metavar="true/false", help="Color 0 is transparent (default false)", dest="transparent", type=parsebool, default=False)
	parser_dec_image.add_argument("-c", "--compressed", metavar="true/false", help="Decompress image resource on load (default true)", dest="compressed", type=parsebool, default=True)
	parser_dec_image.set_defaults(action=afunc)
	
	aname = "decode-tiles"
	ahelp = "Decode a 4bpp tile sheet"
	afunc = cmd_decode_tiles
	parser_dec_tiles = subparsers.add_parser(aname, prog=f"{progname} {aname}", help=ahelp)
	parser_dec_tiles.add_argument("path_res_tiles_in", metavar="res_tiles", help="Tilesheet resource file path (decompressed)")
	parser_dec_tiles.add_argument("path_res_pal_in", metavar="res_palette", help="Palette resource file path")
	parser_dec_tiles.add_argument("path_image_out", metavar="output.png", help="Sheet image output path")
	parser_dec_tiles.add_argument("-t", "--transparent", metavar="true/false", help="Color 0 is transparent (default true)", dest="transparent", type=parsebool, default=True)
	parser_dec_tiles.add_argument("-c", "--compressed", metavar="true/false", help="Decompress tilesheet resource on load (default true)", dest="compressed", type=parsebool, default=True)
	parser_dec_tiles.set_defaults(action=afunc)
	
	parsed_args = parser.parse_args(args)
	parsed_args.action(parsed_args)

if __name__ == "__main__":
	main(sys.argv)
