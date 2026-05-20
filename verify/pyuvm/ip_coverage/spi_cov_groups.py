"""SPI coverage groups — auto-generated + SPI-specific custom coverage."""

from cocotb_coverage.coverage import CoverPoint, CoverCross

from cf_verify.coverage.auto_coverage import generate_coverage_from_yaml
from cf_verify.bus_env.bus_item import bus_item
from ip_item.spi_item import spi_item

SPI_FIELD_BINS = {
    ("CFG", "cpol"): [(0, 0), (1, 1)],
    ("CFG", "cpha"): [(0, 0), (1, 1)],
    ("PR", None): [(2, 3), (4, 7), (8, 15), (16, 31), (32, 255)],
}

DATA_BINS = [(i * 32, i * 32 + 31) for i in range(8)]


class spi_cov_groups:
    def __init__(self, hierarchy, regs):
        self.hierarchy = hierarchy
        self.regs = regs

        self.txdata_addr = regs.reg_name_to_address.get("TXDATA")
        self.rxdata_addr = regs.reg_name_to_address.get("RXDATA")

        self.auto_points = generate_coverage_from_yaml(
            regs, hierarchy, field_bins_override=SPI_FIELD_BINS,
        )

        self.data_cov = self._data_coverage()
        self.mode_cov = self._mode_coverage()
        self.status_cov = self._status_coverage()
        self.irq_cov = self._irq_coverage()

        self._init_sample(None)

    def _init_sample(self, tr):
        """Cold-start: register all CoverPoints without actually counting."""
        @self._apply_decorators(
            self.auto_points + self.data_cov + self.mode_cov
            + self.status_cov + self.irq_cov
        )
        def _cold(tr):
            pass

    def sample(self, tr):
        """Sample everything using a spi_item."""
        @self._apply_decorators(
            self.auto_points + self.data_cov + self.mode_cov
            + self.status_cov + self.irq_cov
        )
        def _s(tr):
            pass
        _s(tr)

    def sample_bus(self, tr):
        """Sample from bus transactions; synthesise spi_item for TXDATA/RXDATA."""
        rname = self.regs._reg_address_to_name.get(tr.addr)
        if rname:
            self.regs._reg_values[rname.lower()] = tr.data

        @self._apply_decorators(
            self.auto_points + self.mode_cov + self.status_cov + self.irq_cov
        )
        def _bus(tr):
            pass
        _bus(tr)

        if (self.txdata_addr is not None
                and tr.addr == self.txdata_addr
                and tr.kind == bus_item.WRITE):
            self.sample(self._synth(tr.data, spi_item.TX))
        elif (self.rxdata_addr is not None
              and tr.addr == self.rxdata_addr
              and tr.kind == bus_item.READ):
            # Avoid crediting RX semantic coverage on empty FIFO reads.
            rx_lvl = self.regs.read_reg_value("RX_FIFO_LEVEL")
            if rx_lvl > 0 or tr.data != 0:
                self.sample(self._synth(tr.data, spi_item.RX))

    def _synth(self, data, direction):
        """Build a synthetic spi_item from bus data + current CFG state."""
        cfg = self.regs.read_reg_value("CFG")
        cpol = cfg & 0x1
        cpha = (cfg >> 1) & 0x1

        item = spi_item("synth")
        item.direction = direction
        item.data = data & 0xFF
        item.cpol = cpol
        item.cpha = cpha
        return item

    def _data_coverage(self):
        points = []
        for direction in [spi_item.TX, spi_item.RX]:
            d_str = "TX" if direction == spi_item.TX else "RX"
            points.append(CoverPoint(
                f"{self.hierarchy}.{d_str}.Data",
                xf=lambda tr, d=direction: (
                    (tr.direction, tr.data) if tr else (0, 0)
                ),
                bins=DATA_BINS,
                bins_labels=[f"0x{lo:02x}-0x{hi:02x}" for lo, hi in DATA_BINS],
                rel=lambda val, b, d=direction: (
                    val[0] == d and b[0] <= val[1] <= b[1]
                ),
            ))
        return points

    def _mode_coverage(self):
        return [
            CoverPoint(
                f"{self.hierarchy}.SPI_Mode",
                xf=lambda tr: (
                    self.regs.read_reg_value("CFG") & 0x1,
                    (self.regs.read_reg_value("CFG") >> 1) & 0x1,
                ),
                bins=[(0, 0), (0, 1), (1, 0), (1, 1)],
                bins_labels=["mode0", "mode1", "mode2", "mode3"],
                at_least=1,
            ),
            CoverPoint(
                f"{self.hierarchy}.RX_Enable",
                xf=lambda tr: (self.regs.read_reg_value("CTRL") >> 2) & 1,
                bins=[0, 1], bins_labels=["disabled", "enabled"], at_least=1,
            ),
            CoverPoint(
                f"{self.hierarchy}.SS_Active",
                xf=lambda tr: self.regs.read_reg_value("CTRL") & 1,
                bins=[0, 1], bins_labels=["deselected", "selected"], at_least=1,
            ),
        ]

    def _status_coverage(self):
        labels = [
            ("TX_E", 0), ("TX_F", 1), ("RX_E", 2), ("RX_F", 3),
            ("TX_B", 4), ("RX_A", 5), ("busy", 6), ("done", 7),
        ]
        points = []
        for name, bit in labels:
            points.append(CoverPoint(
                f"{self.hierarchy}.Status.{name}",
                xf=lambda tr, b=bit: (self.regs.read_reg_value("STATUS") >> b) & 1,
                bins=[0, 1], bins_labels=[f"no_{name}", name], at_least=1,
            ))
        return points

    def _irq_coverage(self):
        flags = [
            ("TXE", 0), ("TXF", 1), ("RXE", 2), ("RXF", 3),
            ("TXB", 4), ("RXA", 5),
        ]
        points = []
        for name, bit in flags:
            points.append(CoverPoint(
                f"{self.hierarchy}.IRQ.{name}",
                xf=lambda tr, b=bit: (self.regs.read_reg_value("RIS") >> b) & 1,
                bins=[0, 1], bins_labels=[f"no_{name}", name], at_least=1,
            ))
        return points

    @staticmethod
    def _apply_decorators(decorators):
        def wrapper(func):
            for dec in decorators:
                func = dec(func)
            return func
        return wrapper
