#!/usr/bin/env python3

import ctypes, logging, os.path, getopt, sys
from fcntl import ioctl

# ioctl

_IOC_NRBITS = 8
_IOC_TYPEBITS = 8
_IOC_SIZEBITS = 14

_IOC_NRSHIFT = 0
_IOC_TYPESHIFT = _IOC_NRSHIFT + _IOC_NRBITS
_IOC_SIZESHIFT = _IOC_TYPESHIFT + _IOC_TYPEBITS
_IOC_DIRSHIFT = _IOC_SIZESHIFT + _IOC_SIZEBITS

_IOC_WRITE = 1
_IOC_READ  = 2

def _IOC(dir_, type_, nr, size):
    return (
        ctypes.c_int32(dir_ << _IOC_DIRSHIFT).value |
        ctypes.c_int32(ord(type_) << _IOC_TYPESHIFT).value |
        ctypes.c_int32(nr << _IOC_NRSHIFT).value |
        ctypes.c_int32(size << _IOC_SIZESHIFT).value)

def _IOC_TYPECHECK(t):
    return ctypes.sizeof(t)

def _IOR(type_, nr, size):
    return _IOC(_IOC_READ, type_, nr, _IOC_TYPECHECK(size))

def _IOWR(type_, nr, size):
    return _IOC(_IOC_READ | _IOC_WRITE, type_, nr, _IOC_TYPECHECK(size))

#
# ioctl structs, codes for UVC extensions
#
enum = ctypes.c_uint

class v4l2_capability(ctypes.Structure):
    _fields_ = [
        ('driver', ctypes.c_char * 16),
        ('card', ctypes.c_char * 32),
        ('bus_info', ctypes.c_char * 32),
        ('version', ctypes.c_uint32),
        ('capabilities', ctypes.c_uint32),
        ('device_caps', ctypes.c_uint32),
        ('reserved', ctypes.c_uint32 * 3),
    ]

V4L2_CAP_VIDEO_CAPTURE = 0x00000001

# controls

v4l2_ctrl_type = enum
(
    V4L2_CTRL_TYPE_INTEGER,
    V4L2_CTRL_TYPE_BOOLEAN,
    V4L2_CTRL_TYPE_MENU,
    V4L2_CTRL_TYPE_BUTTON,
    V4L2_CTRL_TYPE_INTEGER64,
    V4L2_CTRL_TYPE_CTRL_CLASS,
    V4L2_CTRL_TYPE_STRING,
    V4L2_CTRL_TYPE_BITMASK,
    V4L2_CTRL_TYPE_INTEGER_MENU,
) = range(1, 10)

V4L2_CTRL_FLAG_UPDATE = 0x0008
V4L2_CTRL_FLAG_INACTIVE = 0x0010
V4L2_CTRL_FLAG_NEXT_CTRL = 0x80000000
V4L2_CTRL_FLAG_NEXT_COMPOUND = 0x40000000

V4L2_CTRL_CLASS_USER = 0x00980000
V4L2_CTRL_CLASS_CAMERA = 0x009a0000

V4L2_CID_BASE = V4L2_CTRL_CLASS_USER | 0x900
V4L2_CID_AUTO_WHITE_BALANCE	= V4L2_CID_BASE + 12
V4L2_CID_WHITE_BALANCE_TEMPERATURE = V4L2_CID_BASE + 26

V4L2_CID_CAMERA_CLASS_BASE = V4L2_CTRL_CLASS_CAMERA | 0x900
V4L2_CID_EXPOSURE_AUTO = V4L2_CID_CAMERA_CLASS_BASE + 1
V4L2_CID_FOCUS_AUTO	= V4L2_CID_CAMERA_CLASS_BASE + 12
V4L2_CID_FOCUS_ABSOLUTE = V4L2_CID_CAMERA_CLASS_BASE + 10
V4L2_CID_ISO_SENSITIVITY_AUTO = V4L2_CID_CAMERA_CLASS_BASE + 24

