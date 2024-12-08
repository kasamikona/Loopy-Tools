import argparse
import sys, os, struct
from util import parsenum, parsebool

from cmds_resource import *
from cmds_image import *
from cmds_tilesheet import *
from cmds_palette import *
from cmds_metasprite import *

class ArgParserHelpOnError(argparse.ArgumentParser):
	def error(self, message):
		self.print_help()
		print()
		print(f"ERROR: {message}")
		sys.exit(2)

def main(args):
	progname = os.path.basename(args.pop(0))
	
	parser = ArgParserHelpOnError(prog=progname, epilog="Select an action for more help.")
	globalopts = ""
	subparsers = parser.add_subparsers(required=True, metavar="action")
	
	aname = "extract"
	ahelp = "Extract a raw or compressed resource"
	afunc = cmd_extract
	parser_extract = subparsers.add_parser(aname, prog=f"{progname} {aname}", help=ahelp)
	parser_extract.set_defaults(action=afunc)
	parser_extract.add_argument("path_rom_in", metavar="rom.bin", help="Source ROM input path")
	parser_extract.add_argument("res_index", metavar="res_index", help="Resource number to extract", type=parsenum)
	parser_extract.add_argument("path_res_out", metavar="output.bin", help="Resource output path")
	parser_extract.add_argument("-s", "--size", metavar="res_size", dest="res_size", help="Size of the source data", type=parsenum)
	parser_extract.add_argument("-c", "--compressed", metavar="true/false", help="Decompress resource on extraction (default false)", type=parsebool, default=False)
	
	aname = "decode-image"
	ahelp = "Decode an 8bpp image"
	afunc = cmd_decode_image
	parser_dec_image = subparsers.add_parser(aname, prog=f"{progname} {aname}", help=ahelp)
	parser_dec_image.set_defaults(action=afunc)
	parser_dec_image.add_argument("path_res_im_in", metavar="res_image.bin", help="Image resource file path")
	parser_dec_image.add_argument("path_res_pal_in", metavar="res_palette.bin", help="Palette resource file path")
	parser_dec_image.add_argument("path_image_out", metavar="output.png", help="Image output path")
	parser_dec_image.add_argument("-t", "--transparent", metavar="true/false", help="Color 0 is transparent (default false)", dest="transparent", type=parsebool, default=False)
	parser_dec_image.add_argument("-c", "--compressed", metavar="true/false", help="Decompress image resource on load (default true)", dest="compressed", type=parsebool, default=True)
	
	aname = "decode-tiles"
	ahelp = "Decode a 4bpp tilesheet to a sheet image"
	afunc = cmd_decode_tilesheet
	parser_dec_tiles = subparsers.add_parser(aname, prog=f"{progname} {aname}", help=ahelp)
	parser_dec_tiles.set_defaults(action=afunc)
	parser_dec_tiles.add_argument("path_res_tiles_in", metavar="res_tiles", help="Tilesheet resource file path (decompressed)")
	parser_dec_tiles.add_argument("path_res_pal_in", metavar="res_palette", help="Palette resource file path")
	parser_dec_tiles.add_argument("path_image_out", metavar="output.png", help="Sheet image output path")
	parser_dec_tiles.add_argument("-t", "--transparent", metavar="true/false", help="Color 0 is transparent (default true)", dest="transparent", type=parsebool, default=True)
	parser_dec_tiles.add_argument("-c", "--compressed", metavar="true/false", help="Decompress tilesheet resource on load (default true)", dest="compressed", type=parsebool, default=True)
	parser_dec_tiles.add_argument("-s", "--subpalette", metavar="subpal", help="Subpalette index (default 0)", dest="subpalette", type=parsenum, default=0)

	aname = "decode-palette"
	ahelp = "Decode a palette to a grid image"
	afunc = cmd_decode_palette
	parser_dec_pal = subparsers.add_parser(aname, prog=f"{progname} {aname}", help=ahelp)
	parser_dec_pal.set_defaults(action=afunc)
	parser_dec_pal.add_argument("path_pal_in", metavar="res_palette.bin", help="Palette resource file path")
	parser_dec_pal.add_argument("path_image_out", metavar="output.png", help="Palette grid image output path")
	
	aname = "decode-metasprite"
	ahelp = "Decode a metasprite to a text representation"
	afunc = cmd_decode_metasprite
	parser_dec_msp = subparsers.add_parser(aname, prog=f"{progname} {aname}", help=ahelp)
	parser_dec_msp.set_defaults(action=afunc)
	parser_dec_msp.add_argument("path_metasprite_in", metavar="res_metasprite.bin", help="Metasprite resource file path")
	parser_dec_msp.add_argument("path_text_out", metavar="output.txt", help="Text output path")
	
	parsed_args = parser.parse_args(args)
	parsed_args.action(parsed_args)

if __name__ == "__main__":
	main(sys.argv)
