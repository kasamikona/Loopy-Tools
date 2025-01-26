#!/usr/bin/env python3

import sys, os, struct, glob, re
from PIL import Image

ROM_BASE = 0x0E000000
RESOURCES_TABLE_PTR = 0x0E070004
FONT_RESOURCE_NUM = 646
FONT_RESOURCE_LEN = 0xF72C
NUM_PLANES = 20

GLYPHS_PER_ROW = 16
GRIDLINE = True

COLOR_ZERO = 0
COLOR_ONE = 255
COLOR_GRIDLINE = 96

def unpack_glyph(data, pix, gx, gy):
	raw_bits = [0]*144
	for i in range(144):
		raw_bits[i] = (data[i>>3]>>(7-(i&7)))&1
		
	glyph = [[0]*12 for i in range(12)]
	for y in range(0, 12):
		for x in range(0, 8):
			glyph[x][y] = raw_bits[y*8 + x] == 1
		for x in range(8, 12):
			glyph[x][y] = raw_bits[y*4 + x-8 + 96] == 1
	
	for x in range(12):
		for y in range(12):
			pix[gx+x, gy+y] = COLOR_ONE if glyph[x][y] else COLOR_ZERO

def pack_glyph(pix, gx, gy):
	glyph = [[0]*12 for i in range(12)]
	for y in range(12):
		for x in range(12):
			c = pix[gx+x, gy+y]
			glyph[x][y] = abs(c-COLOR_ONE) < abs(c-COLOR_ZERO)
	
	raw_bits = [0]*144
	for y in range(0, 12):
		for x in range(0, 8):
			raw_bits[y*8 + x] = 1 if glyph[x][y] else 0
		for x in range(8, 12):
			raw_bits[y*4 + x-8 + 96] = 1 if glyph[x][y] else 0
	
	data = [0]*18
	for i in range(144):
		data[i>>3] |= raw_bits[i]<<(7-(i&7))
	
	return bytes(data)

num_re = re.compile(r'(\d+)')
def last_num(s):
	search = num_re.search(s)
	if search:
		return int(search.groups()[-1])
	else:
		return float('-inf')

