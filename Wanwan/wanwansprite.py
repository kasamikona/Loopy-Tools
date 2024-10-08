import sys, os, struct
from PIL import Image

ROM_BASE = 0x0E000000
RESOURCES = 0x0E070000
MAX_LENGTH = 65536

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


def cmd_extract(args):
	if len(args) < 4 or len(args) > 5:
		print("Usage:", sys.argv[0], sys.argv[1], "<rom.bin> <sprite resource> <palette resource> <output.png> [transparent true/false]")
		return
	
	use_transp = False
	if len(args) >= 5:
		use_transp = args[4].lower() in ['true', '1', 't', 'y', 'yes', 'transp', 'transparent']
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
			chex = rgbhex(crgb) if i > 0 else "Transp."
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
		decompressed = bytearray()
		
		bitcounter = 1
		modebits = 0
		copyoffset = 0
		copycount = 0
		try:
			while True:
				if len(decompressed) >= MAX_LENGTH:
					print("Decompressed data exceeded max length")
					return
				while True:
					bitcounter -= 1
					if bitcounter == 0:
						bitcounter = 8
						modebits = rom.read(1)[0]
					mode = modebits&1
					modebits >>= 1
					if mode == 0:
						break
					decompressed += rom.read(1)
				bitcounter -= 1
				if bitcounter == 0:
					bitcounter = 8
					modebits = rom.read(1)[0]
				mode = modebits&1
				modebits >>= 1
				if mode == 1:
					shortcopy = rom.read(1)[0]
					copyoffset = (shortcopy&63)-64
					copycount = (shortcopy>>6)&3
				else:
					longcopy = struct.unpack(">H",rom.read(2))[0]
					copyoffset = (longcopy&4095)-4096
					copycount = (longcopy>>12)&15
					if copycount == 0:
						copycount = rom.read(1)[0]
						if copycount == 0:
							break
				for i in range(copycount+2):
					decompressed.append(decompressed[copyoffset:][0])
		except IndexError:
			print("Decompression error")
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