"""SPI coverage closure — systematically hits all remaining coverage bins."""

from pyuvm import uvm_sequence, ConfigDB
from cocotb.triggers import ClockCycles

from cf_verify.bus_env.bus_seq_lib import write_reg_seq, read_reg_seq, reset_seq
from seq_lib.spi_config_seq import spi_config_seq


class spi_coverage_closure_seq(uvm_sequence):
    async def body(self):
        await reset_seq("rst").start(self.sequencer)

        regs = ConfigDB().get(None, "", "bus_regs")
        self.addr = regs.reg_name_to_address
        self.dut = ConfigDB().get(None, "", "DUT")

        if "GCLK" in self.addr:
            await self._w("gclk", "GCLK", 1)

        await self._all_spi_modes()
        await self._ctrl_combos()
        await self._prescaler_sweep()
        await self._fifo_levels()
        await self._status_done()
        await self._data_sweep()

    async def _w(self, name, reg, val):
        await write_reg_seq(name, self.addr[reg], val).start(self.sequencer)

    async def _r(self, name, reg):
        await read_reg_seq(name, self.addr[reg]).start(self.sequencer)

    async def _all_spi_modes(self):
        """Hit all 4 CPOL/CPHA modes — write CFG then READ it back."""
        for cpol in [0, 1]:
            for cpha in [0, 1]:
                await self._w("ctrl_off", "CTRL", 0)
                await self._w("pr", "PR", 4)
                cfg = cpol | (cpha << 1)
                await self._w("cfg", "CFG", cfg)
                await self._r("cfg_rd", "CFG")

                ctrl = 1 | (1 << 1) | (1 << 2)  # SS + enable + rx_en
                await self._w("ctrl", "CTRL", ctrl)
                await self._r("ctrl_rd", "CTRL")

                await self._w("tx", "TXDATA", 0xA5)
                bit_cyc = 5 * 16
                await ClockCycles(self.dut.CLK, bit_cyc * 12)

                await self._r("status", "STATUS")
                await self._r("rxdata", "RXDATA")
                await self._r("ris", "RIS")

    async def _ctrl_combos(self):
        """Sweep CTRL field combinations: SS, enable, rx_en in all states."""
        combos = [
            (0, 0, 0), (0, 0, 1), (0, 1, 0), (0, 1, 1),
            (1, 0, 0), (1, 0, 1), (1, 1, 0), (1, 1, 1),
        ]
        for ss, en, rx_en in combos:
            ctrl = (ss & 1) | ((en & 1) << 1) | ((rx_en & 1) << 2)
            await self._w("ctrl", "CTRL", ctrl)
            await self._r("ctrl_rd", "CTRL")

    async def _prescaler_sweep(self):
        """Hit all 5 PR bins: (2-3), (4-7), (8-15), (16-31), (32-255)."""
        for pr_val in [2, 5, 10, 20, 64]:
            await self._w("ctrl_off", "CTRL", 0)
            await self._w("pr", "PR", pr_val)
            await self._r("pr_rd", "PR")

            cfg = 0  # mode 0
            await self._w("cfg", "CFG", cfg)
            ctrl = 1 | (1 << 1) | (1 << 2)
            await self._w("ctrl", "CTRL", ctrl)

            await self._w("tx", "TXDATA", 0x55)
            bit_cyc = (pr_val + 1) * 16
            await ClockCycles(self.dut.CLK, bit_cyc * 12)
            await self._r("status", "STATUS")

    async def _fifo_levels(self):
        """Hit all 4 FIFO level bins: empty(0), low(1-4), mid(5-12), high(13-15)."""
        # TX FIFO: disable SPI so data stays in FIFO
        await self._w("ctrl_off", "CTRL", 0)
        await self._w("pr", "PR", 2)
        await self._w("cfg", "CFG", 0)

        for fill_count in [0, 3, 8, 16]:
            if "TX_FIFO_FLUSH" in self.addr:
                await self._w("flush_tx", "TX_FIFO_FLUSH", 1)
            for i in range(fill_count):
                await self._w("tx", "TXDATA", i & 0xFF)
            if "TX_FIFO_LEVEL" in self.addr:
                await self._r("tx_lvl", "TX_FIFO_LEVEL")
            await self._r("status", "STATUS")

        if "TX_FIFO_FLUSH" in self.addr:
            await self._w("flush_tx", "TX_FIFO_FLUSH", 1)

        # Set TX threshold high so TX_B (below threshold) fires
        if "TX_FIFO_THRESHOLD" in self.addr:
            await self._w("tx_thr", "TX_FIFO_THRESHOLD", 14)
        await self._r("status_txb", "STATUS")
        await self._r("ris_txb", "RIS")

        # RX FIFO: enable SPI with loopback to fill RX
        ctrl = 1 | (1 << 1) | (1 << 2)  # SS + enable + rx_en
        bit_cyc = 3 * 16

        # Bins: empty, low(1-4), mid(5-12), high(13-15). Need 13-15 in RX_LEVEL
        # without relying on overflow; 16 TX beats can miss the high window.
        for fill_count in [0, 3, 8, 14, 15]:
            if "RX_FIFO_FLUSH" in self.addr:
                await self._w("flush_rx", "RX_FIFO_FLUSH", 1)
            await self._w("ctrl", "CTRL", ctrl)
            for i in range(fill_count):
                await self._w("tx", "TXDATA", (i * 17) & 0xFF)
            wait_cyc = bit_cyc * 12 * max(fill_count * 2, 24)
            await ClockCycles(self.dut.CLK, wait_cyc)
            if "RX_FIFO_LEVEL" in self.addr:
                await self._r("rx_lvl", "RX_FIFO_LEVEL")
            await self._r("status", "STATUS")
            await self._w("ctrl_off2", "CTRL", 0)

        if "RX_FIFO_FLUSH" in self.addr:
            await self._w("flush_rx", "RX_FIFO_FLUSH", 1)

    async def _status_done(self):
        """Ensure STATUS.done is set after a completed transfer."""
        await self._w("ctrl_off", "CTRL", 0)
        await self._w("pr", "PR", 2)
        await self._w("cfg", "CFG", 0)
        ctrl = 1 | (1 << 1)  # SS + enable (no rx_en)
        await self._w("ctrl", "CTRL", ctrl)

        if "IM" in self.addr:
            await self._w("im", "IM", 0x3F)

        await self._w("tx", "TXDATA", 0x42)
        bit_cyc = 3 * 16
        # Poll STATUS until done flag (bit 7) is set.
        done_seen = False
        for _ in range(20):
            await ClockCycles(self.dut.CLK, bit_cyc * 2)
            rd = read_reg_seq("status_done", self.addr["STATUS"])
            await rd.start(self.sequencer)
            done_seen |= ((rd.result >> 7) & 1) == 1
        assert done_seen, "STATUS.done was never observed during completed transfer"
        await self._r("ris_done", "RIS")
        if "MIS" in self.addr:
            await self._r("mis_done", "MIS")

    async def _data_sweep(self):
        """Hit all 8 TX and RX data bins (0x00-0x1F, 0x20-0x3F, ..., 0xE0-0xFF)."""
        await self._w("ctrl_off", "CTRL", 0)
        await self._w("pr", "PR", 2)
        await self._w("cfg", "CFG", 0)
        ctrl = 1 | (1 << 1) | (1 << 2)
        await self._w("ctrl", "CTRL", ctrl)

        bit_cyc = 3 * 16
        data_reps = [0x08, 0x28, 0x48, 0x68, 0x88, 0xA8, 0xC8, 0xE8]

        for d in data_reps:
            await self._w("tx_d", "TXDATA", d)
            await ClockCycles(self.dut.CLK, bit_cyc * 12)
            await self._r("rx_d", "RXDATA")
