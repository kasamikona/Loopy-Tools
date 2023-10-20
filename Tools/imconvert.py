import sys, struct
from PIL import Image

C_BACKDROP = (0,0,0,64)

if __name__ == "__main__":
	if len(sys.argv)-1 != 6:
		print(f"{sys.argv[0]} <data> <palette> <paloffset> <width> <height> <output>")
	else:
		ndata = sys.argv[1]
		npal = sys.argv[2]
		opal = int(sys.argv[3])
		width = int(sys.argv[4])
		height = int(sys.argv[5])
		nout = sys.argv[6]
		img = Image.new('RGBA', (width,height), color = C_BACKDROP)
		pix = img.load()
		with open(ndata, "rb") as fdata:
			dataraw = fdata.read()
		data = list(struct.unpack_from(f">{width*height}B", dataraw))
		if npal != "@":
			with open(npal, "rb") as fpal:
				palraw = fpal.read(512)
			pal = list(struct.unpack(f">{len(palraw)//2}H", palraw[:len(palraw)&-2]))
			palfull = [0]*256
			for i in range(len(pal)):
				palfull[i+opal] = pal[i]
			pal = palfull
			for i in range(256):
				c = pal[i]
				r = (c>>10)&31
				g = (c>>5)&31
				b = c&31
				pal[i] = ((r*255)//31,(g*255)//31,(b*255)//31,255)
			pal[0] = C_BACKDROP
		else:
			pal = [(x,x,x,255) for x in range(256)]
		for y in range(height):
			for x in range(width):
				p = data[y*width+x]
				pix[x,y] = pal[p]
		img.save(nout)
