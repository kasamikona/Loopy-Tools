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
	except ValueError:
		return None

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

def parse_boolean(s):
	return s.lower() in ['true', '1', 't', 'y', 'yes']

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
	path_rom_in = args.path_rom_in
	path_res_out = args.path_res_out
	if not check_files(exist=[path_rom_in], noexist=[path_res_out]):
		return
	res_index = parsenum(args.res_index)
	if not res_index:
		print("Invalid index")
		return
	res_size = None
	if args.res_size != None:
		res_size = parsenum(args.res_size)
		if not res_size or res_size <= 0:
			print("Invalid size")
			return
	
	# Read input data
	with open(path_rom_in, "rb") as rom:
		res_data = get_resource(rom, res_index, res_size)
	
	# Decompress if requested
	if args.compressed:
		res_data = decompress(res_data)
		if not res_data:
			return
		print(f"Decompressed {len(res_data)} bytes")
	
	# Write output data
	with open(path_res_out, "wb") as res:
		res.write(res_data)
		print(f"Saved resource {res_index} to {path_res_out}")

def cmd_extract_image(args):
	# Parse and verify command arguments
	path_rom_in = args.path_rom_in
	path_image_out = args.path_image_out
	if not check_files(exist=[path_rom_in], noexist=[path_image_out]):
		return
	use_transp = args.transparent
	print("Transparency: " + ("YES" if use_transp else "NO"))
	res_image = parsenum(args.res_image)
	res_palette = parsenum(args.res_palette)
	if res_image == None or res_palette == None:
		print("Invalid resource number")
		return
	
	# Read input data
	with open(path_rom_in, "rb") as rom:
		data_image = get_resource(rom, res_image)
		data_palette = get_resource(rom, res_palette)
		if (not data_image) or (not data_palette):
			return
	
	# Load palette
	palette = load_palette(data_palette, use_transp, do_print=True)
	if not palette:
		return
	palette_rgba, palette_size = palette
	
	# Decompress image data
	data_image = decompress(data_image)
	if not data_image:
		return
	print(f"Decompressed {len(data_image)} bytes")
	
	# Load and verify image dimensions
	img_width, img_height = data_image[:2]
	data_image = data_image[2:]
	if img_width == 0:
		img_width = 256
	if img_height == 0:
		img_height = 256
	print(f"Image dimensions {img_width}x{img_height}")
	if len(data_image) != img_width*img_height:
		print("Data size mismatch")
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
	print(f"Saving to {path_image_out}")
	img.save(path_image_out)

def cmd_extract_tiles(args):
	# Parse and verify command arguments
	path_rom_in = args.path_rom_in
	path_image_out = args.path_image_out
	if not check_files(exist=[path_rom_in], noexist=[path_image_out]):
		return
	use_transp = True
	res_tiles = parsenum(args.res_tiles)
	res_palette = parsenum(args.res_palette)
	if (not res_tiles) or (not res_palette):
		print("Invalid resource number")
		return
	
	# Read input data
	with open(path_rom_in, "rb") as rom:
		data_tiles = get_resource(rom, res_tiles)
		data_palette = get_resource(rom, res_palette)
		if (not data_tiles) or (not data_palette):
			return
	
	# Load palette
	palette = load_palette(data_palette, use_transp, do_print=True)
	if not palette:
		return
	palette_rgba, palette_size = palette
	
	# Decompress tilesheet data
	data_tiles = decompress(data_tiles)
	if not data_tiles:
		return
	print(f"Decompressed {len(data_tiles)} bytes")
	
	# Load and verify tile count
	num_tiles = struct.unpack(">H", data_tiles[:2])[0]
	data_tiles = data_tiles[2:]
	if num_tiles == 0:
		print("No tiles")
		return
	if len(data_tiles) != num_tiles*32:
		print("Data size mismatch")
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
	print(f"Saving to {path_image_out}")
	img.save(path_image_out)

class ArgParserHelpOnError(argparse.ArgumentParser):
	def error(self, message):
		print(f"error: {message}")
		print()
		self.print_help()
		sys.exit(2)

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
	parser_extract.add_argument("res_index", metavar="res_index", help="Resource number to extract")
	parser_extract.add_argument("path_res_out", metavar="output.bin", help="Resource output path")
	parser_extract.add_argument("-s", "--size", metavar="res_size", dest="res_size", help="Size of the source data")
	parser_extract.add_argument("-z", "--lzss", help="Use LZSS decompression", dest="compressed", action='store_true')
	parser_extract.set_defaults(action=afunc)
	
	aname = "extract-image"
	ahelp = "Extract an 8bpp image"
	afunc = cmd_extract_image
	parser_ext_image = subparsers.add_parser(aname, prog=f"{progname} {aname}", help=ahelp)
	parser_ext_image.add_argument("path_rom_in", metavar="rom.bin", help="Source ROM input path")
	parser_ext_image.add_argument("res_image", metavar="res_image", help="Resource number of image")
	parser_ext_image.add_argument("res_palette", metavar="res_palette", help="Resource number of palette")
	parser_ext_image.add_argument("path_image_out", metavar="output.png", help="Image output path")
	parser_ext_image.add_argument("-t", "--transparent", help="Treat color 0 as transparent", dest="transparent", action='store_true')
	parser_ext_image.set_defaults(action=afunc)
	
	aname = "extract-tiles"
	ahelp = "Extract a 4bpp tile sheet"
	afunc = cmd_extract_tiles
	parser_ext_tiles = subparsers.add_parser(aname, prog=f"{progname} {aname}", help=ahelp)
	parser_ext_tiles.add_argument("path_rom_in", metavar="rom.bin", help="Source ROM input path")
	parser_ext_tiles.add_argument("res_tiles", metavar="res_tiles", help="Resource number of tile sheet")
	parser_ext_tiles.add_argument("res_palette", metavar="res_palette", help="Resource number of palette")
	parser_ext_tiles.add_argument("path_image_out", metavar="output.png", help="Sheet image output path")
	parser_ext_tiles.set_defaults(action=afunc)
	
	parsed_args = parser.parse_args(args)
	parsed_args.action(parsed_args)

if __name__ == "__main__":
	main(sys.argv)
