import struct, time
import mido

MIDI_DEBUG = True
MIDI_COMPRESS = False

midi_callback_data = None
midi_last_status = None

def run_cmd_midiport(cmd, suffix, args, protocol):
	global midi_callback_data, midi_last_status

	if args == None or len(args) != 1:
		print(f"Syntax: {cmd} <midi port>")
		print_midi_ports(out=False)
		return False

	midi_port_name = find_midi_port(args[0], out=False)
	if midi_port_name == None:
		print(f"Invalid MIDI port \"{midi_name}\"")
		print_midi_ports(out=False)
		return False

	midi_callback_data = {"protocol": protocol}
	midi_last_status = None
	midi_port = mido.open_input(midi_port_name, callback=midi_callback)

	protocol.open_midi_passthru()
	print(f"Passing through MIDI port \"{midi_port_name}\" (Ctrl-C to end)...")

	try:
		while True:
			time.sleep(0.1)
	except KeyboardInterrupt as e:
		pass
	finally:
		midi_port.close()
		time.sleep(0.1)
		protocol.close_midi_passthru()
		print("Stopped MIDI passthrough")
	return True

def midi_callback(msg):
	global midi_callback_data, midi_last_status
	msg_bytes = msg.bin()
	try:
		if midi_callback_data != None:
			protocol = midi_callback_data["protocol"]
			if MIDI_COMPRESS:
				if msg_bytes[0] & 0xF0 == 0x80:
					msg_bytes[0] |= 0x10
					msg_bytes[2] = 0
				new_status = msg_bytes[0]
				if new_status == midi_last_status:
					msg_bytes = msg_bytes[1:]
				if new_status < 0xF8:
					midi_last_status = new_status if new_status < 0xF0 else None
			if MIDI_DEBUG:
				print(" ".join([f"{b:02X}" for b in msg_bytes]))
			protocol.send_midi(msg_bytes)
	except Exception as e:
		print(e)

def find_midi_port(name, out=False):
	midi_ports = mido.get_input_names()
	if out:
		midi_ports = mido.get_output_names()
	try:
		port_num = int(name)
		if port_num < 0 or port_num >= len(midi_ports):
			return None
		return midi_ports[port_num]
	except ValueError:
		for port in midi_ports:
			if port.strip().upper().startswith(name.strip().upper()):
				return port
	return None

def print_midi_ports(out=False):
	print("Available MIDI ports:")
	midi_ports = mido.get_input_names()
	if out:
		midi_ports = mido.get_output_names()
	for num, name in enumerate(midi_ports):
		print(f"{num}: {name}")
