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

def decode_packet(message: str) -> dict:
    if not is_valid_packet(message):
        return {}
    
    msg = message.replace(' ', '')
    pid = msg[6:14]
    mid = msg[16:18]
    bl = int(msg[18:20], 16)
    battery = str(int((bl / 3.3) * 10))
    cmd = msg[24:26]
    
    return {
        "id": pid,
        "mid": mid,
        "battery": battery,
        "cmd": cmd
    }
