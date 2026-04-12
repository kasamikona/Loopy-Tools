#!/usr/bin/env python3

# Requires: pyserial, pillow, mido[ports-rtmidi]
# Optional: gnureadline

import sys, struct, shlex, os, time, io
import serial, serial.tools.list_ports

from PIL import Image
import mido

MAX_READ_SIZE = 1024
MAX_WRITE_SIZE = 256
NO_OVERWRITE = True
INITIAL_BAUD = 38400
MIDI_DEBUG = True

CMD_READ8   = 0x01
CMD_READ16  = 0x02
CMD_READ32  = 0x03
CMD_WRITE8  = 0x04
CMD_WRITE16 = 0x05
CMD_WRITE32 = 0x06
CMD_CALL    = 0x07
CMD_MIDI    = 0x08
CMD_BAUD    = 0xFF

LABELS = { # (address, length); bytes
	# CPU/system memory
	"BIOS":                  (0x00000000, 0x8000 ),
	"SRAM":                  (0x02000000, None   ),
	"OCPM":                  (0x05FFFE00, 0x200  ),
	"RAM":                   (0x09000000, 0x80000),
	"ROM":                   (0x0E000000, None   ),
	"OCRAM":                 (0x0F000000, 0x400  ),
	# VDP Memory
	"VDP.BITMAP_VRAM":       (0x0C000000, 0x20000),
	"VDP.TILE_VRAM":         (0x0C040000, 0x10000),
	"VDP.OAM":               (0x0C050000, 0x200  ),
	"VDP.PALETTE":           (0x0C051000, 0x200  ),
	"VDP.CAPTURE_DATA":      (0x0C052000, 0x200  ),
	# VDP General
	"VDPREGS":               (0x0C058000, 0x4000 ),
	"VDP.MODE":              (0x0C058000, None   ),
	"VDP.HCOUNT":            (0x0C058002, None   ),
	"VDP.VCOUNT":            (0x0C058004, None   ),
	"VDP.TRIGGER":           (0x0C058006, None   ),
	"VDP.SYNC_IRQ_CTRL":     (0x0C058008, None   ),
	# Bitmaps
	"VDP.BM_SCROLLX":        (0x0C059000, 8      ),
	"VDP.BM_SCROLLY":        (0x0C059008, 8      ),
	"VDP.BM_POSX":           (0x0C059010, 8      ),
	"VDP.BM_POSY":           (0x0C059018, 8      ),
	"VDP.BM_WIDTH":          (0x0C059020, 8      ),
	"VDP.BM_HEIGHT":         (0x0C059028, 8      ),
	"VDP.BM_CTRL":           (0x0C059030, None   ),
	"VDP.BM_SUBPAL":         (0x0C059040, None   ),
	"VDP.BM_COL_LATCH":      (0x0C059050, 8      ),
	# Backgrounds & Objects
	"VDP.BG_CTRL":           (0x0C05A000, None   ),
	"VDP.BG_SCROLL":         (0x0C05A002, 8      ),
	"VDP.BG_SUBPAL":         (0x0C05A00A, 4      ),
	"VDP.OBJ_CTRL":          (0x0C05A010, None   ),
	"VDP.OBJ_SUBPAL":        (0x0C05A012, 4   ),
	"VDP.CHAR_SPLIT":        (0x0C05A020, None   ),
	# Display
	"VDP.BLEND_MODE":        (0x0C05B000, None   ),
	"VDP.LAYER_CTRL":        (0x0C05B002, None   ),
	"VDP.SCREEN_CTRL":       (0x0C05B004, None   ),
	"VDP.BACKDROP_B":        (0x0C05B006, None   ),
	"VDP.BACKDROP_A":        (0x0C05B008, None   ),
	"VDP.CAPTURE_CTRL":      (0x0C05B00A, None   ),
	# Interrupts
	"VDP.IRQ0_NMI_CTRL":     (0x0C05C000, None   ),
	"VDP.IRQ0_HCMP":         (0x0C05C002, None   ),
	"VDP.IRQ0_VCMP":         (0x0C05C004, None   ),
	# Controller & Printer
	"VDP.PRINTER_TEMP":      (0x0C05D000, None   ),
	"VDP.CONTROL_IN":        (0x0C05D010, 6      ),
	"VDP.UNK5D020":          (0x0C05D020, None   ),
	"VDP.PRINTER_STATUS":    (0x0C05D030, None   ),
	"VDP.PRINTER_HEAD_DATA": (0x0C05D040, None   ),
	"VDP.PRINTER_MOTOR":     (0x0C05D042, None   ),
	"VDP.PRINTER_HEAD_CTRL": (0x0C05D044, None   ),
	"VDP.CONTROL_MOUSE":     (0x0C05D050, 4      ),
	"VDP.CONTROL_OUT":       (0x0C05D054, None   ),
	# Bitmap VRAM Control
	"VDP.BM_MEM_CTRL":       (0x0C05E000, None   ),
	"VDP.BM_FILL_MASK":      (0x0C05E002, None   ),
	"VDP.BM_FILL_VALUE":     (0x0C05E004, None   ),
	"VDP.BM_FILL_TRIGGER":   (0x0C05F000, 0x400  ),
	# Advanced Display
	"VDP.SYNC_CALIBRATION":  (0x0C060000, None   ),
	# Sound & Expansion
	"VDP.SOUND_CTRL":        (0x0C080000, None   ),
	"VDP.SOUND_EXP_DATA":    (0x0C0A0000, None   ),
}

