import os, time

from monitor_protocol import DataType
import monitor_util as util
import monitor_addresses as addresses

RESET_DELAY = 1.3

PTR_TYPE  = DataType.LONG
SIZE_TYPE = DataType.LONG
MIN_TYPE  = DataType.BYTE
MAX_TYPE  = DataType.LONG

def run_cmd_read_nbit(cmd, suffix, args, protocol):
	if args == None or len(args) != 1:
		print(f"Syntax: {cmd}{suffix} <address>")
		util.print_addr_help()
		util.print_num_help()
		return False

	data_type = DataType.from_str(suffix)

	address = addresses.data_addr(args[0], data_type)
	if address == None:
		print(f"Invalid address or label: {args[0]}")
		return False
	if (address & data_type.addr_mask) != address:
		print(f"Invalid alignment for {data_type.nbits}-bit access: 0x{address:08X}")
		return False

	protocol.flush_in()
	value = protocol.read_value(address, data_type)
	if value == None:
		print("Timed out")
		return False

	print(f"0x{value:0{data_type.nbits//4}X}")
	return True

def run_cmd_write_nbit(cmd, suffix, args, protocol):
	if args == None or len(args) != 2:
		print(f"Syntax: {cmd}{suffix} <address> <value>")
		util.print_addr_help()
		util.print_data_help()
		util.print_num_help()
		return False

	data_type = DataType.from_str(suffix)

	address = addresses.data_addr(args[0], data_type)
	if address == None:
		print(f"Invalid address or label: {args[0]}")
		return False
	if (address & data_type.addr_mask) != address:
		print(f"Invalid alignment for {data_type.nbits}-bit access: 0x{address:08X}")
		return False

	value = util.try_parse_num(args[1], data_type.nbits)
	if value == None:
		print(f"Invalid data for {data_type.nbits}-bit write: {args[1]}")
		return False

	protocol.write_value(address, value, data_type)
	protocol.flush_out()
	return True

def run_cmd_fread_nbit(cmd, suffix, args, protocol):
	if args == None or len(args) != 3:
		print(f"Syntax: {cmd}{suffix} <address> <length> <output.bin>")
		util.print_addr_help()
		print("Length is a number in bytes.")
		util.print_num_help()
		print("Prefix output file with ! to force overwrite.")
		return False

	data_type = DataType.from_str(suffix)

	address, length = addresses.data_addr_len(args[0], data_type)
	if address == None:
		print(f"Invalid address or label: {args[0]}")
		return False
	if (address & data_type.addr_mask) != address:
		print(f"Invalid alignment for {data_type.nbits}-bit access: 0x{address:08X}")
		return False
	
	if args[1] != "*":
		length = util.try_parse_num(args[1], SIZE_TYPE.nbits)
	if length == None:
		print("Invalid length: "+args[1])
		return False

	out_name = args[2]
	if out_name.startswith("!"):
		out_name = out_name[1:]
	elif os.path.exists(out_name):
		print(f"File {out_name} already exists. Prefix with ! to overwrite.")
		return False

	count = length // data_type.nbytes
	with open(out_name, "wb") as f_out:
		protocol.flush_in()
		if not protocol.read_to_stream(address, count, data_type, f_out):
			print("Timed out")
			return False

	return True

def run_cmd_fwrite_nbit(cmd, suffix, args, protocol):
	if args == None or len(args) != 2:
		print(f"Syntax: {cmd}{suffix} <address> <input.bin>")
		util.print_addr_help()
		util.print_num_help()
		return False

	data_type = DataType.from_str(suffix)

	address = addresses.data_addr(args[0], data_type)
	if address == None:
		print(f"Invalid address or label: {args[0]}")
		return False
	if (address & data_type.addr_mask) != address:
		print(f"Invalid alignment for {data_type.nbits}-bit access: 0x{address:08X}")
		return False

	in_name = args[1]
	if os.path.isdir(in_name) or not os.path.exists(in_name):
		print(f"File {in_name} does not exist or is not readable.")
		return False

	length = os.path.getsize(in_name)
	count = length // data_type.nbytes
	with open(in_name, "rb") as f_in:
		if not protocol.write_from_stream(address, count, data_type, f_in):
			print("File error")
			return False
		protocol.flush_out()

	return True

