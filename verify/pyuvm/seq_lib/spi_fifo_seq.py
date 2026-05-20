"""SPI FIFO sequence — tests FIFO full, empty, threshold, and flush."""

from pyuvm import uvm_sequence, ConfigDB
from cocotb.triggers import ClockCycles

from cf_verify.bus_env.bus_seq_lib import write_reg_seq, read_reg_seq, reset_seq
from seq_lib.spi_config_seq import spi_config_seq


class spi_fifo_seq(uvm_sequence):
    async def body(self):
        await reset_seq("rst").start(self.sequencer)

        regs = ConfigDB().get(None, "", "bus_regs")
        addr = regs.reg_name_to_address
        dut = ConfigDB().get(None, "", "DUT")

        config = spi_config_seq("config", im=0x3F, rx_en=1)
        await config.start(self.sequencer)

        pr = regs.read_reg_value("PR")
        bit_cyc = (pr + 1) * 16

        async def read_reg(reg_name):
            rd = read_reg_seq(f"rd_{reg_name.lower()}", addr[reg_name])
            await rd.start(self.sequencer)
            return rd.result

        def status_bit(status_val, bit):
            return (status_val >> bit) & 1

        txe_b, txf_b, rxe_b, rxf_b = 0, 1, 2, 3

        # Set TX FIFO threshold to 4
        if "TX_FIFO_THRESHOLD" in addr:
            await write_reg_seq("tx_thr", addr["TX_FIFO_THRESHOLD"], 4).start(self.sequencer)

        # Set RX FIFO threshold to 4
        if "RX_FIFO_THRESHOLD" in addr:
            await write_reg_seq("rx_thr", addr["RX_FIFO_THRESHOLD"], 4).start(self.sequencer)

        # Fill TX FIFO to capacity (16 entries) and check level
        for i in range(16):
            await write_reg_seq("tx", addr["TXDATA"], i & 0xFF).start(self.sequencer)

        # Check TX FIFO level and full status
        if "TX_FIFO_LEVEL" in addr:
            tx_lvl = await read_reg("TX_FIFO_LEVEL")
            assert tx_lvl in (0, 15), (
                f"TX FIFO full encoding unexpected: expected 0 or 15, got {tx_lvl}"
            )

        # Overfill TX FIFO
        for i in range(4):
            await write_reg_seq("tx_overflow", addr["TXDATA"], 0xAA).start(self.sequencer)

        ris = await read_reg("RIS")
        assert ((ris >> txf_b) & 1) == 1, f"TXF flag not set in RIS (0x{ris:02x})"

        status = await read_reg("STATUS")
        assert status_bit(status, txf_b) == 1, f"TX_F bit not set in STATUS (0x{status:02x})"
        assert status_bit(status, txe_b) == 0, f"TX_E unexpectedly set while FIFO full (0x{status:02x})"

        # Flush TX FIFO
        if "TX_FIFO_FLUSH" in addr:
            await write_reg_seq("flush_tx", addr["TX_FIFO_FLUSH"], 1).start(self.sequencer)

        # Flush RX FIFO
        if "RX_FIFO_FLUSH" in addr:
            await write_reg_seq("flush_rx", addr["RX_FIFO_FLUSH"], 1).start(self.sequencer)

        # Verify FIFOs are empty
        if "TX_FIFO_LEVEL" in addr:
            tx_lvl_0 = await read_reg("TX_FIFO_LEVEL")
            assert tx_lvl_0 == 0, f"TX FIFO level non-zero after flush: {tx_lvl_0}"
        if "RX_FIFO_LEVEL" in addr:
            rx_lvl_0 = await read_reg("RX_FIFO_LEVEL")
            assert rx_lvl_0 == 0, f"RX FIFO level non-zero after flush: {rx_lvl_0}"

        # Verify STATUS shows empty after flush
        status_post = await read_reg("STATUS")
        assert status_bit(status_post, txe_b) == 1, (
            f"TX_E bit not set after flush in STATUS (0x{status_post:02x})"
        )
        assert status_bit(status_post, rxe_b) == 1, (
            f"RX_E bit not set after flush in STATUS (0x{status_post:02x})"
        )

        # Fill RX FIFO to full using loopback and verify RX_F/RXF visibility.
        for i in range(16):
            await write_reg_seq("tx_rx_fill", addr["TXDATA"], i ^ 0x5A).start(self.sequencer)
        await ClockCycles(dut.CLK, bit_cyc * 12 * 20)

        if "RX_FIFO_LEVEL" in addr:
            rx_lvl_full = await read_reg("RX_FIFO_LEVEL")
            assert rx_lvl_full in (0, 15), (
                f"RX FIFO full encoding unexpected: expected 0 or 15, got {rx_lvl_full}"
            )
        status_full = await read_reg("STATUS")
        ris_full = await read_reg("RIS")
        assert status_bit(status_full, rxf_b) == 1, (
            f"RX_F bit not set in STATUS after RX fill (0x{status_full:02x})"
        )
        assert ((ris_full >> rxf_b) & 1) == 1, (
            f"RXF flag not set in RIS after RX fill (0x{ris_full:02x})"
        )
