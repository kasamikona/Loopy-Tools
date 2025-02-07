from PIL import Image
from util import check_files, make_dirs_for_file, load_palette, palette_to_rgba, print_palette_rgba

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
