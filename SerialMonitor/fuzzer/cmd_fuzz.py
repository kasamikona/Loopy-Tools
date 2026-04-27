import importlib

import fuzzer.common

def run_cmd_fuzz(cmd, suffix, args, protocol):
	if args == None or not (len(args) == 2 or (len(args) == 3 and args[2].lower() == "accept")):
		print(f"Syntax: {cmd} <script> <log.txt>")
		print("Advanced use only")
		return False

	script_arg = args[0].lower()
	logfile_arg = args[1]
	skip_warning = len(args) == 3

	if logfile_arg.startswith("!"):
		logfile_arg = logfile_arg[1:]
	elif os.path.exists(logfile_arg):
		print(f"File {logfile_arg} already exists. Prefix with ! to overwrite.")
		return False

	try:
		script_module = importlib.import_module(f"fuzzer.script_{script_arg}")
		if not skip_warning:
			try:
				show_warning = script_module.show_warning
			except AttributeError:
				show_warning = fuzzer.common.show_default_warning
			if show_warning() == False:
				return False
		with open(logfile_arg, "w") as logfile:
			print(f"Logging to file {logfile_arg}")
			return script_module.run(protocol, logfile)
	except ImportError as e:
		print("Unknown fuzzer script")
		print(e)
	except KeyboardInterrupt:
		print("Aborted")

	return False
