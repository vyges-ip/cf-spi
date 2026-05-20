"""SPI configuration sequence — sets up prescaler, CFG, CTRL, IM registers."""

import random

from pyuvm import uvm_sequence, ConfigDB

from cf_verify.bus_env.bus_seq_lib import write_reg_seq, reset_seq


class spi_config_seq(uvm_sequence):
    def __init__(self, name="spi_config_seq", prescaler=None, cpol=None,
                 cpha=None, im=None, ss=1, enable=1, rx_en=1):
        super().__init__(name)
        self.prescaler = prescaler
        self.cpol = cpol
        self.cpha = cpha
        self.im = im
        self.ss = ss
        self.enable = enable
        self.rx_en = rx_en

    async def body(self):
        await reset_seq("rst").start(self.sequencer)

        regs = ConfigDB().get(None, "", "bus_regs")
        addr = regs.reg_name_to_address

        # Enable clock gate
        if "GCLK" in addr:
            await write_reg_seq("wr_gclk", addr["GCLK"], 1).start(self.sequencer)

        # Disable SPI first
        await write_reg_seq("wr_ctrl_off", addr["CTRL"], 0).start(self.sequencer)

        # Prescaler (minimum 2 per spec)
        pr = self.prescaler if self.prescaler is not None else random.choice([4, 8])
        await write_reg_seq("wr_pr", addr["PR"], pr).start(self.sequencer)

        # Configuration: cpol + cpha
        cpol = self.cpol if self.cpol is not None else random.randint(0, 1)
        cpha = self.cpha if self.cpha is not None else random.randint(0, 1)
        cfg = cpol | (cpha << 1)
        await write_reg_seq("wr_cfg", addr["CFG"], cfg).start(self.sequencer)

        # Interrupt mask
        im_val = self.im if self.im is not None else 0x3F
        if "IM" in addr:
            await write_reg_seq("wr_im", addr["IM"], im_val).start(self.sequencer)

        # Enable SPI: SS[0], enable[1], rx_en[2]
        ctrl = (self.ss & 1) | ((self.enable & 1) << 1) | ((self.rx_en & 1) << 2)
        await write_reg_seq("wr_ctrl", addr["CTRL"], ctrl).start(self.sequencer)
