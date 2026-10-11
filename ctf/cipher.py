"""Documented ASCII-only Vigenere convention, continuous across lines."""
def transform(text, key="ORACLE", decrypt=False):
    if not key or any(not ('A' <= c <= 'Z') for c in key):
        raise ValueError("Key must contain uppercase ASCII letters")
    result, position = [], 0
    for char in text:
        if 'A' <= char <= 'Z' or 'a' <= char <= 'z':
            base = ord('A' if char.isupper() else 'a')
            shift = ord(key[position % len(key)]) - 65
            result.append(chr(base + (ord(char) - base + (-shift if decrypt else shift)) % 26))
            position += 1
        else:
            result.append(char)
    return ''.join(result)
