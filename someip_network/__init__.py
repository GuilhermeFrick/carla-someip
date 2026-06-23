SOMEIP_HOST     = '0.0.0.0'
SOMEIP_PORT     = 30490          # SOME/IP-SD standard port
BRIDGE_HOST     = '0.0.0.0'
BRIDGE_PORT     = 5000           # TCP bridge from Windows CARLA

# Service IDs
SERVICE_DYNAMICS = 0x1001
SERVICE_GNSS     = 0x1002
SERVICE_IMU      = 0x1003
SERVICE_LIDAR    = 0x1004
SERVICE_ADAS     = 0x1005

# Method IDs (event notifications)
METHOD_NOTIFY    = 0x8100

# Message types
MSG_NOTIFICATION = 0x02
MSG_REQUEST      = 0x00
MSG_RESPONSE     = 0x80

# Protocol version
PROTO_VERSION    = 0x01
IFACE_VERSION    = 0x01
