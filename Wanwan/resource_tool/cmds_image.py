import struct
from PIL import Image
from util import check_files, load_palette, palette_to_rgba, print_palette_rgba
from lzss_ww import decompress

def cmd_decode_image(args):
	# Parse and verify command arguments
	res_im_in = args.path_res_im_in
	res_pal_in = args.path_res_pal_in
	im_out = args.path_image_out
	transp = args.transparent
	comp = args.compressed
	if not check_files(exist=[res_im_in, res_pal_in], noexist=[im_out]):
		return
	print("Transparent: " + ("YES" if transp else "NO"))
	print("Compressed: " + ("YES" if comp else "NO"))
	
	# Read input data
	with open(res_im_in, "rb") as f:
		data_image = f.read()
	with open(res_pal_in, "rb") as f:
		data_palette = f.read()
	
	# Load palette
	palette = load_palette(data_palette)
	if not palette:
		return
	palette_rgba = palette_to_rgba(palette, first_transparent=transp)
	palette_size = len(palette)
	print_palette_rgba(palette_rgba)
	
	# Decompress image data if necessary
	if comp:
		data_image = decompress(data_image)
		if data_image == None:
			return
		print(f"Decompressed {len(data_image)} bytes")
	#comp_uncomp_other = "uncompressed" if comp else "compressed"
	comp_uncomp_other = "compressed = false" if comp else "compressed = true"
	
	# Load and verify image dimensions
	header_fmt = "BB"
	header_size = struct.calcsize(header_fmt)
	if len(data_image) < header_size:
		print(f"Data too short, try {comp_uncomp_other}.")
		return
	img_width, img_height = struct.unpack(header_fmt, data_image[:header_size])
	data_image = data_image[header_size:]
	img_width = img_width or 256
	img_height = img_height or 256
	print(f"Image dimensions {img_width}x{img_height}")
	expect_size = img_width*img_height
	# Some resources are 1 byte too long for some reason
	if len(data_image) not in [expect_size, expect_size+1]:
		print(f"Data size mismatch, try {comp_uncomp_other}.")
		return
	
	# Write output image
	img = Image.new("RGBA", (img_width, img_height), color = (0,0,0,0))
	pix = img.load()
	for x in range(img_width):
		for y in range(img_height):
			ci = data_image[y*img_width+x]
			if ci >= palette_size:
				print(f"Invalid color {ci} at {x},{y}")
				continue
			pix[x,y] = palette_rgba[ci]
	print(f"Saving to {im_out}")
	img.save(im_out)
