import struct
from PIL import Image
from util import check_files, make_dirs_for_file
from util import load_palette, palette_to_rgba, print_palette_rgba
from util import col2rgb, rgb2col
from util import load_image_as_indexed
from lzss_ww import compress, decompress

def cmd_decode_image(args):
	# Parse and verify command arguments
	res_im_in = args.path_res_im_in
	res_pal_in = args.path_res_pal_in
	im_out = args.path_image_out
	transp = args.transparent
	comp = args.compressed
	indexed = args.indexed
	if not check_files(exist=[res_im_in, res_pal_in], noexist=[im_out]):
		return False
	print("Transparent: " + ("YES" if transp else "NO"))
	print("Compressed: " + ("YES" if comp else "NO"))
	print("Indexed-color: " + ("YES" if indexed else "NO"))
	
	# Read input data
	with open(res_im_in, "rb") as f:
		data_image = f.read()
	with open(res_pal_in, "rb") as f:
		data_palette = f.read()
	
	# Load palette
	palette = load_palette(data_palette)
	if not palette:
		return False
	palette_rgba = palette_to_rgba(palette, first_transparent=(transp and not indexed))
	palette_size = len(palette)
	#print_palette_rgba(palette_rgba)
	
	# Decompress image data if necessary
	if comp:
		data_image = decompress(data_image)
		if data_image == None:
			return False
		print(f"Decompressed {len(data_image)} bytes")
	#comp_uncomp_other = "uncompressed" if comp else "compressed"
	comp_uncomp_other = "compressed = false" if comp else "compressed = true"
	
	# Load and verify image dimensions
	header_fmt = "BB"
	header_size = struct.calcsize(header_fmt)
	if len(data_image) < header_size:
		print(f"Data too short, try {comp_uncomp_other}.")
		return False
	img_width, img_height = struct.unpack(header_fmt, data_image[:header_size])
	data_image = data_image[header_size:]
	img_width = img_width or 256
	img_height = img_height or 256
	print(f"Image dimensions {img_width}x{img_height}")
	expect_size = img_width*img_height
	# Some resources are longer due to padding
	if len(data_image) not in range(expect_size, expect_size+4):
		print(f"Data size mismatch, try {comp_uncomp_other}.")
		return False
	data_image = data_image[:expect_size]
	
	# Convert to output format
	if indexed:
		img = Image.new("P", (img_width, img_height), color = 0)
		palette_rgb_flat = [0]*(palette_size*3)
		for i in range(palette_size):
			palette_rgb_flat[i*3:i*3+3] = list(palette_rgba[i])[:3]
		img.putpalette(palette_rgb_flat)
		img.putdata(data_image)
		if transp:
			img.info["transparency"] = 0
	else:
		img = Image.new("RGBA", (img_width, img_height), color = (0,0,0,0))
		pix = img.load()
		for x in range(img_width):
			for y in range(img_height):
				ci = data_image[y*img_width+x]
				if ci >= palette_size:
					print(f"Invalid color {ci} at {x},{y}")
					continue
				pix[x,y] = palette_rgba[ci]
	
	# Write output image
	print(f"Saving to {im_out}")
	make_dirs_for_file(im_out)
	img.save(im_out, **img.info)
	return True

def cmd_encode_image(args):
	# Parse and verify command arguments
	im_in = args.path_image_in
	res_pal_in = args.path_res_pal_in
	res_im_out = args.path_res_im_out
	transp = args.transparent
	comp = args.compressed
	indexed = args.indexed
	dither = args.dither
	if not check_files(exist=[im_in] if indexed else [im_in, res_pal_in], noexist=[res_im_out]):
		return False
	print("Transparent: " + ("YES" if transp else "NO"))
	print("Compressed: " + ("YES" if comp else "NO"))
	print("Indexed-color: " + ("YES" if indexed else "NO"))
	print("Dither: " + ("YES" if dither else "NO"))
	
	if indexed:
		print()
		print("Indexed-color will be converted directly, ignoring palette input and transparent/dither settings!")
	
	# Read input data
	try:
		img = Image.open(im_in)
	except Exception as e:
		print("Error opening image")
		return False
	if img.width > 256 or img.height > 256:
		print("Image dimensions too large (max 256x256)")
		return False
	
	# Get pixel values from image
	if indexed:
		img = load_image_as_indexed(img, 256)
		if img == None:
			return False
		data_image = list(img.getdata())
	else:
		img = img.convert("RGBA")
		if transp:
			img_alpha = img.getchannel("A").convert("1")
			img_alpha_px = img_alpha.load()
		
		with open(res_pal_in, "rb") as f:
			data_palette = f.read()
	
		# Load palette
		data_palette = load_palette(data_palette)
		if not data_palette:
			return False
		if transp:
			data_palette = data_palette[1:]
		palette_size = len(data_palette)
		palette_rgba = palette_to_rgba(data_palette, first_transparent=False)
		
		# Make opaque by compositing over first color, so we can use dithering later
		img = Image.alpha_composite(Image.new("RGBA", img.size, palette_rgba[0]), img).convert("RGB")
		
		# Extend palette to 256 colors and create an image with it
		last_color = palette_rgba[-1]
		if palette_size < 256:
			palette_rgba += [last_color]*(256-palette_size)
		palette_rgb_flat = [0]*(palette_size*3)
		for i in range(palette_size):
			palette_rgb_flat[i*3:i*3+3] = list(palette_rgba[i])[:3]
		img_palette = Image.new("P", (16,16))
		img_palette.putpalette(palette_rgb_flat)
		
		# Quantize to palette with optional dithering
		dither_method = Image.Dither.FLOYDSTEINBERG if dither else Image.Dither.NONE
		img_quantized = img.quantize(dither=dither_method, palette=img_palette)
		
		# Extract pixel values and reapply transparency
		data_image = bytearray(img.width*img.height)
		img_quantized_px = img_quantized.load()
		for x in range(img.width):
			for y in range(img.height):
				cv = 0
				if (not transp) or img_alpha_px[x,y]:
					cv = min(img_quantized_px[x,y], palette_size-1)
					if transp:
						cv += 1
				data_image[y*img.width+x] = cv
	
	# Serialize image and palette data
	data_image = struct.pack("BB", img.width&255, img.height&255) + bytes(data_image)
	
	# Compress image data if necessary
	if comp:
		data_image = compress(data_image)
	
	# Write output data
	print(f"Saving to {res_im_out}")
	make_dirs_for_file(res_im_out)
	with open(res_im_out, "wb") as f:
		f.write(data_image)