FUNC_LABELS = {
	# Known BIOS functions
	"bios_vdpMode":               (0x0668, 2, 0, False),
	"bios_printParts":            (0x06D4, 8, 1, True ),
	"bios_printDirect":           (0x0FD6, 7, 1, True ),
	"bios_print15bpp":            (0x101C, 2, 1, True ),
	"bios_print8bpp":             (0x1064, 3, 1, True ),
	"bios_getSealType":           (0x115C, 0, 1, False),
	"bios_measurePrintTemp":      (0x13B0, 0, 1, False),
	"bios_colorInverseGray":      (0x2D68, 1, 1, False),
	"bios_valueBlendQuarter":     (0x2DC6, 2, 1, False),
	"bios_colorBlendQuarter":     (0x2DE0, 2, 1, False),
	"bios_mulS16":                (0x2E68, 2, 1, False),
	"bios_mulU16":                (0x2E72, 2, 1, False),
	"bios_divU16":                (0x2E7C, 2, 1, False),
	"bios_divS16":                (0x2EA6, 2, 1, False),
	"bios_divS32":                (0x2EDE, 2, 1, False),
	"bios_drawLine":              (0x37A0, 6, 0, False),
	"bios_initSoundTransmission": (0x613C, 0, 0, False),
	"bios_playBgm":               (0x61A0, 4, 0, False),
	"bios_playSfx":               (0x61B8, 4, 0, False),
	"bios_updateBgm":             (0x6238, 2, 0, False),
	"bios_dma":                   (0x66D0, 2, 0, False),
	"bios_vsyncIfDma":            (0x6A0E, 1, 0, False),
	"bios_vsyncDma":              (0x6A48, 1, 0, False),
	"bios_vsync":                 (0x6A5A, 0, 0, False),
	"bios_soundChannels":         (0x6AC0, 1, 0, False),
	"bios_soundVolume":           (0x6B50, 2, 0, False),
	"bios_soundToggleDemo":       (0x6B86, 0, 0, False),
	# Internal BIOS functions
	"_bios_disablePrinterTimer":  (0x15F2, 0, 0, False),
	"_bios_movePrinter":          (0x1B76, 2, 1, True ),
	"_bios_resetPrinter":         (0x1C2C, 0, 0, True ),
	# Misc
	"cart_init": (0x0E000480, 0, 0, False),
}

MIDI_DEBUG = True
MIDI_COMPRESS = True
midi_last_status = None

def parseaddr(x, t):
	x = x.upper()
	offset = None
	if "+" in x:
		x, y = x.split("+", 1)
		offset = parsenum(y, 4)
		if offset == None:
			return (None, None)
	elif "[" in x and x.endswith("]"):
		x, y = x.split("[", 1)
		offset = parsenum(y[:-1], 4)
		if offset == None:
			return (None, None)
		offset *= t
	if x in LABELS:
		l = LABELS[x]
		if offset == None:
			if l[1] == None:
				return (l[0], t)
			return l
		else:
			return (l[0]+offset, t)
	xn = parsenum(x, 4)
	if xn == None or xn < 0 or xn > 0xFFFFFFFF:
		return (None, None)
	if offset != None:
		return ((xn+offset)&(-t), t)
	return (xn&(-t), t)

