import sys, struct, csv

rombase = 0x0E000000
valid_pointers = range(rombase, rombase+0x400000, 4)

def should_exclude_string(data):
	for ch in data:
		#if (ch < 0x20 and not (ch == 0x09 or ch == 0x0A or ch == 0x0D)) or ch == 0x7F:
		if ch < 0x20 or ch == 0x7F:
			return True
	try:
		data.decode("shift-jis")
	except UnicodeDecodeError:
		return True
	return False

def gather_strings(data, valid_range):
	parts = []
	for addr in range(0, len(data), 4):
		ptr = struct.unpack(">I", data[addr:addr+4])[0]
		if ptr in valid_range:
			strdata = b""
			for ptr2 in range(ptr - rombase, len(data)):
				newchar = data[ptr2:ptr2+1]
				if newchar == b"\0":
					break
				strdata += newchar
			if len(strdata) == 0 or should_exclude_string(strdata):
				continue
			parts.append( (addr, ptr, strdata) )
	return parts

def string_escape(string_raw):
	# Working with unicode so fullwidth character block is at 0xFF01 etc.
	
	string_esc = ""
	for c in string_raw:
		# Escape ASCII
		if ord(c) < 0x20:
			string_esc += "\\x{0:02x}".format(ord(c))
		elif c == "x":
			string_esc += "\\xx" # special case for x
		elif ord(c) <= 0x7E:
			string_esc += "\\"+c
		# Convert fullwidth to ASCII
		elif ord(c) == 0x3000: # Ideographic space
			string_esc += " "
		elif ord(c) >= 0xFF01 and ord(c) <= 0xFF5E: # Regular fullwidth block
			string_esc += chr(ord(c)-0xFEE0)
		else:
			string_esc += c
	
	# Test round-trip
	string_roundtrip = string_unescape(string_esc)
	if string_roundtrip != string_raw:
		raise Exception("Round-trip error for string {0} -> {1} -> {2}".format(string_raw, string_esc, string_roundtrip))
	
	return string_esc

def string_unescape(string_esc):
	string_raw = ""
	in_escape = 0
	escape_ord = 0
	for c in string_esc:
		if in_escape == 1: # \?
			if c == "x":
				in_escape = 2
			else:
				string_raw += c
				in_escape = 0
		elif in_escape == 2: # \x?
			if c == "x":
				string_raw += c
				in_escape = 0
			else:
				escape_ord = int(c, 16)*16
				in_escape = 3
		elif in_escape == 3: # \xN?
			escape_ord += int(c, 16)
			string_raw += chr(escape_ord)
			in_escape = 0
		else: # Not in escape
			if c == "\\":
				in_escape = 1
			else:
				# Convert unescaped ASCII to fullwidth
				if c == " ":
					string_raw += chr(0x3000)
				elif ord(c) >= 0x20 and ord(c) <= 0x7E:
					string_raw += chr(ord(c)+0xFEE0)
				else:
					string_raw += c
	return string_raw