V4L2_CTRL_UPDATERS = [
    V4L2_CID_EXPOSURE_AUTO,
    V4L2_CID_FOCUS_AUTO,
    V4L2_CID_AUTO_WHITE_BALANCE,
    V4L2_CID_ISO_SENSITIVITY_AUTO,
]

V4L2_CTRL_REORDERS = {
    V4L2_CID_FOCUS_AUTO: V4L2_CID_FOCUS_ABSOLUTE,
    V4L2_CID_AUTO_WHITE_BALANCE: V4L2_CID_WHITE_BALANCE_TEMPERATURE,
}

class v4l2_control(ctypes.Structure):
    _fields_ = [
        ('id', ctypes.c_uint32),
        ('value', ctypes.c_int32),
    ]

class v4l2_queryctrl(ctypes.Structure):
    _fields_ = [
        ('id', ctypes.c_uint32),
        ('type', v4l2_ctrl_type),
        ('name', ctypes.c_char * 32),
        ('minimum', ctypes.c_int32),
        ('maximum', ctypes.c_int32),
        ('step', ctypes.c_int32),
        ('default', ctypes.c_int32),
        ('flags', ctypes.c_uint32),
        ('reserved', ctypes.c_uint32 * 2),
    ]

class v4l2_querymenu(ctypes.Structure):
    class _u(ctypes.Union):
        _fields_ = [
            ('name', ctypes.c_char * 32),
            ('value', ctypes.c_int64),
        ]

    _fields_ = [
        ('id', ctypes.c_uint32),
        ('index', ctypes.c_uint32),
        ('_u', _u),
        ('reserved', ctypes.c_uint32),
    ]
    _anonymous_ = ('_u',)
    _pack_ = True

class uvc_xu_control_query(ctypes.Structure):
    _fields_ = [
        ('unit', ctypes.c_uint8),
        ('selector', ctypes.c_uint8),
        ('query', ctypes.c_uint8),      # Video Class-Specific Request Code,
                                        # defined in linux/usb/video.h A.8.
        ('size', ctypes.c_uint16),
        ('data', ctypes.c_void_p),
    ]

VIDIOC_QUERYCAP = _IOR('V', 0, v4l2_capability)
UVCIOC_CTRL_QUERY = _IOWR('u', 0x21, uvc_xu_control_query)
VIDIOC_G_CTRL = _IOWR('V', 27, v4l2_control)
VIDIOC_S_CTRL = _IOWR('V', 28, v4l2_control)
VIDIOC_QUERYCTRL = _IOWR('V', 36, v4l2_queryctrl)
VIDIOC_QUERYMENU = _IOWR('V', 37, v4l2_querymenu)

# A.8. Video Class-Specific Request Codes
UVC_RC_UNDEFINED = 0x00
UVC_SET_CUR      = 0x01
UVC_GET_CUR      = 0x81
UVC_GET_MIN      = 0x82
UVC_GET_MAX      = 0x83
UVC_GET_RES      = 0x84
UVC_GET_LEN      = 0x85
UVC_GET_INFO     = 0x86
UVC_GET_DEF      = 0x87

EU1_SET_ISP = 0x01
EU1_GET_ISP_RESULT = 0x02

# UVC EU1 extension GUID 23e49ed0-1178-4f31-ae52-d2fb8a8d3b48
UVC_EU1_GUID = b'\xd0\x9e\xe4\x23\x78\x11\x31\x4f\xae\x52\xd2\xfb\x8a\x8d\x3b\x48'

# Razer Kiyo Pro specific registers and values

AF_RESPONSIVE = b'\xff\x06\x00\x00\x00\x00\x00\x00'
AF_PASSIVE =    b'\xff\x06\x01\x00\x00\x00\x00\x00'

HDR_OFF =       b'\xff\x02\x00\x00\x00\x00\x00\x00'
HDR_ON =        b'\xff\x02\x01\x00\x00\x00\x00\x00'