def parsefunc(x):
	for fl in FUNC_LABELS.keys():
		if x.upper() == fl.upper():
			return FUNC_LABELS[fl]
	return None

def listfuncs():
	for fl in FUNC_LABELS.keys():
		addr, nargs, retsize, long_running = FUNC_LABELS[fl]
		nargs = nargs or "no"
		addr_desc = f"{fl}: 0x{addr:08X}, {nargs} arguments"
		if retsize > 0:
			addr_desc += f", {retsize*8}bit return"
		if long_running:
			addr_desc += ", long-running"
		print(addr_desc) 

def parseaddrlen(x, y, t):
	if y == "*":
		return parseaddr(x, t)
	return (parseaddr(x, t)[0], parsenum(y, 4))

def parsenum(x, t):
	x = x.lower()
	try:
		if x.startswith("0x"):
			a = int(x[2:], 16)
		elif x.endswith("h"):
			a = int(x[:-1], 16)
		else:
			a = int(x, 10)
		if a < -pow(2, t*8-1) or a >= pow(2, t*8):
			return None
		return a
	except ValueError:
		return None

def do_read_bytes(ser, addr, count, tsize, info=True):
	c = CMD_READ8
	if tsize == 2:
		c = CMD_READ16
	elif tsize == 4:
		c = CMD_READ32
	else:
		tsize = 1
	addr &= (-tsize) & 0xFFFFFFFF
	if info:
		print("Reading {0} {1}-byte values from 0x{2:08X}".format(count, tsize, addr))
	split_count = MAX_READ_SIZE // tsize
	dat = b""
	for offset in range(0, count, split_count):
		part_count = min(count - offset, split_count)
		ser.write(struct.pack(">BIH", c, addr+(offset*tsize), part_count-1))
		part_dat = ser.read(part_count*tsize)
		if len(part_dat) < part_count*tsize:
			#print("Timed out")
			return None
		dat = dat + part_dat
	return dat

def do_write_bytes(ser, addr, data, tsize, info=True):
	c = CMD_WRITE8
	if tsize == 2:
		c = CMD_WRITE16
	elif tsize == 4:
		c = CMD_WRITE32
	else:
		tsize = 1
	addr &= (-tsize) & 0xFFFFFFFF
	count = len(data) // tsize
	data = data[:count*tsize]
	if info:
		print("Writing {0}x {1}-byte values to 0x{2:08X}".format(count, tsize, addr))
	split_count = MAX_WRITE_SIZE // tsize
	for offset in range(0, count, split_count):
		part_count = min(count - offset, split_count)
		part_data = data[(offset*tsize):((offset+part_count)*tsize)]
		ser.write(struct.pack(">BIH", c, addr+(offset*tsize), part_count-1))
		ser.write(part_data)

valstruct = {1:">B",2:">H",4:">I"}
valmask = {1:0xFF,2:0xFFFF,4:0xFFFFFFFF}

def do_read_value(ser, addr, tsize):
	if tsize != 2 and tsize != 4:
		tsize = 1
	b = do_read_bytes(ser, addr, 1, tsize, info=False)
	if b == None:
		return None
	return struct.unpack(valstruct[tsize], b)[0]

def do_write_value(ser, addr, value, tsize):
	if tsize != 2 and tsize != 4:
		tsize = 1
	b = struct.pack(valstruct[tsize], value&valmask[tsize])
	do_write_bytes(ser, addr, b, tsize, info=False)

def do_read_stream(ser, addr, count, tsize, stream):
	if tsize != 2 and tsize != 4:
		tsize = 1
	max_count = MAX_READ_SIZE // tsize
	i = 0
	while i < count:
		c_count = min(max_count, count - i)
		c_dat = do_read_bytes(ser, addr&0xFFFFFFFF, c_count, tsize, info=False)
		if c_dat == None:
			return False
		i += c_count
		addr += c_count * tsize
		stream.write(c_dat)
	return True