grid_px = 13 if GRIDLINE else 12
px_per_plane = grid_px*((GLYPHS_PER_ROW+191)//GLYPHS_PER_ROW)

def get_font_start_end(fi):
	fi.seek(RESOURCES_TABLE_PTR-ROM_BASE+(FONT_RESOURCE_NUM*4))
	start = struct.unpack(">I", fi.read(4))[0]-ROM_BASE
	end = start+FONT_RESOURCE_LEN
	return (start, end)

def extract(rom_in, img_out, plane):
	img_out = os.path.normpath(img_out)
	if plane.lower() == "all":
		path_parts = img_out.split("*")
		if len(path_parts) != 2:
			print("Output filename must contain one wildcard (*) for plane number.")
			print("Escape the wildcard (\\*) or use quotes to prevent command expansion.")
			return
		path_prefix, path_suffix = path_parts
		planes = [(pn, path_prefix+f"{pn:02d}"+path_suffix) for pn in range(NUM_PLANES)]
	else:
		try:
			plane = int(plane)
		except ValueError:
			print("Invalid plane number")
			return
		if plane < 0 or plane >= NUM_PLANES:
			print("Plane number out of range")
			return
		planes = [ (plane, os.path.normpath(img_out)) ]
	for plane, img_path in planes:
		if os.path.exists(img_path):
			print(f"Output file {os.path.basename(img_path)} already exists.")
			return
	with open(rom_in, "rb") as fi:
		FONT_START, FONT_END = get_font_start_end(fi)
		fi.seek(FONT_START)
		plane_offsets = struct.unpack(f"<{NUM_PLANES}H", fi.read(NUM_PLANES*2))
		
		for plane, img_path in planes:
			img_name = os.path.basename(img_path)
			img = Image.new("L", (GLYPHS_PER_ROW*grid_px, px_per_plane), color = COLOR_GRIDLINE)
			pix = img.load()
			fi.seek(FONT_START+plane_offsets[plane])
			
			num_glyphs = (FONT_END - (FONT_START+plane_offsets[plane])) // 18
			if plane < NUM_PLANES-1:
				num_glyphs = (plane_offsets[plane+1] - plane_offsets[plane]) // 18
			if num_glyphs > 192:
				num_glyphs = 192
			
			for i in range(num_glyphs):
				glyph_data = fi.read(18)
				col = i % GLYPHS_PER_ROW
				row = i // GLYPHS_PER_ROW
				ix = col*grid_px
				iy = row*grid_px
				unpack_glyph(glyph_data, pix, ix, iy)
			print(f"Saving plane {plane} to {img_name}")
			img.save(img_path)

def inject(rom_in, img_in, rom_out, plane):
	img_in = os.path.normpath(img_in)
	if plane.lower() == "all":
		img_in_glob = glob.glob(img_in)
		if len(img_in_glob) != NUM_PLANES:
			print(f"Wrong number of images, expected {NUM_PLANES} planes")
			return
		planes = enumerate(sorted(img_in_glob, key=last_num))
	else:
		try:
			plane = int(plane)
		except ValueError:
			print("Invalid plane number")
			return
		if plane < 0 or plane >= NUM_PLANES:
			print("Plane number out of range")
			return
		planes = [(plane, img_in)]
	planes_imgs = []
	for plane, img_path in planes:
		img_name = os.path.basename(img_path)
		try:
			img = Image.open(img_path).convert("L")
		except Exception:
			print(f"{img_name} is not a valid image.")
			return
		if img.width != GLYPHS_PER_ROW*grid_px or img.height != px_per_plane:
			print(f"Wrong image dimensions in {img_name}, expected {GLYPHS_PER_ROW*grid_px} x {px_per_plane}.")
			print("Check you are using the same script version.")
			return
		planes_imgs.append( (plane, img_path, img) )
	
	if os.path.exists(rom_out):
		print(f"Output file {rom_out} already exists.")
		return
	
	with open(rom_in, "rb") as fi:
		with open(rom_out, "wb") as fo:
			fo.write(fi.read())
			
			FONT_START, FONT_END = get_font_start_end(fi)
			fi.seek(FONT_START)
			plane_offsets = struct.unpack(f"<{NUM_PLANES}H", fi.read(NUM_PLANES*2))
			
			for plane, img_path, img in planes_imgs:
				img_name = os.path.basename(img_path)
				pix = img.load()
				fo.seek(FONT_START+plane_offsets[plane])
				
				num_glyphs = (FONT_END - (FONT_START+plane_offsets[plane])) // 18
				if plane < NUM_PLANES-1:
					num_glyphs = (plane_offsets[plane+1] - plane_offsets[plane]) // 18
				if num_glyphs > 192:
					num_glyphs = 192
			
				print(f"Injecting {img_name} to plane {plane}")
				for i in range(num_glyphs):
					col = i % GLYPHS_PER_ROW
					row = i // GLYPHS_PER_ROW
					ix = col*grid_px
					iy = row*grid_px
					glyph_data = pack_glyph(pix, ix, iy)
					fo.write(glyph_data)

def main():
	if len(sys.argv) == 5 and sys.argv[1].lower() == "extract":
		rom_in = sys.argv[2]
		plane = sys.argv[3]
		img_out = sys.argv[4]
		extract(rom_in, img_out, plane)
		return
	if len(sys.argv) == 6 and sys.argv[1].lower() == "inject":
		rom_in = sys.argv[2]
		plane = sys.argv[3]
		img_in = sys.argv[4]
		rom_out = sys.argv[5]
		inject(rom_in, img_in, rom_out, plane)
		return
	
	print(sys.argv[0], "extract <rom in> <plane num|all> <image(s) out>")
	print(sys.argv[0], "inject <rom in> <plane num|all> <image(s) in> <rom out>")
	print()
	print("Use a wildcard (*) in multi image paths.")
	print("Escape the wildcard (\\*) or use quotes to prevent command expansion.")
	print("Input wildcard is used to match multiple files.")
	print("Output wildcard is replaced by plane number.")
	print("Please use lossless image formats, PNG recommended.")

if __name__ == "__main__":
	main()