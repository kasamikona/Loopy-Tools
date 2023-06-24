#!/usr/bin/env python3

import struct, time, sys, os, math, binascii

try:
	import serial, serial.tools.list_ports
except ImportError:
	print("Serial package not found, please run 'pip install pyserial'.")
	exit()

DUMP_CART = True
DUMP_SAVE = True
DUMP_BIOS = False

# Buggy windows/FTDI drivers limit this
MAX_CHUNK_SIZE = 4096
MAX_READ_SIZE = 64

DUMPER_CHECKSUM = 0xA5A5A5A5

MAX_RETRIES = 10
RESYNC_LATENCY = 0.05

ROM_BASE = 0x0E000000

def dump(ser, addr, count, retries=MAX_RETRIES):
	OFFSET_BYTES = 4
	LENGTH_BYTES = 2
	CHECKSUM_BYTES = 4
	HEADER_STRUCT = ">LH"
	CHECKSUM_STRUCT = ">L"
	
	request = struct.pack(HEADER_STRUCT, addr&0xFFFFFFFF, count)

	response = b''
	timedout = False
	ser.write(request)
	while len(response) < (OFFSET_BYTES+LENGTH_BYTES+count+CHECKSUM_BYTES):
		toread = (OFFSET_BYTES+LENGTH_BYTES+count+CHECKSUM_BYTES)-len(response)
		if toread > MAX_READ_SIZE:
			toread = MAX_READ_SIZE
		newdata = ser.read(toread)
		response = response + newdata
		if len(newdata) == 0:
			print("Timed out. Check serial connection.")
			timedout = True
			break

	data = None
	if not timedout:
		header = response[:(OFFSET_BYTES+LENGTH_BYTES)]
		crc = response[-CHECKSUM_BYTES:]
		data = response[(OFFSET_BYTES+LENGTH_BYTES):-CHECKSUM_BYTES]
		
		crc = struct.unpack(CHECKSUM_STRUCT, crc)[0]
		crc_computed = binascii.crc32(data)
		
		if header != request:
			print("Read error (header mismatch). Check serial connection.")
			print(request)
			print(header)
			data = None
		elif len(data) != count:
			print("Read error (length mismatch). Check serial connection.")
			data = None
		elif crc != crc_computed:
			print("Read error (CRC mismatch). Check serial and cart connection.")
			data = None
	
	if data == None:
		if retries > 0:
			print("{0} retries left...".format(retries))
			# decent chance we're out of sync
			time.sleep(1)
			resync(ser)
			return dump(ser, addr, count, retries-1)
		else:
			print("Too many retries, aborting.")
			return None

	return data

