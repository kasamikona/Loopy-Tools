from monitor_util import try_parse_num
from monitor_protocol import DataType

PTR_TYPE  = DataType.LONG

DATA_LABELS = { # label -> (addr, data_len); length in bytes
	## CPU/system memory
	
	"BIOS":  (0x00000000, 0x8000),
	"SRAM":  (0x02000000, None),
	"OCPM":  (0x05FFFE00, 0x200),
	"RAM":   (0x09000000, 0x80000),
	"ROM":   (0x0E000000, None),
	"OCRAM": (0x0F000000, 0x400),

	## VDP

	# VDP Memory
	"VDP.BITMAP_VRAM":       (0x0C000000, 0x20000),
	"VDP.TILE_VRAM":         (0x0C040000, 0x10000),
	"VDP.OAM":               (0x0C050000, 0x200),
	"VDP.PALETTE":           (0x0C051000, 0x200),
	"VDP.CAPTURE_DATA":      (0x0C052000, 0x200),
	# VDP General
	"VDPREGS":               (0x0C058000, 0x4000),
	"VDP.MODE":              (0x0C058000, None),
	"VDP.HCOUNT":            (0x0C058002, None),
	"VDP.VCOUNT":            (0x0C058004, None),
	"VDP.TRIGGER":           (0x0C058006, None),
	"VDP.RASTER_DMA_CTRL":   (0x0C058008, None),
	# Bitmaps
	"VDP.BM_SCROLLX":        (0x0C059000, 8),
	"VDP.BM_SCROLLY":        (0x0C059008, 8),
	"VDP.BM_POSX":           (0x0C059010, 8),
	"VDP.BM_POSY":           (0x0C059018, 8),
	"VDP.BM_WIDTH":          (0x0C059020, 8),
	"VDP.BM_HEIGHT":         (0x0C059028, 8),
	"VDP.BM_CTRL":           (0x0C059030, None),
	"VDP.BM_SUBPAL":         (0x0C059040, None),
	"VDP.BM_COL_LATCH":      (0x0C059050, 8),
	# Backgrounds & Objects
	"VDP.BG_CTRL":           (0x0C05A000, None),
	"VDP.BG_SCROLL":         (0x0C05A002, 8),
	"VDP.BG_SUBPAL":         (0x0C05A00A, 4),
	"VDP.OBJ_CTRL":          (0x0C05A010, None),
	"VDP.OBJ_SUBPAL":        (0x0C05A012, 4),
	"VDP.CHAR_SPLIT":        (0x0C05A020, None),
	# Display
	"VDP.BLEND_MODE":        (0x0C05B000, None),
	"VDP.LAYER_CTRL":        (0x0C05B002, None),
	"VDP.SCREEN_CTRL":       (0x0C05B004, None),
	"VDP.BACKDROP_B":        (0x0C05B006, None),
	"VDP.BACKDROP_A":        (0x0C05B008, None),
	"VDP.CAPTURE_CTRL":      (0x0C05B00A, None),
	# Interrupts
	"VDP.INTERRUPT_CTRL":    (0x0C05C000, None),
	"VDP.IRQ0_HCMP":         (0x0C05C002, None),
	"VDP.IRQ0_VCMP":         (0x0C05C004, None),
	# Controller & Printer
	"VDP.PRINTER_TEMP":      (0x0C05D000, None),
	"VDP.CONTROL_IN":        (0x0C05D010, 6),
	"VDP.UNK5D020":          (0x0C05D020, None),
	"VDP.PRINTER_STATUS":    (0x0C05D030, None),
	"VDP.PRINTER_HEAD_DATA": (0x0C05D040, None),
	"VDP.PRINTER_MOTOR":     (0x0C05D042, None),
	"VDP.PRINTER_HEAD_CTRL": (0x0C05D044, None),
	"VDP.CONTROL_MOUSE":     (0x0C05D050, 4),
	"VDP.CONTROL_OUT":       (0x0C05D054, None),
	# Bitmap VRAM Control
	"VDP.BM_MEM_CTRL":       (0x0C05E000, None),
	"VDP.BM_FILL_MASK":      (0x0C05E002, None),
	"VDP.BM_FILL_VALUE":     (0x0C05E004, None),
	"VDP.BM_FILL_TRIGGER":   (0x0C05F000, 0x400),
	# Advanced Display
	"VDP.SYNC_CALIBRATION":  (0x0C060000, None),
	# Sound & Expansion
	"VDP.SOUND_CTRL":        (0x0C080000, None),
	"VDP.SOUND_EXP_DATA":    (0x0C0A0000, None),

	## CPU OCPM registers

	# Serial Communication Interface (SCI)
	"SCI_SMR0":        (0x05FFFEC0, None),
	"SCI_BRR0":        (0x05FFFEC1, None),
	"SCI_SCR0":        (0x05FFFEC2, None),
	"SCI_TDR0":        (0x05FFFEC3, None),
	"SCI_SSR0":        (0x05FFFEC4, None),
	"SCI_RDR0":        (0x05FFFEC5, None),
	"SCI_SMR1":        (0x05FFFEC8, None),
	"SCI_BRR1":        (0x05FFFEC9, None),
	"SCI_SCR1":        (0x05FFFECA, None),
	"SCI_TDR1":        (0x05FFFECB, None),
	"SCI_SSR1":        (0x05FFFECC, None),
	"SCI_RDR1":        (0x05FFFECD, None),
	# Integrated-Timer Pulse Unit (ITU)
	"ITU_TSTR":        (0x05FFFF00, None),
	"ITU_TSNC":        (0x05FFFF01, None),
	"ITU_TMDR":        (0x05FFFF02, None),
	"ITU_TFCR":        (0x05FFFF03, None),
	"ITU_TCR0":        (0x05FFFF04, None),
	"ITU_TIOR0":       (0x05FFFF05, None),
	"ITU_TIER0":       (0x05FFFF06, None),
	"ITU_TSR0":        (0x05FFFF07, None),
	"ITU_TCNT0":       (0x05FFFF08, None),
	"ITU_GRA0":        (0x05FFFF0A, None),
	"ITU_GRB0":        (0x05FFFF0C, None),
	"ITU_TCR1":        (0x05FFFF0E, None),
	"ITU_TIOR1":       (0x05FFFF0F, None),
	"ITU_TIER1":       (0x05FFFF10, None),
	"ITU_TSR1":        (0x05FFFF11, None),
	"ITU_TCNT1":       (0x05FFFF12, None),
	"ITU_GRA1":        (0x05FFFF14, None),
	"ITU_GRB1":        (0x05FFFF16, None),
	"ITU_TCR2":        (0x05FFFF18, None),
	"ITU_TIOR2":       (0x05FFFF19, None),
	"ITU_TIER2":       (0x05FFFF1A, None),
	"ITU_TSR2":        (0x05FFFF1B, None),
	"ITU_TCNT2":       (0x05FFFF1C, None),
	"ITU_GRA2":        (0x05FFFF1E, None),
	"ITU_GRB2":        (0x05FFFF20, None),
	"ITU_TCR3":        (0x05FFFF22, None),
	"ITU_TIOR3":       (0x05FFFF23, None),
	"ITU_TIER3":       (0x05FFFF24, None),
	"ITU_TSR3":        (0x05FFFF25, None),
	"ITU_TCNT3":       (0x05FFFF26, None),
	"ITU_GRA3":        (0x05FFFF28, None),
	"ITU_GRB3":        (0x05FFFF2A, None),
	"ITU_BRA3":        (0x05FFFF2C, None),
	"ITU_BRB3":        (0x05FFFF2E, None),
	"ITU_TOCR":        (0x05FFFF31, None),
	"ITU_TCR4":        (0x05FFFF32, None),
	"ITU_TIOR4":       (0x05FFFF33, None),
	"ITU_TIER4":       (0x05FFFF34, None),
	"ITU_TSR4":        (0x05FFFF35, None),
	"ITU_TCNT4":       (0x05FFFF36, None),
	"ITU_GRA4":        (0x05FFFF38, None),
	"ITU_GRB4":        (0x05FFFF3A, None),
	"ITU_BRA4":        (0x05FFFF3C, None),
	"ITU_BRB4":        (0x05FFFF3E, None),
	# DMA Controller (DMAC)
	"DMAC_SAR0":       (0x05FFFF40, None),
	"DMAC_DAR0":       (0x05FFFF44, None),
	"DMAC_DMAOR":      (0x05FFFF48, None),
	"DMAC_TCR0":       (0x05FFFF4A, None),
	"DMAC_CHCR0":      (0x05FFFF4E, None),
	"DMAC_SAR1":       (0x05FFFF50, None),
	"DMAC_DAR1":       (0x05FFFF54, None),
	"DMAC_TCR1":       (0x05FFFF5A, None),
	"DMAC_CHCR1":      (0x05FFFF5E, None),
	"DMAC_SAR2":       (0x05FFFF60, None),
	"DMAC_DAR2":       (0x05FFFF64, None),
	"DMAC_TCR2":       (0x05FFFF6A, None),
	"DMAC_CHCR2":      (0x05FFFF6E, None),
	"DMAC_SAR3":       (0x05FFFF70, None),
	"DMAC_DAR3":       (0x05FFFF74, None),
	"DMAC_TCR3":       (0x05FFFF7A, None),
	"DMAC_CHCR3":      (0x05FFFF7E, None),
	# Interrupt Controller (INTC)
	"INTC_IPRA":       (0x05FFFF84, None),
	"INTC_IPRB":       (0x05FFFF86, None),
	"INTC_IPRC":       (0x05FFFF88, None),
	"INTC_IPRD":       (0x05FFFF8A, None),
	"INTC_IPRE":       (0x05FFFF8C, None),
	"INTC_ICR":        (0x05FFFF8E, None),
	# User Break Controller (UBC)
	"UBC_BARH":        (0x05FFFF90, None),
	"UBC_BARL":        (0x05FFFF92, None),
	"UBC_BAMRH":       (0x05FFFF94, None),
	"UBC_BAMRL":       (0x05FFFF96, None),
	"UBC_BBR":         (0x05FFFF98, None),
	# Bus State Controller (BSC)
	"BSC_BCR":         (0x05FFFFA0, None),
	"BSC_WCR1":        (0x05FFFFA2, None),
	"BSC_WCR2":        (0x05FFFFA4, None),
	"BSC_WCR3":        (0x05FFFFA6, None),
	"BSC_DCR":         (0x05FFFFA8, None),
	"BSC_PCR":         (0x05FFFFAA, None),
	"BSC_RCR":         (0x05FFFFAC, None),
	"BSC_RTCSR":       (0x05FFFFAE, None),
	"BSC_RTCNT":       (0x05FFFFB0, None),
	"BSC_RTCOR":       (0x05FFFFB2, None),
	# Watchdog Timer (WDT)
	# These are a *mess*, read the datasheet...
	"WDT_TCSR_TCNT_W": (0x05FFFFB8, None),
	"WDT_TCSR_R":      (0x05FFFFB8, None),
	"WDT_TCNT_R":      (0x05FFFFB9, None),
	"WDT_RSTCSR_W":    (0x05FFFFBA, None),
	"WDT_RSTCSR_R":    (0x05FFFFBB, None),
	# Power-down state
	"PWR_SBYCR":       (0x05FFFFBC, None),
	# Pin Function Controller (PFC) and parallel I/O Ports
	"PFC_PADR":        (0x05FFFFC0, None),
	"PFC_PBDR":        (0x05FFFFC2, None),
	"PFC_PAIOR":       (0x05FFFFC4, None),
	"PFC_PBIOR":       (0x05FFFFC6, None),
	"PFC_PACR1":       (0x05FFFFC8, None),
	"PFC_PACR2":       (0x05FFFFCA, None),
	"PFC_PBCR1":       (0x05FFFFCC, None),
	"PFC_PBCR2":       (0x05FFFFCE, None),
	"PFC_CASCR":       (0x05FFFFEE, None),
	# Programmable Timing Pattern Controller (TPC)
	# Module also uses PBDR, PBCR1, PBCR2
	"TPC_TPMR":        (0x05FFFFF0, None),
	"TPC_TPCR":        (0x05FFFFF1, None),
	"TPC_NDERB":       (0x05FFFFF2, None),
	"TPC_NDERA":       (0x05FFFFF3, None),
	"TPC_NDRB1":       (0x05FFFFF4, None),
	"TPC_NDRA1":       (0x05FFFFF5, None),
	"TPC_NDRB0":       (0x05FFFFF6, None),
	"TPC_NDRA0":       (0x05FFFFF7, None),

}

