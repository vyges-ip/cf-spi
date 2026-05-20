"""SPI IP monitor — observes MOSI, MISO, SCLK, and CSB signals."""

import cocotb
from cocotb.triggers import RisingEdge, FallingEdge, ClockCycles, Timer
from cocotb.utils import get_sim_time
from pyuvm import uvm_monitor, uvm_analysis_port, ConfigDB

from ip_item.spi_item import spi_item


class spi_monitor(uvm_monitor):
    def build_phase(self):
        super().build_phase()
        self.ap = uvm_analysis_port("ap", self)
        self.dut = ConfigDB().get(self, "", "DUT")
        self.regs = ConfigDB().get(None, "", "bus_regs")
        self.tx_received = cocotb.triggers.Event()
        self.rx_received = cocotb.triggers.Event()

    async def run_phase(self):
        cocotb.start_soon(self._sample_spi())

    async def _sample_spi(self):
        """Watch for SPI transactions by monitoring CSB and SCLK."""
        while True:
            try:
                await FallingEdge(self.dut.SSn)
            except Exception:
                await ClockCycles(self.dut.CLK, 1)
                continue

            mosi_bits = []
            miso_bits = []

            cpol = self._get_cpol()
            cpha = self._get_cpha()

            if cpha == 0:
                sample_edge = RisingEdge if cpol == 0 else FallingEdge
            else:
                sample_edge = FallingEdge if cpol == 0 else RisingEdge

            for _ in range(8):
                try:
                    await sample_edge(self.dut.SCK)
                except Exception:
                    break
                await Timer(1, "ns")
                try:
                    mosi_val = int(self.dut.MOSI.value)
                except Exception:
                    mosi_val = 0
                try:
                    miso_val = int(self.dut.MISO.value)
                except Exception:
                    miso_val = 0
                mosi_bits.append(mosi_val)
                miso_bits.append(miso_val)

            if len(mosi_bits) == 8:
                tx_data = 0
                for bit in mosi_bits:
                    tx_data = (tx_data << 1) | bit

                rx_data = 0
                for bit in miso_bits:
                    rx_data = (rx_data << 1) | bit

                tr_tx = spi_item("tx_mon")
                tr_tx.data = tx_data
                tr_tx.direction = spi_item.TX
                tr_tx.cpol = cpol
                tr_tx.cpha = cpha
                self.ap.write(tr_tx)
                self.tx_received.set()

                tr_rx = spi_item("rx_mon")
                tr_rx.data = rx_data
                tr_rx.direction = spi_item.RX
                tr_rx.cpol = cpol
                tr_rx.cpha = cpha
                self.ap.write(tr_rx)
                self.rx_received.set()

            try:
                await RisingEdge(self.dut.SSn)
            except Exception:
                await ClockCycles(self.dut.CLK, 1)

    def _get_cpol(self):
        try:
            return self.regs.read_reg_value("CFG") & 0x1
        except Exception:
            return 0

    def _get_cpha(self):
        try:
            return (self.regs.read_reg_value("CFG") >> 1) & 0x1
        except Exception:
            return 0
