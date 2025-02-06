import sys, struct, csv, os

ROM_BASE = 0x0E000000
VALID_POINTERS = range(ROM_BASE, ROM_BASE+0x400000, 4)
REPACK_FOR_PATCHED = True
CSV_IGNORE_NEWLINES = False

def _jis(h):
	return bytes.fromhex(h).decode("shift-jis")

REPACK_PATCH_CUSTOM_CHARS = {
	"^":  ["{note}", "{music}"],
	"`":  ["{dogface}"],
	"{": ["{smiley}", "{smile}"],
	"|": ["{heart}"],
	"}": ["{star}"],
	_jis("8163"): ["{ellipsis}", "{...}"],
	_jis("8180 8190"): ["{dpad_u}"],
	_jis("8181 8191"): ["{dpad_d}"],
	_jis("8182 8192"): ["{dpad_l}"],
	_jis("8183 8193"): ["{dpad_r}"],
	_jis("8182 8193"): ["{dpad_lr}", "{dpad_h}"],
	_jis("8184 8194"): ["{dpad_ud}", "{dpad_v}"],
	_jis("8185 8195"): ["{dpad_udlr}", "{dpad_all}", "{dpad}"],
	_jis("8186 8196"): ["{btn_a}", "{button_a}"],
	_jis("8187 8197"): ["{btn_b}", "{button_b}"],
	_jis("8188 8198"): ["{btn_c}", "{button_c}"],
	_jis("8189 8199"): ["{btn_d}", "{button_d}"],
	_jis("818A 819A"): ["{btn_lt}", "{button_lt}"],
	_jis("818B 819B"): ["{btn_rt}", "{button_rt}"],
}

def should_exclude_string(data):
	for ch in data:
		if (ch < 0x20 and not (ch in b"\x09\x0A\x0D")) or ch == 0x7F:
		#if ch < 0x20 or ch == 0x7F:
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
	
	mapping = {
		"!": "{opt}",
		"#": "{aopt}",
		">": "{hsp}",
		"@": "{fast}",
		"c": "{clr}", "C": "{clr}",
		"k": "{np}", "K": "{np}",
		"n": "{nl}", "N": "{nl}",
		"^": "{slow}",
		"%B": "{baku}",
		"%M": "{momo}",
	}
	
	is_ascii = True
	has_noncontrol_ascii = False
	for c in string_raw:
		if ord(c) > 0x7E:
			is_ascii = False
			break
		elif c not in "!#@>CcKkNn^%BMDdXxcs0123456789.":
			has_noncontrol_ascii = True
	
	is_ascii = is_ascii & has_noncontrol_ascii
	if is_ascii:
		#print("Warning: plain ASCII string "+str(string_raw.encode("shift-jis")))
		pass
	
	string_hex = ""
	for c in string_raw:
		if ord(c) < 0x20:
			string_hex += f"\\x{ord(c):02x}"
			print("Warning: escaped non-printable ASCII in string "+str(string_raw.encode("shift-jis")))
		elif c == "\\":
			string_hex += "\\\\"
		else:
			string_hex += c
	
	string_esc = string_hex
	if not is_ascii:
		string_esc = ""
		i = 0
		maxsrc = max([len(x) for x in mapping.keys()])
		while i < len(string_hex):
			matched = False
			for src,dst in mapping.items():
				if string_hex[i:i+maxsrc].startswith(src):
					string_esc += dst
					i += len(src)
					matched = True
					break
			if not matched:
				string_esc += string_hex[i]
				i += 1
	
	# Test round-trip
	string_roundtrip = string_unescape(string_esc, False)
	if string_roundtrip.lower() != string_raw.lower() or (is_ascii and string_roundtrip != string_raw):
		raise Exception(f"Round-trip error for string {string_raw.encode('shift-jis')} -> {string_esc.encode('shift-jis')} -> {string_roundtrip.encode('shift-jis')}")
	
	return string_esc

