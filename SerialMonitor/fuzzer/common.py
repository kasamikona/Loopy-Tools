import itertools, os, random, struct, time

import monitor_addresses as addresses
from monitor_protocol import DataType

VECTABLE_BASE = 0x09000800
TEMPCODE_BASE = 0x09000C00
MAINCODE_BASE = 0x09001000

def load_address_specs(spec_list, cumulative_weights=True):
	addr_list = []
	weight_list = []
	for spec in spec_list:
		label, data_type, count, weight = spec[:4]
		data_mask = data_type.data_mask
		data_force = 0
		if len(spec) >= 5:
			data_mask = spec[4] & data_type.data_mask
		if len(spec) >= 6:
			data_force = spec[5]
		addr = addresses.data_addr(label, data_type)
		if addr == None:
			raise ValueError(f"Bad address spec {label}")
			return None
		for i in range(0, count):
			iaddr = addr + data_type.nbytes*i
			addr_list.append( (iaddr, data_type, data_mask, data_force) )
			weight_list.append(weight / count)
	if cumulative_weights:
		weight_list = list(itertools.accumulate(weight_list))
	return addr_list, weight_list

def write_opcodes(protocol, opcodes, address):
	opcodes_bytes = struct.pack(f">{len(opcodes)}H", *opcodes)
	protocol.write_bytes(address, opcodes_bytes, DataType.WORD)

def run_temp_code(protocol, opcodes, args, ret_type):
	write_opcodes(protocol, opcodes, TEMPCODE_BASE)
	return protocol.call_function(TEMPCODE_BASE, args, ret_type, timeout=2)

def setup_ram_vectable(protocol):
	# Get the current VBR
	current_vbr = run_temp_code(protocol, [
		0x0022, # stc vbr,r0
		0x000B, # rts
		0x0009, # _nop
	], [], DataType.LONG)
	if current_vbr == None:
		return False

	#print("Setting up vector table in RAM")
	#print(f"Current VBR = 0x{current_vbr:08X}")

	# Copy the existing table to RAM
	vectable_bytes = protocol.read_bytes(current_vbr, 256, DataType.LONG)
	protocol.write_bytes(VECTABLE_BASE, vectable_bytes, DataType.LONG)

	# Update the VBR
	return run_temp_code(protocol, [
		0x442E, # ldc r4,vbr
		0x000B, # rts
		0x0009, # _nop
	], [VECTABLE_BASE], None) != None

def change_vector(protocol, vec_num, vec_addr):
	protocol.write_value(VECTABLE_BASE + vec_num*4, vec_addr, DataType.LONG)

def align4(x):
	return x + ((-x) & 3)

def loword(x):
	return x & 0xFFFF

def hiword(x):
	return (x >> 16) & 0xFFFF

def log_print(s, log_file):
	if log_file != None:
		log_file.write(s+"\n")

def print_and_log(s, log_file):
	print(s)
	log_print(s, log_file)

def format_write_action(w):
	addr, val, data_type = w
	return f"write{data_type.nbits} 0x{addr:08X} 0x{val:0{data_type.nbits//4}X}"