def cmd_unpack(args):
	if len(args) != 1:
		print("Usage:", sys.argv[0], sys.argv[1], "<rom.bin>")
		return
	
	with open(args[0], "rb") as f:
		data = f.read()
	
	# Check if ROM is valid
	startptr = struct.unpack(">I", data[0:4])[0]
	if not startptr in valid_pointers:
		print("Doesn't look like a valid ROM")
		return
	
	# Gather all valid string pointers
	# (ptrloc, strloc, strdata)
	stringpointers = gather_strings(data, valid_pointers)
	print("Found {0:d} string pointers".format(len(stringpointers)))
	
	origin_set = set()
	string_list = [] # (strloc, strlen, strdata)
	pointer_list = [] # (ptrloc, strloc)
	region_list = [] 
	
	# Separate unique strings and their pointers
	bytes_used = 0
	for sp in stringpointers:
		ptrloc = sp[0]
		strloc = sp[1]
		strdata = sp[2]
		strlen = len(strdata) + 1 # +1 for null terminator
		if not strloc in origin_set:
			string_list.append( (strloc, strlen, strdata) )
			origin_set.add(strloc)
			region_list.append( (strloc-rombase, strlen) )
			bytes_used += strlen
		pointer_list.append( (ptrloc, strloc) )
	
	print("String data uses {0:d} bytes".format(bytes_used))
	
	# Write unique strings
	with open(args[0]+"_strings.csv", "w", encoding="utf-8", newline="") as f:
		header = ["origin", "origin_length", "text_jp", "text_en", "verified"]
		w = csv.writer(f, delimiter=",", quotechar='"')
		w.writerow(header)
		for e in string_list:
			w.writerow( ["0x{0:08x}".format(e[0]), e[1], string_escape(e[2].decode("shift-jis")), "", ""] )
		print("Wrote {0:d} unique strings to {1}".format(len(string_list), f.name))
	
	# Write pointers
	with open(args[0]+"_pointers.csv", "w", encoding="utf-8", newline="") as f:
		header = ["ptrloc", "strloc"]
		w = csv.writer(f, delimiter=",", quotechar='"')
		w.writerow(header)
		for e in pointer_list:
			w.writerow( ["0x{0:08x}".format(e[0]), "0x{0:08x}".format(e[1])] )
		print("Wrote {0:d} pointers to {1}".format(len(pointer_list), f.name))

def cmd_regions(args):
	if len(args) < 2:
		print("Usage:", sys.argv[0], sys.argv[1], "<rom.bin> <strings.csv> [0xExtraStart-0xExtraEnd] ...")
		return
	
	regions = [] # (start, length)
	for i in range(2, len(args)):
		start, end = args[i].split("-")
		start = int(start, 16)
		end = int(end, 16)
		length = end-start
		regions.append( (start, length) )
	
	with open(args[0], "rb") as f:
		data = f.read()
	
	# Check if ROM is valid, swap if necessary
	startptr = struct.unpack(">I", data[0:4])[0]
	swapped = False
	if not startptr in valid_pointers:
		print("Doesn't look like a valid ROM")
		return
	
	with open(args[1], newline='', encoding="utf-8") as f:
		cr = csv.reader(f, delimiter=",", quotechar='"')
		for i, row in enumerate(cr):
			if i == 0:
				continue
			strloc = int(row[0], 16)-rombase
			strlen = int(row[1])
			strlen_padded = strlen
			# Always pad to 2 bytes
			if (strlen & 1):
				strlen += 1
			# Pad to 4 bytes if it looks like padding pattern
			if (strlen & 2):
				if data[strloc+strlen] == 0 and data[strloc+strlen+1] == 9:
					strlen += 2
			regions.append( (strloc, strlen) )
	
	# Sort and merge regions
	#regions.sort(key=lambda r: r[0])
	#for i in range(len(regions)-2, -1, -1): # [n-2 .. 0]
	#	thisstart = regions[i][0]
	#	thislen = regions[i][1]
	#	nextstart = regions[i+1][0]
	#	nextlen = regions[i+1][1]
	#	if thisstart+thislen == nextstart:
	#		regions[i] = (thisstart, nextstart+nextlen-thisstart)
	#		regions.pop(i+1)
	
	# Resolve overlaps
	DO_RESOLVE_OVERLAPS = True
	if DO_RESOLVE_OVERLAPS:
		region_data = [0]*len(data)
		for r in regions:
			for i in range(r[0], r[0]+r[1]):
				region_data[i] = 1
		regions = []
		current_start = None
		current_len = 0
		for i in range(len(data)):
			inside = region_data[i]
			if current_start == None:
				if inside:
					current_start = i
					current_len = 1
			else:
				if inside:
					current_len += 1
				else:
					regions.append((current_start, current_len))
					current_start = None
		if current_start != None:
			regions.append((current_start, current_len))

	# Write memory regions
	with open(args[0]+"_regions.csv", "w", encoding="utf-8", newline="") as f:
		header = ["start", "length"]
		w = csv.writer(f, delimiter=",", quotechar='"')
		w.writerow(header)
		for e in regions:
			w.writerow( ["0x{0:08x}".format(e[0]), "{0:d}".format(e[1])] )
		print("Wrote {0:d} memory regions to {1}".format(len(regions), f.name))
	
	# Count total length
	total_bytes = 0
	for r in regions:
		total_bytes += r[1]
	print("Total {0:d} bytes available".format(total_bytes))