HDR_DARK =      b'\xff\x07\x00\x00\x00\x00\x00\x00'
HDR_BRIGHT =    b'\xff\x07\x01\x00\x00\x00\x00\x00'

FOV_WIDE =       b'\xff\x01\x00\x03\x00\x00\x00\x00'
FOV_MEDIUM_PRE = b'\xff\x01\x00\x03\x01\x00\x00\x00'
FOV_MEDIUM =     b'\xff\x01\x01\x03\x01\x00\x00\x00'
FOV_NARROW_PRE = b'\xff\x01\x00\x03\x02\x00\x00\x00'
FOV_NARROW =     b'\xff\x01\x01\x03\x02\x00\x00\x00'

# Unknown yet, the synapse sends it in start
UNKNOWN =       b'\xff\x04\x00\x00\x00\x00\x00\x00'

# save previous values to the camera
SAVE =          b'\xc0\x03\xa8\x00\x00\x00\x00\x00'

LOAD =          b'\x00\x00\x00\x00\x00\x00\x00\x00'

def to_buf(b):
    return ctypes.create_string_buffer(b)

def get_length_xu_control(fd, unit_id, selector):
    length = ctypes.c_uint16(0)

    xu_ctrl_query = uvc_xu_control_query()
    xu_ctrl_query.unit = unit_id
    xu_ctrl_query.selector = selector
    xu_ctrl_query.query = UVC_GET_LEN
    xu_ctrl_query.size = 2 # sizeof(length)
    xu_ctrl_query.data = ctypes.cast(ctypes.pointer(length), ctypes.c_void_p)

    try:
       ioctl(fd, UVCIOC_CTRL_QUERY, xu_ctrl_query)
    except Exception as e:
        logging.warning(f'UVCIOC_CTRL_QUERY (GET_LEN) - Fd: {fd} - Error: {e}')

    return length

def query_xu_control(fd, unit_id, selector, query, data):
    len = get_length_xu_control(fd, unit_id, selector)

    xu_ctrl_query = uvc_xu_control_query()
    xu_ctrl_query.unit = unit_id
    xu_ctrl_query.selector = selector
    xu_ctrl_query.query = query
    xu_ctrl_query.size = len
    xu_ctrl_query.data = ctypes.cast(ctypes.pointer(data), ctypes.c_void_p)

    try:
        ioctl(fd, UVCIOC_CTRL_QUERY, xu_ctrl_query)
    except Exception as e:
        logging.warning(f'UVCIOC_CTRL_QUERY ({query}) - Fd: {fd} - Error: {e}')

# the usb device descriptors file contains the descriptors in a binary format
# the byte before the extension guid is the extension unit id
def find_unit_id_in_sysfs(device, guid):
    if os.path.islink(device):
        device = os.readlink(device)
    device = os.path.basename(device)
    descfile = f'/sys/class/video4linux/{device}/../../../descriptors'
    if not os.path.isfile(descfile):
        return 0

    try:
        with open(descfile, 'rb') as f:
            descriptors = f.read()
            guid_start = descriptors.find(guid)
            if guid_start > 0:
                return descriptors[guid_start - 1]
    except Exception as e:
        logging.warning(f'Failed to read uvc xu unit id from {descfile}: {e}')

    return 0

def find_usb_ids_in_sysfs(device):
    if os.path.islink(device):
        device = os.readlink(device)
    device = os.path.basename(device)
    vendorfile = f'/sys/class/video4linux/{device}/../../../idVendor'
    productfile = f'/sys/class/video4linux/{device}/../../../idProduct'
    if not os.path.isfile(vendorfile) or not os.path.isfile(productfile):
        return ''

    vendor = read_usb_id_from_file(vendorfile)
    product = read_usb_id_from_file(productfile)

    return vendor + ':' + product

