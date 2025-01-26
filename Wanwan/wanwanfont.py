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

def unpackGlyph(data, pix, gx, gy):
	rawbits = [0]*144
	for i in range(144):
		rawbits[i] = (data[i>>3]>>(7-(i&7)))&1
		
	glyph = [[0]*12 for i in range(12)]
	for y in range(0, 12):
		for x in range(0, 8):
			glyph[x][y] = rawbits[y*8 + x] == 1
		for x in range(8, 12):
			glyph[x][y] = rawbits[y*4 + x-8 + 96] == 1
	
	for x in range(12):
		for y in range(12):
			pix[gx+x, gy+y] = COLOR_ONE if glyph[x][y] else COLOR_ZERO

def packGlyph(pix, gx, gy):
	glyph = [[0]*12 for i in range(12)]
	for y in range(12):
		for x in range(12):
			c = pix[gx+x, gy+y]
			glyph[x][y] = abs(c-COLOR_ONE) < abs(c-COLOR_ZERO)
	
	rawbits = [0]*144
	for y in range(0, 12):
		for x in range(0, 8):
			rawbits[y*8 + x] = 1 if glyph[x][y] else 0
		for x in range(8, 12):
			rawbits[y*4 + x-8 + 96] = 1 if glyph[x][y] else 0
	
	data = [0]*18
	for i in range(144):
		data[i>>3] |= rawbits[i]<<(7-(i&7))
	
	return bytes(data)

def fileNameSuffix(filename, suffix):
	return "{0}{2}{1}".format(*os.path.splitext(filename) + (suffix,))

numRe = re.compile(r'(\d+)')
def lastNum(s):
	search = numRe.search(s)
	if search:
		return int(search.groups()[-1])
	else:
		return float('-inf')

gridpx = 13 if GRIDLINE else 12
pxPerPlane = gridpx*((GLYPHS_PER_ROW+191)//GLYPHS_PER_ROW)

def getFontStartEnd(fi):
	fi.seek(RESOURCES_TABLE_PTR-ROM_BASE+(FONT_RESOURCE_NUM*4))
	start = struct.unpack(">I", fi.read(4))[0]-ROM_BASE
	end = start+FONT_RESOURCE_LEN
	return (start, end)

def extract(romin, imgout, plane):
	if plane.lower() == "all":
		nameparts = imgout.split("*")
		if len(nameparts) != 2:
			print("Output filename must contain one wildcard (*) for plane number.")
			print("Escape the wildcard (\\*) or use quotes to prevent command expansion.")
			return
		nameout_prefix, nameout_suffix = nameparts
		planes = [(pn, os.path.normpath(nameout_prefix+f"{pn:02d}"+nameout_suffix)) for pn in range(NUM_PLANES)]
	else:
		try:
			plane = int(plane)
		except ValueError:
			print("Invalid plane number")
			return
		if plane < 0 or plane >= NUM_PLANES:
			print("Plane number out of range")
			return
		planes = [ (plane, os.path.normpath(imgout)) ]
	for plane, img_path in planes:
		if os.path.exists(img_path):
			print(f"Output file {os.path.basename(img_path)} already exists.")
			return
	with open(romin, "rb") as fi:
		FONT_START, FONT_END = getFontStartEnd(fi)
		fi.seek(FONT_START)
		planeOffsets = struct.unpack(f"<{NUM_PLANES}H", fi.read(NUM_PLANES*2))
		
		for plane, img_path in planes:
			img_name = os.path.basename(img_path)
			img = Image.new("L", (GLYPHS_PER_ROW*gridpx, pxPerPlane), color = COLOR_GRIDLINE)
			pix = img.load()
			fi.seek(FONT_START+planeOffsets[plane])
			
			numGlyphs = (FONT_END - (FONT_START+planeOffsets[plane])) // 18
			if plane < NUM_PLANES-1:
				numGlyphs = (planeOffsets[plane+1] - planeOffsets[plane]) // 18
			if numGlyphs > 192:
				numGlyphs = 192
			
			for i in range(numGlyphs):
				gdata = fi.read(18)
				col = i % GLYPHS_PER_ROW
				row = i // GLYPHS_PER_ROW
				ix = col*gridpx
				iy = row*gridpx
				unpackGlyph(gdata, pix, ix, iy)
			print(f"Saving plane {plane} to {img_name}")
			img.save(img_path)

def inject(romin, imgin, romout, plane):
	imgin = os.path.normpath(imgin)
	if plane.lower() == "all":
		imgin_glob = glob.glob(imgin)
		if len(imgin_glob) != NUM_PLANES:
			print(f"Wrong number of images, expected {NUM_PLANES} planes")
			return
		planes = enumerate(sorted(imgin_glob, key=lastNum))
	else:
		try:
			plane = int(plane)
		except ValueError:
			print("Invalid plane number")
			return
		if plane < 0 or plane >= NUM_PLANES:
			print("Plane number out of range")
			return
		planes = [(plane, imgin)]
	planes_tmp = []
	for plane, img_path in planes:
		img_name = os.path.basename(img_path)
		try:
			img = Image.open(img_path).convert("L")
		except Exception:
			print(f"{img_name} is not a valid image.")
			return
		if img.width != GLYPHS_PER_ROW*gridpx or img.height != pxPerPlane:
			print(f"Wrong image dimensions in {img_name}, expected {GLYPHS_PER_ROW*gridpx} x {pxPerPlane}.")
			print("Check you are using the same script version.")
			return
		planes_tmp.append( (plane, img_path, img) )
	planes = planes_tmp
	
	if os.path.exists(romout):
		print(f"Output file {romout} already exists.")
		return
	
	with open(romin, "rb") as fi:
		with open(romout, "wb") as fo:
			fo.write(fi.read())
			
			FONT_START, FONT_END = getFontStartEnd(fi)
			fi.seek(FONT_START)
			planeOffsets = struct.unpack(f"<{NUM_PLANES}H", fi.read(NUM_PLANES*2))
			
			for plane, img_path, img in planes:
				img_name = os.path.basename(img_path)
				pix = img.load()
				fo.seek(FONT_START+planeOffsets[plane])
				
				numGlyphs = (FONT_END - (FONT_START+planeOffsets[plane])) // 18
				if plane < NUM_PLANES-1:
					numGlyphs = (planeOffsets[plane+1] - planeOffsets[plane]) // 18
				if numGlyphs > 192:
					numGlyphs = 192
			
				print(f"Injecting {img_name} to plane {plane}")
				for i in range(numGlyphs):
					col = i % GLYPHS_PER_ROW
					row = i // GLYPHS_PER_ROW
					ix = col*gridpx
					iy = row*gridpx
					gdata = packGlyph(pix, ix, iy)
					fo.write(gdata)

def main():
	if len(sys.argv) == 5 and sys.argv[1].lower() == "extract":
		romin = sys.argv[2]
		plane = sys.argv[3]
		imgout = sys.argv[4]
		extract(romin, imgout, plane)
		return
	if len(sys.argv) == 6 and sys.argv[1].lower() == "inject":
		romin = sys.argv[2]
		plane = sys.argv[3]
		imgin = sys.argv[4]
		romout = sys.argv[5]
		inject(romin, imgin, romout, plane)
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