group = 1
firstcode = 0x21
lastcode = 0x7E

fullhex = "０１２３４５６７８９ＡＢＣＤＥＦ"

out = b""

j1 = group+32

s1 = (j1+1)//2 + 112
if j1 >= 95:
	s1 += 176-112

for j2 in range(firstcode, lastcode+1):
	codetxt = fullhex[j1&15]+fullhex[j2>>4]+fullhex[j2&15]
	out += codetxt.encode("shift-jis")
	s2 = j2
	s2 = 0x23
	if (j1&1) == 1:
		s2 += 31 + s2//96
	else:
		s1 += 126
	out += bytes([s1, s2])
	
	m = ((j2-firstcode) % 6)
	if j2 == lastcode:
		out += b"k"
	elif m == 5:
		out += b"kn@"
	elif m == 1 or m == 3:
		out += b"n"
	else:
		out += "　".encode("shift-jis")

with open("wanwan_chars_{0:02x}.txt".format(j1), "wb") as f:
	f.write(out)