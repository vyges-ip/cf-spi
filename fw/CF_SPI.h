#ifndef CF_SPI_H
#define CF_SPI_H

#include <CF_SPI_regs.h>
#include <stdint.h>
#include <stdbool.h>
void CF_SPI_setGclkEnable (uint32_t spi_base, int value);
void CF_SPI_writeData(uint32_t spi_base, int data);
int CF_SPI_readData(uint32_t spi_base);
void CF_SPI_writepolarity(uint32_t spi_base, bool polarity);
void CF_SPI_writePhase(uint32_t spi_base, bool phase);
int CF_SPI_readTxFifoEmpty(uint32_t spi_base);
int CF_SPI_readRxFifoEmpty(uint32_t spi_base);
void CF_SPI_waitTxFifoEmpty(uint32_t spi_base);
void CF_SPI_waitRxFifoNotEmpty(uint32_t spi_base);
void CF_SPI_FifoRxFlush(uint32_t spi_base);
void CF_SPI_enable(uint32_t spi_base);
void CF_SPI_disable(uint32_t spi_base);
void CF_SPI_enableRx(uint32_t spi_base);
void CF_SPI_disableRx(uint32_t spi_base);
void CF_SPI_assertCs(uint32_t spi_base);
void CF_SPI_deassertCs(uint32_t spi_base);
void CF_SPI_setInterruptMask(uint32_t spi_base, int mask);

// Additional helpers
void CF_SPI_setPrescaler(uint32_t spi_base, uint32_t pr_value);
int  CF_SPI_isBusy(uint32_t spi_base);
void CF_SPI_waitNotBusy(uint32_t spi_base);

#endif