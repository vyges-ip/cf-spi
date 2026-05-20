"""SPI loopback sequence — sends via TX, reads back from RXDATA via loopback."""

import os
import random

from pyuvm import uvm_sequence, ConfigDB
from cocotb.triggers import ClockCycles

from cf_verify.bus_env.bus_seq_lib import write_reg_seq, read_reg_seq, reset_seq
from seq_lib.spi_config_seq import spi_config_seq


class spi_loopback_seq(uvm_sequence):
    def __init__(self, name="spi_loopback_seq"):
        super().__init__(name)

    async def body(self):
        await reset_seq("rst").start(self.sequencer)

        regs = ConfigDB().get(None, "", "bus_regs")
        addr = regs.reg_name_to_address
        dut = ConfigDB().get(None, "", "DUT")

        config = spi_config_seq("config", rx_en=1, prescaler=4)
        await config.start(self.sequencer)

        pr = regs.read_reg_value("PR") or 4
        bit_cyc = (pr + 1) * 16

        n = 4
        sent_data = []
        for _ in range(n):
            data = random.randint(0, 0xFF)
            sent_data.append(data)
            await write_reg_seq("tx_wr", addr["TXDATA"], data).start(self.sequencer)
            await ClockCycles(dut.CLK, bit_cyc * 12)

        # Verilator: RX level can go non-zero before loopback data is byte-stable
        if os.environ.get("SIM", "").lower() == "verilator":
            await ClockCycles(dut.CLK, bit_cyc * 12 * n * 48)
        elif "RX_FIFO_LEVEL" in addr:
            for _ in range(200_000):
                await ClockCycles(dut.CLK, 2)
                rdl = read_reg_seq("rxlvl_wait", addr["RX_FIFO_LEVEL"])
                await rdl.start(self.sequencer)
                if int(rdl.result) & 0xF >= n:
                    break
        else:
            await ClockCycles(dut.CLK, bit_cyc * 12 * n)

        # Read back from RXDATA (loopback: MISO = MOSI)
        for expected in sent_data:
            rd = read_reg_seq("rx_rd", addr["RXDATA"])
            await rd.start(self.sequencer)
            rx_val = rd.result & 0xFF
            assert rx_val == expected, (
                f"SPI loopback MISMATCH: sent 0x{expected:02x}, "
                f"received 0x{rx_val:02x}"
            )
