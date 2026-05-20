#ifndef CF_SPI_C
#define CF_SPI_C

#include <CF_SPI.h>

void CF_SPI_setGclkEnable (uint32_t spi_base, int value){
    CF_SPI_TYPE* spi = (CF_SPI_TYPE*)spi_base;
    spi->GCLK = value;
}

void CF_SPI_writeData(uint32_t spi_base, int data){

    CF_SPI_TYPE* spi = (CF_SPI_TYPE*)spi_base;

    spi->TXDATA = data;
}

int CF_SPI_readData(uint32_t spi_base){
    CF_SPI_TYPE* spi = (CF_SPI_TYPE*)spi_base;

    return (spi->RXDATA);
}

void CF_SPI_writepolarity(uint32_t spi_base, bool polarity){

    CF_SPI_TYPE* spi = (CF_SPI_TYPE*)spi_base;

    int config = spi->CFG;
    if (polarity == true)
        config |= CF_SPI_CFG_REG_CPOL_MASK;
    else
        config &= ~CF_SPI_CFG_REG_CPOL_MASK;
    spi->CFG = config; 
}

void CF_SPI_writePhase(uint32_t spi_base, bool phase){

    CF_SPI_TYPE* spi = (CF_SPI_TYPE*)spi_base;

    int config = spi->CFG;
    if (phase == true)
        config |= CF_SPI_CFG_REG_CPHA_MASK;
    else
        config &= ~CF_SPI_CFG_REG_CPHA_MASK;
    spi->CFG = config;
}


int CF_SPI_readTxFifoEmpty(uint32_t spi_base){

    CF_SPI_TYPE* spi = (CF_SPI_TYPE*)spi_base;

    return (spi->STATUS & CF_SPI_STATUS_REG_TX_E_MASK);
}

int CF_SPI_readRxFifoEmpty(uint32_t spi_base){

    CF_SPI_TYPE* spi = (CF_SPI_TYPE*)spi_base;

    return ((spi->STATUS & CF_SPI_STATUS_REG_RX_E_MASK) >> CF_SPI_STATUS_REG_RX_E_BIT);
}


void CF_SPI_waitTxFifoEmpty(uint32_t spi_base){
    CF_SPI_TYPE* spi = (CF_SPI_TYPE*)spi_base;
    while(CF_SPI_readTxFifoEmpty(spi_base) == 0);
}

void CF_SPI_waitRxFifoNotEmpty(uint32_t spi_base){
    CF_SPI_TYPE* spi = (CF_SPI_TYPE*)spi_base;
    while(CF_SPI_readRxFifoEmpty(spi_base) == 1);
}
void CF_SPI_FifoRxFlush(uint32_t spi_base){
    CF_SPI_TYPE* spi = (CF_SPI_TYPE*)spi_base;
    spi->RX_FIFO_FLUSH = 1;
}

void CF_SPI_enable(uint32_t spi_base){
    CF_SPI_TYPE* spi = (CF_SPI_TYPE*)spi_base;
    int control = spi->CTRL;
    control |= CF_SPI_CTRL_REG_ENABLE_MASK;
    spi->CTRL = control;
    // control &= ~1;
    // spi->CTRL = control;
}

void CF_SPI_disable(uint32_t spi_base){
    CF_SPI_TYPE* spi = (CF_SPI_TYPE*)spi_base;
    int control = spi->CTRL;
    control &= ~CF_SPI_CTRL_REG_ENABLE_MASK;
    spi->CTRL = control;
}

void CF_SPI_enableRx(uint32_t spi_base){
    CF_SPI_TYPE* spi = (CF_SPI_TYPE*)spi_base;
    int control = spi->CTRL;
    control |= CF_SPI_CTRL_REG_RX_EN_MASK;
    spi->CTRL = control;
}

void CF_SPI_disableRx(uint32_t spi_base){
    CF_SPI_TYPE* spi = (CF_SPI_TYPE*)spi_base;
    int control = spi->CTRL;
    control &= ~CF_SPI_CTRL_REG_RX_EN_MASK;
    spi->CTRL = control;
}


void CF_SPI_assertCs(uint32_t spi_base){
    CF_SPI_TYPE* spi = (CF_SPI_TYPE*)spi_base;
    int control = spi->CTRL;
    control |= CF_SPI_CTRL_REG_SS_MASK;
    spi->CTRL = control;
}

void CF_SPI_deassertCs(uint32_t spi_base){
    CF_SPI_TYPE* spi = (CF_SPI_TYPE*)spi_base;
    int control = spi->CTRL;
    control &= ~CF_SPI_CTRL_REG_SS_MASK;
    spi->CTRL = control;
}

void CF_SPI_setInterruptMask(uint32_t spi_base, int mask){
    CF_SPI_TYPE* spi = (CF_SPI_TYPE*)spi_base;
    // bit 0: Done
    spi->IM = mask;
}

void CF_SPI_setPrescaler(uint32_t spi_base, uint32_t pr_value){
    CF_SPI_TYPE* spi = (CF_SPI_TYPE*)spi_base;
    spi->PR = pr_value;
}

int CF_SPI_isBusy(uint32_t spi_base){
    CF_SPI_TYPE* spi = (CF_SPI_TYPE*)spi_base;
    return (spi->STATUS & CF_SPI_STATUS_REG_BUSY_MASK) != 0;
}

void CF_SPI_waitNotBusy(uint32_t spi_base){
    while(CF_SPI_isBusy(spi_base)){}
}

#endif