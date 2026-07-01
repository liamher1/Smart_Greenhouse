from machine import I2C, Pin
from config import I2C_SDA_PIN, I2C_SCL_PIN, RELAY_I2C_ADDR

_i2c = I2C(0, sda=Pin(I2C_SDA_PIN), scl=Pin(I2C_SCL_PIN), freq=100000)

_CMD_CHANNEL_CTRL = 0x10
_state = 0x00


def _sync():
    _i2c.writeto(RELAY_I2C_ADDR, bytes([_CMD_CHANNEL_CTRL, _state]))


def on(channel):
    global _state
    _state |= 1 << (channel - 1)
    _sync()


def off(channel):
    global _state
    _state &= ~(1 << (channel - 1))
    _sync()


def is_on(channel):
    return bool(_state & (1 << (channel - 1)))


# Safe initial state
_sync()
