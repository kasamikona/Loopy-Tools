import sys, os, io, struct
from PIL import Image
from colorthief import ColorThief

STATE_BACKDROP_COLOR = 0x4616
DO_DITHER = False

def color_to_15bit(c, top=255):
	r = round(c[0] * 31 / top) & 31
	g = round(c[1] * 31 / top) & 31
	b = round(c[2] * 31 / top) & 31
	return r<<10 | g<<5 | b

def color_from_15bit(c, top=255):
	r = round(((c>>10)&31) * top / 31)
	g = round(((c>>5)&31) * top / 31)
	b = round((c&31) * top / 31)
	return (r, g, b)

def file_write_align(f, n):
	pos = f.tell()
	posmod = pos % n
	if posmod != 0:
		f.write(bytes([255]*(n-posmod)))

def main():
	if len(sys.argv)-1 != 6:
		print(f"{sys.argv[0]} <image> <width> <height> <palmin> <palmax> <output>")
		return
	arg_image, arg_width, arg_height, arg_palmin, arg_palmax, arg_output = sys.argv[1:]
	
	# Load image
	try:
		im = Image.open(arg_image)
	except Exception as e:
		print("Image does not exist or cannot be read")
		return
	imratio = im.width/im.height
	
	# Parse size
	try:
		width = int(arg_width)
		height = int(arg_height)
	except ValueError:
		print("Invalid size")
		return
	if width == -1 and height == -1:
		im = im.resize((round(im.width*7/8), im.height))
		imratio = im.width/im.height
		if imratio > 256/224:
			width = 256
		else:
			height = 224
	if width == -1:
		width = round(height * imratio)
	elif height == -1:
		height = round(width / imratio)
	if width < 1 or width > 256 or height < 1 or height > 224:
		print("Invalid size")
		return
	
	# Parse palette range
	try:
		palmin = int(arg_palmin)
		palmax = int(arg_palmax)
	except ValueError:
		print("Invalid palette range")
		return
	if palmin < 1 or palmin > 255 or palmax < 1 or palmax > 255 or palmax < palmin+1:
		print("Invalid palette range")
		return
	
	# Check output valid
	path_bin = f"{arg_output}.bin"
	path_pal = f"{arg_output}.pal"
	path_state = f"{arg_output}.state"
	if os.path.exists(path_bin) or os.path.exists(path_pal) or os.path.exists(path_state):
		print("One or more output files (.bin/.pal/.state) already exists")
		return
	
	# Resize image
	#im = im.convert("L")
	im = im.convert("RGB")
	if im.width != width or im.height != height:
		im = im.resize((width, height))
	im = im.transpose(Image.Transpose.ROTATE_90)
	
	# Get color palette
	num_colors = 1+palmax-palmin
	
	if DO_DITHER:
		im_quant = im.copy()
		quant_px = im_quant.load()
		for x in range(height):
			for y in range(width):
				c = quant_px[x,y]
				quant_px[x,y] = color_from_15bit(color_to_15bit(c,255),31)
		im_quant = im_quant.convert('P', palette=Image.Palette.ADAPTIVE, dither=Image.Dither.NONE, colors=num_colors)
		palette = im_quant.getpalette()[:num_colors*3]
		loopy_palette = [0]*num_colors
		for i in range(num_colors):
			c = tuple(palette[i*3:i*3+3])
			cl = color_to_15bit(c,31)
			loopy_palette[i] = cl
			palette[i*3:i*3+3] = list(color_from_15bit(cl,255))
		im_quant.putpalette(palette)
		
		im_dither = im.quantize(dither=Image.Dither.FLOYDSTEINBERG, palette=im_quant)
	else:
		im_dither = im.convert('P', palette=Image.Palette.ADAPTIVE, dither=Image.Dither.NONE, colors=num_colors)
		palette = im_dither.getpalette()[:num_colors*3]
		loopy_palette = [0]*num_colors
		for i in range(num_colors):
			c = tuple(palette[i*3:i*3+3])
			cl = color_to_15bit(c,255)
			loopy_palette[i] = cl
	
	im_dither = im_dither.transpose(Image.Transpose.ROTATE_270)
	im_dither_px = im_dither.load()
	
	# Save loopy data
	pad_top = (224-height) // 2
	pad_bottom = 224-height-pad_top
	pad_left = (256-width) // 2
	pad_right = 256-width-pad_left
	
	bm_data = b""
	if pad_top > 0:
		bm_data += bytes([0])*256*pad_top
	for y in range(height):
		cols = [im_dither_px[x,y]+palmin for x in range(width)]
		if pad_left > 0:
			bm_data += bytes([0])*pad_left
		bm_data += struct.pack(f">{width}B", *cols)
		if pad_right > 0:
			bm_data += bytes([0])*pad_right
	if pad_bottom > 0:
		bm_data += bytes([0])*256*pad_bottom
	
	pal_data = struct.pack(f">{num_colors}H", *loopy_palette)
	
	with open(path_bin, "wb") as f_bin:
		f_bin.write(bm_data)
	with open(path_pal, "wb") as f_pal:
		f_pal.write(pal_data)
	
	bm_addr = 0x0C000000
	pal_addr = 0x0C051000+(palmin*2)
	
	with open(path_state, "wb") as f_state:
		f_state.write(b"LPSTATE\0")
		# VDP_LAYER_CTRL, VDP_BLEND_CTRL, VDP_BACKDROP_B, VDP_BACKDROP_A
		f_state.write(struct.pack(">III", 0x0C05B002, 8, 2))
		f_state.write(struct.pack(">HHHH", 0xAA04, 0x0066, 0x0000, STATE_BACKDROP_COLOR))
		file_write_align(f_state, 4)
		# VDP_BM0_SCROLLX, VDP_BM0_SCROLLY, VDP_BM0_SCREENX, VDP_BM0_SCREENY, VDP_BM0_WIDTH, VDP_BM0_HEIGHT, VDP_BM_CTRL
		f_state.write(struct.pack(">IIIHxx", 0x0C059000, 2, 2, 0))
		f_state.write(struct.pack(">IIIHxx", 0x0C059008, 2, 2, 0))
		f_state.write(struct.pack(">IIIHxx", 0x0C059010, 2, 2, 0))
		f_state.write(struct.pack(">IIIHxx", 0x0C059018, 2, 2, 0))
		f_state.write(struct.pack(">IIIHxx", 0x0C059020, 2, 2, 256-1))
		f_state.write(struct.pack(">IIIHxx", 0x0C059028, 2, 2, 224-1))
		f_state.write(struct.pack(">IIIHxx", 0x0C059030, 2, 2, 0))
		# Palette and bitmap
		f_state.write(struct.pack(">III", pal_addr, len(pal_data), 2))
		f_state.write(pal_data)
		file_write_align(f_state, 4)
		f_state.write(struct.pack(">III", bm_addr, len(bm_data), 1))
		f_state.write(bm_data)
		file_write_align(f_state, 4)
	
	print(f"Load {os.path.basename(path_pal)} at 0x{pal_addr:08X},"+\
	f"{os.path.basename(path_bin)} at 0x{bm_addr:08X}, set registers appropriately")
	print("OR")
	print(f"Load state {os.path.basename(path_state)} to view directly")

if __name__ == "__main__":
	main()
