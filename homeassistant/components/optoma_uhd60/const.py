"""Constants for the Optoma UHD60 integration."""

from typing import Final

DOMAIN: Final = "optoma_uhd60"

# Configuration
DEFAULT_NAME: Final = "Optoma UHD60"
DEFAULT_PORT: Final = 23

# Telnet communication
TELNET_TIMEOUT: Final = 5
COMMAND_TERMINATOR: Final = "\r"

# Command types
CMD_GET_INPUT: Final = "~00124 1"
CMD_SET_INPUT_HDMI1: Final = "~0012 1"
CMD_SET_INPUT_HDMI2: Final = "~0012 15"
CMD_SET_INPUT_VGA: Final = "~0012 5"

CMD_GET_MAC: Final = "~00555 1"
CMD_GET_SW_VERSION: Final = "~00122 1"
CMD_GET_SERIAL: Final = "~00353 1"
CMD_GET_LAMP_HOURS: Final = "~00108 1"
CMD_GET_MODEL: Final = "~00151 1"

CMD_SET_LAMP_ECO: Final = "~00110 2"
CMD_SET_LAMP_BRIGHT: Final = "~00110 1"
CMD_SET_LAMP_DYNAMIC: Final = "~00110 4"

CMD_SET_BRILLIANT_COLOR: Final = "~0034 {value}"

CMD_GET_DISPLAY_MODE: Final = "~00123 1"
CMD_SET_DISPLAY_CINEMA: Final = "~0020 3"
CMD_SET_DISPLAY_BRIGHT: Final = "~0020 2"
CMD_SET_DISPLAY_FILM: Final = "~0020 11"
CMD_SET_DISPLAY_VIVID: Final = "~0020 16"
CMD_SET_DISPLAY_USER: Final = "~0020 5"
CMD_SET_DISPLAY_HDR: Final = "~0020 21"

CMD_RESYNC_HDMI: Final = "~0001 1"

CMD_NAV_UP: Final = "~00140 10"
CMD_NAV_DOWN: Final = "~00140 14"
CMD_NAV_LEFT: Final = "~00140 11"
CMD_NAV_RIGHT: Final = "~00140 13"
CMD_NAV_SELECT: Final = "~00140 12"
CMD_NAV_MENU: Final = "~00140 20"
CMD_NAV_INFO: Final = "~00140 40"

CMD_BRIGHTNESS_INC: Final = "~0046 2"
CMD_BRIGHTNESS_DEC: Final = "~0046 1"
CMD_SET_BRIGHTNESS: Final = "~0021 {value}"
CMD_GET_BRIGHTNESS: Final = "~00125 1"

CMD_CONTRAST_INC: Final = "~0047 2"
CMD_CONTRAST_DEC: Final = "~0047 1"
CMD_SET_CONTRAST: Final = "~0022 {value}"
CMD_GET_CONTRAST: Final = "~00126 1"

# Response codes
RESPONSE_OK: Final = "OK"
RESPONSE_PASS: Final = "P"
RESPONSE_FAIL: Final = "F"

# Input source mappings
INPUT_HDMI1: Final = "hdmi1"
INPUT_HDMI2: Final = "hdmi2"
INPUT_VGA: Final = "vga"

INPUT_SOURCE_MAP: Final = {
    "OK1": INPUT_HDMI1,
    "OK01": INPUT_HDMI1,
    "OK15": INPUT_HDMI2,
    "OK5": INPUT_VGA,
    "OK05": INPUT_VGA,
}

# Display mode mappings
DISPLAY_CINEMA: Final = "cinema"
DISPLAY_BRIGHT: Final = "bright"
DISPLAY_FILM: Final = "film"
DISPLAY_VIVID: Final = "vivid"
DISPLAY_USER: Final = "user"
DISPLAY_HDR: Final = "hdr"

DISPLAY_MODE_MAP: Final = {
    "OK03": DISPLAY_CINEMA,
    "OK02": DISPLAY_BRIGHT,
    "OK11": DISPLAY_FILM,
    "OK14": DISPLAY_VIVID,
    "OK05": DISPLAY_USER,
    "OK21": DISPLAY_HDR,
}

# Lamp modes
LAMP_ECO: Final = "eco"
LAMP_BRIGHT: Final = "bright"
LAMP_DYNAMIC: Final = "dynamic"

# Value ranges
BRIGHTNESS_MIN: Final = -50
BRIGHTNESS_MAX: Final = 50
CONTRAST_MIN: Final = -50
CONTRAST_MAX: Final = 50
BRILLIANT_COLOR_MIN: Final = 1
BRILLIANT_COLOR_MAX: Final = 10
