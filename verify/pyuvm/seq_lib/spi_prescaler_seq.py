"""SPI prescaler sequence — tests different SPI clock prescaler values."""

import random

from pyuvm import uvm_sequence, ConfigDB
from cocotb.triggers import ClockCycles

from cf_verify.bus_env.bus_seq_lib import write_reg_seq, read_reg_seq, reset_seq
from seq_lib.spi_config_seq import spi_config_seq


class spi_prescaler_seq(uvm_sequence):
    async def body(self):
        await reset_seq("rst").start(self.sequencer)

        regs = ConfigDB().get(None, "", "bus_regs")
        addr = regs.reg_name_to_address
        dut = ConfigDB().get(None, "", "DUT")

        for pr in [2, 4, 8, 16]:
            config = spi_config_seq("config", prescaler=pr, rx_en=1)
            await config.start(self.sequencer)

            bit_cyc = (pr + 1) * 16

            for _ in range(2):
                data = random.randint(0, 0xFF)
                await write_reg_seq("tx", addr["TXDATA"], data).start(self.sequencer)
                await ClockCycles(dut.CLK, bit_cyc * 12)

            await read_reg_seq("status", addr["STATUS"]).start(self.sequencer)
