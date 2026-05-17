import binascii

def is_valid_packet(message: str) -> bool:
    message = message.replace(' ', '')
    try:
        int(message, 16)
        raw = binascii.unhexlify(message)
        if len(raw) < 16:
            return False
        if raw[0] != 0x6C or raw[1] != 0x76 or raw[2] != 0x63:
            return False
        if raw[-1] != 0x0A or raw[-2] != 0x0D or raw[-3] != 0x64:
            return False
        return True
    except Exception:
        return False

_decode_value = {
    '01': '1', '02': '0', '03': 'toggle', '04': 'toggle', '05': 'toggle', '06': 'toggle', 
    '07': 'up', '08': 'toggle', '09': '1', '0A': '0', '0B': '0', '0C': '0', '0D': '0', 
    '0E': '0', '0F': '0', '10': '0', '11': '0', '12': '0', '13': '0', '14': '0', '15': '0', 
    '16': '0', '17': '0', '18': '0', '19': '0', '1A': '1', '1F': '0', '20': '0', '21': '0', 
    'F1': '20', 'F2': '20', 'F3': '30', 'F4': '40', 'F5': '50', 'F6': '60', 'F7': '70', 
    'F8': '80', 'F9': '90', 'FA': '100'
}

def decode_packet(message: str) -> dict:
    if not is_valid_packet(message):
        return {}
    
    msg = message.replace(' ', '')
    pid = msg[6:14]
    bid = msg[14:16]
    mid = msg[16:18]
    bl = int(msg[18:20], 16)
    battery = str(int((bl / 3.3) * 10))
    cmd = msg[24:26]
    
    action = _decode_value.get(cmd, str(cmd))
    
    return {
        "id": pid,
        "button": bid,
        "mid": mid,
        "battery": battery,
        "cmd": cmd,
        "action": action
    }
