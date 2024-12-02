import struct
from PIL import Image
from util import check_files, load_palette
from lzss_ww import decompress

def cmd_decode_tilesheet(args):
	# Parse and verify command arguments
	res_ts_in = args.path_res_tiles_in
	res_pal_in = args.path_res_pal_in
	im_out = args.path_image_out
	transp = args.transparent
	comp = args.compressed
	if not check_files(exist=[res_ts_in, res_pal_in], noexist=[im_out]):
		return
	print("Transparent: " + ("YES" if transp else "NO"))
	print("Compressed: " + ("YES" if comp else "NO"))
	
	# Read input data
	with open(res_ts_in, "rb") as f:
		data_tiles = f.read()
	with open(res_pal_in, "rb") as f:
		data_palette = f.read()
	
	# Load palette
	palette = load_palette(data_palette, transp, do_print=True)
	if not palette:
		return
	palette_rgba, palette_size = palette
	
	# Decompress tilesheet data if necessary
	if comp:
		data_tiles = decompress(data_tiles)
		if data_tiles == None:
			return
		print(f"Decompressed {len(data_tiles)} bytes")
	#comp_uncomp_other = "uncompressed" if comp else "compressed"
	comp_uncomp_other = "compressed = false" if comp else "compressed = true"
	
	# Load and verify tile count
	header_fmt = ">H"
	header_size = struct.calcsize(header_fmt)
	if len(data_tiles) < header_size:
		print(f"Data too short, try {comp_uncomp_other}.")
		return
	num_tiles = struct.unpack(header_fmt, data_tiles[:header_size])[0]
	data_tiles = data_tiles[header_size:]
	if num_tiles == 0:
		print("No tiles")
		return
	if len(data_tiles) != num_tiles*32:
		print(f"Data size mismatch, try {comp_uncomp_other}.")
		return
	
	# Compute output image dimensions
	img_width = 64
	img_height = ((num_tiles+7)//8) * 8
	print(f"Sheet contains {num_tiles} tiles, output in {img_width}x{img_height} image")

	# Write output image
	img = Image.new("RGBA", (img_width, img_height), color = (0,0,0,0))
	pix = img.load()
	for t in range(num_tiles):
		for tx in range(8):
			for ty in range(8):
				ci = data_tiles[t*32 + ty*4 + tx//2]
				if tx & 1 == 0:
					ci >>= 4
				ci &= 15
				if ci >= palette_size:
					print(f"Invalid color {ci} at T{t}:{tx},{ty}")
					continue
				ix = (t&7)*8 + tx
				iy = (t//8)*8 + ty
				pix[ix,iy] = palette_rgba[ci]
	print(f"Saving to {im_out}")
	img.save(im_out)
