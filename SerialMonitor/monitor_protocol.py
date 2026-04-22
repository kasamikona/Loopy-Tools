from enum import Enum
import struct, time
import serial
import serial.tools.list_ports as serial_list_ports

MAX_READ_SIZE = 1024
MAX_WRITE_SIZE = 256
INITIAL_BAUD = 38400
BAUD_CHANGE_DELAY = 0.2
RESET_DELAY = 1.3

CMD_READ8   = 0x01
CMD_READ16  = 0x02
CMD_READ32  = 0x03
CMD_WRITE8  = 0x04
CMD_WRITE16 = 0x05
CMD_WRITE32 = 0x06
CMD_CALL    = 0x07
CMD_MIDI    = 0x08
CMD_BAUD    = 0xFF

class DataType(Enum):
	# (nbits, struct_fmt)
	BYTE = (8,   "{n}B")
	WORD = (16, ">{n}H")
	LONG = (32, ">{n}I")

	@property
	def nbits(self):
		return self.value[0]

	@property
	def nbytes(self):
		return self.value[0] // 8

	@property
	def data_mask(self):
		return (1 << self.value[0]) - 1

	@property
	def addr_mask(self):
		return (-self.value[0] // 8) & 0xFFFFFFFF

	@property
	def signed_min(self):
		return -(1 << (self.value[0] - 1))

	@property
	def signed_max(self):
		return (1 << (self.value[0] - 1)) - 1

	@property
	def unsigned_max(self):
		return (1 << self.value[0]) - 1

	def struct_fmt(self, count=1):
		count = max(1, count)
		return self.value[1].format(n=count)

	@classmethod
	def from_str(cls, s):
		s = s.lower()
		if s in ["8", "byte"]:
			return cls.BYTE
		if s in ["16", "word", "short"]:
			return cls.WORD
		if s in ["32", "long", "int"]:
			return cls.LONG
		raise ValueError("Invalid type string")

	@classmethod
	def from_nbits(cls, nbits):
		if nbits == 8:
			return cls.BYTE
		if nbits == 16:
			return cls.WORD
		if nbits == 32:
			return cls.LONG
		raise ValueError("Invalid type bits")

	@classmethod
	def from_nbytes(cls, nbytes):
		return cls.from_nbits(nbytes * 8)

CMD_READ_TYPE = {
	DataType.BYTE: CMD_READ8,
	DataType.WORD: CMD_READ16,
	DataType.LONG: CMD_READ32,
}

CMD_WRITE_TYPE = {
	DataType.BYTE: CMD_WRITE8,
	DataType.WORD: CMD_WRITE16,
	DataType.LONG: CMD_WRITE32,
}

class Protocol:
	def __init__(self):
		self.serial = None
		self.is_midi_passthru = False

	@property
	def is_connected(self):
		return self.serial != None and self.serial.is_open

	def connect(self, port_name, baud=None):
		if self.is_connected:
			raise ValueError("Port already open")

		self.is_midi_passthru = False
		if baud == None:
			baud = INITIAL_BAUD
		try:
			self.serial = serial.Serial(port_name, timeout=1, baudrate=baud)
			time.sleep(0.1)
			self.flush_in()
		except serial.SerialException:
			self.serial = None
			return False
		return True

	def disconnect(self):
		if self.is_connected:
			self.serial.close()
		self.serial = None

	def list_ports(self):
		return [d.device for d in serial_list_ports.comports()]

	def set_baud(self, baud, tell=True):
		if not self.is_connected:
			raise ValueError("Port not open")

		# Change without telling first to check if rate is fine
		baud_was = self.serial.baudrate
		try:
			self.serial.baudrate = baud
			self.serial.baudrate = baud_was
		except serial.SerialException:
			print("Serial adapter error. Rate unchanged.")
			self.serial.baudrate = baud_was
			return False
		time.sleep(BAUD_CHANGE_DELAY)

		if tell:
			self.serial.write(struct.pack(">BI", CMD_BAUD, baud))
		self.flush_out()

		time.sleep(BAUD_CHANGE_DELAY)
		self.serial.baudrate = baud

	def reset_baud(self, tell=True):
		self.set_baud(baud=INITIAL_BAUD, tell=tell)

	def get_baud(self):
		if not self.is_connected:
			raise ValueError("Port not open")

		return self.serial.baudrate

	def get_default_baud(self):
		return INITIAL_BAUD

	def flush_in(self):
		if not self.is_connected:
			raise ValueError("Port not open")

		time.sleep(0.01)
		self.serial.reset_input_buffer()
		self.serial.read_all()

	def flush_out(self):
		if not self.is_connected:
			raise ValueError("Port not open")

		self.serial.flush()

	def read_bytes(self, address, count, data_type):
		if self.serial == None or not self.serial.is_open:
			raise ValueError("Port not open")
		if self.is_midi_passthru:
			raise ValueError("Currently in MIDI passthrough mode")

		if not isinstance(data_type, DataType):
			raise ValueError("Invalid data type")

		address &= data_type.addr_mask
		command_byte = CMD_READ_TYPE[data_type]

		split_count = MAX_READ_SIZE // data_type.nbytes
		dat = bytearray()
		for offset in range(0, count, split_count):
			part_count = min(count - offset, split_count)
			self.serial.write(struct.pack(">BIH", command_byte, address+(offset*data_type.nbytes), part_count-1))
			part_dat = self.serial.read(part_count*data_type.nbytes)
			if len(part_dat) < part_count*data_type.nbytes:
				#print("Timed out")
				return None
			dat.extend(part_dat)
		return bytes(dat)

	def write_bytes(self, address, data, data_type):
		if self.serial == None or not self.serial.is_open:
			raise ValueError("Port not open")
		if self.is_midi_passthru:
			raise ValueError("Currently in MIDI passthrough mode")

		if not isinstance(data_type, DataType):
			raise ValueError("Invalid data type")

		address &= data_type.addr_mask
		command_byte = CMD_WRITE_TYPE[data_type]

		count = len(data) // data_type.nbytes
		data = data[:count*data_type.nbytes]

		split_count = MAX_WRITE_SIZE // data_type.nbytes
		for offset in range(0, count, split_count):
			part_count = min(count - offset, split_count)
			part_data = data[(offset*data_type.nbytes):((offset+part_count)*data_type.nbytes)]
			self.serial.write(struct.pack(">BIH", command_byte, address+(offset*data_type.nbytes), part_count-1))
			self.serial.write(part_data)

	def read_value(self, address, data_type):
		if not isinstance(data_type, DataType):
			raise ValueError("Invalid data type")

		b = self.read_bytes(address, 1, data_type)
		if b == None:
			return None
		return struct.unpack(data_type.struct_fmt(1), b)[0]

	def write_value(self, address, value, data_type):
		if not isinstance(data_type, DataType):
			raise ValueError("Invalid data type")

		b = struct.pack(data_type.struct_fmt(1), value & data_type.data_mask)
		self.write_bytes(address, b, data_type)

	def read_to_stream(self, address, count, data_type, stream):
		if not isinstance(data_type, DataType):
			raise ValueError("Invalid data type")

		max_count = MAX_READ_SIZE // data_type.nbytes
		i = 0
		while i < count:
			c_count = min(max_count, count - i)
			c_dat = self.read_bytes(address, c_count, data_type)
			if c_dat == None:
				return False
			i += c_count
			address += c_count * data_type.nbytes
			stream.write(c_dat)
		return True

	def write_from_stream(self, address, count, data_type, stream):
		if not isinstance(data_type, DataType):
			raise ValueError("Invalid data type")

		max_count = MAX_WRITE_SIZE // data_type.nbytes
		i = 0
		while i < count:
			c_count = min(max_count, count - i)
			c_dat = stream.read(c_count * data_type.nbytes)
			if len(c_dat) < c_count * data_type.nbytes:
				return False
			#if type(c_dat) != bytes:
			#	c_dat = bytes(c_dat, "ascii")
			self.write_bytes(address, c_dat, data_type)
			i += c_count
			address += c_count * data_type.nbytes
		return True

	def open_midi_passthru(self):
		if self.serial == None or not self.serial.is_open:
			raise ValueError("Port not open")
		if self.is_midi_passthru:
			raise ValueError("Already in MIDI passthrough mode")

		self.serial.write(struct.pack("B", CMD_MIDI))
		self.is_midi_passthru = True

	def close_midi_passthru(self):
		if self.serial == None or not self.serial.is_open:
			raise ValueError("Port not open")
		if not self.is_midi_passthru:
			raise ValueError("Not in MIDI passthrough mode")

		self.serial.write(b"\xFF")
		self.is_midi_passthru = False

	def send_midi(self, data):
		if self.serial == None or not self.serial.is_open:
			raise ValueError("Port not open")
		if not self.is_midi_passthru:
			raise ValueError("Not in MIDI passthrough mode")

		data = bytes(data)
		data = [x for x in data if x != b"\xFF"]
		while len(data) > 0:
			chunk = data[:254]
			data = data[254:]
			self.serial.write(struct.pack("B", len(chunk)-1))
			self.serial.write(chunk)
			self.flush_out()

	def call_function(self, addr, args, ret_type, timeout=None):
		if self.serial == None or not self.serial.is_open:
			raise ValueError("Port not open")

		# If timeout is zero or None, wait forever
		# If timeout is negative, use current timeout
		timeout_was = self.serial.timeout
		wait_forever = False
		if timeout == None or timeout == 0:
			timeout = 0
			wait_forever = True
		elif timeout < 0:
			timeout = timeout_was

		self.flush_out()
		self.flush_in()
		self.serial.write(struct.pack(">BIB", CMD_CALL, addr, len(args)))
		for arg in args:
			self.serial.write(struct.pack(f">I", arg&0xFFFFFFFF))

		ret_data = b""
		try:
			# Loop with short timeout so Ctrl-C can be caught
			# If given timeout is negative, loop forever
			time_start = time.time()
			self.serial.timeout = 0.2
			while wait_forever or time.time() <= time_start + timeout:
				ret_data += self.serial.read(4)
				if len(ret_data) >= 4:
					break
			self.serial.timeout = timeout_was
		except Exception as e:
			self.serial.timeout = timeout_was
			raise e

		if len(ret_data) < 4:
			return None

		if ret_type == None:
			return 0
		return struct.unpack(">I", ret_data)[0] & ret_type.data_mask

	def soft_reset(self):
		if not self.is_connected:
			raise ValueError("Port not open")

		WDT_TCSR_TCNT_W = 0x5FFFFB8
		WDT_RSTCSR_W    = 0x5FFFFBA

		# Set up the watchdog to immediately reset the console
		self.write_value(WDT_TCSR_TCNT_W, 0xA500, DataType.WORD) # disable watchdog & clear counter
		self.write_value(WDT_RSTCSR_W,    0x5A40, DataType.WORD) # enable system reset, power-on reset type
		self.write_value(WDT_TCSR_TCNT_W, 0xA560, DataType.WORD) # enable watchdog, fastest clock

		# Set to default baud rate
		baud_old = self.get_baud()
		self.reset_baud(tell=False)
		baud_changed = (baud_old != self.get_baud())

		# Wait for finish rebooting
		time.sleep(RESET_DELAY)
		comm_check = self.read_value(0, DataType.BYTE)
		if comm_check == None:
			return False

		# Set back to previous baud rate
		self.set_baud(baud_old)

		return True
