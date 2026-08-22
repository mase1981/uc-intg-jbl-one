"""Constants for the JBL One integration."""

# UPnP media-rendering control port (LinkPlay / Harman OEM).
UPNP_PORT = 59152

# mDNS service advertised by JBL One soundbars.
MDNS_SERVICE_TYPE = "_jbl-product._tcp.local."

# Device reachability / power states.
STATE_ON = "ON"
STATE_STANDBY = "STANDBY"
STATE_UNAVAILABLE = "UNAVAILABLE"

# sendAppController key-press strings (verified against the JBL One firmware).
KEY_POWER = "power"
KEY_MUTE = "mute"
KEY_VOLUME_UP = "volumeUp"
KEY_VOLUME_DOWN = "volumeDown"
KEY_PLAY_PAUSE = "musicPlayPause"
KEY_MOMENT = "smart_triger"
KEY_CALIBRATION = "calibration"
KEY_REAR = "keyRear"
KEY_BASS_BOOST = "bassboost"
KEY_ATMOS = "keyAtmosLevel"
KEY_SOURCE_HDMI = "source-hdmi-switch"
KEY_SOURCE_BLUETOOTH = "bluetooth"
KEY_SOURCE_TV = "source-tv"
KEY_SMART_MODE = "surround"

# Selectable source labels -> sendAppController key.
SOURCE_HDMI = "HDMI"
SOURCE_TV = "TV"
SOURCE_BLUETOOTH = "Bluetooth"

SOURCE_KEYS: dict[str, str] = {
    SOURCE_HDMI: KEY_SOURCE_HDMI,
    SOURCE_TV: KEY_SOURCE_TV,
    SOURCE_BLUETOOTH: KEY_SOURCE_BLUETOOTH,
}

# play_medium values (from GetInfoEx) that map back to a friendly source label.
PLAY_MEDIUM_SOURCE_MAP: dict[str, str] = {
    "HDMI": SOURCE_HDMI,
    "TV": SOURCE_TV,
    "OPTICAL": "Optical",
    "ARC": "HDMI ARC",
    "BLUETOOTH": SOURCE_BLUETOOTH,
}

# Attribute values on the device state are truncated to this length before
# being pushed to the Remote (JBL TrackURI can be very long - issue #17).
MAX_ATTR_LEN = 255
