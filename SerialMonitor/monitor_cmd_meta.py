import monitor_addresses as addresses

LIST_FUNC_ADDRESSES = False

def run_cmd_labels(cmd, suffix, args, protocol):
	if args == None:
		return False

	all_labels = addresses.list_data()
	pad_len = max([len(x) for x in all_labels])

	for label in all_labels:
		data_addr, data_length = all_labels[label]
		if data_length != None:
			#print(f"{label.ljust(pad_len)} = 0x{data_addr:08X}-0x{data_addr+data_length-1:08X}")
			print(f"{label.ljust(pad_len)} = 0x{data_addr:08X} (0x{data_length:X} bytes)")
		else:
			print(f"{label.ljust(pad_len)} = 0x{data_addr:08X}")

	return True

def run_cmd_listfuncs(cmd, suffix, args, protocol):
	if args == None or len(args) != 0:
		print(f"Syntax: {cmd}")
		return False

	all_functions = addresses.list_functions()
	pad_len = max([len(x) for x in all_functions])

	for func_name in all_functions:
		addr, num_args, ret_type, long_run = all_functions[func_name]
		desc = (func_name).ljust(pad_len) + " : "
		if LIST_FUNC_ADDRESSES:
			desc += f"0x{addr:08X}, "
		if num_args > 1:
			desc += f"{num_args} arguments"
		elif num_args == 1:
			desc += "1 argument"
		else:
			desc += "no arguments"
		if ret_type != None:
			desc += f", {ret_type.nbits}-bit return"
		if long_run:
			desc += ", long-running"
		print(desc)
	return True
