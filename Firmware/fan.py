import relay_board
from config import FAN_RELAY_CHANNEL


def on():
    relay_board.on(FAN_RELAY_CHANNEL)
    print("Fan ON")


def off():
    relay_board.off(FAN_RELAY_CHANNEL)
    print("Fan OFF")


def is_on():
    return relay_board.is_on(FAN_RELAY_CHANNEL)