def read_usb_id_from_file(file):
    id = ''
    try:
        with open(file, 'r') as f:
            id = f.read().strip()
    except Exception as e:
        logging.warning(f'Failed to read usb id from {file}: {e}')
    return id

def get_device_capabilities(device):
    cap = v4l2_capability()
    try:
        fd = os.open(device, os.O_RDWR, 0)
        ioctl(fd, VIDIOC_QUERYCAP, cap)
        os.close(fd)
    except Exception as e:
        logging.error(f'get_device_capabilities({device}) failed: {e}')

    return cap.device_caps

def find_by_value(menu, value):
    for m in menu:
        if m.value == value:
            return m
    return None

def find_by_text_id(ctrls, text_id):
    for c in ctrls:
        if c.text_id == text_id:
            return c
    return None

def find_idx(ctrls, pred):
    for i, c in enumerate(ctrls):
        if pred(c):
            return i
    return None

class BaseCtrl:
    def __init__(self, text_id, name, type, value = None, default = None, min = None, max = None, step = None, menu = None):
        self.text_id = text_id
        self.name = name
        self.type = type
        self.value = value
        self.default = default
        self.min = min
        self.max = max
        self.step = step
        self.updater = False
        self.inactive = False
        self.menu = menu

class BaseCtrlMenu:
    def __init__(self, text_id, name, value):
        self.text_id = text_id
        self.name = name
        self.value = value

class KiyoCtrl(BaseCtrl):
    def __init__(self, text_id, name, menu):
        super().__init__(text_id, name, 'menu', menu=menu)

class KiyoMenu(BaseCtrlMenu):
    def __init__(self, text_id, name, value, before = None):
        super().__init__(text_id, name, value)
        self._before = before

class KiyoProCtrls:
    KIYO_PRO_USB_ID = '1532:0e05'
    def __init__(self, device, fd):
        self.device = device
        self.fd = fd
        self.unit_id = find_unit_id_in_sysfs(device, UVC_EU1_GUID)
        self.usb_ids = find_usb_ids_in_sysfs(device)
        self.get_device_controls()

    def supported(self):
        return self.unit_id != 0 and self.usb_ids == KiyoProCtrls.KIYO_PRO_USB_ID

    def get_device_controls(self):
        if not self.supported():
            self.ctrls = []
            return

        self.ctrls = [
            KiyoCtrl(
                'kiyo_pro_af_mode',
                'AF Mode',
                [
                    KiyoMenu('passive', 'Passive', AF_PASSIVE),
                    KiyoMenu('responsive', 'Responsive', AF_RESPONSIVE),
                ]
            ),
            KiyoCtrl(
                'kiyo_pro_hdr',
                'HDR',
                [
                    KiyoMenu('off', 'Off', HDR_OFF),
                    KiyoMenu('on', 'On', HDR_ON),
                ]
            ),
            KiyoCtrl(
                'kiyo_pro_hdr_mode',
                'HDR Mode',
                [
                    KiyoMenu('bright', 'Bright', HDR_BRIGHT),
                    KiyoMenu('dark', 'Dark', HDR_DARK),
                ]
            ),
            KiyoCtrl(
                'kiyo_pro_fov',
                'FOV',
                [
                    KiyoMenu('wide', 'Wide', FOV_WIDE),
                    KiyoMenu('medium', 'Medium', FOV_MEDIUM, FOV_MEDIUM_PRE),
                    KiyoMenu('narrow', 'Narrow', FOV_NARROW, FOV_NARROW_PRE),
                ]
            ),
        ]

    def setup_ctrls(self, params):
        if not self.supported():
            return

        for k, v in params.items():
            ctrl = find_by_text_id(self.ctrls, k)
            if ctrl == None:
                continue
            menu = find_by_text_id(ctrl.menu, v)
            if menu == None:
                logging.warning(f'KiyoProCtrls: can\'t find {v} in {[c.text_id for c in ctrl.menu]}')
                continue
            ctrl.value = menu.text_id

            if menu._before:
                query_xu_control(self.fd, self.unit_id, EU1_SET_ISP, UVC_SET_CUR, to_buf(menu._before))

            query_xu_control(self.fd, self.unit_id, EU1_SET_ISP, UVC_SET_CUR, to_buf(menu.value))

        query_xu_control(self.fd, self.unit_id, EU1_SET_ISP, UVC_SET_CUR, to_buf(SAVE))

    def update_ctrls(self):
        return

    def get_ctrls(self):
        return self.ctrls

