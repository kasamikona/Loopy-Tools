import os, shlex, struct, time

import monitor_util as util
import monitor_addresses as addresses
from monitor_protocol import DataType

SCREENCAP_SHOW_INDICES = False

SIZE_TYPE = DataType.LONG

def run_cmd_savestate(cmd, suffix, args, protocol):
	if args == None or len(args) != 2:
		print(f"Syntax: {cmd} <template.txt> <output.state>")
		print("Each line of template specifies (address, data type, length) separated by whitespace, with optional name following" +
			" which will be printed during saving. Addresses and lengths work as in dump commands. Data type is bit width.")
		return False

	tplname = args[0]
	if os.path.isdir(tplname) or not os.path.exists(tplname):
		print(f"File \"{tplname}\" does not exist or is not readable.")
		return False

	outname = args[1]
	if outname.startswith("!"):
		outname = outname[1:]
	elif os.path.exists(outname):
		print(f"File \"{outname}\" already exists. Prefix with ! to overwrite.")
		return False

	blocks = []
	with open(tplname, "r") as f_template:
		for line in f_template.readlines():
			line = line.strip()
			if line.startswith("#") or len(line) == 0:
				continue
			parts = shlex.split(line)
			if len(parts) < 3:
				print(f"Incomplete line: {line}")
				return False
			line_addr, line_type, line_len = parts[:3]
			if not line_type in ["8","16","32"]:
				print(f"Bad data type in line: {line}")
				return False
			data_type = DataType.from_str(line_type)
			addr, length = addresses.data_addr_len(line_addr, data_type)
			if addr == None:
				print(f"Bad address in line: {line}")
				return False
			if line_len != "*":
				length = util.try_parse_num(line_len, SIZE_TYPE.nbits)
			if length == None or (length % data_type.nbytes) != 0:
				print(f"Bad length in line: {line}")
				return False
			name = None
			if len(parts) >= 4:
				name = parts[3]
			blocks.append( (addr, length, data_type, name) )

	try:
		with open(outname, "wb") as f_state:
			f_state.write(b"LPSTATE\0")
			util.file_write_align(f_state, 4)
			for block in blocks:
				addr, length, data_type, name = block
				if name:
					print(f"Reading 0x{addr:08X} ({name})")
				else:
					print(f"Reading 0x{addr:08X}")
				f_state.write(struct.pack(">III", addr, length, data_type.nbytes))
				util.file_write_align(f_state, 4)
				if not protocol.read_to_stream(addr, length // data_type.nbytes, data_type, f_state):
					print("Timed out")
					return False
				util.file_write_align(f_state, 4)

	except KeyboardInterrupt:
		print("Cancelled")
		return True

	print("State saved")
	return True

def run_cmd_loadstate(cmd, suffix, args, protocol):
	if args == None or len(args) != 1:
		print(f"Syntax: {cmd} <input.state>")
		return False

	inname = args[0]
	if os.path.isdir(inname) or not os.path.exists(inname):
		print(f"File \"{inname}\" does not exist or is not readable.")
		return False

	try:
		with open(inname, "rb") as f_state:
			if f_state.read(8) != b"LPSTATE\0":
				print("Invalid state file")
				return False
			util.file_read_align(f_state, 4)
			while True:
				chunkhead = f_state.read(12)
				if len(chunkhead) < 12:
					break
				util.file_read_align(f_state, 4)
				addr, length, type_nbytes = struct.unpack(">III", chunkhead)
				if type_nbytes not in [1,2,4]:
					print(f"Bad data type in block 0x{addr:08X}")
					return False
				data_type = DataType.from_nbytes(type_nbytes)
				print(f"Writing 0x{addr:08X}")
				if not protocol.write_from_stream(addr, length // data_type.nbytes, data_type, f_state):
					return False
				util.file_read_align(f_state, 4)

	except KeyboardInterrupt:
		print("Cancelled")
		return True

	print("State loaded")
	return True

def run_cmd_screencap(cmd, suffix, args, protocol):
	if args == None or len(args) != 2:
		print(f"Syntax: {cmd} <capture mode> <output name>")
		print("File name should not include extension. Saves PNG+BIN(+PAL) automatically.")
		print("Capture modes:")
		print("0: 15bpp raw blend")
		print("1: 15bpp raw screen A")
		print("2: 8bpp paletted screen A")
		print("3: same as 2?")
		return False

	try:
		capture_mode = int(args[0])
	except ValueError:
		capture_mode = None
	if capture_mode == None or capture_mode not in range(4):
		print("Invalid capture mode")
		return False
	has_palette = capture_mode >= 2

	fname = args[1]
	if fname.startswith("!"):
		fname = fname[1:]
	elif NO_OVERWRITE:
		exist = False
		if os.path.exists(f"{fname}.bin"):
			print(f"{fname}.bin already exists")
			exist = True
		if os.path.exists(f"{fname}.png"):
			print(f"{fname}.png already exists")
			exist = True
		if has_palette and os.path.exists(f"{fname}.pal"):
			print(f"{fname}.pal already exists")
			exist = True
		if has_palette and os.path.exists(f"{fname}.ind.png"):
			print(f"{fname}.ind.png already exists")
			exist = True
		if exist:
			return False

	VDP_MODE         = 0xC058000
	VDP_PALETTE      = 0xC051000
	VDP_CAPTURE_CTRL = 0xC05B00A
	VDP_TRIGGER      = 0xC058006
	VDP_CAPTURE_DATA = 0xC052000

	vdp_mode_val = protocol.read_value(VDP_MODE, DataType.WORD)
	if vdp_mode_val == None:
		print("Failed to get video mode")
		return False
	video_standard = (["NTSC", "PAL"])[vdp_mode_val & 1]
	video_height = ([224, 240])[(vdp_mode_val >> 1) & 1]
	print(f"Video mode: {video_standard} 256x{video_height}")

	color_data_type = DataType.WORD
	pixel_data_type = DataType.BYTE if has_palette else color_data_type

	try:
		palette = []
		img_ind = None
		pix_ind = None
		if has_palette:
			with open(f"{fname}.pal", "wb") as f_pal:
				print("Reading palette")
				pal_dat = protocol.read_bytes(VDP_PALETTE, 256, color_data_type)
				if pal_dat == None:
					return False
				f_pal.write(pal_dat)
				palette = struct.unpack(color_data_type.struct_fmt(256), pal_dat)
			if SCREENCAP_SHOW_INDICES:
				img_ind = Image.new('RGB', (256, video_height), color = (0,0,0))
				pix_ind = img_ind.load()

		img = Image.new('RGBA', (256, video_height), color = (0,0,0,0))
		pix = img.load()
		with open(f"{fname}.bin", "wb") as f_bin:
			for y in range(video_height):
				protocol.write_value(VDP_CAPTURE_CTRL, (capture_mode<<8)+y, DataType.WORD)
				protocol.write_value(VDP_TRIGGER, 0x0001, DataType.WORD)
				time.sleep(0.02)
				if (y%16) == 0:
					print(f"Capturing lines {y}-{y+15}...")
				dat = protocol.read_bytes(VDP_CAPTURE_DATA, 256, pixel_data_type)
				if dat == None:
					break
				f_bin.write(dat)
				colors = struct.unpack(pixel_data_type.struct_fmt(256), dat)
				for x in range(256):
					c = colors[x]
					if pix_ind != None:
						pix_ind[x,y] = (c,c,c)
						alpha = 1 if c>0 else 0
						pix[x,y] = util.rgb555_to_img_color(palette[c], alpha)
					else:
						pix[x,y] = util.rgb555_to_img_color(c, 255)

		img.save(f"{fname}.png")
		if img_ind != None:
			img_ind.save(f"{fname}.ind.png")

	except KeyboardInterrupt:
		print("Cancelled")
		return True

	return True

def run_cmd_movemotor(cmd, suffix, args, protocol):
	if args == None or len(args) != 1:
		print(f"Syntax: {cmd} <steps>")
		print("Steps is a positive number to move forwards or negative to move backwards.")
		print_number_help()
		return False

	steps = util.try_parse_num(args[0], DataType.WORD.nbits)
	if steps == None or steps == 0 or abs(steps) > 32767:
		print(f"Invalid steps: {args[0]}")
		return False

	direction = 1
	if steps < 0:
		direction = -1
		steps = abs(steps)

	expected_runtime = steps/500
	print("WARNING: if command hangs, shut off console!")
	print(f"Expected to take {expected_runtime:.02f} seconds")

	VDP_PRINTER_STATUS = 0xC05D030
	VDP_PRINTER_MOTOR  = 0xC05D042
	INTC_IPRD          = 0x5FFFF8A
	func_bios_movePrinter = 0x1B76

	# Enable motor movement
	protocol.write_value(INTC_IPRD,          0x0F,   DataType.BYTE) # unmask ITU3 (and mask ITU2)
	protocol.write_value(VDP_PRINTER_STATUS, 0x0100, DataType.WORD) # enable printer writes

	# Call _bios_movePrinter(steps, direction)
	time_start = time.time()
	alerted = False
	try:
		ret = protocol.call_function(func_bios_movePrinter, [steps, direction], None, timeout=expected_runtime+0.5)
		if ret == None:
			print("Timed out! SHUT OFF CONSOLE IMMEDIATELY!")
			alerted = True
			# continue to try stop it anyway
	except KeyboardInterrupt:
		print("Still waiting!")
		time_wait =  expected_runtime + 0.5 - (time.time() - time_start)
		if time_wait > 0:
			time.sleep(time_wait)

	# Stop interrupt and turn off motor safely
	protocol.write_value(INTC_IPRD,          0x00,   DataType.BYTE) # mask ITU3 (and ITU2)
	protocol.write_value(VDP_PRINTER_STATUS, 0x0100, DataType.WORD) # enable printer writes (to ensure we can turn off)
	protocol.write_value(VDP_PRINTER_MOTOR,  0x5A50, DataType.WORD) # turn off motor
	protocol.write_value(VDP_PRINTER_STATUS, 0x0000, DataType.WORD) # disable printer writes

	# Ensure everything is safe
	vdp_printer_motor_val = protocol.read_value(VDP_PRINTER_MOTOR, DataType.WORD)
	if vdp_printer_motor_val == None or (vdp_printer_motor_val & 0x000F) != 0:
		if not alerted:
			print("Motor not stopped! SHUT OFF CONSOLE IMMEDIATELY!")
			alerted = True
		return False
	else:
		print("Motor safely stopped")

	return True
