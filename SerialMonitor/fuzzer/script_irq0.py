# Fuzzer script for Kasami's Loopy serial monitor

# This script is intended to verify known behavior for IRQ0.
# When run, it should indicate VDP.INTERRUPT_CTRL must be written
# with 0x0082 or a superset of those bits (xxxx xxxx 1xxx xx1x).
# Finding the exact value would be left to the user.

import monitor_addresses as addresses
from monitor_protocol import DataType
import fuzzer.common as common

irq0fuzz_addr_spec = [
	# (name, data_type, count, weight)
#	("VDP.MODE",              DataType.WORD, 1,   10),
	("VDP.TRIGGER",           DataType.WORD, 1,   10),
	("VDP.RASTER_DMA_CTRL",   DataType.WORD, 1,   10),
	("VDP.BM_SCROLLX",        DataType.WORD, 4,   10),
	("VDP.BM_SCROLLY",        DataType.WORD, 4,   10),
	("VDP.BM_POSX",           DataType.WORD, 4,   10),
	("VDP.BM_POSY",           DataType.WORD, 4,   10),
	("VDP.BM_WIDTH",          DataType.WORD, 4,   10),
	("VDP.BM_HEIGHT",         DataType.WORD, 4,   10),
	("VDP.BM_CTRL",           DataType.WORD, 1,   10),
	("VDP.BM_SUBPAL",         DataType.WORD, 1,   10),
	("VDP.BM_COL_LATCH",      DataType.WORD, 4,   10),
	("VDP.BG_CTRL",           DataType.WORD, 1,   10),
	("VDP.BG_SCROLL",         DataType.WORD, 4,   10),
	("VDP.BG_SUBPAL",         DataType.WORD, 2,   10),
	("VDP.OBJ_CTRL",          DataType.WORD, 1,   10),
	("VDP.OBJ_SUBPAL",        DataType.WORD, 2,   10),
	("VDP.CHAR_SPLIT",        DataType.WORD, 1,   10),
	("VDP.BLEND_MODE",        DataType.WORD, 1,   10),
	("VDP.LAYER_CTRL",        DataType.WORD, 1,   10),
	("VDP.SCREEN_CTRL",       DataType.WORD, 1,   10),
#	("VDP.BACKDROP_B",        DataType.WORD, 1,   10),
#	("VDP.BACKDROP_A",        DataType.WORD, 1,   10),
	("VDP.CAPTURE_CTRL",      DataType.WORD, 1,   10),
	("VDP.INTERRUPT_CTRL",    DataType.WORD, 1,   10),
	("VDP.IRQ0_HCMP",         DataType.WORD, 1,   10),
	("VDP.IRQ0_VCMP",         DataType.WORD, 1,   10),
	("VDP.PRINTER_TEMP",      DataType.WORD, 1,   10),
	("VDP.CONTROL_IN",        DataType.WORD, 3,   10),
	("VDP.PRINTER_STATUS",    DataType.WORD, 1,   10),
	("VDP.CONTROL_MOUSE",     DataType.WORD, 2,   10),
	("VDP.CONTROL_OUT",       DataType.WORD, 1,   10),
	("VDP.BM_MEM_CTRL",       DataType.WORD, 1,   10),
	("VDP.BM_FILL_MASK",      DataType.WORD, 1,   10),
	("VDP.BM_FILL_VALUE",     DataType.WORD, 1,   10),
	("VDP.BM_FILL_TRIGGER",   DataType.WORD, 512, 10),
#	("VDP.SOUND_CTRL",        DataType.WORD, 1,   10),
	("VDP.SOUND_EXP_DATA",    DataType.WORD, 1,   10),
	("0x0C05D020",            DataType.WORD, 1,   10),
]

flag_addr = None

def irq0fuzz_setup(protocol):
	global flag_addr

	if not (protocol.check_connection() and protocol.soft_reset()):
		print("Failed to communicate with console")
		return False

	test_baud = 125000
	if protocol.get_baud() != test_baud:
		protocol.set_baud(test_baud)

	if not common.setup_ram_vectable(protocol):
		print("Failed to move vector table")
		return False

	_addr = common.align4(common.MAINCODE_BASE)

	# Create a flag variable in memory
	flag_addr = _addr
	_addr = common.align4(_addr + 2)

	# Patch NMI to clear DMAOR:NMIF so it doesn't crash
	nmi_vec_addr = _addr
	nmi_vec_num = 11
	nmi_vec_code = [
		0x2F16, # mov.l r1,@-r15
		0x2F06, # mov.l r0,@-r15
		0x4F13, # stc.l gbr,@-r15
		0xD105, # mov.l @(ptr_ocpm,pc),r1
		0x411E, # ldc r1,gbr
		0xC524, # mov.w @(0x48,gbr),r0 ;DMAOR
		0xE001, # mov #0x1,r0
		0xC124, # mov.w r0,@(0x48,gbr) ;DMAOR
		0x4F17, # ldc.l @r15+,gbr
		0x60F6, # mov.l @r15+,r0
		0x61F6, # mov.l @r15+,r1
		0x002B, # rte
		0x0009, # _nop
		# pad
		0x0009,
		# ptr_ocpm=
		0x05FF,
		0xFF00
	]
	common.write_opcodes(protocol, nmi_vec_code, nmi_vec_addr)
	_addr = common.align4(_addr + len(nmi_vec_code)*2)
	common.change_vector(protocol, nmi_vec_num, nmi_vec_addr)

	# Set up IRQ0 to write 1 into the flag variable
	irq0_vec_addr = _addr
	irq0_vec_num = 64
	irq0_vec_code = [
		0x2F16, # mov.l r1,@-r15
		0x2F06, # mov.l r0,@-r15
		0xD003, # mov.l @(ptr_flag,pc),r0
		0x0009, # nop
		0xE101, # mov #0x1,r1
		0x2011, # mov.w r1,@r0
		0x60F6, # mov.l @r15+,r0
		0x61F6, # mov.l @r15+,r1
		0x002B, # rte
		0x0009, # _nop
		# ptr_flag=
		common.hiword(flag_addr),
		common.loword(flag_addr)
	]
	common.write_opcodes(protocol, irq0_vec_code, irq0_vec_addr)
	_addr = common.align4(_addr + len(irq0_vec_code)*2)
	common.change_vector(protocol, irq0_vec_num, irq0_vec_addr)

	# Initialize the flag variable to 0
	protocol.write_value(flag_addr, 0, DataType.WORD)

	# Enable pin to trigger interrupt
	# BIOS already configures the pin so we only need to unmask it
	INTC_IPRA = addresses.data_addr("INTC_IPRA", DataType.WORD)
	ipra_val = protocol.read_value(INTC_IPRA, DataType.WORD)
	if ipra_val == None:
		print("Failed to change interrupt priorities")
		return False
	ipra_val |= 0xF000
	protocol.write_value(INTC_IPRA, ipra_val, DataType.WORD)

	return protocol.read_value(flag_addr, DataType.WORD) == 0

def irq0fuzz_check(protocol):
	global flag_addr
	return protocol.read_value(flag_addr, DataType.WORD) != 0

def run(protocol, log_file):
	return common.run_fuzz_reduce(protocol, irq0fuzz_addr_spec, irq0fuzz_setup, irq0fuzz_check, 100000, log_file)

def show_warning():
	print()
	print("This script is intended to verify known behavior for IRQ0.")
	return common.show_default_warning()
