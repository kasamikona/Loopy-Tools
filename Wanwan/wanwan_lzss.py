import io
import struct

# Compressor & decompressor implementation by Kasami (2024)
# For modified LZSS used in "Wanwan Aijou Monogatari" by Alfa System (1995)

def compress(input_data):
	# input_data is bytes or bytearray input
	# returns compressed bytes
	
	input_size = len(input_data)
	output_data = bytearray()
	
	# Set up convenience for writing flag bits
	flags_pointer = 0
	flags_counter = 0
	def _write_flag_bit(b):
		nonlocal output_data, flags_pointer, flags_counter
		if flags_counter&7 == 0:
			flags_counter = 0
			flags_pointer = len(output_data)
			output_data.append(0)
		if b:
			output_data[flags_pointer] |= 1 << flags_counter
		flags_counter += 1
	
	input_ptr = 0
	while input_ptr < input_size:
		match_len = 0
		match_offset = 0
		available_length = min(input_size-input_ptr, 257)
		available_offset = min(input_ptr, 4096)
		
		# Find the longest possible match in valid search window, biased to nearest (rfind)
		# being careful not to start any further along than previous character
		if input_ptr > 0 and available_length >= 2:
			for try_len in range(2, available_length+1):
				try_match = input_data[input_ptr:input_ptr+try_len]
				match_index = input_data.rfind(try_match, input_ptr-available_offset, input_ptr+try_len-1)
				if match_index == -1:
					break
				try_offset = input_ptr-match_index
				
				# Exclude short&far matches that can't be encoded, but keep searching
				if try_len > 2 or try_offset <= 64:
					match_len = try_len
					match_offset = try_offset
		
		# Encode the result with Wanwan's encoding
		if match_len > 0:
			input_ptr += match_len
			# Emit copy codes for the match
			_write_flag_bit(0)
			if match_offset <= 64 and match_len >= 2 and match_len <= 5:
				# Short copy
				_write_flag_bit(1)
				out_o = -match_offset+64
				out_c = match_len-2
				output_data.append(out_c<<6 | out_o)
			elif match_offset <= 4096 and match_len >= 3 and match_len <= 257:
				# Long copy
				_write_flag_bit(0)
				out_o = -match_offset+4096
				out_c = match_len-2
				if match_len <= 17:
					# Non-extended
					output_data.append(out_c<<4 | out_o>>8)
					output_data.append(out_o&255)
				else:
					# Extended
					output_data.append(0 | out_o>>8)
					output_data.append(out_o&255)
					output_data.append(out_c&255)
			else:
				# Search should exclude this case
				assert(False)
		else:
			# Emit literal code for this character
			_write_flag_bit(1)
			output_data.append(input_data[input_ptr])
			input_ptr += 1
	
	# Emit EOF marker (long-extended copy with minimum length)
	_write_flag_bit(0)
	_write_flag_bit(0)
	output_data.append(0x0F)
	output_data.append(0xFF)
	output_data.append(0x00)
	return output_data

