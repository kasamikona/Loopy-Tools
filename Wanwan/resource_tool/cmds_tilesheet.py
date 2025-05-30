import struct
from PIL import Image
from util import check_files, make_dirs_for_file
from util import load_palette, palette_to_rgba, print_palette_rgba
from util import load_image_as_grayscale, load_image_as_indexed
from lzss_ww import compress, decompress

def _load_tiles(data):
	header_fmt = ">H"
	header_size = struct.calcsize(header_fmt)
	if len(data) < header_size:
		print("Data too short")
		return None
	num_tiles = struct.unpack(header_fmt, data[:header_size])[0]
	data = data[header_size:]
	if num_tiles == 0:
		print("No tiles")
		return None
	expect_size = num_tiles*32
	# Resources may be padded
	if len(data) not in range(expect_size, expect_size+4):
		print("Data size mismatch")
		return None
	tiles = [None]*num_tiles
	for t in range(num_tiles):
		tiles[t] = [0]*64
		for p in range(64):
			pv = data[t*32 + p//2]
			if p&1 == 0:
				pv >>= 4
			pv &= 15
			tiles[t][p] = pv
	return tiles

def _store_tiles(tiles):
	num_tiles = len(tiles)
	if num_tiles == 0:
		print("No tiles")
		return None
	header_fmt = ">H"
	header_size = struct.calcsize(header_fmt)
	data = bytearray(num_tiles*32)
	for t in range(num_tiles):
		for p in range(64):
			pv = tiles[t][p] & 15
			if p&1 == 0:
				pv <<= 4
			data[t*32 + p//2] |= pv
	data = struct.pack(header_fmt, num_tiles) + bytes(data)
	return data

def _load_map(data):
	header_fmt = ">BB"
	header_size = struct.calcsize(header_fmt)
	if len(data) < header_size:
		print("Data too short")
		return None
	map_width, map_height = struct.unpack(header_fmt, data[:header_size])
	data = data[header_size:]
	map_width = map_width or 256
	map_height = map_height or 256
	expect_size = map_width*map_height*2
	if len(data) not in range(expect_size, expect_size+4):
		print("Data size mismatch")
		return None
	tdata = struct.unpack(f">{map_width*map_height}H", data)
	tilemap = [[None]*map_height for i in range(map_width)]
	for y in range(map_height):
		for x in range(map_width):
			t = tdata[y*map_width+x]
			tile_idx = t & 0x7FF
			tile_scrn = (t>>11) & 1
			tile_subpal = (t>>12) & 3
			tile_flipx = ((t>>14) & 1) == 1
			tile_flipy = ((t>>15) & 1) == 1
			tilemap[x][y] = (tile_idx, tile_flipx, tile_flipy, tile_subpal, tile_scrn)
	return (tilemap, map_width, map_height)

def cmd_decode_tilesheet(args):
	# Parse and verify command arguments
	res_tiles_in = args.path_res_tiles_in
	res_pal_in = args.path_res_pal_in
	im_out = args.path_image_out
	transp = args.transparent
	comp = args.compressed
	indexed = args.indexed
	subpal = args.subpalette
	use_graymap = res_pal_in == "-"
	if not check_files(exist=[res_tiles_in] if use_graymap else [res_tiles_in, res_pal_in], noexist=[im_out]):
		return False
	print("Transparent: " + ("YES" if transp else "NO"))
	print("Compressed: " + ("YES" if comp else "NO"))
	print("Indexed-color: " + ("YES" if indexed else "NO"))
	print(f"Subpalette: {subpal}")
	
	# Read input data
	with open(res_tiles_in, "rb") as f:
		data_tiles = f.read()
	if not use_graymap:
		with open(res_pal_in, "rb") as f:
			data_palette = f.read()
	
	# Load palette
	if use_graymap:
		palette_rgba = [(x,x,x,255) for x in [round(x*255/15) for x in range(16)]]
		if transp:
			palette_rgba[0] = (0,0,0,0)
		print("Using 16-step grayscale map (subpalette ignored)")
	else:
		palette = load_palette(data_palette)
		if not palette:
			return False
		palette_size = len(palette)
		
		# Get subpalette from palette
		num_subpals = palette_size // 16
		print(f"Available subpalettes: {num_subpals}")
		if subpal < 0 or subpal >= num_subpals:
			print(f"Invalid subpalette {subpal}")
			return False
		palette = palette[subpal*16:][:16]
		palette_size = 16
		
		# Convert palette to RGBA
		palette_rgba = palette_to_rgba(palette, first_transparent=transp)
		#print_palette_rgba(palette_rgba)
	
	# Decompress tilesheet data if necessary
	if comp:
		data_tiles = decompress(data_tiles)
		if data_tiles == None:
			return False
		print(f"Decompressed {len(data_tiles)} bytes")
	#comp_uncomp_other = "uncompressed" if comp else "compressed"
	comp_uncomp_other = "compressed = false" if comp else "compressed = true"
	
	# Load and verify tiles
	tiles = _load_tiles(data_tiles)
	if tiles == None:
		print(f"Try {comp_uncomp_other}.")
		return False
	num_tiles = len(tiles)
	
	# Compute output image dimensions
	img_width = 64
	img_height = ((num_tiles+7)//8) * 8
	print(f"Sheet contains {num_tiles} tiles, output in {img_width}x{img_height} image")
	img_size = (img_width, img_height)

	# Write output image
	if indexed:
		img = Image.new("P", img_size, color=0)
		if transp:
			img.info["transparency"] = 0
		palette_rgb_flat = [0]*16*3
		for i in range(16):
			palette_rgb_flat[i*3:i*3+3] = palette_rgba[i][:3]
		img.putpalette(palette_rgb_flat)
	else:
		img = Image.new("RGBA", img_size, color=(0,0,0,0))
	pix = img.load()
	for t in range(num_tiles):
		for tx in range(8):
			for ty in range(8):
				color_value = tiles[t][ty*8 + tx]
				ix = (t&7)*8 + tx
				iy = (t//8)*8 + ty
				if indexed:
					pix[ix,iy] = color_value
				else:
					pix[ix,iy] = palette_rgba[color_value]
	print(f"Saving to {im_out}")
	make_dirs_for_file(im_out)
	img.save(im_out)
	return True

def cmd_encode_tilesheet(args):
	# Parse and verify command arguments
	im_in = args.path_image_in
	res_tiles_out = args.path_res_tiles_out
	comp = args.compressed
	indexed = args.indexed
	num_tiles = args.num_tiles
	trim_end = False
	if num_tiles < 1:
		num_tiles = None
		trim_end = True
	if not check_files(exist=[im_in], noexist=[res_tiles_out]):
		return False
	print("Compressed: " + ("YES" if comp else "NO"))
	print("Indexed-color: " + ("YES" if indexed else "NO"))
	print("Number of tiles: " + str(num_tiles or "(from image)"))
	
	# Read input data
	try:
		img = Image.open(im_in)
	except Exception as e:
		print("Error opening image")
		return False
	num_columns = img.width // 8
	num_rows = img.height // 8
	print(f"Image contains {num_columns} columns x {num_rows} rows")
	if num_tiles == None:
		num_tiles = num_columns * num_rows
	if indexed:
		img = load_image_as_indexed(img, 16)
	else:
		img = load_image_as_grayscale(img, 16)
	if img == None:
		return False
	pix = img.load()
	
	# Get tiles from input image
	tiles = [None]*num_tiles
	last_nonempty = -1
	for t in range(num_tiles):
		tiledata = [0]*64
		empty = True
		for tx in range(8):
			for ty in range(8):
				ix = (t%num_columns)*8 + tx
				iy = (t//num_columns)*8 + ty
				value =  pix[ix,iy]
				if value > 0:
					empty = False
				tiledata[ty*8 + tx] = value
		tiles[t] = tiledata
		if not empty:
			last_nonempty = t
	if trim_end and last_nonempty+1 != num_tiles:
		diff = num_tiles - (last_nonempty+1)
		num_tiles = last_nonempty+1
		print(f"Last {diff} cells in image are empty, trimming to {num_tiles} tiles (specify num_tiles to override)")
		if num_tiles < 1:
			print("No tiles to encode")
			return False
		tiles = tiles[:num_tiles]
	
	# Create tilesheet data
	data_tiles = _store_tiles(tiles)
	if data_tiles == None:
		return False
	
	# Compress tilesheet data if necessary
	if comp:
		data_tiles = compress(data_tiles)
		if data_tiles == None:
			return False
		print(f"Compressed {len(data_tiles)} bytes")
	
	# Write output data
	print(f"Saving to {res_tiles_out}")
	with open(res_tiles_out, "wb") as f:
		f.write(data_tiles)
	return True

def cmd_decode_tilemap(args):
	# Parse and verify command arguments
	res_map_in = args.path_res_map_in
	res_tiles_in = args.path_res_tiles_in
	res_pal_in = args.path_res_pal_in
	im_out = args.path_image_out
	transp = args.transparent
	comp = args.compressed
	scrnb = args.screenb
	if not check_files(exist=[res_map_in, res_tiles_in, res_pal_in], noexist=[im_out]):
		return False
	print("Transparent: " + ("YES" if transp else "NO"))
	print("Compressed: " + ("YES" if comp else "NO"))
	print("Screen: " + ("B" if scrnb else "A"))
	
	# Read input data
	with open(res_map_in, "rb") as f:
		data_map = f.read()
	with open(res_tiles_in, "rb") as f:
		data_tiles = f.read()
	with open(res_pal_in, "rb") as f:
		data_palette = f.read()
	
	# Load palette
	palette = load_palette(data_palette)
	if not palette:
		return False
	palette_size = len(palette)
	
	# Get subpalettes from palette
	num_subpals = palette_size // 16
	print(f"Available subpalettes: {num_subpals}")
	subpalettes_rgba = [None]*num_subpals
	for i in range(num_subpals):
		sp = palette[i*16:i*16+16]
		sp_rgba = palette_to_rgba(sp, first_transparent=transp)
		print(f"Subpalette {i}:")
		print_palette_rgba(sp_rgba)
		subpalettes_rgba[i] = sp_rgba
	
	# Decompress tilemap and tilesheet data if necessary
	if comp:
		data_map = decompress(data_map)
		data_tiles = decompress(data_tiles)
		if data_map == None or data_tiles == None:
			return False
		#print(f"Decompressed {len(data_map)} bytes")
	comp_uncomp_other = "compressed = false" if comp else "compressed = true"
	
	# Load and verify map
	tm = _load_map(data_map)
	if tm == None:
		print(f"Try {comp_uncomp_other}.")
		return False
	tilemap, map_width, map_height = tm
	tilesize = 8
	
	# Load and verify tiles
	tiles = _load_tiles(data_tiles)
	if tiles == None:
		print(f"Try {comp_uncomp_other}.")
		return False
	num_tiles = len(tiles)
	print(f"Tilesheet contains {num_tiles} tiles")
	
	# Compute output image dimensions
	img_width = map_width * tilesize
	img_height = map_height * tilesize
	print(f"Tilemap contains {map_width}x{map_height} tiles, output in {img_width}x{img_height} image")

	# Write output image
	img = Image.new("RGBA", (img_width, img_height), color = (0,0,0,0))
	pix = img.load()
	for x in range(map_width):
		for y in range(map_height):
			tile_idx, tile_flipx, tile_flipy, tile_subpal, tile_scrn = tilemap[x][y]
			#tile_flipx = True
			if (tile_scrn==1) != scrnb:
				continue
			if tile_idx >= num_tiles:
				print(f"Invalid tile index {tile_idx} at tile {x},{y}")
				return False
			if tile_subpal >= num_subpals:
				print(f"Invalid subpalette {tile_subpal} at tile {x},{y}")
				return False
			for tx in range(tilesize):
				for ty in range(tilesize):
					color_value = tiles[tile_idx][ty*8 + tx]
					ix = x*tilesize + ((tilesize-1-tx) if tile_flipx else tx) 
					iy = y*tilesize + ((tilesize-1-ty) if tile_flipy else ty) 
					pix[ix,iy] = subpalettes_rgba[tile_subpal][color_value]
	print(f"Saving to {im_out}")
	make_dirs_for_file(im_out)
	img.save(im_out)
	return True