def string_unescape(string_esc, for_patched):
	if for_patched:
		mapping = {
			"\x19": ["{opt}","{option}"],
			"\x1A": ["{aopt}","{altoption}"],
			"\x1F": ["{hsp}","{halfspace}"],
			"\x1B": ["{fast}"],
			"\x1C": ["{clr}","{clear}"],
			"\x1D": ["{np}","{newpage}"],
			"\x1E": ["{nl}","{newline}"],
			"\x18": ["{slow}","{nofast}"],
			"%b": ["{baku}","{dog}","{doggie}"],
			"%m": ["{momo}","{player}","{momomo}"],
			"%B": ["{BAKU}","{DOG}","{DOGGIE}"],
			"%M": ["{MOMO}","{PLAYER}","{MOMOMO}"],
			"": ["{empty}","{nul}"],
		}
		mapping.update(REPACK_PATCH_CUSTOM_CHARS)
	else:
		mapping = {
			"!": ["{opt}","{option}"],
			"#": ["{aopt}","{altoption}"],
			">": ["{hsp}","{halfspace}"],
			"@": ["{fast}"],
			"c": ["{clr}","{clear}"],
			"k": ["{np}","{newpage}"],
			"n": ["{nl}","{newline}"],
			"^": ["{slow}","{nofast}"],
			"%B": ["{baku}","{dog}","{doggie}","{BAKU}","{DOG}","{DOGGIE}"],
			"%M": ["{momo}","{player}","{momomo}","{MOMO}","{PLAYER}","{MOMOMO}"],
			"": ["{empty}","{nul}"],
		}
	
	string_raw = string_esc
	
	for dst,srcs in mapping.items():
		for src in srcs:
			string_raw = string_raw.replace(src,dst)
	
	# Python really has no clean way to just parse this escape style in a unicode string
	# so we manually do the ones we care about
	string_unhex = ""
	i = 0
	while i < len(string_raw):
		e = string_raw[i:i+4]
		if len(e) == 4 and e[:2].lower() == "\\x":
			string_unhex += chr(int(e[2:],16))
			i += 4
		elif len(e) >= 2 and e[:2] == "\\\\":
			string_unhex += "\\"
			i += 2
		else:
			string_unhex += e[0]
			i += 1
	return string_unhex

def change_suffix(s, change_from, change_to):
	s2 = s
	if change_from:
		index = s.rfind(change_from)
		if index >= 0:
			s2 = s[:index] + change_to + s[index+len(change_from):]
	if s2 == s:
		s2 = s+change_to
	return s2

#def change_suffix_filename(s, change_from, change_to, extension):
#	return change_suffix(os.path.splitext(s)[0], change_from, change_to)+extension

def csv_decomment(csvfile):
	for row in csvfile:
		if not row.strip().startswith("#"): yield row

def check_files(exist, noexist):
	for f in exist:
		if not os.path.exists(f):
			print("Can't open file: "+f)
			return False
	for f in noexist:
		if os.path.exists(f):
			print("File already exists: "+f)
			return False
	return True

def validate_rom(data):
	startptr = struct.unpack(">I", data[0:4])[0]
	if not startptr in VALID_POINTERS:
		print("Doesn't look like a valid ROM")
		return False
	return True

def cmd_extract(args, cmdline):
	if len(args) != 2:
		print(f"Usage: {cmdline} <rom_in.bin> <strings_out.csv>")
		return
	
	path_rom_in = args[0]
	path_strings_out = args[1]
	
	if not check_files(exist=[path_rom_in], noexist=[path_strings_out]):
		return
	
	with open(path_rom_in, "rb") as f:
		data = f.read()
	if not validate_rom(data):
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
	with open(path_strings_out, "w", newline="", encoding="utf-8") as f:
		fields = ["origin", "origin_length", "text_original", "text_translated", "pointers"]
		cw = csv.DictWriter(f, fieldnames=fields, delimiter=",", quotechar='"')
		cw.writeheader()
		for e in string_list:
			cw.writerow({
				"origin":          f"0x{e[0]:08X}", # origin address in hex
				"origin_length":   f"{e[1]:d}",
				"text_original":   string_escape(e[2].decode("shift-jis")),
				"text_translated": "", # to be filled by user
				"pointers":        ";".join([f"0x{p:08X}" for p in e[3]]) # pointers separated by semicolon
			})
		print(f"Extracted {len(string_list):d} strings to {f.name}")

def cmd_regions(args, cmdline):
	if len(args) < 3:
		print(f"Usage: {cmdline} <rom_in.bin> <strings_in.csv> <regions_out.csv> [0xExtraStart-0xExtraEnd] ...")
		print("Multiple extra regions may be given. End address is exclusive.")
		return
	
	path_rom_in = args[0]
	path_strings_in = args[1]
	path_regions_out = args[2]
	
	if not check_files(exist=[path_rom_in, path_strings_in], noexist=[path_regions_out]):
		return
	
	regions = [] # (start, length)
	for i in range(3, len(args)):
		start, end = args[i].split("-")
		start = int(start, 16)
		end = int(end, 16)
		length = end-start
		regions.append( (start, length) )
	
	with open(path_rom_in, "rb") as f:
		data = f.read()
	if not validate_rom(data):
		return
	
	with open(path_strings_in, newline="", encoding="utf-8") as f:
		cr = csv.DictReader(csv_decomment(f), restval="", delimiter=",", quotechar='"')
		for row in cr:
			strloc = int(row["origin"], 16)-ROM_BASE
			strlen = int(row["origin_length"])
			strlen_padded = strlen
			# Always pad to 2 bytes as SuperH code is generally word-aligned
			if (strlen & 1):
				strlen += 1
			# Pad to 4 bytes if it looks like padding pattern
			if (strlen & 2):
				nextdata = struct.unpack(">H", data[strloc+strlen:strloc+strlen+2])[0]
				if nextdata in [0x0009, 0xFFFF]:
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
	with open(path_regions_out, "w", newline="", encoding="utf-8") as f:
		fields = ["start", "length"]
		cw = csv.DictWriter(f, fieldnames=fields, delimiter=",", quotechar='"')
		cw.writeheader()
		for e in regions:
			cw.writerow({
				"start":  f"0x{e[0]:08X}",
				"length": f"{e[1]:d}"
			})
		print(f"Wrote {len(regions):d} memory regions to {f.name}")
	
	# Count total length
	total_bytes = 0
	for r in regions:
		total_bytes += r[1]
	print(f"Total {total_bytes:d} bytes available")

