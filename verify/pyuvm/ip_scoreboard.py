"""SPI scoreboard — compares both TX and RX transactions from DUT and reference."""

from cf_verify.base.scoreboard import scoreboard
from ip_item.spi_item import spi_item


class spi_scoreboard(scoreboard):
    def build_phase(self):
        super().build_phase()
        self.bus_count = 0
        self.tx_count = 0
        self.rx_count = 0

    async def _compare_bus(self):
        while True:
            dut_tr = await self.bus_dut_fifo.get()
            ref_tr = await self.bus_ref_fifo.get()
            self.bus_count += 1
            self._check("BUS", dut_tr, ref_tr)

    async def _compare_ip(self):
        """Compare both TX and RX SPI transactions against reference model."""
        while True:
            dut_tr = await self.ip_dut_fifo.get()
            ref_tr = await self.ip_ref_fifo.get()
            if hasattr(dut_tr, "direction") and dut_tr.direction == spi_item.TX:
                self.tx_count += 1
            else:
                self.rx_count += 1
            self._check("IP", dut_tr, ref_tr)

    def check_phase(self):
        assert self.failed == 0, (
            f"SPI scoreboard mismatches detected: failed={self.failed}, passed={self.passed}"
        )
        total_checks = self.bus_count + self.tx_count + self.rx_count
        assert total_checks > 0, "SPI scoreboard did not compare any transactions"

    def report_phase(self):
        self.logger.info(
            f"SPI Scoreboard: {self.bus_count} BUS + "
            f"{self.tx_count} TX + {self.rx_count} RX checked"
        )