FUNC_LABELS = { # name -> (addr, num_args, ret_type, long_run)
	# BIOS functions
	"bios_vdpMode":               (0x0668, 2, None,          False),
	"bios_printParts":            (0x06D4, 8, DataType.LONG, True),
	"bios_printDirect":           (0x0FD6, 7, DataType.LONG, True),
	"bios_print15bpp":            (0x101C, 2, DataType.LONG, True),
	"bios_print8bpp":             (0x1064, 3, DataType.LONG, True),
	"bios_getSealType":           (0x115C, 0, DataType.LONG, False),
	"bios_measurePrintTemp":      (0x13B0, 0, DataType.LONG, False),
	"bios_colorInverseGray":      (0x2D68, 1, DataType.WORD, False),
	"bios_valueBlendQuarter":     (0x2DC6, 2, DataType.BYTE, False),
	"bios_colorBlendQuarter":     (0x2DE0, 2, DataType.WORD, False),
	"bios_mulS16":                (0x2E68, 2, DataType.LONG, False),
	"bios_mulU16":                (0x2E72, 2, DataType.LONG, False),
	"bios_divU16":                (0x2E7C, 2, DataType.LONG, False),
	"bios_divS16":                (0x2EA6, 2, DataType.LONG, False),
	"bios_divS32":                (0x2EDE, 2, DataType.LONG, False),
	"bios_drawLine":              (0x37A0, 6, None,          False),
	"bios_initSoundTransmission": (0x613C, 0, None,          False),
	"bios_playBgm":               (0x61A0, 4, None,          False),
	"bios_playSfx":               (0x61B8, 4, None,          False),
	"bios_updateBgm":             (0x6238, 2, None,          False),
	"bios_dma":                   (0x66D0, 2, None,          False),
	"bios_vsyncIfDma":            (0x6A0E, 1, None,          False),
	"bios_vsyncDma":              (0x6A48, 1, None,          False),
	"bios_vsync":                 (0x6A5A, 0, None,          False),
	"bios_soundChannels":         (0x6AC0, 1, None,          False),
	"bios_soundVolume":           (0x6B50, 2, None,          False),
	"bios_soundToggleDemo":       (0x6B86, 0, None,          False),

	# Internal BIOS functions (not meant for direct use)
	"_bios_disablePrinterTimer": (0x15F2, 0, None, False),
	"_bios_movePrinter":         (0x1B76, 2, None, True),
	"_bios_resetPrinter":        (0x1C2C, 0, None, True),

	# Misc
	"cart_init": (0x0E000480, 0, None, False),
}