# Logitech peripheral GUID ffe52d21-8030-4e2c-82d9-f587d00540bd
LOGITECH_PERIPHERAL_GUID = b'\x21\x2d\xe5\xff\x30\x80\x2c\x4e\x82\xd9\xf5\x87\xd0\x05\x40\xbd'

LOGITECH_PERIPHERAL_LED1_SEL = 0x09
LOGITECH_PERIPHERAL_LED1_LEN = 5

LOGITECH_PERIPHERAL_LED1_MODE_OFFSET = 1
LOGITECH_PERIPHERAL_LED1_MODE_OFF =   0x00
LOGITECH_PERIPHERAL_LED1_MODE_ON =    0x01
LOGITECH_PERIPHERAL_LED1_MODE_BLINK = 0x02
LOGITECH_PERIPHERAL_LED1_MODE_AUTO =  0x03

LOGITECH_PERIPHERAL_LED1_FREQUENCY_OFFSET = 3

class LogitechCtrl(BaseCtrl):
    def __init__(self, text_id, name, type, selector, len, offset, menu = None):
        super().__init__(text_id, name, type, menu=menu)
        self._selector = selector
        self._len = len
        self._offset = offset

class LogitechCtrls:
    def __init__(self, device, fd):
        self.device = device
        self.fd = fd
        self.unit_id = find_unit_id_in_sysfs(device, LOGITECH_PERIPHERAL_GUID)

        self.get_device_controls()

    def supported(self):
        return self.unit_id != 0

    def get_device_controls(self):
        if not self.supported():
            self.ctrls = []
            return

        self.ctrls = [
            LogitechCtrl(
                'logitech_led1_mode',
                'LED1 Mode',
                'menu',
                LOGITECH_PERIPHERAL_LED1_SEL,
                LOGITECH_PERIPHERAL_LED1_LEN,
                LOGITECH_PERIPHERAL_LED1_MODE_OFFSET,
                [
                    BaseCtrlMenu('off', 'Off', LOGITECH_PERIPHERAL_LED1_MODE_OFF),
                    BaseCtrlMenu('on', 'On', LOGITECH_PERIPHERAL_LED1_MODE_ON),
                    BaseCtrlMenu('blink', 'Blink', LOGITECH_PERIPHERAL_LED1_MODE_BLINK),
                    BaseCtrlMenu('auto', 'Auto', LOGITECH_PERIPHERAL_LED1_MODE_AUTO),
                ]
            ),
            LogitechCtrl(
                'logitech_led1_frequency',
                'LED1 Frequency',
                'integer',
                LOGITECH_PERIPHERAL_LED1_SEL,
                LOGITECH_PERIPHERAL_LED1_LEN,
                LOGITECH_PERIPHERAL_LED1_FREQUENCY_OFFSET,
            ),
        ]

        for c in self.ctrls:
            default_config = to_buf(bytes(c._len))
            minimum_config = to_buf(bytes(c._len))
            maximum_config = to_buf(bytes(c._len))
            current_config = to_buf(bytes(c._len))

            query_xu_control(self.fd, self.unit_id, c._selector, UVC_GET_DEF, default_config)
            query_xu_control(self.fd, self.unit_id, c._selector, UVC_GET_MIN, minimum_config)
            query_xu_control(self.fd, self.unit_id, c._selector, UVC_GET_MAX, maximum_config)
            query_xu_control(self.fd, self.unit_id, c._selector, UVC_GET_CUR, current_config)
            
            c.default = default_config[c._offset][0]
            c.min = minimum_config[c._offset][0]
            c.max = maximum_config[c._offset][0]
            c.value = current_config[c._offset][0]

            if c.type == 'menu':
                valmenu = find_by_value(c.menu, c.value)
                if valmenu:
                    c.value = valmenu.text_id
                defmenu = find_by_value(c.menu, c.default)
                if defmenu:
                    c.default = defmenu.text_id


    def setup_ctrls(self, params):
        if not self.supported():
            return

        for k, v in params.items():
            ctrl = find_by_text_id(self.ctrls, k)
            if ctrl == None:
                continue
            if ctrl.type == 'menu':
                menu  = find_by_text_id(ctrl.menu, v)
                if menu == None:
                    logging.warning(f'LogitechCtrls: can\'t find {v} in {[c.text_id for c in ctrl.menu]}')
                    continue
                desired = menu.value
            elif ctrl.type == 'integer':
                desired = int(v)
            else:
                logging.warning(f'Can\'t set {k} to {v} (Unsupported control type {ctrl.type})')
                continue

            current_config = to_buf(bytes(ctrl._len))
            query_xu_control(self.fd, self.unit_id, ctrl._selector, UVC_GET_CUR, current_config)
            current_config[ctrl._offset] = desired
            query_xu_control(self.fd, self.unit_id, ctrl._selector, UVC_SET_CUR, current_config)
            query_xu_control(self.fd, self.unit_id, ctrl._selector, UVC_GET_CUR, current_config)
            current = current_config[ctrl._offset][0]

            if ctrl.type == 'menu':
                desmenu = find_by_value(ctrl.menu, desired)
                if desmenu:
                    desired = desmenu.text_id
                curmenu = find_by_value(ctrl.menu, current)
                if curmenu:
                    current = curmenu.text_id
            if current != desired:
                logging.warning(f'LogitechCtrls: failed to set {k} to {desired}, current value {current}\n')
                continue

            ctrl.value = desired

    def update_ctrls(self):
        return

    def get_ctrls(self):
        return self.ctrls