def decompress(input_data, debug=False):
	# input_data is a bytes or bytearray, must start with contain the entire data
	# returns uncompressed bytes to proper end, or None if error
	
	output_data = bytearray()
	
	# Create a stream for conveniently reading one byte at a time
	with io.BytesIO(input_data) as input_stream:
		# Set up convenience function for reading flag bits
		flags_counter = 0
		flags_buffer = 0
		def _read_flag_bit():
			nonlocal input_stream, flags_buffer, flags_counter
			if flags_counter == 0:
				flags_buffer = input_stream.read(1)[0]
			flags_counter = (flags_counter-1) & 7
			flag = flags_buffer&1
			flags_buffer >>= 1
			return flag
		
		# Do decompression unless an error occurs
		try:
			while True:
				# Grab another flag bit
				# 0 = copy match
				# 1 = literal byte
				flag_literal = _read_flag_bit()
				if flag_literal:
					b = input_stream.read(1)[0]
					output_data.append(b)
					if debug:
						print(f"{b:02X} ", end="")
				else:
					# Grab another flag bit
					# 0 = long copy
					# 1 = short copy
					flag_shortcopy = _read_flag_bit()
					copy_offset = 0
					copy_count = 0
					if flag_shortcopy:
						# Short copy
						# next byte ccoooooo
						# cc = count 2..5 (encoded 0..3)
						# oooooo = offset -64..-1 (encoded 0..63)
						shortcopy = input_stream.read(1)[0]
						copy_offset = (shortcopy&63)-64
						copy_count = (shortcopy>>6)&3
						if debug:
							print(f"<s/{-copy_offset},{copy_count+2}> ", end="")
					else:
						# Long copy
						# next 2 bytes ccccoooo oooooooo
						# cccc = count 3..17 (encoded 1..15) or extended/EOF (encoded 0)
						# oooooooooooo = offset -4096..-1 (encoded 0..4095)
						longcopy = struct.unpack(">H",input_stream.read(2))[0]
						copy_offset = (longcopy&4095)-4096
						copy_count = (longcopy>>12)&15
						if copy_count == 0:
							# Extended count or EOF
							# next byte = count 3..257 (encoded 1..255) or EOF (encoded 0)
							copy_count = input_stream.read(1)[0]
							if copy_count == 0:
								if debug:
									print(f"<eof>")
								break
						if debug:
							print(f"<l/{-copy_offset},{copy_count+2}> ", end="")
					for i in range(copy_count+2):
						output_data.append(output_data[copy_offset:][0])
		except IndexError:
			print("Decompression error")
			return None
	return output_data

def run_self_test(benchmark_only=False):
	test_lengths = [0, -1, 100, 1000, 5000]
	test_repeats = 10
	random_range = 10
	import random
	rng = random.Random()
	#rng.seed(1234)
	def _hexstr(b):
		return " ".join([f"{x:02X}" for x in b])
	if not benchmark_only:
		print("Running round-trip tests")
		for tl in test_lengths:
			if tl > 0:
				print(f"Testing {tl} random bytes with range {random_range}")
			elif tl == 0:
				print(f"Testing empty input")
			else:
				print(f"Testing 256 unique bytes with random offset")
			reps = test_repeats if (tl != 0) else 1
			for tr in range(reps):
				x = bytes()
				if tl > 0:
					x = bytes([rng.randint(0, random_range-1) for k in range(tl)])
				elif tl < 0:
					ro = rng.randint(0, 256)
					x = bytes([(i+ro)&255 for i in range(256)])
				y = ww_lzss_compress(x)
				if y == None:
					print("X:"+_hexstr(x))
					print("Failed to compress the above data")
					return
				z = ww_lzss_decompress(y)
				if z == None:
					print("X:"+_hexstr(x))
					print("Y:"+_hexstr(y))
					print("Failed to decompress the above data")
					return
				if x != z:
					print("X:"+_hexstr(x))
					print("Failed to round-trip the above data")
					return
				print(f"{len(x)} -> {len(y)} -> {len(z)} PASS")
		print("All tests passed")
	benchmark_length = 256*224+2
	benchmark_repeats = 5
	import time, math
	sum_time_compress = 0
	sum_time_decompress = 0
	sum_ratio = 0
	print(f"Benchmarking {benchmark_length} random bytes with range {random_range}")
	for tr in range(benchmark_repeats):
		print(f"Run {tr+1}...")
		x = bytes([rng.randint(0, random_range-1) for k in range(benchmark_length)])
		ts = time.time()
		y = ww_lzss_compress(x)
		time_compress = time.time()-ts
		ts = time.time()
		z = ww_lzss_decompress(y)
		time_decompress = time.time()-ts
		ratio = len(y)/len(x)
		sum_time_compress += time_compress
		sum_time_decompress += time_decompress
		sum_ratio += ratio
	comp_ratio = sum_ratio/benchmark_repeats
	comp_time = sum_time_compress/benchmark_repeats
	comp_speed = benchmark_length/comp_time
	decomp_time = sum_time_decompress/benchmark_repeats
	decomp_speed = benchmark_length/decomp_time
	print(f"Average compression ratio: {comp_ratio:.02f}")
	print(f"Average compression time: {comp_time:.03f}s ({round(comp_speed/1024)} KiB/s)")
	print(f"Average decompression time: {decomp_time:.03f}s ({round(decomp_speed/1024)} KiB/s)")

if __name__ == "__main__":
	import sys
	run_self_test(len(sys.argv) > 1)
