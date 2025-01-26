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
	print(f"{RESOURCES_TABLE_PTR-ROM_BASE+(FONT_RESOURCE_NUM*4):08X}")
	print(f"Font location in rom {start+ROM_BASE:08X}-{end+ROM_BASE:08X}")
	return (start, end)

def extract(romin, imgout):
	imgout = os.path.normpath(imgout)
	nameparts = imgout.split("*")
	if len(nameparts) != 2:
		print("Output filename must contain one wildcard (*) for plane number")
		return
	nameout_prefix, nameout_suffix = nameparts
	imgNames = [nameout_prefix+f"{pn:02d}"+nameout_suffix for pn in range(NUM_PLANES)]
	for imn in imgNames:
		if os.path.exists(imn):
			print(f"Output file {imn} already exists.")
			return
	with open(romin, "rb") as fi:
		FONT_START, FONT_END = getFontStartEnd(fi)
		fi.seek(FONT_START)
		planeOffsets = struct.unpack(f"<{NUM_PLANES}H", fi.read(NUM_PLANES*2))
		
		for pn in range(NUM_PLANES):
			img = Image.new("L", (GLYPHS_PER_ROW*gridpx, pxPerPlane), color = COLOR_GRIDLINE)
			pix = img.load()
			fi.seek(FONT_START+planeOffsets[pn])
			
			numGlyphs = (FONT_END - (FONT_START+planeOffsets[pn])) // 18
			if pn < NUM_PLANES-1:
				numGlyphs = (planeOffsets[pn+1] - planeOffsets[pn]) // 18
			if numGlyphs > 192:
				numGlyphs = 192
			
			for i in range(numGlyphs):
				gdata = fi.read(18)
				col = i % GLYPHS_PER_ROW
				row = i // GLYPHS_PER_ROW
				ix = col*gridpx
				iy = row*gridpx
				unpackGlyph(gdata, pix, ix, iy)
			print(f"Saving plane {pn} to {os.path.basename(imgNames[pn])}")
			img.save(imgNames[pn])

def inject(romin, imgin, romout):
	fimages = glob.glob(imgin)
	if len(fimages) != NUM_PLANES:
		print(f"Wrong number of images, expected {NUM_PLANES} planes")
		return
	fimages = sorted(fimages, key=lastNum)
	images = [None]*NUM_PLANES
	for pn in range(NUM_PLANES):
		try:
			img = Image.open(fimages[pn]).convert("L")
			images[pn] = img
		except Exception:
			print(f"{fimages[pn]} is not a valid image.")
			return
		if img.width != GLYPHS_PER_ROW*gridpx or img.height != pxPerPlane:
			print(f"Wrong image dimensions in {fimages[pn]}, expected {GLYPHS_PER_ROW*gridpx} x {pxPerPlane}.")
			print("Check you are using the same script version.")
			return
	
	if os.path.exists(romout):
		print(f"Output file {romout} already exists.")
		return
	
	with open(romin, "rb") as fi:
		with open(romout, "wb") as fo:
			fo.write(fi.read())
			
			FONT_START, FONT_END = getFontStartEnd(fi)
			fi.seek(FONT_START)
			planeOffsets = struct.unpack(f"<{NUM_PLANES}H", fi.read(NUM_PLANES*2))
			
			for pn in range(NUM_PLANES):
				img = images[pn]
				pix = img.load()
				fo.seek(FONT_START+planeOffsets[pn])
				
				numGlyphs = (FONT_END - (FONT_START+planeOffsets[pn])) // 18
				if pn < NUM_PLANES-1:
					numGlyphs = (planeOffsets[pn+1] - planeOffsets[pn]) // 18
				if numGlyphs > 192:
					numGlyphs = 192
			
				print(f"Injecting {os.path.basename(fimages[pn])} to plane {pn}")
				for i in range(numGlyphs):
					col = i % GLYPHS_PER_ROW
					row = i // GLYPHS_PER_ROW
					ix = col*gridpx
					iy = row*gridpx
					gdata = packGlyph(pix, ix, iy)
					fo.write(gdata)

def main():
	if len(sys.argv) == 4 and sys.argv[1].lower() == "extract":
		romin = sys.argv[2]
		imgout = sys.argv[3]
		extract(romin, imgout)
		return
	if len(sys.argv) == 5 and sys.argv[1].lower() == "inject":
		romin = sys.argv[2]
		imgin = sys.argv[3]
		romout = sys.argv[4]
		inject(romin, imgin, romout)
		return
	
	print(sys.argv[0], "extract", "<rom in>", "<images out>")
	print(sys.argv[0], "inject", "<rom in>", "<images in>", "<rom out>")
	print()
	print("For image output, plane number will be added before file extension e.g. font.png->font_1.png.")
	print("For image input, use a wildcard e.g. font*.png, images will be loaded in sorted order.")
	print("Please use lossless image formats, PNG recommended.")

if __name__ == "__main__":
	main()