def run_fuzz_reduce(protocol, addr_spec, test_setup_func, test_check_func, max_writes, log_file):
	# This fuzzing process starts by writing random values until a check passes,
	# then iteratively removes some writes until a minimal set of writes is found.
	# It assumes that write order *may* matter (but doesn't currently check it),
	# and that the tested behavior is deterministic and fairly time-insensitive.
	# It currently makes no attempt to analyze data values beyond which random values work.
	# This is by no means a *good* fuzzer, but it serves its purpose well.

	if not protocol.check_connection():
		print("Failed to communicate with console")
		return False

	addrs, addr_cweights = load_address_specs(addr_spec, True)
	print(f"Loaded {len(addrs)} addresses")

	group_size = 200

	sift_count = 20
	sift_fract_start = 0.2
	sift_fract_end = 0.8
	sift_threshold = 15

	refine_count = 100
	refine_threshold = 1

	test_baud = 125000
	if test_baud != protocol.get_baud():
		protocol.set_baud(test_baud)

	# Initial random writes: Write random values until the check passes

	if not test_setup_func(protocol):
		print("Setup failed")
		return False
	if test_check_func(protocol):
		print("Check passing without any writes!")
		return False

	print_and_log("[Initial Random Writes]", log_file)
	print(f"Writing up to {max_writes} random values...")
	write_list = []
	while True:
		for i in range(group_size):
			#protocol.flush_out()
			#protocol.flush_in()

			addr, data_type, data_mask, data_force = random.choices(addrs, cum_weights=addr_cweights, k=1)[0]
			val = (random.randint(0, data_type.unsigned_max) & data_mask) | data_force

			protocol.write_value(addr, val, data_type)
			w = (addr, val, data_type)
			write_list.append(w)
			log_print(format_write_action(w), log_file)

			#debug_read = protocol.read_value(0x05FFFF60, DataType.LONG)
			##debug_read = protocol.call_function(0x0E0009D8, [], DataType.LONG, timeout=0.5)
			#if debug_read == None:
			#	print(f"{i:04X} ????????")
			#else:
			#	print(f"{i:04X} {debug_read:08X}")
		protocol.flush_out()
		log_file.flush()

		if not protocol.check_connection():
			print_and_log("Console crashed", log_file)
			print(f"Check log file for last writes")
			return False

		if test_check_func(protocol):
			print_and_log(f"Check passed after {len(write_list)} writes", log_file)
			break
		else:
			if len(write_list) >= max_writes:
				print_and_log("Check did not pass after all writes", log_file)
				return True

	log_file.flush()

	# Verifying: Try the full list of writes again

	print_and_log("[Verifying]", log_file)

	if not test_setup_func(protocol):
		print_and_log("Setup failed", log_file)
		return False

	for addr, val, data_type in write_list:
		protocol.write_value(addr, val, data_type)
	protocol.flush_out()

	if not protocol.check_connection():
		print_and_log("Console crashed", log_file)
		return False

	if test_check_func(protocol):
		print_and_log("Verify passed", log_file)
		log_print("", log_file)
		log_file.flush()
	else:
		print_and_log("Verify failed", log_file)
		return False

	# Sifting: Try several times keeping a fraction of all writes
	# Refining: Try many times omitting one write each time
	# In both cases, the write list is updated to the reduced list if the check passes

	for sr_stage in [0, 1]:
		sifting = sr_stage == 0

		print_and_log("[Sifting]" if sifting else "[Refining]", log_file)
		try_count = sift_count if sifting else refine_count
		threshold = sift_threshold if sifting else refine_threshold

		if len(write_list) <= threshold:
			continue

		essential_writes = [False]*len(write_list)
		num_essential_writes = 0
		removed_index = 0

		for try_num in range(try_count):
			if sifting:
				sift_fract = (sift_fract_end - sift_fract_start) * (try_num / (try_count-1)) + sift_fract_start
				write_list_reduced = [x for x in write_list if random.random() < sift_fract]
				print(f"Try {try_num}: {len(write_list_reduced)} randomly selected writes ({sift_fract:.02f})")
			else:
				while True:
					removed_index = random.randrange(len(write_list))
					if not essential_writes[removed_index]:
						break
				write_list_reduced = write_list[:]
				write_list_reduced.pop(removed_index)
				print(f"Try {try_num}: {len(write_list_reduced)} writes")

			if not test_setup_func(protocol):
				print_and_log("Setup failed", log_file)
				return False

			for addr, val, data_type in write_list_reduced:
				protocol.write_value(addr, val, data_type)
			protocol.flush_out()

			if not protocol.check_connection():
				print_and_log("Console crashed", log_file)
				return False

			if test_check_func(protocol):
				print("Check passed")
				write_list = write_list_reduced
				if not sifting:
					essential_writes.pop(removed_index)
			else:
				print("Check failed, discarding")
				if not sifting:
					essential_writes[removed_index] = True
					num_essential_writes += 1

			if len(write_list) <= threshold:
				break
			if num_essential_writes == len(write_list):
				break

		print_and_log(f"Reduced to {len(write_list)} writes", log_file)
		for w in write_list:
			log_print(format_write_action(w), log_file)
		log_print("", log_file)
		log_file.flush()

	print_and_log("[Finished]", log_file)
	return True

def show_default_warning():
	print()
	print("WARNING: Disconnect video or abort test if you are sensitive to flashing lights.")
	print("The fuzzing process may cause the console's video output to flash rapidly.")
	print("Feedback on the output is not required for this test.")
	print()
	try:
		if input('Type "accept" to continue: ').lower() == "accept":
			print()
			return True
	except KeyboardInterrupt:
		print()
	print("Not continuing.")
	return False
