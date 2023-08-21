#!/usr/bin/env python3

import sys, os
from PIL import Image

FONT_BASE = 0x100ED0
NUM_GLYPHS = 3513
GRID_WIDTH = 60

GRIDLINE = True

COLOR_ZERO = (0,0,0)
COLOR_ONE = (255,255,255)
COLOR_GRIDLINE = (128,128,128)

def parseGlyph(data):
	rawbits = [0]*(12*12)
	for i in range(12*12):
		rawbits[i] = (data[i>>3]>>(7-(i&7)))&1
		
	glyph = [[0]*12 for i in range(12)]
	for y in range(0, 12):
		for x in range(0, 8):
			glyph[x][y] = rawbits[y*8 + x] == 1
		for x in range(8, 12):
			glyph[x][y] = rawbits[y*4 + x-8 + 8*12] == 1
	return glyph

def extract(rompath, imgpath):
	with open(rompath, "rb") as f:
		f.seek(FONT_BASE)
		data = f.read(NUM_GLYPHS * 18)
	glyphs = [parseGlyph(data[i*18:(i+1)*18]) for i in range(NUM_GLYPHS)]
	
	needRows = ((NUM_GLYPHS-1) // GRID_WIDTH) + 1
	gridpx = 13 if GRIDLINE else 12
	img = Image.new('RGB', (GRID_WIDTH*gridpx, needRows*gridpx), color = COLOR_GRIDLINE)
	pix = img.load()
	
	for i in range(NUM_GLYPHS):
		col = i % GRID_WIDTH
		row = i // GRID_WIDTH
		ix = col*gridpx
		iy = row*gridpx
		for gx in range(12):
			for gy in range(12):
				pix[ix+gx, iy+gy] = COLOR_ONE if glyphs[i][gx][gy] else COLOR_ZERO
	img.save(imgpath)

def main():
	if len(sys.argv) == 4 and sys.argv[1].lower() == "extract":
		rompath = sys.argv[2]
		imgpath = sys.argv[3]
		extract(rompath, imgpath)
		return
	
	print(sys.argv[0], "extract", "<rom path>", "<image path>")

if __name__ == "__main__":
	main()