class V4L2Ctrl(BaseCtrl):
    def __init__(self, id, text_id, name, type, value, default = None, min = None, max = None, step = None, menu = None):
        super().__init__(text_id, name, type, value, default, min, max, step, menu)
        self._id = id

class V4L2Ctrls:
    to_type = {
        V4L2_CTRL_TYPE_INTEGER: 'integer',
        V4L2_CTRL_TYPE_BOOLEAN: 'boolean',
        V4L2_CTRL_TYPE_MENU: 'menu',
        V4L2_CTRL_TYPE_INTEGER_MENU: 'menu',
    }
    strtrans = bytes.maketrans(b' -', b'__')


    def __init__(self, device, fd):
        self.device = device
        self.fd = fd
        self.get_device_controls()


    def setup_ctrls(self, params):
        for k, v in params.items():
            ctrl = find_by_text_id(self.ctrls, k)
            if ctrl == None:
                continue
            intvalue = 0
            if ctrl.type == 'integer':
                intvalue = int(v)
            elif ctrl.type == 'boolean':
                intvalue = int(bool(v))
            elif ctrl.type == 'menu':
                menu = find_by_text_id(ctrl.menu, v)
                if menu == None:
                    logging.warning(f'V4L2Ctrls: Can\'t find {v} in {[c.text_id for c in ctrl.menu]}')
                    continue
                intvalue = menu.value
            else:
                logging.warning(f'V4L2Ctrls: Can\'t set {k} to {v} (Unsupported control type {ctrl.type})')
                continue
            try:
                new_ctrl = v4l2_control(ctrl._id, intvalue)
                ioctl(self.fd, VIDIOC_S_CTRL, new_ctrl)
                if new_ctrl.value != intvalue:
                    logging.warning(f'V4L2Ctrls: Can\'t set {k} to {v} using {new_ctrl.value} instead of {intvalue}')
                    continue
                
                if ctrl.type == 'menu':
                    ctrl.value = v
                else:
                    ctrl.value = intvalue
            except Exception as e:
                logging.warning(f'V4L2Ctrls: Can\'t set {k} to {v} ({e})')

    def get_device_controls(self):
        ctrls = []
        next_flag = V4L2_CTRL_FLAG_NEXT_CTRL | V4L2_CTRL_FLAG_NEXT_COMPOUND
        qctrl = v4l2_queryctrl(next_flag)
        while True:
            try:
                ioctl(self.fd, VIDIOC_QUERYCTRL, qctrl)
            except:
                break
            if qctrl.type in [V4L2_CTRL_TYPE_INTEGER, V4L2_CTRL_TYPE_BOOLEAN,
                V4L2_CTRL_TYPE_MENU, V4L2_CTRL_TYPE_INTEGER_MENU]:

                try:
                    ctrl = v4l2_control(qctrl.id)
                    ioctl(self.fd, VIDIOC_G_CTRL, ctrl)
                except:
                    logging.warning(f'V4L2Ctrls: Can\'t get ctrl {qctrl.name} value')

                text_id = self.to_text_id(qctrl.name)
                text = str(qctrl.name, 'utf-8')
                ctrl_type = V4L2Ctrls.to_type.get(qctrl.type)
                v4l2ctrl = V4L2Ctrl(qctrl.id, text_id, text, ctrl_type, int(ctrl.value),
                    qctrl.default, qctrl.minimum, qctrl.maximum, qctrl.step)

                # doesn't work, uvc driver bug?
                # v4l2ctrl.updater = bool(qctrl.flags & V4L2_CTRL_FLAG_UPDATE)
                v4l2ctrl.updater = qctrl.id in V4L2_CTRL_UPDATERS
                v4l2ctrl.inactive = bool(qctrl.flags & V4L2_CTRL_FLAG_INACTIVE)

                if qctrl.type in [V4L2_CTRL_TYPE_MENU, V4L2_CTRL_TYPE_INTEGER_MENU]:
                    v4l2ctrl.menu = []
                    for i in range(qctrl.minimum, qctrl.maximum + 1):
                        try:
                            qmenu = v4l2_querymenu(qctrl.id, i)
                            ioctl(self.fd, VIDIOC_QUERYMENU, qmenu)
                        except:
                            continue
                        if qctrl.type == V4L2_CTRL_TYPE_MENU:
                            menu_text = str(qmenu.name, 'utf-8')
                            menu_text_id = self.to_text_id(qmenu.name)
                        else:
                            menu_text_id = str(qmenu.value)
                            menu_text = menu_text_id
                        v4l2menu = BaseCtrlMenu(menu_text_id, menu_text, int(qmenu.index))
                        v4l2ctrl.menu.append(v4l2menu)
                        if v4l2ctrl.value == qmenu.index:
                            v4l2ctrl.value = menu_text_id
                        if v4l2ctrl.default == qmenu.index:
                            v4l2ctrl.default = menu_text_id
                        
                ctrls.append(v4l2ctrl)
            qctrl = v4l2_queryctrl(qctrl.id | next_flag)



        # move the controls in the 'auto' control groups near each other
        for k, v in V4L2_CTRL_REORDERS.items():
            what = find_idx(ctrls, lambda c: c._id == k)
            where = find_idx(ctrls, lambda c: c._id == v)
            if what and where:
                ctrls.insert(where - 1 if what < where else where, ctrls.pop(what))

        self.ctrls = ctrls

    def update_ctrls(self):
        for c in self.ctrls:
            qctrl = v4l2_queryctrl(c._id)
            try:
                ioctl(self.fd, VIDIOC_QUERYCTRL, qctrl)
            except:
                logging.warning(f'V4L2Ctrls: Can\'t update ctrl {c.name} ')
                continue
            c.inactive = bool(qctrl.flags & V4L2_CTRL_FLAG_INACTIVE)

    def get_ctrls(self):
        return self.ctrls
    
    def to_text_id(self, text):
        return str(text.lower().translate(V4L2Ctrls.strtrans, delete = b',&(.)/').replace(b'__', b'_'), 'utf-8')


