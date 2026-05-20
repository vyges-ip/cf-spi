"""Test library for CF_SPI verification — 8 tests covering full SPI functionality."""

import os
from pathlib import Path

import cocotb
import pyuvm
from pyuvm import uvm_root, ConfigDB

from cocotb.triggers import ClockCycles
from cocotb_coverage.coverage import coverage_db

from cf_verify.base.base_test import base_test
from cf_verify.base.top_env import top_env
from cf_verify.bus_env.bus_regs import BusRegs
from cf_verify.bus_env.bus_seq_lib import write_read_regs_seq, reset_seq
from cf_verify.ip_env.ip_agent import ip_agent
from cf_verify.ip_env.ip_driver import ip_driver
from cf_verify.ip_env.ip_monitor import ip_monitor
from cf_verify.ip_env.ip_coverage import ip_coverage

from ip_agent.spi_driver import spi_driver
from ip_agent.spi_monitor import spi_monitor
from ip_coverage.spi_coverage import spi_coverage
from ip_scoreboard import spi_scoreboard


class spi_env(top_env):
    """SPI-specific top environment with proper component wiring."""

    def build_phase(self):
        from cf_verify.bus_env.bus_agent import bus_agent
        from cf_verify.ip_env.ip_logger import ip_logger
        from cf_verify.base.ref_model import ref_model

        self.bus_agent = bus_agent("bus_agent", self)
        self.ip_agent = spi_ip_agent("ip_agent", self)
        self.ref_model = ref_model("ref_model", self)
        self.scoreboard = spi_scoreboard("scoreboard", self)
        self.ip_coverage = spi_coverage("ip_coverage", self)
        self.ip_logger = ip_logger("ip_logger", self)

    def connect_phase(self):
        super().connect_phase()
        self.bus_agent.monitor.ap.connect(self.ip_coverage.analysis_export)


class spi_ip_agent(ip_agent):
    driver_cls = spi_driver
    monitor_cls = spi_monitor


class spi_base_test(base_test):
    """Base test for CF_SPI — wires up the SPI environment."""

    def build_phase(self):
        import os
        import cocotb

        dut = cocotb.top
        bus_type = os.environ.get("BUS_TYPE", "APB")
        yaml_file = os.environ.get(
            "YAML_FILE",
            str(Path(__file__).resolve().parent.parent.parent / "CF_SPI.yaml"),
        )
        test_path = os.environ.get("TEST_PATH", "./sim")

        regs = BusRegs(yaml_file)

        ConfigDB().set(None, "*", "DUT", dut)
        ConfigDB().set(None, "*", "BUS_TYPE", bus_type)
        ConfigDB().set(None, "*", "bus_regs", regs)
        ConfigDB().set(None, "*", "irq_exist", regs.get_irq_exist())
        ConfigDB().set(None, "*", "collect_coverage", True)
        ConfigDB().set(None, "*", "disable_logger", False)
        ConfigDB().set(None, "*", "TEST_PATH", test_path)

        self.env = spi_env("env", self)
        super().build_phase()


# ──────────────────────────────────────────
#  8 SPI TESTS
# ──────────────────────────────────────────

@pyuvm.test()
class WriteReadRegsTest(spi_base_test):
    """Write/read all accessible registers."""

    async def run_phase(self):
        from cf_verify.bus_env.bus_seq_lib import write_reg_seq, read_reg_seq

        self.raise_objection()
        # Keep broad auto-generated sequence for register access stimulation.
        seq = write_read_regs_seq("write_read_regs")
        await seq.start(self.env.bus_agent.sequencer)

        # Add strict local assertions so mismatches never pass via log-only behavior.
        regs = ConfigDB().get(None, "", "bus_regs")
        addr = regs.reg_name_to_address
        for reg in regs.get_writable_regs():
            if reg.name in ("IC", "GCLK") or reg.name.endswith("_FLUSH"):
                continue
            wr_val = (
                0xA5 if reg.size <= 8
                else 0xA5A5 if reg.size <= 16
                else 0xDEAD_BEEF
            ) & ((1 << reg.size) - 1)
            await write_reg_seq("wr_chk", addr[reg.name], wr_val).start(
                self.env.bus_agent.sequencer
            )
            rd = read_reg_seq("rd_chk", addr[reg.name])
            await rd.start(self.env.bus_agent.sequencer)
            rd_val = rd.result & ((1 << reg.size) - 1)
            assert rd_val == wr_val, (
                f"WriteReadRegsTest mismatch on {reg.name}: "
                f"wrote 0x{wr_val:x}, read 0x{rd_val:x}"
            )
        self.drop_objection()


