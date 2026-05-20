"""SPI transaction item — carries data, cpol, cpha, direction."""

import random

from pyuvm import uvm_sequence_item


class spi_item(uvm_sequence_item):
    RX = 0
    TX = 1

    def __init__(self, name="spi_item"):
        super().__init__(name)
        self.data = 0
        self.direction = spi_item.TX
        self.cpol = 0
        self.cpha = 0

    def randomize(self, max_val=0xFF):
        self.data = random.randint(0, max_val)

    def convert2string(self):
        d = "RX" if self.direction == spi_item.RX else "TX"
        return (
            f"spi data=0x{self.data:02x} direction={d}, "
            f"cpol={self.cpol}, cpha={self.cpha}"
        )

    def do_compare(self, rhs):
        return (
            self.data == rhs.data
            and self.direction == rhs.direction
            and self.cpol == rhs.cpol
            and self.cpha == rhs.cpha
        )

    def do_copy(self, rhs):
        super().do_copy(rhs)
        self.data = rhs.data
        self.direction = rhs.direction
        self.cpol = rhs.cpol
        self.cpha = rhs.cpha

    def do_clone(self):
        new = spi_item(self.get_name())
        new.do_copy(self)
        return new