def dump_chunks(ser, start, count, file=None):
	totalchunks = math.ceil(count / MAX_CHUNK_SIZE)
	donechunks = 0
	alldata = b""
	start_time = time.time()
	average_time_taken = None
	eta_str = ""
	for addr in range(start, start+count, MAX_CHUNK_SIZE):
		time_start = time.time()
		dlen = min(MAX_CHUNK_SIZE, start+count-addr)
		donechunks += 1
		print("Reading chunk {0} of {1} ({2:08X}) {3}".format(donechunks, totalchunks, addr, eta_str))
		data = dump(ser, addr, dlen)
		time_taken = time.time() - time_start
		if average_time_taken == None:
			average_time_taken = time_taken
		average_time_taken += (time_taken - average_time_taken) / 2
		if totalchunks > 8:
			eta_rem = int((totalchunks - donechunks) * average_time_taken)
			if eta_rem >= 60:
				eta_str = " Remaining ~{0:d}m{1:02d}s".format(eta_rem//60, eta_rem%60)
			else:
				eta_str = " Remaining ~{0:d}s".format(eta_rem)
		if data == None:
			return None
		if file != None:
			file.write(data)
		else:
			alldata = alldata + data
		
	if file == None:
		return alldata

def resync(ser):
	# send individual null bytes until we start receiving data
	for i in range(10):
		ser.write(b"\0")
		time.sleep(RESYNC_LATENCY)
		if ser.in_waiting > 0:
			break
	# then keep discarding data that comes in
	while ser.in_waiting > 0:
		ser.reset_input_buffer()
		time.sleep(RESYNC_LATENCY)
	# now we're in sync again

def romintegrity(data):
	check_start, check_end, check_expect = struct.unpack(">LLL", data[0:12])
	check_start -= ROM_BASE
	check_end -= ROM_BASE
	if check_start < 0 or check_start >= len(data):
		print("ROM has invalid start address!")
		return False
	if check_end < 0 or check_end >= len(data):
		print("ROM has invalid end address!")
		return False
	if check_end < check_start or (check_start&1) != 0 or (check_end&1) != 0:
		print("ROM has invalid start/end addresses!")
	s = 0
	for i in range(check_start, check_end+1, 2):
		s = (s+struct.unpack(">H", data[i:i+2])[0])&0xFFFFFFFF
	print("Computed checksum: {0:08X} ({1})".format(s, "Match" if s == check_expect else "MISMATCH"))
	return s == check_expect

def dump_loopy(ser, name):
	try:
		bios_path = sys.argv[2]+".bios.bin"
		cart_path = sys.argv[2]+".bin"
		save_path = sys.argv[2]+".sav"
		
		if DUMP_BIOS and os.path.exists(bios_path):
			print("Error: {0} already exists".format(bios_path))
			return
		if DUMP_CART and os.path.exists(cart_path):
			print("Error: {0} already exists".format(cart_path))
			return
		if DUMP_SAVE and os.path.exists(save_path):
			print("Error: {0} already exists".format(save_path))
			return
	
		if DUMP_BIOS:
			with open(bios_path, "wb") as dumpfile:
				print("Dumping BIOS to", dumpfile.name)
				dump_chunks(ser, 0, 0x8000, dumpfile)
		
		if not (DUMP_CART or DUMP_SAVE):
			return
	
		print("Reading game header...")
		headerdata = dump(ser, 0x0E000000, 24)
		if headerdata == None:
			return
		gameheader = struct.unpack(">LLLLLL", headerdata)
		vbr,romend,checksum,_,sramstart,sramend = gameheader
		print("VBR:       {0:08X}".format(vbr))
		print("ROMEND:    {0:08X}".format(romend))
		print("CHECKSUM:  {0:08X}".format(checksum))
		print("SRAMSTART: {0:08X}".format(sramstart))
		print("SRAMEND:   {0:08X}".format(sramend))
		
		if vbr < 0x0E000000 or vbr > 0x0E3FFFFF:
			print("Invalid VBR! Check cartridge connection.")
			return
			
		if romend < 0x0E000000 or romend > 0x0E3FFFFF:
			print("Invalid ROMEND! Check cartridge connection.")
			return
			
		if checksum == DUMPER_CHECKSUM:
			print("Checksum looks like dumper cart! Please hot-swap to target cart without resetting.")
			return
		
		if DUMP_SAVE and sramend>sramstart:
			with open(save_path, "wb") as dumpfile:
				print("Dumping SRAM to", dumpfile.name)
				dump_chunks(ser, sramstart, sramend+1-sramstart, dumpfile)
		
		if DUMP_CART:
			with open(cart_path, "wb") as dumpfile:
				print("Dumping ROM to", dumpfile.name)
				dump_chunks(ser, 0x0E000000, romend+2-0x0E000000, dumpfile)
			with open(cart_path, "rb") as checkfile:
				data = checkfile.read()
				if romintegrity(data):
					print("ROM integrity OK! Dump complete.")
				else:
					print("ROM integrity NOT OK! Reinsert cart and try again.")
		
	except KeyboardInterrupt:
		print("Aborted by keyboard interrupt")
		return

if __name__ == "__main__":
	if len(sys.argv) == 3:
		ser = serial.Serial(sys.argv[1],timeout=1,baudrate=38400)
		dump_loopy(ser, sys.argv[2])
		ser.close()
	else:
		print(sys.argv[0], "<port>", "<output name>")
		print("All available serial ports:", ", ".join([d.device for d in serial.tools.list_ports.comports()]))