class CameraCtrls:
    def __init__(self, device, fd):
        self.device = device
        self.fd = fd
        self.ctrls = [
            V4L2Ctrls(device, fd),
            KiyoProCtrls(device, fd),
            LogitechCtrls(device, fd),
        ]
    
    def print_ctrls(self):
        for c in self.get_ctrls():
            print(f'{c.text_id} = ', end = '')
            if c.type == 'menu':
                print(f'{c.value}\t( ', end = '')
                if c.default:
                    print(f'default: {c.default} ', end = '')
                print('values:', end = ' ')
                print(', '.join([m.text_id for m in c.menu]), end = ' )')
            elif c.type in ['integer', 'boolean']:
                print(f'{c.value}\t( default: {c.default} min: {c.min} max: {c.max}', end = '')
                if c.step != 1:
                    print(f' step: {c.step}', end = '')
                print(' )', end = '')
            if c.updater:
                print(' | updater', end = '')
            if c.inactive:
                print(' | inactive', end = '')
            print()
    
    def setup_ctrls(self, params):
        for c in self.ctrls:
            c.setup_ctrls(params)
        unknown_ctrls = list(set(params.keys()) - set([c.text_id for c in self.get_ctrls()]))
        if len(unknown_ctrls) > 0:
            logging.warning(f'CameraCtrls: can\'t find {unknown_ctrls} controls')

    def update_ctrls(self):
        for c in self.ctrls:
            c.update_ctrls()

    def get_ctrls(self):
        ctrls = []
        for c in self.ctrls:
            ctrls += c.get_ctrls()
        return ctrls


