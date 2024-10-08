import sys, struct, csv, os

ROM_BASE = 0x0E000000
VALID_POINTERS = range(ROM_BASE, ROM_BASE+0x400000, 4)
REPACK_FOR_HALFWIDTH = False

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
			for ptr2 in range(ptr - ROM_BASE, len(data)):
				newchar = data[ptr2:ptr2+1]
				if newchar == b"\0":
					break
				strdata += newchar
			if len(strdata) == 0 or should_exclude_string(strdata):
				continue
			parts.append( (addr, ptr, strdata) )
	return parts

def string_escape(string_raw):
	if not string_raw:
		return "{empty}"
	
	string_esc = ""
	
	is_ascii = True
	has_noncontrol_ascii = False
	for c in string_raw:
		if ord(c) > 0x7E:
			is_ascii = False
			break
		elif c not in "!#>@CcKkNn^%BM":
			has_noncontrol_ascii = True
	
	is_ascii = is_ascii & has_noncontrol_ascii
	
	if is_ascii:
		#print("Warning: plain ASCII string "+str(string_raw.encode("sjis")))
		for c in string_raw:
			if ord(c) < 0x20:
				string_esc += f"\\x{ord(c):02x}"
				print("Warning: escaped ASCII control code in string "+str(string_raw.encode("sjis")))
			else:
				string_esc += c
	else:
		for c in string_raw:
			if ord(c) < 0x20:
				string_esc += f"\\x{ord(c):02x}"
				print("Warning: escaped ASCII control code in string "+str(string_raw.encode("sjis")))
			elif c == "!":
				string_esc += "{opt}"
			elif c == "#":
				string_esc += "{aopt}"
			elif c == ">":
				string_esc += "{hsp}"
			elif c == "@":
				string_esc += "{fast}"
			elif c == "C" or c == "c":
				string_esc += "{clr}"
			elif c == "K" or c == "k":
				string_esc += "{np}"
			elif c == "N" or c == "n":
				string_esc += "{nl}"
			elif c == "^":
				string_esc += "{slow}"
			else:
				string_esc += c
	
	# Test round-trip
	string_roundtrip = string_unescape(string_esc, False)
	if string_roundtrip.lower() != string_raw.lower() or (is_ascii and string_roundtrip != string_raw):
		raise Exception(f"Round-trip error for string {string_raw} -> {string_esc} -> {string_roundtrip}")
	
	return string_esc

def string_unescape(string_esc, alternate_mapping):
	shorten = {"option":"opt","altoption":"aopt","halfspace":"hsp","clear":"clr","newpage":"np","newline":"nl","nofast":"slow"}
	mapping = {"opt":"!","aopt":"#","hsp":">","fast":"@","clr":"c","np":"k","nl":"n","slow":"^"}
	if alternate_mapping:
		mapping = {"opt":"\x19","aopt":"\x1A","hsp":"\x1F","fast":"\x1B","clr":"\x1C","np":"\x1D","nl":"\x1E","slow":"\x18"}
	string_raw = string_esc.replace("{empty}","")
	for k,v in mapping.items():
		string_raw = string_raw.replace("{"+k+"}",v)
	for k,v in shorten.items():
		string_raw = string_raw.replace("{"+k+"}",mapping[v])
	return string_raw

def change_suffix(s, change_from, change_to):
	s2 = s
	if change_from:
		index = s.rfind(change_from)
		if index >= 0:
			s2 = s[:index] + change_to + s[index+len(change_from):]
	if s2 == s:
		s2 = s+change_to
	return s2

def change_suffix_filename(s, change_from, change_to, extension):
	return change_suffix(os.path.splitext(s)[0], change_from, change_to)+extension

def csv_quote(s):
	qs = '"'
	for ch in s:
		qs += ch
		if ch == '"':
			qs += ch
	qs += '"'
	return qs

