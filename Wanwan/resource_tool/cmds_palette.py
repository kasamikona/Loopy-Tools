from PIL import Image
from util import check_files, load_palette

def cmd_preview_palette(args):
	# Parse and verify command arguments
	pal_in = args.path_pal_in
	im_out = args.path_image_out
	if not check_files(exist=[pal_in], noexist=[im_out]):
		return
	
	# Load palette
	with open(pal_in, "rb") as f:
		data_palette = f.read()
	palette = load_palette(data_palette, use_transp=False, do_print=True)
	if not palette:
		return
	palette_rgba, palette_size = palette
	
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
	img.save(im_out)