def usage():
    print(f'usage: {sys.argv[0]} [--help] [-d DEVICE] [--list] [-c CONTROLS]\n')
    print(f'optional arguments:')
    print(f'  -h, --help    show this help message and exit')
    print(f'  -d DEVICE     use DEVICE, default /dev/video0')
    print(f'  -l, --list    list the controls and values')
    print(f'  -c CONTROLS   set CONTROLS (eg.: hdr=on,fov=wide)')
    print()
    print(f'example:')
    print(f'  {sys.argv[0]} -c brightness=128,kiyo_pro_hdr=on,kiyo_pro_fov=wide')

def main():
    try:
        arguments, values = getopt.getopt(sys.argv[1:], 'hd:lc:', ['help', 'list'])
    except getopt.error as err:
        print(err)
        usage()
        sys.exit(2)

    if len(arguments) == 0:
        usage()
        sys.exit(0)

    list_controls = False
    device = '/dev/video0'
    controls = ''

    for current_argument, current_value in arguments:
        if current_argument in ('-h', '--help'):
            usage()
            sys.exit(0)
        elif current_argument in ('-d', '--device'):
            device = current_value
        elif current_argument in ('-l', '--list'):
            list_controls = True
        elif current_argument in ('-c'):
            controls = current_value

    try:
        fd = os.open(device, os.O_RDWR, 0)
    except Exception as e:
        logging.error(f'os.open({device}, os.O_RDWR, 0) failed: {e}')
        sys.exit(2)

    camera_ctrls = CameraCtrls(device, fd)

    if list_controls:
        camera_ctrls.print_ctrls()

    if controls != '':
        ctrlsmap = {}
        for control in controls.split(','):
            kv = control.split('=', maxsplit=1)
            if len(kv) != 2:
                logging.warning(f'invalid value: {control}')
                continue
            ctrlsmap[kv[0]]=kv[1]

        camera_ctrls.setup_ctrls(ctrlsmap)

if __name__ == '__main__':
    main()
