#include "loopy.h"
#include "serial.h"
#include "music_data.h"

bool gamepadActive = false;
bool mouseControlMode = false;
uint32_t pressedButtons = 0;
uint32_t heldButtons = 0;

struct soundstate_t soundState;

void setupSystem() {
	// Turn off all video output
	VDP.SCREENPRIO = 0;
	VDP.BACKDROP_A = 0;
	VDP.BACKDROP_B = 0;

	// Turn off controller input
	bios_vdpMode(CONTROL_MODE_NONE, 0);

	// Setup sound hardware (takes a few frames)
	bios_soundChannels(SOUND_CHANS_4CH);
	bios_soundVolume(SOUND_VOL_CH2_3, SOUND_VOL_100);
	bios_soundVolume(SOUND_VOL_CH4,   SOUND_VOL_100);
	bios_initSoundTransmission();

	// Check mouse presence and set control mode accordingly
	// Requires that controller input was turned off for the last few frames
	mouseControlMode = (MOUSE_DET != 0);

	// Enable interrupts and DMA for music
	sys_setInterruptPriority(INT_PRIO_ITU0, 0xF);
	sys_setInterruptMask(0xE);
	sys_setDmaEnabled(true);
}

void showGraphics() {
	bios_vsync();
	// Fill a 256x224 area with a 16x15 grid of colors 1-240
	for(uint16_t y = 0; y < 224; y++) {
		uint16_t gradY = bios_mathDivU16(y, 15);
		for(uint16_t x = 0; x < 256; x++) {
			uint16_t gradX = x / 16;
			VDP.BITMAP_VRAM_8BIT[(y*256)+x] = gradY * 16 + gradX + 1;
		}
	}

	// Create a 2D gradient in colors 1-240
	for(int j = 1; j <= 240; j++) {
		int gradX = (j-1) % 16;
		int gradY = (j-1) / 16;
		VDP.PALETTE[j] = RGB555(gradX*2+1, gradY*2+1, 0);
	}

	// Set up registers to display BM0 full screen
	VDP.BACKDROP_A      = 0;
	VDP.BACKDROP_B      = 0;
	VDP.BLEND           = BLEND_MATH;
	VDP.BM_SCROLLX[0]   = 0;
	VDP.BM_SCROLLY[0]   = 0;
	VDP.BM_SCREENX[0]   = 0;
	VDP.BM_SCREENY[0]   = 0;
	VDP.BM_WIDTH[0]     = 256-1;
	VDP.BM_HEIGHT[0]    = 224-1;
	VDP.BM_CTRL         = BM_MODE_8BPP_SHARED;
	VDP.BM_SUBPAL       = BM_SUBPAL(0,0,0,0);
	VDP.BM_COL_LATCH[0] = 0;
	VDP.SCREENPRIO      = BLEND_MATH_ADD | SCREEN_A_ENABLE | PRIORITY_BM_A | PRIORITY_BG0_A | PRIORITY_OBJ0_A;
	VDP.LAYER_CTRL      = LAYER_SCREEN(LAYER_SCREEN_A, LAYER_SCREEN_A, LAYER_SCREEN_A, LAYER_SCREEN_A) | LAYER_ENABLE_BM0;
}

int main() {
	// Initialize the hardware and system state, and check controller mode
	setupSystem();

	// Print a hellorld message on the serial port
	serial_begin(9600);
	serial_print("Casio Loopy says hello world\r\n");

	// Set the appropriate controller scanning mode and video height
	bios_vdpMode(mouseControlMode ? CONTROL_MODE_MOUSE : CONTROL_MODE_GAMEPAD, VIDEO_HEIGHT_224P);

	// Display some graphics on the BM0 layer and set a backdrop
	showGraphics();
	VDP.BACKDROP_A = mouseControlMode ? RGB555(0,15,31) : RGB555(0,0,31);

	// Play some music
	biosvar_autoSoundState = &soundState;
	bios_playBgm(&soundState, 0x80, 0, &data_musicTrackList);

	// Every frame, move the BM0 layer according to gamepad/mouse
	while(1) {
		bios_vsync();

		int16_t moveX = 0;
		int16_t moveY = 0;
		bool resetPos = false;
		if (mouseControlMode) {
			// Get the mouse XY deltas and buttons
			int16_t mouseXB = VDP.IO_MOUSEX;
			int16_t mouseY  = VDP.IO_MOUSEY;

			// Set the motion from XY deltas
			// A scale of 1/2 seems comfortable but may not match other games
			// Convert from 12bit signed using MOUSE_DELTA
			moveX =  MOUSE_DELTA(mouseXB) / 2; // X is +right
			moveY = -MOUSE_DELTA(mouseY)  / 2; // Y is +up so invert it

			// Update button state from mouse buttons
			uint32_t buttonsNow = MOUSE_BUTTONS(mouseXB);
			pressedButtons = buttonsNow & ~heldButtons;
			heldButtons = buttonsNow;

			// Reset position if either mouse button was pressed
			if (pressedButtons & (MOUSE_BTN_LEFT | MOUSE_BTN_RIGHT)) {
				resetPos = true;
			}
		} else {
			// Update button state from gamepad buttons
			uint32_t buttonsNow = READ_GAMEPAD1;
			pressedButtons = buttonsNow & ~heldButtons;
			heldButtons = buttonsNow;

			// Increase speed if the A button is held
			int speed = (heldButtons & GAMEPAD_BTN_A) ? 3 : 1;

			// Set the motion from D-pad directions
			if (heldButtons & GAMEPAD_BTN_LEFT) {
				moveX = -speed;
			} else if (heldButtons & GAMEPAD_BTN_RIGHT) {
				moveX =  speed;
			}
			if(heldButtons & GAMEPAD_BTN_UP) {
				moveY = -speed;
			} else if(heldButtons & GAMEPAD_BTN_DOWN) {
				moveY =  speed;
			}

			// Reset position if the B button was pressed
			if (pressedButtons & GAMEPAD_BTN_B) {
				resetPos = true;
			}

			// Toggle demo music if the D button was pressed
			if (pressedButtons & GAMEPAD_BTN_D) {
				if (sys_bgmRunning()) {
					sys_stopBgm(&soundState);
					while (sys_bgmRunning()) {};
				}
				bios_soundToggleDemo();
			}
		}

		// Apply the motion to the BM0 layer position
		if (resetPos) {
			VDP.BM_SCREENX[0] = 0;
			VDP.BM_SCREENY[0] = 0;
		} else {
			VDP.BM_SCREENX[0] += moveX;
			VDP.BM_SCREENY[0] += moveY;
		}
	}

	return 0;
}
