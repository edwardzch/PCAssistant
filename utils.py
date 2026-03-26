# utils.py
import functools
import crc
from zlib import crc32

class Checksums:
    @staticmethod
    def sum(data: bytes) -> bytes: return (sum(data) & 0xFF).to_bytes(1, 'big')
    @staticmethod
    def crc8(data: bytes) -> bytes: return crc.Calculator(crc.Crc8.CCITT).checksum(data).to_bytes(1, 'big')
    @staticmethod
    def crc16_modbus(data: bytes) -> bytes: return crc.Calculator(crc.Crc16.MODBUS).checksum(data).to_bytes(2, 'little')
    @staticmethod
    def crc32(data: bytes) -> bytes: return (crc32(data) & 0xFFFFFFFF).to_bytes(4, 'big')
    @staticmethod
    def bcc(data: bytes) -> bytes: return functools.reduce(lambda x, y: x ^ y, data).to_bytes(1, 'big')
    @staticmethod
    def lrc(data: bytes) -> bytes: return (((sum(data) & 0xFF) ^ 0xFF) + 1 & 0xFF).to_bytes(1, 'big')
    @staticmethod
    def crc16_xmodem(data: bytes) -> bytes: return crc.Calculator(crc.Crc16.XMODEM).checksum(data).to_bytes(2, 'big')
