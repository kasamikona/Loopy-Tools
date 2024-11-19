import sys, os, struct
from PIL import Image
import wanwan_data

ROM_BASE = 0x0E000000
RESOURCES = 0x0E070000
MAX_COMPRESSED_LENGTH = 1<<16
MAX_DECOMPRESSED_LENGTH = 1<<16

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

def cmd_extract(args):
	if len(args) < 4 or len(args) > 5:
		print("Usage:", sys.argv[0], sys.argv[1], "<rom.bin> <sprite resource> <palette resource> <output.png> [transparent true/false]")
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
	
	with open(args[0], "rb") as rom:
		rom.seek(RESOURCES - ROM_BASE)
		num_resources = struct.unpack(">I", rom.read(4))[0]
		
		if res_sprite < 0 or res_sprite >= num_resources:
			print("Sprite resource out of range")
			return
		if res_palette < 0 or res_palette >= num_resources:
			print("Palette resource out of range")
			return
		
		rom.seek(RESOURCES+4 + res_sprite*4 - ROM_BASE)
		res_sprite_ptr = struct.unpack(">I", rom.read(4))[0]
		rom.seek(RESOURCES+4 + res_palette*4 - ROM_BASE)
		res_palette_ptr = struct.unpack(">I", rom.read(4))[0]
		
		if res_sprite_ptr == 0 or res_palette_ptr == 0:
			print("Null resource")
			return
		
		rom.seek(res_palette_ptr-ROM_BASE)
		unk, palette_length = struct.unpack("2B", rom.read(2))
		palette_data = struct.unpack(f">{palette_length}H", rom.read(palette_length*2))
		palette_rgba = [0]*palette_length
		print("Palette:")
		for i in range(palette_length):
			crgb = col2rgb(palette_data[i])
			chex = rgbhex(crgb) if (i > 0 or not use_transp) else "Transp."
			if i&3 == 3 or i == palette_length-1:
				print(chex)
			else:
				print(chex.ljust(12), end="")
			crgba = (*crgb, 0 if (i == 0 and use_transp) else 255)
			palette_rgba[i] = crgba
		
		for i in range(palette_length):
			for j in range(0, i):
				if palette_data[i] == palette_data[j]:
					print(f"Warning: color {i} is a duplicate of {j}")
					break
		
		rom.seek(res_sprite_ptr-ROM_BASE)
		compressed = rom.read(MAX_COMPRESSED_LENGTH)
	
	decompressed = wanwan_data.decompress(compressed, MAX_DECOMPRESSED_LENGTH)
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
			if ci >= palette_length:
				print(f"Invalid color {ci} at {x},{y}")
				continue
			pix[x,y] = palette_rgba[ci]
	print(f"Saving to {args[3]}")
	img.save(args[3])

def main():
	commands = {"extract":cmd_extract}
	if len(sys.argv) > 1:
		command = sys.argv[1].lower()
		args = sys.argv[2:]
		if command in commands:
			commands[command](args)
			return
	print("Usage:", sys.argv[0], "<"+("|".join(commands.keys()))+"> ...")

if __name__ == "__main__":
	main()