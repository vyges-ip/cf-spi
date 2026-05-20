"""SPI TX sequence — writes data to TXDATA, waits for transfer completion."""

import os
import random

from pyuvm import uvm_sequence, ConfigDB
from cocotb.triggers import ClockCycles

from cf_verify.bus_env.bus_seq_lib import write_reg_seq, read_reg_seq, reset_seq
from seq_lib.spi_config_seq import spi_config_seq


class spi_tx_seq(uvm_sequence):
    def __init__(self, name="spi_tx_seq"):
        super().__init__(name)

    async def body(self):
        await reset_seq("rst").start(self.sequencer)

        regs = ConfigDB().get(None, "", "bus_regs")
        addr = regs.reg_name_to_address
        dut = ConfigDB().get(None, "", "DUT")

        config = spi_config_seq("config")
        await config.start(self.sequencer)

        n_iters = int(os.environ.get("TX_STRESS_ITERS", "5"))
        pr = regs.read_reg_value("PR")
        bit_cyc = (pr + 1) * 16

        for _ in range(n_iters):
            data = random.randint(0, 0xFF)
            await write_reg_seq("tx_wr", addr["TXDATA"], data).start(self.sequencer)
            await ClockCycles(dut.CLK, bit_cyc * 10)
            await read_reg_seq("status_rd", addr["STATUS"]).start(self.sequencer)
