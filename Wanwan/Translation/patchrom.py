import csv, os, shutil, sys

SKIP_MISMATCH_WHEN_REVERSE = True

def check_files(exist=[], noexist=[]):
	for f in exist:
		if not os.path.exists(f):
			print("Can't open file: "+f)
			return False
	for f in noexist:
		if os.path.exists(f):
			print("File already exists: "+f)
			return False
	return True

def parse_hex_num(s):
	s = s.strip()
	sl = s.lower()
	if sl.startswith("0x"):
		sl = sl[2:]
	elif sl.endswith("h"):
		sl = sl[:-1]
	try:
		return int(sl, 16)
	except ValueError as e:
		raise ValueError(f"Invalid hex numeral {s}")

def parse_hex_bytes(s):
	s = s.strip()
	sl = s.lower().replace("0x", "")
	sl = ''.join([c for c in sl if (c in "0123456789abcdef")])
	try:
		return bytes.fromhex(sl)
	except ValueError as e:
		if len(s) > 16:
			s = s[:16]+"..."
		raise ValueError(f"Invalid hex data {s}")

def parse_bool(s):
	sl = s.lower()
	if sl in ["true", "1", "t", "y", "yes"]:
		return True
	if sl in ["false", "0", "f", "n", "no"]:
		return False
	raise ValueError(f"Invalid boolean value {s}")

def load_patchfile(patchpath, get_all=False):
	if not check_files(exist=[patchpath]):
		return None
	patches = []
	patches_enabled = []
	print("Loading patches")
	with open(patchpath, newline="", encoding="utf-8") as f:
		cr = csv.DictReader(f, restval="", delimiter=",", quotechar='"')
		enabled_state = True
		next_address = 0
		for row in cr:
			addr = None
			try:
				COMMENT_PREFIX = "#"
				ADDR_CONTINUATION_STRS = ['"', "..", "...", "~", "^"]
				enabled = (row.get("enabled") or "").split(COMMENT_PREFIX)[0].strip()
				if enabled != "":
					enabled_state = parse_bool(enabled)
				addr_label = (row.get("address_label") or row.get("address") or "").split(COMMENT_PREFIX)[0].strip()
				if addr_label == "":
					continue
				if addr_label in ADDR_CONTINUATION_STRS:
					addr = next_address
				else:
					addr = parse_hex_num(addr_label)
					next_address = addr
				data_old = parse_hex_bytes((row.get("data_old") or "").split(COMMENT_PREFIX)[0])
				data_new = parse_hex_bytes((row.get("data_new") or "").split(COMMENT_PREFIX)[0])
				if len(data_old) != len(data_new):
					print(f"Data length mismatch for patch at address {addr:X}")
					return None
				if len(data_new) > 0:
					patch = (addr, data_old, data_new, enabled_state)
					patches.append(patch)
					#print(patch)
				next_address = addr + len(data_new)
			except ValueError as e:
				if addr:
					print(f"Value error while parsing patch at address {addr:X}:")
				else:
					print(f"Value error while parsing patchfile line {cr.line_num}:")
				print(e)
				return None
	patches_enabled = [tuple(p[:3]) for p in patches if p[3]]
	print(f"Loaded {len(patches)} patches, of which {len(patches_enabled)} are enabled.")
	return patches if get_all else patches_enabled

def apply_patch(inpath, outpath, patches, in_memory=True, reverse=False, skip_on_mismatch=False):
	if not check_files(exist=[inpath], noexist=[outpath]):
		return False
	expect_size = max([p[0]+len(p[1]) for p in patches])
	if reverse:
		print("Reversing patches")
		patches = [(p[0], p[2], p[1]) for p in patches]
		patches.reverse()
	if in_memory:
		print("Reading input file")
		with open(inpath, "rb") as infile:
			file_data = bytearray(infile.read())
		if len(file_data) < expect_size:
			print("Patch locations exceed file size")
			return False
		print("Applying patches in memory")
		for patch in patches:
			addr, data_old, data_new = patch
			patch_size = len(data_new)
			if bytes(file_data[addr:addr+patch_size]) != data_old:
				if skip_on_mismatch:
					print(f"Data mismatch at address {addr:X}, skipping")
					continue
				else:
					print(f"Data mismatch at address {addr:X}")
					return False
			file_data[addr:addr+patch_size] = data_new
		print("Writing output file")
		with open(outpath, "wb") as outfile:
			outfile.write(file_data)
	else:
		print("Copying output file")
		shutil.copyfile(inpath, outpath)
		if os.path.getsize(outpath) < expect_size:
			print("Patch locations exceed file size")
			return False
		print("Applying patches on disk")
		with open(outpath, "r+b") as outfile:
			for patch in patches:
				addr, data_old, data_new = patch
				patch_size = len(data_new)
				outfile.seek(addr)
				if outfile.read(patch_size) != data_old:
					if skip_on_mismatch:
						print(f"Data mismatch at address {addr:X}, skipping")
						continue
					else:
						print(f"Data mismatch at address {addr:X}")
						return False
				outfile.seek(addr)
				outfile.write(data_new)
	print("Done")
	return True

def main():
	print()
	if len(sys.argv) >= 2:
		cmd = sys.argv[1].lower().strip()
		if cmd in ["patch","unpatch"] and len(sys.argv) == 5:
			inpath, patchpath, outpath = sys.argv[2:]
			patches = load_patchfile(patchpath)
			if not patches:
				return
			in_memory = False
			reverse = (cmd == "unpatch")
			skip_on_mismatch = reverse and SKIP_MISMATCH_WHEN_REVERSE
			success = apply_patch(inpath, outpath, patches, in_memory, reverse, skip_on_mismatch)
			if not success:
				exit(1)
			return
		elif cmd == "validate" and len(sys.argv) == 3:
			patchpath = sys.argv[2]
			print("Validating patchfile")
			if load_patchfile(patchpath, get_all=True):
				print("OK")
			return
	print("Syntax:")
	print(f"{sys.argv[0]} patch <input.bin> <patches.csv> <output.bin>")
	print(f"{sys.argv[0]} unpatch <input.bin> <patches.csv> <output.bin>")
	print(f"{sys.argv[0]} validate <patches.csv>")

if __name__ == "__main__":
	main()
