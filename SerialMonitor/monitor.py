#!/usr/bin/env python3

# Requires: pyserial, pillow, mido[ports-rtmidi]
# Optional: gnureadline

import sys, shlex

from PIL import Image

from monitor_protocol import Protocol, DataType
from monitor_util import try_parse_num
import monitor_addresses as addresses

ENABLE_DIRECT_MODE = True
CHECK_ON_CONNECT = True

PTR_TYPE  = DataType.LONG
SIZE_TYPE = DataType.LONG
MIN_TYPE  = DataType.BYTE
MAX_TYPE  = DataType.LONG

import monitor_cmd_lowlevel as cmd_low
import monitor_cmd_highlevel as cmd_high
import monitor_cmd_meta as cmd_meta
import monitor_cmd_midi as cmd_midi
import fuzzer.cmd_fuzz as cmd_fuzz

cmd_map = {
	"read":       (cmd_low.run_cmd_read_nbit,   ["8","16","32"], "Read a single address and print the value"),
	"write":      (cmd_low.run_cmd_write_nbit,  ["8","16","32"], "Write a value to a single address"),
	"fread":      (cmd_low.run_cmd_fread_nbit,  ["8","16","32"], "Read a range of memory to a local file"),
	"fwrite":     (cmd_low.run_cmd_fwrite_nbit, ["8","16","32"], "Write a range of memory from a local file"),
	"hist":       (cmd_low.run_cmd_hist_nbit,   ["8","16","32"], "Read an address repeatedly and log a histogram (slow)"),
	"call":       (cmd_low.run_cmd_call,        None,            "Call a known function with up to 8 numeric arguments"),
	"labels":     (cmd_meta.run_cmd_labels,     None,            "List labels and sizes for memory addresses/ranges"),
	"listfuncs":  (cmd_meta.run_cmd_listfuncs,  None,            "List known callable functions for the call command"),
	"savestate":  (cmd_high.run_cmd_savestate,  None,            "Save a state file using a template (slow)"),
	"loadstate":  (cmd_high.run_cmd_loadstate,  None,            "Load a state file (slow)"),
	"screencap":  (cmd_high.run_cmd_screencap,  None,            "Capture the current screen contents (slow)"),
	"movemotor":  (cmd_high.run_cmd_movemotor,  None,            "Move the printer motor forward or backward (UNSAFE)"),
	"midiport":   (cmd_midi.run_cmd_midiport,   None,            "Pass through a local MIDI input to the console"),
	"baud":       (cmd_low.run_cmd_baud,        None,            "Change the baud rate (recommended for slow commands)"),
	"reset":      (cmd_low.run_cmd_reset,       None,            "Attempt to reset the console via software"),
	"fuzz":       (cmd_fuzz.run_cmd_fuzz,       None,            "Run fuzzing script (advanced use only)"),
}

def run_cmd_help(cmd, suffix, args, protocol):
	if args == None or len(args) > 1:
		print(f"Syntax: {cmd} [command]")
		return False

	if len(args) == 0:
		help_list = []
		longest = 0
		for cmd_name in cmd_map:
			cmd_func, cmd_suffixes, cmd_help_msg = cmd_map[cmd_name]
			cmd_help_name = cmd_name
			if cmd_suffixes != None:
				cmd_help_name = ",".join([cmd_name+s for s in cmd_suffixes])
			help_list.append( (cmd_help_name, cmd_help_msg) )
			longest = max(longest, len(cmd_help_name))

		help_list.append( ("exit", "Exit the monitor") )
		longest = max(longest, len("exit"))

		print()
		print("Commands:")
		print()
		for help_name, help_msg in help_list:
			print(help_name.ljust(longest) + "  " + help_msg)

		return True

	else:
		matched_cmd, matched_suffix = match_cmd_suffix(args[0])
		if matched_cmd == None:
			print(f"Unknown command \"{args[0]}\"")
			return False

		matched_help_name = matched_cmd
		matched_help_func, matched_suffixes, matched_help_msg = cmd_map[matched_cmd]
		if matched_suffix != None:
			matched_help_name = ",".join([matched_cmd+s for s in matched_suffixes])

		print()
		print(f"{matched_help_name}: {matched_help_msg}")
		matched_help_func(matched_cmd, matched_suffix, None, None)
		return True

cmd_map["help"] = (run_cmd_help, None, "Show a list of commands, or help for a given command")

def match_cmd_suffix(cmd):
	# Normal (untyped) commands
	if cmd.lower() in cmd_map and cmd_map[cmd][1] == None:
		return (cmd.lower(), None)

	# Suffixed (typed) commands
	cmd_base = cmd
	cmd_suffix = ""
	while cmd_base != "":
		cmd_base, cmd_suffix = cmd_base[:-1], cmd_base[-1:] + cmd_suffix
		cmd_base_l = cmd_base.lower()
		if cmd_base != "" and cmd_base_l in cmd_map and cmd_map[cmd_base_l][1] != None:
			if cmd_suffix in cmd_map[cmd_base_l][1]:
				return (cmd_base_l, cmd_suffix)

	return (None, None)

def parse_command(args, protocol):
	if len(args) == 0:
		return False
	cmd = args.pop(0)

	if cmd.lower() == "exit":
		exit()

	cmd, cmd_suffix = match_cmd_suffix(cmd)
	if cmd == None:
		print("Unknown command. Use command \"help\" for a list of commands.")
		return False

	cmd_func = cmd_map[cmd][0]
	return cmd_func(cmd, cmd_suffix, args, protocol)

def main(args, prog):
	protocol = Protocol()
	if (len(args) > 1 and ENABLE_DIRECT_MODE) or len(args) == 1:
		port_name = args[0]
		if not protocol.connect(port_name):
			print(f"Failed to open port {port_name}, check connection.")
			print("Available ports: ", ", ".join(protocol.list_ports()))
			return False
		if CHECK_ON_CONNECT and not protocol.check_connection():
			print("Failed to communicate with console")
			return False
		if len(args) > 1 and ENABLE_DIRECT_MODE:
			try:
				return parse_command(args[1:], protocol)
			except (KeyboardInterrupt, EOFError):
				# this fixed "some dumb error" but I didn't write down what error, so *shrug*
				#print()
				return False
		else:
			print("Use command \"help\" for a list of commands.")
			print()
			if sys.platform.startswith("darwin"):
				try:
					import gnureadline
				except ImportError:
					print("Warning: Package gnureadline missing, interactive functionality may be limited")
					print()
			try:
				while True:
					inp = input("> ")
					parse_command(shlex.split(inp), protocol)
					print()
			except (KeyboardInterrupt, EOFError):
				# this fixed "some dumb error" but I didn't write down what error, so *shrug*
				#print()
				pass
			return True
	else:
		if ENABLE_DIRECT_MODE:
			print(f"Interactive: {prog} <port>")
			print(f"Direct mode: {prog} <port> <command> [command args...]")
			print("Use command \"help\" for a list of commands.")
			print()
		else:
			print(f"Syntax: {prog} <port>")
		print("Available ports: ", ", ".join(protocol.list_ports()))
	return False

if __name__ == "__main__":
	exit(0 if main(sys.argv[1:], sys.argv[0]) else 1)
