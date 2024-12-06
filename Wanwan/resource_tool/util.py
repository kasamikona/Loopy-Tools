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

def col2rgb(c):
	r = (c>>10)&31
	g = (c>>5)&31
	b = c&31
	return ((r*255)//31,(g*255)//31,(b*255)//31)

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
