import io
import struct

ROM_BASE = 0x0E000000
RESOURCES = 0x0E070000
MAX_RESOURCE_LENGTH = 65536

def decompress(compressed, max_length):
	# compressed is bytes or bytearray input, must contain the entire compressed data
	# max_length is limit for decompressed data size
	# returns decompressed bytes to proper end, or None if error
	if max_length <= 0:
		max_length = 1<<20 # 1MB more than enough for "unlimited"
	
	input_ptr = 0
	decompressed = bytearray()
	bitcounter = 0
	flagbits = 0
	copyoffset = 0
	copycount = 0
	with io.BytesIO(compressed) as compressed_stream:
		try:
			while True:
				# Grab another flag bit
				# 0 = copy match
				# 1 = literal byte
				if bitcounter == 0:
					flagbits = compressed_stream.read(1)[0]
				bitcounter = (bitcounter-1) & 7
				flag_literal = flagbits&1
				flagbits >>= 1
				
				if flag_literal:
					decompressed.append(compressed_stream.read(1)[0])
					if len(decompressed) >= max_length:
						print("Decompressed data exceeded max length")
						return None
				else:
					# Grab another flag bit
					# 0 = long copy
					# 1 = short copy
					if bitcounter == 0:
						flagbits = compressed_stream.read(1)[0]
					bitcounter = (bitcounter-1) & 7
					flag_shortcopy = flagbits&1
					flagbits >>= 1
					
					if flag_shortcopy:
						# Short copy
						# next byte ccoooooo
						# cc = count 2..5 (encoded 0..3)
						# oooooo = offset -64..-1 (encoded 0..63)
						shortcopy = compressed_stream.read(1)[0]
						copyoffset = (shortcopy&63)-64
						copycount = (shortcopy>>6)&3
					else:
						# Long copy
						# next 2 bytes ccccoooo oooooooo
						# cccc = count 3..17 (encoded 1..15) or extended/EOF (encoded 0)
						# oooooooooooo = offset -4096..-1 (encoded 0..4095)
						longcopy = struct.unpack(">H",compressed_stream.read(2))[0]
						copyoffset = (longcopy&4095)-4096
						copycount = (longcopy>>12)&15
						if copycount == 0:
							# Extended count or EOF
							# next byte = count 3..257 (encoded 1..255) or EOF (encoded 0)
							copycount = compressed_stream.read(1)[0]
							if copycount == 0:
								break
					for i in range(copycount+2):
						decompressed.append(decompressed[copyoffset:][0])
					if len(decompressed) >= max_length:
						print("Decompressed data exceeded max length")
						return None
		except IndexError:
			print("Decompression error")
			return None
	return decompressed
