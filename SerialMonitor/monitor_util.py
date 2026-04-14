def parse_num(x, nbits):
	x = x.lower()
	if x.startswith("0x"):
		a = int(x[2:], 16)
	elif x.endswith("h"):
		a = int(x[:-1], 16)
	else:
		a = int(x, 10)
	signed_min = -(1 << (nbits - 1))
	unsigned_max = (1 << nbits) - 1
	if a < signed_min or a > unsigned_max:
		raise ValueError
	return a

def try_parse_num(x, nbits):
	try:
		return parse_num(x, nbits)
	except ValueError:
		return None

def file_write_align(f, nbytes):
	pos = f.tell()
	posmod = pos % nbytes
	if posmod != 0:
		f.write(bytes([255]*(nbytes-posmod)))

def file_read_align(f, nbytes):
	pos = f.tell()
	posmod = pos % nbytes
	if posmod != 0:
		f.read(nbytes-posmod)

def rgb555_to_img_color(c, alpha=None):
	r = (c>>10)&31
	g = (c>>5)&31
	b = c&31
	if alpha != None:
		return ((r*255)//31, (g*255)//31, (b*255)//31, alpha)
	return ((r*255)//31, (g*255)//31, (b*255)//31)

def print_addr_help():
	print("The address can be a number or a label.")
	print("Use command \"labels\" to see a list of labels.")
	print("Can be offset by +num or -num bytes, or [num] indices.")
	print("Addresses must be a valid location in memory and properly aligned.")

def print_data_help():
	print("Data is a signed or unsigned number in range of the data type.")

def print_num_help(signed=True):
	print("Numbers are decimal (NNN) or hex (0xNNN / NNNh)." + (" Use -num for negative." if signed else ""))
