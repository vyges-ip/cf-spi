# CF_SPI Failure Triage

## Resolved Failure Class

### F1: `STATUS.done` Not Observable — **Closed**

- **Signature (before fix)**:
  - `AssertionError: STATUS.done was never observed during completed transfer`
- **Root cause**:
  - `spi_master` asserted `done` for only a few clock cycles; slow `STATUS` polling missed the pulse.
- **Resolution**:
  - RTL: sticky `done` in `CF_SPI.v` (set on `done_pe`, clear on next `tx_wr`); `done_pe` still derived from raw `done` from `spi_master`.
- **Verification**:
  - `CoverageClosureTest` passes on all buses; `Status.done` / `reg.STATUS.done` coverage bins close.

## Closed / Mitigated Classes

### C1: Weak interrupt assertions (non-zero-only)
- **Action**: replaced with explicit per-bit checks and mask-consistency assertions.
- **Status**: **Closed**.

### C2: Log-only register mismatch behavior
- **Action**: added strict local readback assertions in `WriteReadRegsTest`.
- **Status**: **Closed**.

### C3: Compare semantics missing SPI mode fields
- **Action**: `spi_item.do_compare()` now includes `cpol`/`cpha`.
- **Status**: **Closed**.

### C4: Scoreboard vacuity risk
- **Action**: scoreboard now asserts `failed == 0` and `total_checks > 0`.
- **Status**: **Closed**.

### C5: RX FIFO `level` high bin (13–15)
- **Action**: coverage closure sequence uses fills **14** and **15** with longer waits so `RX_FIFO_LEVEL` is sampled in the high range.
- **Status**: **Closed**.
