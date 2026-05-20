"""SPI IP driver — minimal driver for loopback testbench.

With MISO wired to MOSI in the testbench, the SPI master drives both
directions automatically. This driver handles any IP-side sequence items
but does not need to bit-bang external signals.
"""

import cocotb
from cocotb.triggers import ClockCycles, FallingEdge, First
from pyuvm import uvm_driver, ConfigDB

from ip_item.spi_item import spi_item


class spi_driver(uvm_driver):
    def build_phase(self):
        super().build_phase()
        self.dut = ConfigDB().get(self, "", "DUT")
        self.regs = ConfigDB().get(None, "", "bus_regs")

    async def run_phase(self):
        while True:
            item = await self.seq_item_port.get_next_item()
            self.logger.info(f"SPI driver got item: {item.convert2string()}")
            self.seq_item_port.item_done()
