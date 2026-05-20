"""SPI coverage component — samples both auto-generated and custom coverage."""

from pyuvm import ConfigDB

from cf_verify.ip_env.ip_coverage import ip_coverage
from ip_coverage.spi_cov_groups import spi_cov_groups
from ip_item.spi_item import spi_item


class spi_coverage(ip_coverage):
    def build_phase(self):
        super().build_phase()
        regs = ConfigDB().get(None, "", "bus_regs")
        self.cov_groups = spi_cov_groups("top.ip", regs)

    def sample(self, tr):
        if isinstance(tr, spi_item):
            self.cov_groups.sample(tr)
        else:
            self.cov_groups.sample_bus(tr)