def run_cmd_hist_nbit(cmd, suffix, args, protocol):
	if args == None or len(args) != 3:
		print(f"Syntax: {cmd}{suffix} <address> <count> <log.txt>")
		util.print_addr_help()
		print("Count is the number of samples to take.")
		util.print_num_help()
		print("Prefix log file with ! to force overwrite.")
		return False

	data_type = DataType.from_str(suffix)

	address = addresses.data_addr(args[0], data_type)
	if address == None:
		print(f"Invalid address or label: {args[0]}")
		return False
	if (address & data_type.addr_mask) != address:
		print(f"Invalid alignment for {data_type.nbits}-bit access: 0x{address:08X}")
		return False

	histcount = util.try_parse_num(args[1], SIZE_TYPE.nbits)
	if histcount == None or histcount < 1 or histcount > 1e6:
		print(f"Invalid count: {args[1]}")
		return False

	out_name = args[2]
	if out_name.startswith("!"):
		out_name = out_name[1:]
	elif os.path.exists(out_name):
		print(f"File {out_name} already exists. Prefix with ! to overwrite.")
		return False

	hist = dict()
	donecount = 0
	percent_done = 0
	percent_modulo = 1
	if histcount < 100000:
		percent_modulo = 10

	protocol.flush_in()
	for i in range(histcount):
		value = protocol.read_value(address, data_type)
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

	if donecount == 0:
		return False

	print(f"Got {donecount} data points")
	hist_values = sorted(hist.keys())
	with open(out_name, "w") as f_hist:
		for value in hist_values:
			frequency = hist[value]
			f_hist.write(f"0x{value:0{data_type.nbits//4}X}: {frequency}\n")

	print(f"Histogram logged to {out_name}")
	return True

def run_cmd_call(cmd, suffix, args, protocol):
	if args == None or len(args) < 1 or len(args) > 9:
		print(f"Syntax: {cmd} <func> [args...]")
		print("Use command \"listfuncs\" to see a list of known functions.")
		print("Currently supports up to 8 numeric arguments.")
		util.print_num_help()
		return False

	func = addresses.func(args[0])
	if func == None:
		print(f"Unknown function: {args[0]}")
		return False
	addr, num_args, ret_type, long_run = func

	if len(args)-1 != num_args:
		print(f"Function {args[0]} takes {num_args} arguments")
		return False
	func_args = []
	for a in args[1:]:
		fa = addresses.data_addr(a, MIN_TYPE)
		if fa == None:
			fa = util.try_parse_num(a, MAX_TYPE)
		if fa == None:
			print("Invalid argument value: "+a)
			return False
		func_args.append(fa)

	if long_run:
		print("Long-running function, timeout disabled!")
	try:
		ret = protocol.call_function(addr, func_args, ret_type, timeout=(0 if long_run else -1))
		if ret == None:
			print("Timed out, maybe crashed")
			return False
		if ret_type != None:
			print(f"0x{ret:0{ret_type.nbits//4}X}")
	except KeyboardInterrupt:
		print("Cancelled call, maybe crashed")
	return True

def run_cmd_baud(cmd, suffix, args, protocol):
	current_rate = protocol.get_baud()
	default_rate = protocol.get_default_baud()
	valid_rates = [
		default_rate,
		# Attainable standard rates
		300, 1200, 2400, 4800, 9600, 19200, 38400,
		# Attainable sensible nonstandard rates
		31250, 50000, 62500, 100000, 125000, 250000
	]
	valid_rates = sorted(list(set(valid_rates)))
	valid_rates_str = ", ".join([str(x) for x in valid_rates])

	if args == None or len(args) != 1:
		print(f"Syntax: {cmd} <rate>")
		print(f"Valid rates: {valid_rates_str}")
		print("High rates may be unstable")
		print(f"Current: {current_rate}, default: {default_rate}")
		return False

	try:
		baud = int(args[0])
	except ValueError:
		baud = None

	if baud == None or baud not in valid_rates:
		print("Invalid baud rate")
		print(f"Valid rates: {valid_rates_str}")
		print("High rates may be unstable")
		print(f"Current: {current_rate}, default: {default_rate}")
		return False

	protocol.set_baud(baud)
	return True

def run_cmd_reset(cmd, suffix, args, protocol):
	if args == None or len(args) != 0:
		print(f"Syntax: {cmd}")
		return False

	WDT_TCSR_TCNT_W = 0x5FFFFB8
	WDT_RSTCSR_W    = 0x5FFFFBA

	# Set up the watchdog to immediately reset the console
	print("Attempting watchdog reset...")
	protocol.write_value(WDT_TCSR_TCNT_W, 0xA500, DataType.WORD) # disable watchdog & clear counter
	protocol.write_value(WDT_RSTCSR_W,    0x5A40, DataType.WORD) # enable system reset, power-on reset type
	protocol.write_value(WDT_TCSR_TCNT_W, 0xA560, DataType.WORD) # enable watchdog, fastest clock

	# Set to default baud rate
	baud_old = protocol.get_baud()
	protocol.reset_baud(tell=False)
	baud_changed = (baud_old != protocol.get_baud())

	# Wait for finish rebooting
	time.sleep(RESET_DELAY)
	comm_check = protocol.read_value(0, DataType.BYTE)
	if comm_check == None:
		print("Can't communicate with console")
		return False
	print("Done")

	# Set back to previous baud rate
	protocol.set_baud(baud_old)

	return True