def cmd_extract(args):
	if len(args) != 1:
		print("Usage:", sys.argv[0], sys.argv[1], "<rom.bin>")
		return
	
	with open(args[0], "rb") as f:
		data = f.read()
	
	# Check if ROM is valid
	startptr = struct.unpack(">I", data[0:4])[0]
	if not startptr in VALID_POINTERS:
		print("Doesn't look like a valid ROM")
		return
	
	# Gather all valid string pointers
	# (ptrloc, strloc, strdata)
	stringpointers = gather_strings(data, VALID_POINTERS)
	print(f"Found {len(stringpointers):d} string pointers")
	
	origin_set = set()
	string_list = [] # (strloc, strlen, strdata, pointers)
	region_list = [] 
	string_indices = {} # strloc -> list index
	
	# Separate strings and their pointers
	bytes_used = 0
	for sp in stringpointers:
		ptrloc = sp[0]
		strloc = sp[1]
		strdata = sp[2]
		strlen = len(strdata) + 1 # +1 for null terminator
		if not strloc in string_indices:
			string_indices[strloc] = len(string_list)
			string_list.append( (strloc, strlen, strdata, []) )
			region_list.append( (strloc-ROM_BASE, strlen) )
			bytes_used += strlen
		string_list[string_indices[strloc]][3].append(ptrloc+ROM_BASE)
	
	string_list = sorted(string_list, key=lambda s: s[0])
	
	print(f"String data uses {bytes_used:d} bytes")
	
	# Write strings
	with open(change_suffix_filename(args[0], None, "_strings", ".csv"), "w", encoding="utf-8") as f:
		header = ["origin", "origin_length", "text_jp", "text_en", "pointers", "game_order"]
		f.write(",".join(header)+"\n")
		for e in string_list:
			row = [""] * len(header)
			row[0] = f"0x{e[0]:08X}" # origin (hex)
			row[1] = f"{e[1]:d}" # origin_length
			row[2] = csv_quote(string_escape(e[2].decode("shift-jis"))) # text_jp
			row[3] = '""' # text_en
			row[4] = ";".join([f"0x{p:08X}" for p in e[3]]) # pointers (semicolon separated)
			# 3:text_en and 5:game_order to be filled by user
			f.write(",".join(row)+"\n")
			
		print(f"Extracted {len(string_list):d} strings to {f.name}")

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
	
	# Check if ROM is valid
	startptr = struct.unpack(">I", data[0:4])[0]
	if not startptr in VALID_POINTERS:
		print("Doesn't look like a valid ROM")
		return
	
	with open(args[1], newline='', encoding="utf-8") as f:
		cr = csv.reader(f, delimiter=",", quotechar='"')
		for i, row in enumerate(cr):
			if i == 0 or row[0].startswith("#"):
				continue
			strloc = int(row[0], 16)-ROM_BASE
			strlen = int(row[1])
			strlen_padded = strlen
			# Always pad to 2 bytes
			if (strlen & 1):
				strlen += 1
			# Pad to 4 bytes if it looks like padding pattern
			if (strlen & 2):
				if data[strloc+strlen] == 0 and data[strloc+strlen+1] == 9:
					strlen += 2
				elif data[strloc+strlen] == 255 and data[strloc+strlen+1] == 255:
					strlen += 2
			regions.append( (strloc, strlen) )
	
	# Resolve overlaps and merge by bitfield
	DO_RESOLVE_OVERLAPS = True
	if DO_RESOLVE_OVERLAPS:
		region_bitfield = [0]*((len(data)+31)//32)
		for r in regions:
			for i in range(r[0], r[0]+r[1]):
				region_bitfield[i//32] |= 1<<(i&31)
		regions = []
		current_start = None
		current_len = 0
		for i in range(len(data)):
			inside = (region_bitfield[i//32] & (1<<(i&31))) != 0
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
	with open(change_suffix_filename(args[1], "_strings", "_regions", ".csv"), "w", encoding="utf-8", newline="") as f:
		header = ["start", "length"]
		w = csv.writer(f, delimiter=",", quotechar='"')
		w.writerow(header)
		for e in regions:
			w.writerow( [f"0x{e[0]:08x}", f"{e[1]:d}"] )
		print(f"Wrote {len(regions):d} memory regions to {f.name}")
	
	# Count total length
	total_bytes = 0
	for r in regions:
		total_bytes += r[1]
	print(f"Total {total_bytes:d} bytes available")

def cmd_inject(args):
	if len(args) != 3:
		print("Usage:", sys.argv[0], sys.argv[1], "<rom.bin> <strings.csv> <regions.csv>")
		return
	
	with open(args[0], "rb") as f:
		data = f.read()
	
	newdata = bytearray(data)
	
	# Check if ROM is valid, swap if necessary
	startptr = struct.unpack(">I", data[0:4])[0]
	if not startptr in VALID_POINTERS:
		print("Doesn't look like a valid ROM")
		return
	
	strings = {} # origin: (text_data, need_len, [pointers])
	string_data_needed = 0
	with open(args[1], newline='', encoding="utf-8") as f:
		cr = csv.reader(f, delimiter=",", quotechar='"')
		for i, row in enumerate(cr):
			if i == 0 or row[0].startswith("#"):
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
	pointers_in_rom = gather_strings(data, VALID_POINTERS)
	print(f"Found {len(pointers_in_rom):d} pointers in ROM")
	pointers_to_change = 0
	
	for r in pointers_in_rom:
		if r[1] in strings:
			strings[r[1]][2].append(r[0])
			pointers_to_change += 1
	print(f"Of which {pointers_to_change:d} will be updated")
	
	regions = []
	available_bytes = 0
	with open(args[2], newline='', encoding="utf-8") as f:
		cr = csv.reader(f, delimiter=",", quotechar='"')
		for i, row in enumerate(cr):
			if i == 0 or row[0].startswith("#"):
				continue
			start = int(row[0],16)
			length = int(row[1])
			regions.append( (start, length) )
			available_bytes += length
	
	print(f"New strings take up {string_data_needed:d} bytes, space available {available_bytes:d} bytes")
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
			#best_region = r
			#best_region_index = i
			#break
		
		if best_region == None:
			print("Can't fit strings with this fitting method! Shorten strings or add more regions")
			return
		
		# Insert data where found
		fit_start = best_region[0]
		fit_end = fit_start + need_len
		newdata[fit_start:fit_end] = text_data
		
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
			newdata[i] = 0xFF #(i&1)*9
		
		# Update pointers
		for p in s[2]:
			newdata[p:p+4] = struct.pack(">I", fit_start+ROM_BASE)
		
	print("All strings injected successfully")
	
	# Write the new ROM
	with open(change_suffix_filename(args[1], "_strings", "_inject", ".bin"), "wb") as f:
		f.write(bytes(newdata))
		print(f"Wrote injected ROM to {f.name}")

def cmd_reclean(args):
	if len(args) != 2:
		print("Usage:", sys.argv[0], sys.argv[1], "<old_clean.csv> <new_strings.csv>")
		return
	
	# Load new strings into a dictionary by origin address
	new_strings = {} # origin: (text_jp, origin_length)
	ns_count = 0
	with open(args[1], newline='', encoding="utf-8") as fn:
		cr = csv.reader(fn, delimiter=",", quotechar='"')
		for i, row in enumerate(cr):
			if i == 0 or row[0].startswith("#"):
				continue
			origin = int(row[0], 16)
			text_jp = row[2]
			origin_length = row[1]
			ns_count += 1
			if origin in new_strings:
				print(f"Warning: duplicate string at 0x{origin:08X} in new strings")
			new_strings[origin] = (text_jp, origin_length)
	print(f"Loaded {ns_count} new strings")
	
	# Use old file as template, replacing strings line by line
	rewritten = 0
	with open(change_suffix_filename(args[1], "_strings", "_reclean", ".csv"), "w", encoding="utf-8") as fclean:
		with open(args[0], newline='', encoding="utf-8") as ftemplate:
			for i, row_raw in enumerate(ftemplate.readlines()):
				row = next(csv.reader([row_raw], delimiter=",", quotechar='"'))
				if i == 0 or row[0].startswith("#"):
					# Preserve header and comments
					fclean.write(row_raw.replace("\r",""))
					continue
				origin = int(row[0], 16)
				if origin in new_strings:
					ns = new_strings[origin]
					row[1] = ns[1] # update origin_length just in case
					row[2] = csv_quote(ns[0]) # update text_jp
					row[3] = csv_quote(row[3]) # requote text_en because csv.reader unquoted
					fclean.write(",".join(row)+"\n")
					rewritten += 1
				else:
					print(f"Warning: string at {template_row[0]} is missing from new string list, omitted")
		print(f"Rewrote {rewritten} clean strings to {fclean.name}")

def handle_command():
	commands = {"extract":cmd_extract, "regions":cmd_regions, "inject":cmd_inject, "reclean":cmd_reclean}
	if len(sys.argv) > 1:
		command = sys.argv[1].lower()
		args = sys.argv[2:]
		if command in commands:
			commands[command](args)
			return
	print("Usage:", sys.argv[0], "<"+("|".join(commands.keys()))+">")

if __name__ == "__main__":
	handle_command()