def do_write_stream(ser, addr, count, tsize, stream):
	if tsize != 2 and tsize != 4:
		tsize = 1
	max_count = MAX_WRITE_SIZE // tsize
	i = 0
	while i < count:
		c_count = min(max_count, count - i)
		c_dat = stream.read(c_count * tsize)
		if len(c_dat) < c_count * tsize:
			return False
		#if type(c_dat) != bytes:
		#	c_dat = bytes(c_dat, "ascii")
		do_write_bytes(ser, addr&0xFFFFFFFF, c_dat, tsize, info=False)
		i += c_count
		addr += c_count * tsize
	return True

def file_write_align(f, n):
	pos = f.tell()
	posmod = pos % n
	if posmod != 0:
		f.write(bytes([255]*(n-posmod)))

def file_read_align(f, n):
	pos = f.tell()
	posmod = pos % n
	if posmod != 0:
		f.read(n-posmod)

def main(ser, args):
	if len(args) > 0:
		cmd = args.pop(0).lower()
		while ser.in_waiting > 0:
			ser.reset_input_buffer()
		if cmd == "labels":
			for k in LABELS:
				print(f"0x{LABELS[k]:08X}: {k}")
		elif cmd in ["read8","read16","read32"]:
			if len(args) != 1:
				print(f"Syntax: {cmd} <address|label[+offset]>")
				return
			t = int(cmd[len("read"):]) // 8 # 1, 2, 4
			address = parseaddr(args[0], t)[0]
			if address == None:
				print(f"Invalid address or label: {args[0]}")
				return
			if address&(-t) != address:
				print(f"Invalid alignment for {t*8}bit access: 0x{address:08X}")
				return
			value = do_read_value(ser, address, t)
			if value == None:
				print("Timed out")
				return
			print(("0x{0:0{1}X}").format(value, t*2))
		elif cmd in ["write8","write16","write32"]:
			if len(args) != 2:
				print(f"Syntax: {cmd} <address|label[+offset]> <data>")
				return
			t = int(cmd[len("write"):]) // 8 # 1, 2, 4
			address = parseaddr(args[0], t)[0]
			if address == None:
				print(f"Invalid address or label: {args[0]}")
				return
			if address&(-t) != address:
				print(f"Invalid alignment for {t*8}bit access: 0x{address:08X}")
				return
			value = parsenum(args[1], t)
			if value == None:
				print(f"Invalid data for {t*8}bit write: {args[1]}")
			else:
				do_write_value(ser, address, value, t)
		elif cmd in ["dump8","dump16","dump32"]:
			if len(args) != 3:
				print(f"Syntax: {cmd} <address|label[+offset]> <length> <output.bin>")
				print("Length in bytes. Prefix filename with ! to force overwrite.")
				return
			t = int(cmd[len("dump"):]) // 8 # 1, 2, 4
			address, length = parseaddrlen(args[0], args[1], t)
			if address == None:
				print(f"Invalid address or label: {args[0]}")
				return
			if address&(-t) != address:
				print(f"Invalid alignment for {t*8}bit access: 0x{address:08X}")
				return
			if length == None:
				print("Invalid length: "+args[1])
				return
			fname = args[2]
			if fname.startswith("!"):
				fname = fname[1:]
			elif NO_OVERWRITE and os.path.exists(fname):
				print("File already exists")
				return
			count = length // t
			with open(fname, "wb") as f:
				if not do_read_stream(ser, address, count, t, f):
					return
		elif cmd in ["burst8","burst16","burst32"]:
			if len(args) != 2:
				print(f"Syntax: {cmd} <address|label[+offset]> <input.bin>")
				return
			t = int(cmd[len("burst"):]) // 8 # 1, 2, 4
			address = parseaddr(args[0], t)[0]
			if address == None:
				print(f"Invalid address or label: {args[0]}")
				return
			if address&(-t) != address:
				print(f"Invalid alignment for {t*8}bit access: 0x{address:08X}")
				return
			fname = args[1]
			if os.path.isdir(fname) or not os.path.exists(fname):
				print(f"File does not exist: {fname}")
				return
			length = os.path.getsize(fname)
			count = length // t
			with open(fname, "rb") as f:
				if not do_write_stream(ser, address, count, t, f):
					print("File error")
					return
		elif cmd == "baud":
			if len(args) != 1:
				print(f"Syntax: {cmd} <new rate>")
				return
			try:
				baud = parsenum(args[0], 4)
			except ValueError:
				print("Invalid baud rate")
				return
			if baud < 300 or baud > 500000:
				print("Invalid baud rate")
				return
			ser.write(struct.pack(">BI", CMD_BAUD, baud))
			ser.flush()
			time.sleep(0.2)
			ser.baudrate = baud
			return
		elif cmd == "resync":
			if len(args) != 0:
				print(f"Syntax: {cmd}")
				return
			zeros = bytes([0]*MAX_WRITE_SIZE)
			ser.write(zeros)
			ser.write(zeros)
			return
		elif cmd == "screencap":
			if len(args) != 2:
				print(f"Syntax: {cmd} <mode> <output name>")
				print("File name should not include extension. Saves PNG+BIN(+PAL) automatically.")
				print("Modes:")
				print("0: 15bpp raw blend")
				print("1: 15bpp raw screen A")
				print("2: 8bpp paletted screen A")
				print("3: same as 2?")
				return
			mode = args[0]
			try:
				mode = int(args[0])
			except ValueError:
				print("Invalid mode")
				return
			if mode not in range(4):
				print("Invalid mode")
				return
			has_palette = mode >= 2
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
					return
			vdp_mode = do_read_value(ser, 0x0C058000, 2)
			if vdp_mode == None:
				print("Failed to get video mode")
				return
			video_standard = (["NTSC", "PAL"])[vdp_mode & 1]
			video_height = ([224, 240])[(vdp_mode >> 1) & 1]
			print(f"Video mode: {video_standard} 256x{video_height}")
			pal = []
			if has_palette:
				with open(f"{fname}.pal", "wb") as f_pal:
					print("Reading palette")
					pal_dat = do_read_bytes(ser, 0x0C051000, 256, 2, False)
					if pal_dat == None:
						return
					f_pal.write(pal_dat)
					pal = struct.unpack(">256H", pal_dat)
				img_ind = Image.new('RGB', (256,video_height), color = (0,0,0))
				pix_ind = img_ind.load()
			img = Image.new('RGBA', (256,video_height), color = (0,0,0,0))
			pix = img.load()
			with open(f"{fname}.bin", "wb") as f_bin:
				for y in range(video_height):
					do_write_value(ser, 0x0C05B00A, (mode<<8)+y, 2)
					do_write_value(ser, 0x0C058006, 1, 2)
					time.sleep(0.02)
					if (y%16) == 0:
						print(f"Capturing lines {y}-{y+15}...")
					dat = do_read_bytes(ser, 0x0C052000, 256, (1 if has_palette else 2), False)
					if dat == None:
						break
					f_bin.write(dat)
					colors = struct.unpack((">256B" if has_palette else ">256H"), dat)
					for x in range(256):
						c = colors[x]
						a = 1
						if has_palette:
							pix_ind[x,y] = (c,c,c)
							a = 1 if c>0 else 0
							c = pal[c]
						r = (c>>10)&31
						g = (c>>5)&31
						b = c&31
						pix[x,y] = ((r*255)//31,(g*255)//31,(b*255)//31,a*255)
			img.save(f"{fname}.png")
			if has_palette:
				img_ind.save(f"{fname}.ind.png")
		elif cmd == "call":
			if len(args) < 1 or len(args) > 9:
				print(f"Syntax: {cmd} <func> [args]")
				print(f"List functions: {cmd} functions")
				print("Currently supports up to 8 args")
				return
			if args[0].lower() in ["funcs", "functions"]:
				listfuncs()
				return
			whatfunc = parsefunc(args[0])
			if whatfunc == None:
				print(f"Invalid label: {args[0]}")
				return
			address, argcount, retsize, long_running = whatfunc
			if argcount != len(args) - 1:
				print(f"Function {args[0]} takes {argcount} arguments")
				return
			callargs = []
			for a in args[1:]:
				ca = parseaddr(a, 1)[0]
				if ca == None:
					ca = parsenum(a, 4)
				if ca == None:
					print("Invalid argument value: "+a)
					return
				callargs.append(ca)
			ser.write(struct.pack(">BIB", CMD_CALL, address, len(callargs)))
			for ca in callargs:
				ser.write(struct.pack(">I", ca&0xFFFFFFFF))
			timeout_was = ser.timeout
			if long_running:
				print("Long-running function, timeout disabled!")
				ret = b""
				# Infinite loop with short timeout so Ctrl-C can be caught
				ser.timeout = 1
				try:
					while True:
						ret += ser.read(4)
						if len(ret) >= 4:
							break
				except KeyboardInterrupt:
					print("Cancelled call, maybe crashed")
					return
				ser.timeout = timeout_was
			else:
				ret = ser.read(4)
				if len(ret) < 4:
					print("Timed out, maybe crashed")
					return
			ret = struct.unpack(">I", ret)[0]
			if retsize != 0:
				print("0x{0:0{1}X}".format(ret, retsize*2))
		elif cmd == "savestate":
			if len(args) != 2:
				print(f"Syntax: {cmd} <template.txt> <output.state>")
				print("Each line of template specifies (address, bit width, length) separated by whitespace, with optional name following" +
					" which will be printed during saving. Addresses and lengths work as in dump commands.")
				return
			outname = args[1]
			if outname.startswith("!"):
				outname = outname[1:]
			elif NO_OVERWRITE:
				if os.path.exists(outname):
					print(f"{outname} already exists")
					return
			actions = []
			with open(args[0], "r") as f_template:
				for line in f_template.readlines():
					line = line.strip()
					if line.startswith("#") or len(line) == 0:
						continue
					parts = shlex.split(line)
					if len(parts) < 3:
						print(f"Incomplete line: {line}")
						return
					width = parts[1]
					if not width in ["8","16","32"]:
						print(f"Bad width in line: {line}")
						return
					t = int(width)//8
					addr, length = parseaddrlen(parts[0], parts[2], t)
					if addr == None:
						print(f"Bad address in line: {line}")
						return
					if length == None or length%t != 0:
						print(f"Bad length in line: {line}")
						return
					name = None
					if len(parts) >= 4:
						name = parts[3]
					actions.append( (addr, length, t, name) )
			with open(outname, "wb") as f_state:
				f_state.write(b"LPSTATE\0")
				file_write_align(f_state, 4)
				for action in actions:
					addr, length, t, name = action
					if name:
						print(f"Reading 0x{action[0]:08X} ({name})")
					else:
						print(f"Reading 0x{action[0]:08X}")
					f_state.write(struct.pack(">III", addr, length, t))
					file_write_align(f_state, 4)
					if not do_read_stream(ser, addr, length//t, t, f_state):
						return
					file_write_align(f_state, 4)
			print("State saved")
		elif cmd == "loadstate":
			if len(args) != 1:
				print(f"Syntax: {cmd} <input.state>")
				print("Loads a state file as created by savestate command.")
				return
			inname = args[0]
			if os.path.isdir(inname) or not os.path.exists(inname):
				print("File does not exist: "+inname)
				return
			with open(inname, "rb") as f_state:
				if f_state.read(8) != b"LPSTATE\0":
					print("Invalid state file")
					return
				file_read_align(f_state, 4)
				while True:
					chunkhead = f_state.read(12)
					if len(chunkhead) < 12:
						break
					file_read_align(f_state, 4)
					addr, length, t = struct.unpack(">III", chunkhead)
					print(f"Writing 0x{addr:08X}")
					if not do_write_stream(ser, addr, length//t, t, f_state):
						return
					file_read_align(f_state, 4)
			print("State loaded")
		elif cmd == "midiport":
			if len(args) != 1:
				print(f"Syntax: {cmd} <port>")
				print_midi_ports(out=False)
				return
			portname = parse_midi_port(args[0], out=False)
			if portname == None:
				print("Invalid port")
				print_midi_ports(out=False)
				return
			global midi_callback_data, midi_last_status
			midi_callback_data = {"ser":ser}
			midi_last_status = None
			port = mido.open_input(portname, callback=midi_callback)
			print(f"Passing through MIDI port \"{portname}\" (Ctrl-C to end)...")
			ser.write(struct.pack(">B", CMD_MIDI))
			try:
				while True:
					time.sleep(0.001)
			except KeyboardInterrupt as e:
				pass
			finally:
				port.close()
				time.sleep(0.1)
				ser.write(b"\xFF")
		elif cmd in ["hist8","hist16","hist32"]:
			if len(args) != 3:
				print(f"Syntax: {cmd} <address|label[+offset]> <count> <logfile>")
				return
			t = int(cmd[len("hist"):]) // 8 # 1, 2, 4
			address = parseaddr(args[0], t)[0]
			if address == None:
				print(f"Invalid address or label: {args[0]}")
				return
			if address&(-t) != address:
				print(f"Invalid alignment for {t*8}bit access: 0x{address:08X}")
				return
			histcount = parsenum(args[1], 4)
			if histcount == None or histcount < 1:
				print(f"Invalid count: {args[1]}")
				return
			outname = args[2]
			if outname.startswith("!"):
				outname = outname[1:]
			elif NO_OVERWRITE:
				if os.path.exists(outname):
					print(f"{outname} already exists")
					return
			hist = dict()
			donecount = 0
			percent_done = 0
			percent_modulo = 1
			if histcount < 100000:
				percent_modulo = 10
			for i in range(histcount):
				value = do_read_value(ser, address, t)
				if value == None:
					print("Timed out")
					break
				donecount += 1
				if value in hist:
					hist[value] = hist[value] + 1
				else:
					hist[value] = 1
				percent_now = (i * 100) // histcount
				if percent_now > percent_done and (percent_now % percent_modulo) == 0:
					print(f"Reading {percent_now}%...")
				percent_done = percent_now
			print(f"Got {donecount} data points")
			histkeys = sorted(hist.keys())
			with open(outname, "w") as f_hist:
				for value in histkeys:
					frequency = hist[value]
					f_hist.write(("0x{0:0{1}X}: {2}\n").format(value, t*2, frequency))
			print(f"Histogram logged to {outname}")
		elif cmd == "movemotor":
			if len(args) != 1:
				print(f"Syntax: {cmd} <steps>")
				print("Steps can be positive or negative")
				return
			steps = parsenum(args[0], 4)
			if steps == None or steps == 0 or abs(steps) > 32767:
				print(f"Invalid steps: {args[0]}")
				return
			direction = 1
			if steps < 0:
				direction = -1
				steps = abs(steps)
			expected_runtime = steps/500
			print("WARNING: if command hangs, shut off console!")
			print(f"Expected to take {expected_runtime:.02f} seconds")
			# Enable motor movement
			do_write_value(ser, 0x05FFFF8A, 0x0F, 1) # IPRD: unmask ITU3 (and mask ITU2)
			do_write_value(ser, 0x0C05D030, 0x0100, 2) # IO_SENSOR: enable printer writes
			# Call _bios_movePrinter(steps, direction)
			ser.write(struct.pack(">BIB", CMD_CALL, 0x1B76, 2))
			ser.write(struct.pack(">Ii", steps, direction))
			# Wait for finish
			timeout_was = ser.timeout
			ret = b""
			ser.timeout = expected_runtime + 1
			ret = ser.read(4)
			ser.timeout = timeout_was
			alerted = False
			if len(ret) < 4:
				print("Timed out! SHUT OFF CONSOLE IMMEDIATELY!")
				alerted = True
				# continue to try stop it anyway
			# Stop interrupt and turn off motor safely
			do_write_value(ser, 0x05FFFF8A, 0x00, 1) # IPRD: mask ITU3 (and ITU2)
			do_write_value(ser, 0x0C05D030, 0x0100, 2) # IO_SENSOR: enable printer writes (to ensure we can turn off)
			do_write_value(ser, 0x0C05D042, 0x5A50, 2) # IO_MOTOR: turn off motor
			do_write_value(ser, 0x0C05D030, 0x0000, 2) # IO_SENSOR: disable printer writes
			# Ensure everything is safe
			motor_reg = do_read_value(ser, 0x0C05D042, 2)
			if motor_reg == None or (motor_reg&0x000F) != 0:
				if not alerted:
					print("Motor not stopped! SHUT OFF CONSOLE IMMEDIATELY!")
					alerted = True
				return
			else:
				print("Motor safely stopped.")
		elif cmd == "help":
			clist = \
			"read8,read16,read32: Read a n-bit value\n"+\
			"write8,write16,write32: Write a n-bit value\n"+\
			"dump8,dump16,dump32: Save a region to a file with n-bit accesses\n"+\
			"burst8,burst16,burst32: Load a region from a file with n-bit accesses\n"+\
			"hist8,hist16,hist32: Read a n-bit value repeatedly and make a histogram of values\n"+\
			"call: Directly call a function with given parameters (UNSAFE)\n"+\
			"savestate: Save multiple regions to a file using a template\n"+\
			"loadstate: Load multiple regions from a file\n"+\
			"screencap: Create a screen capture (slow)\n"+\
			"midiport: Connect a local MIDI input port to console\n"+\
			"movemotor: Directly control the printer motor (UNSAFE)\n"+\
			"baud: Change the communication baud rate if the adapter supports it\n"+\
			"resync: Attempt to resynchronize if a communication error causes problems\n"+\
			"exit: Exit the monitor (same as Ctrl-C)\n"
			print("Commands:")
			print(clist)
		elif cmd == "exit":
			exit()
		else:
			print("Unknown command. Use command \"help\" for a list of commands.")
			return

def midi_callback(msg):
	global midi_callback_data, midi_last_status
	try:
		if midi_callback_data != None:
			ser = midi_callback_data["ser"]
			msg_bytes = msg.bin()
			if MIDI_COMPRESS:
				if msg_bytes[0] & 0xF0 == 0x80:
					msg_bytes[0] |= 0x10
					msg_bytes[2] = 0
				new_status = msg_bytes[0]
				if new_status == midi_last_status:
					msg_bytes = msg_bytes[1:]
					#if MIDI_DEBUG:
					#	print("({0:02X}) ".format(new_status), end="")
				if new_status < 0xF8:
					midi_last_status = new_status if new_status < 0xF0 else None
			while len(msg_bytes) > 0:
				chunk = msg_bytes[:254]
				msg_bytes = msg_bytes[len(chunk):]
				ser.write(bytes([len(chunk)-1]))
				ser.write(chunk)
				if MIDI_DEBUG:
					print(" ".join(["{0:02X}".format(b) for b in chunk]))
				ser.flush()
	except Exception as e:
		print(e)

def parse_midi_port(val, out=False):
	val = str(val)
	ports = mido.get_input_names()
	if out:
		ports = mido.get_output_names()
	try:
		portnum = int(val)
		if portnum < 0 or portnum >= len(ports):
			return None
		return ports[portnum]
	except ValueError:
		for num in range(len(ports)):
			if ports[num].strip().upper().startswith(val.strip().upper()):
				return ports[num]
	return None

def print_midi_ports(out=False):
	print("Available MIDI ports:")
	ports = mido.get_input_names()
	if out:
		ports = mido.get_output_names()
	for num, name in enumerate(ports):
		print(f"{num}: {name}")

def list_serial_ports():
	return ", ".join([d.device for d in serial.tools.list_ports.comports()])

def open_serial_port(name):
	ser = None
	try:
		ser = serial.Serial(name,timeout=1,baudrate=INITIAL_BAUD)
	except serial.SerialException:
		print(f"Failed to open port {name}, check connection.")
		print("Available serial ports:", list_serial_ports())
		return None
	return ser

if __name__ == "__main__":
	if len(sys.argv) > 2:
		ser = open_serial_port(sys.argv[1])
		if ser != None:
			main(ser, sys.argv[2:])
	elif len(sys.argv) > 1:
		ser = open_serial_port(sys.argv[1])
		if ser != None:
			print("Interactive mode. Use command \"help\" for a list of commands.")
			print()
			if sys.platform.startswith("darwin"):
				try:
					import gnureadline
				except ImportError:
					print("Warning: Package gnureadline missing, interactive functionality may be limited")
					print()
			try:
				while True:
					inp = input("> ")
					main(ser, shlex.split(inp))
					print()
			except (KeyboardInterrupt, EOFError):
				print() # this fixes some dumb error
	else:
		print(f"Direct mode: {sys.argv[0]} <port> <command> [command args...]")
		print(f"Interactive: {sys.argv[0]} <port>")
		print("Use command \"help\" for a list of commands.")
		print()
		print("Available serial ports:", list_serial_ports())