def cmd_inject(args, cmdline):
	if len(args) != 4:
		print(f"Usage: {cmdline} <rom_in.bin> <strings_in.csv> <regions_in.csv> <rom_out.bin>")
		return
	
	path_rom_in = args[0]
	path_strings_in = args[1]
	path_regions_in = args[2]
	path_rom_out = args[3]
	
	if REPACK_FOR_PATCHED:
		print("Using alternate control codes and placeholders for patch")
	
	if not check_files(exist=[path_rom_in, path_strings_in, path_regions_in], noexist=[path_rom_out]):
		return
	
	with open(path_rom_in, "rb") as f:
		data = f.read()
	if not validate_rom(data):
		return
	
	newdata = bytearray(data)
	
	strings = [] # (origin, text_data, need_len, [pointers])
	string_data_needed = 0
	pointers_to_change = 0
	with open(path_strings_in, newline="", encoding="utf-8") as f:
		cr = csv.DictReader(csv_decomment(f), restval="", delimiter=",", quotechar='"')
		for row in cr:
			if not row["origin"]:
				continue
			origin = int(row["origin"], 16)
			
			if "text_translated" in cr.fieldnames:
				text = row["text_translated"] or row["text_original"]
			else:
				text = row["text_trans_dialogwidth"] or row["text_trans_bookwidth"] or row["text_trans_printwidth"] or row["text_original"]
			
			if not text:
				continue
			
			text = text.replace("\xA0", " ")
			if not CSV_IGNORE_NEWLINES:
				text = text.replace("\n", "{nl}")
			
			pointers = []
			for p in row["pointers"].split(";"):
				pn = int(p, 16)
				if pn in VALID_POINTERS:
					pointers.append(pn-ROM_BASE)
				else:
					print(f"Warning: pointer \"{p}\" for string at 0x{origin:08X} invalid or out of range.")
			
			text_data = string_unescape(text, REPACK_FOR_PATCHED).encode("shift-jis") + b"\x00"
			need_len = len(text_data)
			string_data_needed += need_len
			pointers_to_change += len(pointers)
			strings.append( (origin, text_data, need_len, pointers) )
	
	print(f"Found {pointers_to_change:d} pointers to update")
	
	regions = []
	available_bytes = 0
	with open(path_regions_in, newline="", encoding="utf-8") as f:
		cr = csv.DictReader(csv_decomment(f), restval="", delimiter=",", quotechar='"')
		for row in cr:
			start = int(row["start"], 16)
			length = int(row["length"])
			regions.append( (start, length) )
			available_bytes += length
	
	print(f"New strings take up {string_data_needed:d} bytes, space available {available_bytes:d} bytes")
	if string_data_needed > available_bytes:
		print("Not enough space! Shorten strings or add more regions")
		return
	
	# Try fit the data into the regions with the chosen fitting algorithm
	FIT_FIRST = True # first-fit, otherwise best-fit
	FIT_DECREASING = True # decreasing (length), otherwise source order
	if FIT_DECREASING:
		strings.sort(key=lambda x: x[2], reverse=True)
	for s in strings:
		origin = s[0]
		text_data = s[1]
		need_len = s[2]
		
		# Find best region
		best_region = None
		best_region_index = 0
		best_region_diff = 0
		for i, r in enumerate(regions):
			diff = r[1] - need_len
			if diff < 0:
				continue
			if FIT_FIRST:
				best_region = r
				best_region_index = i
				break
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
		for p in s[3]:
			newdata[p:p+4] = struct.pack(">I", fit_start+ROM_BASE)
		
	print("All strings injected successfully")
	
	# Write the new ROM
	with open(path_rom_out, "wb") as f:
		f.write(bytes(newdata))
		print(f"Wrote injected ROM to {f.name}")

def handle_command():
	commands = {"extract":cmd_extract, "regions":cmd_regions, "inject":cmd_inject}
	prog = sys.argv[0]
	if len(sys.argv) > 1:
		command = sys.argv[1].lower()
		args = sys.argv[2:]
		if command in commands:
			commands[command](args, f"{prog} {command}")
			return
	print(f"Usage: {prog} <{'|'.join(commands.keys())}> ...")

if __name__ == "__main__":
	handle_command()
