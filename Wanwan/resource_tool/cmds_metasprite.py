from util import check_files, make_dirs_for_file
import struct

def cmd_decode_metasprite(args):
	# Parse and verify command arguments
	msp_in = args.path_metasprite_in
	txt_out = args.path_text_out
	if not check_files(exist=[msp_in], noexist=[txt_out]):
		return False
	
	# Read input data
	with open(msp_in, "rb") as f:
		data = f.read()
	
	# Parse metasprite header
	if len(data) < 5:
		print("Header too short")
		return False
	num_groups, data_offset = struct.unpack(">HH", data[:4])
	if num_groups != 1 or data_offset != 4:
		print(f"Unexpected header: num_groups={num_groups} data_offset={data_offset}")
		print("Metasprite format requires further analysis")
		return False
	num_sprites = data[4]
	data = data[5:]
	if len(data) < num_sprites*4:
		print("Data too short")
		return False
	
	# Read sprite data
	sprites = [None]*num_sprites
	for i in range(num_sprites):
		sprite_data = data[i*4:i*4+4]
		tileidx, offsetx, offsety, oamattr = struct.unpack("BbbB", sprite_data)
		attr_flipx = ((oamattr>>6)&1) == 1
		attr_flipy = ((oamattr>>7)&1) == 1
		attr_size = (oamattr>>2)&3
		sprites[i] = (tileidx, offsetx, offsety, attr_flipx, attr_flipy, attr_size)
	
	# Write output text
	size_table = ["8x8","16x16","16x32","32x32"]
	def _bs(b):
		return str(bool(b)).lower()
	make_dirs_for_file(txt_out)
	print(f"Saving to {txt_out}")
	with open(txt_out, "w") as f:
		for i in range(num_sprites):
			if i > 0:
				f.write("\n")
			f.write(f"[group{0}.sprite{i}]\n")
			tileidx, offsetx, offsety, attr_flipx, attr_flipy, attr_size = sprites[i]
			f.write(f"tile_index={tileidx}\n")
			f.write(f"offset_x={offsetx}\n")
			f.write(f"offset_y={offsety}\n")
			f.write(f"flip_x={_bs(attr_flipx)}\n")
			f.write(f"flip_y={_bs(attr_flipy)}\n")
			f.write(f"size={size_table[attr_size]}\n")
	return True