def cmd_repack(args):
	if len(args) != 3:
		print("Usage:", sys.argv[0], sys.argv[1], "<rom.bin> <strings.csv> <regions.csv>")
		return
	
	with open(args[0], "rb") as f:
		data = f.read()
	
	# Check if ROM is valid, swap if necessary
	startptr = struct.unpack(">I", data[0:4])[0]
	if not startptr in valid_pointers:
		print("Doesn't look like a valid ROM")
		return
	
	strings = {} # origin: (text_data, need_len, [pointers])
	string_data_needed = 0
	with open(args[1], newline='', encoding="utf-8") as f:
		cr = csv.reader(f, delimiter=",", quotechar='"')
		for i, row in enumerate(cr):
			if i == 0:
				continue
			origin = int(row[0], 16)
			text = row[3]
			if len(text) == 0:
				text = row[2]
			text_data = string_unescape(text).encode("shift-jis")
			text_data += b"\x00"
			need_len = len(text_data)
			string_data_needed += need_len
			strings[origin] = (text_data, need_len, [])
	
	# Gather all valid rom pointers
	# (ptrloc, strloc, strdata)
	pointers_in_rom = gather_strings(data, valid_pointers)
	print("Found {0:d} pointers in ROM".format(len(pointers_in_rom)))
	pointers_to_change = 0
	
	for r in pointers_in_rom:
		if r[1] in strings:
			strings[r[1]][2].append(r[0])
			pointers_to_change += 1
	print("Of which {0:d} will be updated".format(pointers_to_change))
	
	regions = []
	available_bytes = 0
	with open(args[2], newline='', encoding="utf-8") as f:
		cr = csv.reader(f, delimiter=",", quotechar='"')
		for i, row in enumerate(cr):
			if i == 0:
				continue
			start = int(row[0],16)
			length = int(row[1])
			regions.append( (start, length) )
			available_bytes += length
	
	print("New strings take up {0:d} bytes, space available {1:d} bytes".format(string_data_needed, available_bytes))
	if string_data_needed > available_bytes:
		print("Not enough space! Shorten strings or add more regions")
		return
	
	# Try fit the data into the regions in a best-fit manner
	for sk in strings:
		s = strings[sk]
		text_data = s[0]
		need_len = s[1]
		
		# Find best region
		best_region = None
		best_region_index = 0
		best_region_diff = 0
		for i, r in enumerate(regions):
			diff = r[1] - need_len
			if diff < 0:
				continue
			if best_region == None or diff < best_region_diff:
				best_region = r
				best_region_diff = diff
				best_region_index = i
		
		if best_region == None:
			print("Can't fit strings with this fitting method! Shorten strings or add more regions")
			return
		
		# Insert data where found
		fit_start = best_region[0]
		fit_end = fit_start + need_len
		data[fit_start:fit_end] = text_data
		
		# Update region size
		new_start = fit_end
		new_start += (4 - (new_start&3))&3 # Pad to 4 bytes
		new_len = best_region[1] + best_region[0] - new_start
		if new_len <= 0:
			regions.remove(best_region)
			new_start += new_len # constrain end for padding
		else:
			regions[best_region_index] = (new_start, new_len)
		
		# Write padding
		for i in range(fit_end, new_start):
			data[i] = (i&1)*9
		
		# Update pointers
		for p in s[2]:
			data[p:p+4] = struct.pack(">I", fit_start+rombase)
		
	print("All strings inserted successfully")
	
	# Write the new ROM
	with open(args[0]+"_repack.bin", "wb") as f:
		f.write(data)
		print("Wrote repacked ROM to {0}".format(f.name))

def handle_command():
	commands = {"unpack":cmd_unpack, "regions":cmd_regions, "repack":cmd_repack}
	if len(sys.argv) > 1:
		command = sys.argv[1].lower()
		args = sys.argv[2:]
		if command in commands:
			commands[command](args)
			return
	print("Usage:", sys.argv[0], "<"+("|".join(commands.keys()))+">")

if __name__ == "__main__":
	handle_command()