def data_addr_len(addr_str, data_type):
	# Argument addr_str: address or label as a string
	# Argument data_type: type for alignment and default length
	# Returns: (address, length) or None
	# For array labels, length is array size in bytes.
	# For value labels or raw addresses, length is data_type size in bytes.

	addr_str = addr_str.upper()
	offset = None
	if "+" in addr_str:
		addr_str, offset_str = addr_str.split("+", 1)
		offset = try_parse_num(offset_str, PTR_TYPE.nbits)
		if offset == None:
			return (None, None)
	elif "[" in addr_str and addr_str.endswith("]"):
		addr_str, offset_str = addr_str.split("[", 1)
		offset = try_parse_num(offset_str[:-1], PTR_TYPE.nbits)
		if offset == None:
			return (None, None)
		offset *= data_type.nbytes
	if addr_str in DATA_LABELS:
		label_addr, label_len = DATA_LABELS[addr_str]
		if offset == None:
			if label_len == None:
				return (label_addr, data_type.nbytes)
			return (label_addr, label_len)
		else:
			return (label_addr+offset, data_type.nbytes)

	addr = try_parse_num(addr_str, PTR_TYPE.nbits)
	if addr == None or addr < 0:
		return (None, None)
	if offset != None:
		addr += offset
	return (addr & data_type.addr_mask, data_type.nbytes)

def data_addr(addr_str, data_type):
	# Argument addr_str: address or label as a string
	# Argument data_type: type for alignment
	# Returns: address or None
	addr = data_addr_len(addr_str, data_type)[0]
	return addr

def func(label):
	# Argument label: function label to match
	# Returns: (address, num_args, return_type, long_running) or None
	for fl in FUNC_LABELS:
		if label.upper() == fl.upper():
			return FUNC_LABELS[fl]
	return None

def list_data():
	# dict: label -> (addr, data_len); length in bytes
	return DATA_LABELS

def list_functions():
	# dict: label -> (addr, num_args, ret_type, long_run)
	return FUNC_LABELS