@pyuvm.test()
class MOSI_StressTest(spi_base_test):
    """TX stress — sends many bytes through the MOSI path."""

    async def run_phase(self):
        self.raise_objection()
        from seq_lib.spi_tx_seq import spi_tx_seq
        seq = spi_tx_seq("mosi_stress")
        await seq.start(self.env.bus_agent.sequencer)
        dut = ConfigDB().get(self, "", "DUT")
        regs = ConfigDB().get(None, "", "bus_regs")
        pr = regs.read_reg_value("PR")
        bit_cyc = (pr + 1) * 16
        await ClockCycles(dut.CLK, bit_cyc * 12)
        self.drop_objection()


@pyuvm.test()
class MISO_StressTest(spi_base_test):
    """RX stress — receives bytes through MISO path (via loopback)."""

    async def run_phase(self):
        self.raise_objection()
        from seq_lib.spi_loopback_seq import spi_loopback_seq
        seq = spi_loopback_seq("miso_stress")
        await seq.start(self.env.bus_agent.sequencer)
        dut = ConfigDB().get(self, "", "DUT")
        regs = ConfigDB().get(None, "", "bus_regs")
        pr = regs.read_reg_value("PR")
        bit_cyc = (pr + 1) * 16
        await ClockCycles(dut.CLK, bit_cyc * 12)
        self.drop_objection()


@pyuvm.test()
class LoopbackTest(spi_base_test):
    """Loopback — sends data through TX, verifies received through RX."""

    async def run_phase(self):
        self.raise_objection()
        from seq_lib.spi_loopback_seq import spi_loopback_seq
        seq = spi_loopback_seq("loopback")
        await seq.start(self.env.bus_agent.sequencer)
        dut = ConfigDB().get(self, "", "DUT")
        regs = ConfigDB().get(None, "", "bus_regs")
        pr = regs.read_reg_value("PR")
        bit_cyc = (pr + 1) * 16
        await ClockCycles(dut.CLK, bit_cyc * 12)
        self.drop_objection()


@pyuvm.test()
class PrescalerTest(spi_base_test):
    """Prescaler sweep — tests SPI at different clock divider values."""

    async def run_phase(self):
        self.raise_objection()
        from seq_lib.spi_prescaler_seq import spi_prescaler_seq
        seq = spi_prescaler_seq("prescaler_test")
        await seq.start(self.env.bus_agent.sequencer)
        self.drop_objection()


@pyuvm.test()
class InterruptTest(spi_base_test):
    """Interrupt — verifies all interrupt sources fire and clear correctly."""

    async def run_phase(self):
        self.raise_objection()
        from seq_lib.spi_interrupt_seq import spi_interrupt_seq
        seq = spi_interrupt_seq("irq_test")
        await seq.start(self.env.bus_agent.sequencer)
        self.drop_objection()


@pyuvm.test()
class FIFOTest(spi_base_test):
    """FIFO — verifies FIFO full, empty, threshold, and flush."""

    async def run_phase(self):
        self.raise_objection()
        from seq_lib.spi_fifo_seq import spi_fifo_seq
        seq = spi_fifo_seq("fifo_test")
        await seq.start(self.env.bus_agent.sequencer)
        self.drop_objection()


@pyuvm.test()
class ConfigTest(spi_base_test):
    """Config — tests all CPOL/CPHA combinations."""

    async def run_phase(self):
        self.raise_objection()
        from seq_lib.spi_config_seq import spi_config_seq
        from cf_verify.bus_env.bus_seq_lib import write_reg_seq, read_reg_seq

        regs = ConfigDB().get(None, "", "bus_regs")
        addr = regs.reg_name_to_address
        dut = ConfigDB().get(self, "", "DUT")

        for cpol in [0, 1]:
            for cpha in [0, 1]:
                config = spi_config_seq(
                    "config", prescaler=4, cpol=cpol, cpha=cpha, rx_en=1,
                )
                await config.start(self.env.bus_agent.sequencer)

                pr = regs.read_reg_value("PR")
                bit_cyc = (pr + 1) * 16

                for byte_val in [0x55, 0xAA, 0x00, 0xFF]:
                    await write_reg_seq("tx", addr["TXDATA"], byte_val).start(
                        self.env.bus_agent.sequencer
                    )
                    await ClockCycles(dut.CLK, bit_cyc * 12)

                await read_reg_seq("status", addr["STATUS"]).start(
                    self.env.bus_agent.sequencer
                )

        self.drop_objection()


@pyuvm.test()
class CoverageClosureTest(spi_base_test):
    """Coverage closure — systematically exercises all coverage bins."""

    async def run_phase(self):
        self.raise_objection()
        from seq_lib.spi_coverage_closure_seq import spi_coverage_closure_seq
        seq = spi_coverage_closure_seq("cov_closure")
        await seq.start(self.env.bus_agent.sequencer)
        self.drop_objection()
