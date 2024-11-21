import sys, os, struct
from PIL import Image
from wanwan_data import decompress

ROM_BASE = 0x0E000000
RESOURCES_COUNT_PTR = 0x0E070000
RESOURCES_TABLE_PTR = 0x0E070004
MAX_RAW_SIZE = 1<<16
MAX_DECOMPRESSED_SIZE = 1<<16

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
	rom.seek(RESOURCES_COUNT_PTR - ROM_BASE)
	num_resources = struct.unpack(">I", rom.read(4))[0]
	if index < 0 or index >= num_resources:
		print(f"Resource {index} out of range")
		return None
	rom.seek(RESOURCES_TABLE_PTR + index*4 - ROM_BASE)
	res_ptr = struct.unpack(">I", rom.read(4))[0]
	if res_ptr < ROM_BASE:
		print(f"Resource {index} is null")
		return None
	if size == None or size <= 0:
		if index == num_resources-1:
			print(f"Warning: resource {index} is last entry, reading max size")
			size = MAX_RAW_SIZE
		else:
			smallest_diff = MAX_RAW_SIZE
			for i in range(num_resources):
				if i == index:
					continue
				rom.seek(RESOURCES_TABLE_PTR + i*4 - ROM_BASE)
				other_ptr = struct.unpack(">I", rom.read(4))[0]
				if other_ptr >= res_ptr:
					diff = other_ptr-res_ptr
					if smallest_diff > diff:
						smallest_diff = diff
			size = smallest_diff
	rom.seek(res_ptr - ROM_BASE)
	res_data = rom.read(size)
	#print(f"Resource {index} size <= {len(res_data)} bytes")
	return res_data

def cmd_extract(args, cmdline, compressed=False):
	if len(args) not in [3, 4]:
		print(f"Usage: {cmdline} <rom.bin> <resource index> <output.bin> [{'compressed size' if compressed else 'size'}]")
		return
	
	path_rom_in = args[0]
	path_res_out = args[2]
	if not check_files(exist=[path_rom_in], noexist=[path_res_out]):
		return
	
	res_index = parsenum(args[1])
	if not res_index:
		print("Invalid index")
		return
	
	res_size = None
	if len(args) >= 4:
		res_size = parsenum(args[3])
		if not res_size or res_size <= 0:
			print("Invalid size")
			return
	
	with open(path_rom_in, "rb") as rom:
		res_data = get_resource(rom, res_index, res_size)
	
	if compressed:
		res_data = decompress(res_data)
		if not res_data:
			return
	
	with open(path_res_out, "wb") as res:
		res.write(res_data)
		print(f"Saved resource {res_index} to {path_res_out}")

def cmd_extract_compressed(args, cmdline):
	cmd_extract(args, cmdline, True)

def cmd_extract_sprite(args, cmdline):
	if len(args) not in [4, 5]:
		print(f"Usage: {cmdline} <rom.bin> <sprite resource> <palette resource> <output.png> [transparent true/(false)]")
		return
	
	path_rom_in = args[0]
	path_image_out = args[3]
	if not check_files(exist=[path_rom_in], noexist=[path_image_out]):
		return
	
	use_transp = False
	if len(args) >= 5:
		use_transp = parse_boolean(args[4])
	print("Transparency: " + ("YES" if use_transp else "NO"))
	
	res_sprite = parsenum(args[1])
	res_palette = parsenum(args[2])
	if res_sprite == None or res_palette == None:
		print("Invalid resource number")
		return
	
	with open(path_rom_in, "rb") as rom:
		data_sprite = get_resource(rom, res_sprite)
		data_palette = get_resource(rom, res_palette)
		if (not data_sprite) or (not data_palette):
			return
	
	unk, palette_size = struct.unpack("2B", data_palette[:2])
	if palette_size > len(data_palette)-2:
		print("Palette data incomplete")
		return
	palette_data = struct.unpack(f">{palette_size}H", data_palette[2:palette_size*2+2])
	palette_rgba = [0]*palette_size
	print("Palette:")
	for i in range(palette_size):
		crgb = col2rgb(palette_data[i])
		chex = rgbhex(crgb) if (i > 0 or not use_transp) else "Transp."
		if i&3 == 3 or i == palette_size-1:
			print(chex)
		else:
			print(chex.ljust(12), end="")
		crgba = (*crgb, 0 if (i == 0 and use_transp) else 255)
		palette_rgba[i] = crgba
	
	for i in range(palette_size):
		for j in range(0, i):
			if palette_data[i] == palette_data[j]:
				print(f"Warning: color {i} is a duplicate of {j}")
				break
	
	decompressed = decompress(data_sprite)
	if not decompressed:
		return
	print(f"Decompressed {len(decompressed)} bytes")
	
	img_width, img_height = decompressed[:2]
	if img_width == 0:
		img_width = 256
	if img_height == 0:
		img_height = 256
	decompressed = decompressed[2:]
	print(f"Image dimensions {img_width}x{img_height}")
	if len(decompressed) != img_width*img_height:
		print("Data size mismatch")
		return
	
	img = Image.new("RGBA", (img_width, img_height), color = (0,0,0,0))
	pix = img.load()
	for x in range(img_width):
		for y in range(img_height):
			ci = decompressed[y*img_width+x]
			if ci >= palette_size:
				print(f"Invalid color {ci} at {x},{y}")
				continue
			pix[x,y] = palette_rgba[ci]
	print(f"Saving to {path_image_out}")
	img.save(path_image_out)

