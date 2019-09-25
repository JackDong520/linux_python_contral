import hashlib
import re


def lstrsub(s: str, sub: str):
    if s[:len(sub)] == sub:
        return s[len(sub):]
    return s


def is_ip_address_format(value):
    IP_ADDRESS_REGEX = r"\b(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\b"
    if value and re.match(IP_ADDRESS_REGEX, value):
        return True
    else:
        return False


def is_url_format(value):
    URL_ADDRESS_REGEX = r"(?:(?:https?):\/\/|www\.|ftp\.)(?:\([-a-zA-Z0-9+&@#\/%=~_|$?!:,.]*\)|[-a-zA-Z0-9+&@#\/%=~_|$?!:,.])*(?:\([-a-zA-Z0-9+&@#\/%=~_|$?!:,.]*\)|[a-zA-Z0-9+&@#\/%=~_|$])"
    if value and re.match(URL_ADDRESS_REGEX, value):
        return True
    else:
        return False

def get_md5(value):
    if isinstance(value, str):
        value = value.encode(encoding='UTF-8')
    return hashlib.md5(value).hexdigest()

