import struct
from PIL import Image
from util import check_files, make_dirs_for_file
from util import col2rgb, load_palette, palette_to_rgba, print_palette_rgba, rgb2col

def cmd_decode_palette(args):
	# Parse and verify command arguments
	pal_in = args.path_pal_in
	im_out = args.path_image_out
	if not check_files(exist=[pal_in], noexist=[im_out]):
		return False
	
	# Read input data
	with open(pal_in, "rb") as f:
		data_palette = f.read()
	
	# Load palette
	palette = load_palette(data_palette)
	if not palette:
		return False
	palette_rgba = palette_to_rgba(palette, first_transparent=False)
	palette_size = len(palette)
	print_palette_rgba(palette_rgba)
	
	# Compute output image dimensions
	img_width = 16
	img_height = (palette_size+15)//16
	print(f"Palette contains {palette_size} colors, output in {img_width}x{img_height} image")
	
	# Write output image
	img = Image.new("RGBA", (img_width, img_height), color = (0,0,0,0))
	pix = img.load()
	for ci in range(palette_size):
		ix = ci&15
		iy = ci//16
		pix[ix,iy] = palette_rgba[ci]
	print(f"Saving to {im_out}")
	make_dirs_for_file(im_out)
	img.save(im_out)
	return True

def cmd_derive_palette(args):
	# Parse and verify command arguments
	im_in = args.path_image_in
	res_pal_out = args.path_res_pal_out
	transp = args.transparent
	palette_size = args.palsize
	if not check_files(exist=[im_in], noexist=[res_pal_out]):
		return False
	if palette_size < (2 if transp else 1) or palette_size > 256:
		print("Palette size out of range")
		return False
	print("Transparent: " + ("YES" if transp else "NO"))
	num_colors_quant = palette_size - (1 if transp else 0)
	
	# Read input data
	try:
		img = Image.open(im_in).convert("RGBA")
	except Exception as e:
		print("Error opening image")
		return False
	
	# Gather only the opaque colors
	
	# Separate alpha out, set transparent pixels to the average opaque color (hacky)
	if transp:
		img_px = img.load()
		opaque_pixels = []
		for x in range(img.width):
			for y in range(img.height):
				r,g,b,a = img_px[x,y]
				if a >= 128:
					opaque_pixels.append((r,g,b))
		if len(opaque_pixels) == img.width*img.height:
			img_colors = img.convert("RGB")
		else:
			img_colors = Image.new("RGB", (len(opaque_pixels), 1))
			img_colors.putdata(opaque_pixels)
	else:
		bgcol = (255,255,255,255)
		img_colors = Image.alpha_composite(Image.new("RGBA", img.size, bgcol), img).convert("RGB")
	
	# Reduce to RGB555 and quantize, add 1 so we can differentiate existing colors in palette
	img_quantized = img_colors.copy()
	img_quantized_px = img_quantized.load()
	for x in range(img_colors.width):
		for y in range(img_colors.height):
			r5, g5, b5 = col2rgb(rgb2col(img_quantized_px[x,y],255),31)
			img_quantized_px[x,y] = (r5+1,g5+1,b5+1)
	#img_quantized = img_quantized.convert('P', palette=Image.Palette.ADAPTIVE, dither=Image.Dither.NONE, colors=num_colors_quant)
	img_quantized = img_quantized.quantize(colors=num_colors_quant, method=Image.Quantize.MAXCOVERAGE, dither=Image.Dither.NONE)
	quant_palette = img_quantized.getpalette()[:num_colors_quant*3]
	
	# Pick out only unique colors
	actual_num_colors_quant = 0
	quant_palette_set = set()
	for i in range(num_colors_quant):
		c = tuple(quant_palette[i*3:i*3+3])
		if c != (0,0,0):
			r5, g5, b5 = c
			quant_palette_set.add((r5-1, g5-1, b5-1))
	
	# Sort colors approximately by brightness
	quant_palette = sorted(list(quant_palette_set), key=lambda x: (x[0]*2 + x[1]*4 + x[2]*1))
	num_colors_quant = len(quant_palette)
	if num_colors_quant < 1:
		raise ValueError("pal empty after quant should not happen")
	print(f"Quantized to {num_colors_quant} colors")
	
	# Extract RGB555 palette, subtracting the 1 we added before
	default_color = rgb2col((0,0,0), 31)
	data_palette = [default_color]*palette_size
	for i in range(num_colors_quant):
		c = quant_palette[i]
		cl = rgb2col(c, 31)
		data_palette[(i+1) if transp else i] = cl
	
	# Write output data
	print(f"Saving palette to {res_pal_out}")
	make_dirs_for_file(res_pal_out)
	print_palette_rgba(palette_to_rgba(data_palette, transp))
	data_palette = struct.pack(f">H{palette_size}H", palette_size, *data_palette)
	with open(res_pal_out, "wb") as f:
		f.write(data_palette)
