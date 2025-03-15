import os
import struct

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

def col2rgb(c, top=255):
	r = round(((c>>10)&31) * top / 31)
	g = round(((c>>5)&31) * top / 31)
	b = round((c&31) * top / 31)
	return (r, g, b)

def rgb2col(c, top=255):
	r = round(c[0] * 31 / top) & 31
	g = round(c[1] * 31 / top) & 31
	b = round(c[2] * 31 / top) & 31
	return r<<10 | g<<5 | b

def rgbhex(rgb):
	return f"#{rgb[0]&255:02X}{rgb[1]&255:02X}{rgb[2]&255:02X}"

def load_palette(palette_data):
	if len(palette_data) < 2:
		print("Palette data incomplete")
		return None
	palette_size = struct.unpack(">H", palette_data[:2])[0]
	palette_data = palette_data[2:]
	if palette_size > len(palette_data):
		print("Palette data incomplete")
		return None
	palette = struct.unpack(f">{palette_size}H", palette_data[:palette_size*2])
	return palette

def palette_to_rgba(palette, first_transparent=True):
	palette_size = len(palette)
	palette_rgba = [None]*palette_size
	for i in range(palette_size):
		crgb = col2rgb(palette[i])
		crgba = (*crgb, 0 if (i == 0 and first_transparent) else 255)
		palette_rgba[i] = crgba
	return palette_rgba

def print_palette_rgba(palette_rgba, warn_duplicates=True):
	palette_size = len(palette_rgba)
	print("Palette:")
	
	# Print color hex values
	for i in range(palette_size):
		crgba = palette_rgba[i]
		chex = rgbhex(crgba[:3]) if (crgba[3] > 0) else "Transp."
		if i&3 == 3 or i == palette_size-1:
			print(chex)
		else:
			print(chex.ljust(12), end="")
	
	# Warn for any duplicates
	if warn_duplicates:
		dupes = [[] for i in range(palette_size)]
		for i in range(palette_size):
			for j in range(0, i):
				if palette_rgba[i] == palette_rgba[j]:
					dupes[j].append(i)
		for i in range(palette_size):
			if len(dupes[i]) > 0:
				dupelist = ", ".join(map(str, dupes[i]))
				print(f"Warning: color {i} has duplicates at: {dupelist}")
			for j in dupes[i]:
				dupes[j] = []

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

def make_dirs_for_file(filepath):
	filepath = os.path.abspath(filepath)
	dirpath = os.path.dirname(filepath)
	os.makedirs(dirpath, exist_ok=True)

def paths_equivalent(a, b):
	return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))

def load_image_as_grayscale(img, max_colors=256):
	max_colors = min(max(2, max_colors), 256)
	img = Image.alpha_composite(Image.new("RGBA", img.size, (0,0,0,0)), img.convert("RGBA")).convert("L")
	img.putdata([round(x*(max_colors-1)/255) for x in list(img.getdata())])
	return img

def load_image_as_indexed(img, max_colors=256):
	img.load()
	max_colors = min(max(2, max_colors), 256)
	if img.mode not in ["P", "PA"]:
		print("Image is not an indexed-color format")
		return None
	if img.mode == "PA":
		#print("Warning: converting PA mode image to P mode")
		img = img.convert("P")
	transp_index = img.info.get("transparency", None)
	transp_list = [False]*256
	transp = False
	if transp_index != None:
		if type(transp_index) == int:
			transp_list[transp_index] = True
			transp = True
		elif type(transp_index) == bytes:
			for i in range(len(transp_index)):
				if transp_index[i] >= 128:
					transp_list[i] = True
					transp = True
	#print("Detected transparency: " + ("YES" if transp else "NO"))
	if transp:
		data_image = list(img.getdata())
		print("Mapping all transparency to color 0")
		pixel_value_map = list(range(256))
		next_opaque = 1
		for i in range(256):
			if transp_list[i]:
				pixel_value_map[i] = 0
			else:
				pixel_value_map[i] = next_opaque
				next_opaque += 1
		data_image = list(map(lambda x: pixel_value_map[x], data_image))
		img.putdata(data_image)
	max_used_color = max(list(img.getdata()))
	if max_used_color >= max_colors:
		print(f"Used palette exceeds maximum of {max_colors} colors")
		return None
	return img