def cmd_extract_tilesheet(args, cmdline):
	if len(args) not in [4, 5]:
		print(f"Usage: {cmdline} <rom.bin> <sheet resource> <palette resource> <output.png> [transparent (true)/false]")
		return
	
	path_rom_in = args[0]
	path_image_out = args[3]
	if not check_files(exist=[path_rom_in], noexist=[path_image_out]):
		return
	
	use_transp = True
	if len(args) >= 5:
		use_transp = parse_boolean(args[4])
	print("Transparency: " + ("YES" if use_transp else "NO"))
	
	res_sheet = parsenum(args[1])
	res_palette = parsenum(args[2])
	if res_sheet == None or res_palette == None:
		print("Invalid resource number")
		return
	
	with open(path_rom_in, "rb") as rom:
		data_sheet = get_resource(rom, res_sheet)
		data_palette = get_resource(rom, res_palette)
		if (not data_sheet) or (not data_palette):
			return
	
	unk, palette_size = struct.unpack("2B", data_palette[:2])
	if palette_size > len(data_palette)-2:
		print("Palette data incomplete")
		return
	palette_data = struct.unpack(f">{palette_size}H", data_palette[2:palette_size*2+2])
	palette_rgba = [0]*palette_size
	print("Palette:")
	for i in range(palette_size):
		crgb = col2rgb(palette_data[i])
		chex = rgbhex(crgb) if (i > 0 or not use_transp) else "Transp."
		if i&3 == 3 or i == palette_size-1:
			print(chex)
		else:
			print(chex.ljust(12), end="")
		crgba = (*crgb, 0 if (i == 0 and use_transp) else 255)
		palette_rgba[i] = crgba
	
	for i in range(palette_size):
		for j in range(0, i):
			if palette_data[i] == palette_data[j]:
				print(f"Warning: color {i} is a duplicate of {j}")
				break
	
	decompressed = decompress(data_sheet)
	if not decompressed:
		return
	print(f"Decompressed {len(decompressed)} bytes")
	
	num_tiles = struct.unpack(">H", decompressed[:2])[0]
	if num_tiles == 0:
		print("No tiles")
		return
	
	img_width = 64
	img_height = ((num_tiles+7)//8) * 8
	print(f"Sheet contains {num_tiles} tiles, output in {img_width}x{img_height} image")

	decompressed = decompressed[2:]
	if len(decompressed) != num_tiles*32:
		print("Data size mismatch")
		return
	
	img = Image.new("RGBA", (img_width, img_height), color = (0,0,0,0))
	pix = img.load()
	for t in range(num_tiles):
		for tx in range(8):
			for ty in range(8):
				ci = decompressed[t*32 + ty*4 + tx//2]
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

def main():
	commands = {
		"extract": cmd_extract,
		"extract-compressed": cmd_extract_compressed,
		"extract-sprite": cmd_extract_sprite,
		"extract-tilesheet": cmd_extract_tilesheet,
	}
	if len(sys.argv) > 1:
		command = sys.argv[1].lower()
		args = sys.argv[2:]
		if command in commands:
			commands[command](args, command)
			return
	print("Usage:", sys.argv[0], "<"+("|".join(commands.keys()))+"> ...")

if __name__ == "__main__":
	main()