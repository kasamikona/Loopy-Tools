# Loopy Serial Dumper
This is a dumper tool designed around a lightly-modded Loopy console using a USB-serial adapter and a flash cart.  

## Modding
First, take the top cover off. You will probably be leaving it off, so keep it somewhere safe.
Now remove the cart eject mechanism and the metal shield over the main board and keep them safe too.  

![Serial Mod.png](Serial%20Mod.png)

Referring to the above image, solder the wires and resistor onto vias on the top side of the board,
and connect them to the serial adapter. Do not connect the adapter's power.
If the serial voltage is selectable, set it for 5V.  

If soldering to the vias (which are relatively large and exposed) doesn't work for you,
remove the board and refer to [Serial Mod Underside.png](Serial%20Mod%20Underside.png) to solder on the larger cart connector pins.
Note that the arrangement shown won't fit back in the console,
I recommend soldering the wires the other direction and putting the resistor at the adapter end.  

The resistor isn't strictly necessary but will prevent damage/malfunction if booting certain games that set both used pins to outputs (e.g. Wanwan).
The value isn't critical, I suggest 1K but anything between 470R and 10K should work.
If you know the console will *only* be used for dumping until the mod is removed and you won't accidentally boot a game, you could omit the resistor.  

The console lid needs to be left off so you can pull the cartridge out while it's on.
The power switch mechanism normally locks the cart in place.
Alternatively as a permanent destructive mod you could just cut off the locking tabs.  

## Dumping
Load the dumper ROM onto your flash cart.
The main file `loopydump.bin` is for corrected big-endian cart systems,
if you're using an old revision or EPROM-based cart you may need `loopydump.swap.bin` instead.  

The dumper script requires Python 3 and the `pyserial` package, install it if you don't have it.
If `python` isn't Python 3 on your system, use the appropriate command (e.g. `python3`) instead below.
Run `python loopydump.py` to view serial ports, connect the adapter and run it again to find the right port name.  

Power on the console with the flash cart, and run `python loopydump.py <port> test`,
replacing `<port>` with the port name you found above.
It should read the cart header and identify that the dumper cart is connected.
If all is good, you can delete test.bin and continue.  

Now **without resetting or powering off the console,** remove the flash cart by firmly pulling straight up.
Now insert the target cart you want to dump, again moving vertically and firmly.  

Run `python loopydump.py <port> <name>` and the dumping process will start automatically.
A 2MB game takes around 10 minutes.
It will notify and retry on any errors, try wiggling the cart if it is making bad contact.
Once the dump is complete it will verify whether it is a clean dump, hopefully it is.
If the dump fails, you can remove and reinsert the target cart without resetting,
delete the created files and try again. Existing files won't be overwritten.  

### Example command line
```
>python loopydump.py
loopydump.py <port> <output name>
All available serial ports: COM1
```
(connect adapter and boot the flash cart)
```
>python loopydump.py
loopydump.py <port> <output name>
All available serial ports: COM1, COM7

>python loopydump.py com7 test
...
Checksum looks like dumper cart! Please hot-swap to target cart without resetting.
```
(swap to Wanwan cart)
```
>python loopydump.py com7 wanwan
Reading game header...
...
Dumping SRAM to wanwan.sav
...
Dumping ROM to wanwan.bin
...
Computed checksum: D90FE762 (Match)
ROM integrity OK! Dump complete.
```
