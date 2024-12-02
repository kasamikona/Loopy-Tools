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
