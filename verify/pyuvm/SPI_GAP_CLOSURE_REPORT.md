# CF_SPI Gap Closure Report

## Baseline (Before Hardening)

- Regression: **27/27 pass**
- Functional coverage: **117/121 (96.7%)**
- Known holes:
  - `Status.RX_F`
  - `reg.STATUS.RX_F`
  - `Status.done`
  - `reg.STATUS.done`
- False-green risks:
  - Scoreboard did not enforce zero mismatches / non-zero checks.
  - SPI compare ignored `cpol`/`cpha`.
  - `WriteReadRegsTest` depended on log-only mismatch reporting in shared `write_read_regs_seq`.
  - Interrupt/FIFO sequences had weak assertions (`non-zero` checks instead of bit-accurate checks).

## Hardening Changes Applied (TB)

- `ip_item/spi_item.py`
  - `do_compare()` now compares `data`, `direction`, `cpol`, and `cpha`.
- `ip_scoreboard.py`
  - Added `bus_count`.
  - Added strict `check_phase()` assertions:
    - `failed == 0`
    - total checks > 0.
- `test_lib.py`
  - `WriteReadRegsTest` now adds strict local readback assertions for all writable non-volatile regs.
- `seq_lib/spi_interrupt_seq.py`
  - Added explicit bit-level assertions for `RIS`/`MIS`.
  - Added per-bit `IM` readback and mask-consistency checks.
  - Added sticky-level-aware `IC` clear verification.
- `seq_lib/spi_fifo_seq.py`
  - Added deterministic FIFO level/full/empty assertions.
  - Added explicit `STATUS` and `RIS` bit checks.
  - Added RX FIFO full scenario with assertions.
- `seq_lib/spi_coverage_closure_seq.py`
  - FIFO sweep tuned so `RX_FIFO.level` hits the **high (13–15)** bin; `STATUS.done` check after RTL fix.
- `ip_coverage/spi_cov_groups.py`
  - RX semantic coverage from `RXDATA` reads is gated by FIFO/data evidence to avoid inflated coverage.

## RTL Fix: Observable `STATUS.done`

**Root cause:** `spi_master` drives `done` high for only a short window (a few system clocks) before returning to idle. Software polling `STATUS` every many cycles could miss it entirely.

**Fix (in `CF_SPI/hdl/rtl/CF_SPI.v`):**

- `done_raw` from `spi_master`; `cf_util_ped` still uses `done_raw` for `done_pe` (RX capture unchanged).
- `done` output to wrappers / `STATUS[7]` is **`done_sticky`**: set on `done_pe`, cleared on the next TX FIFO write (`tx_wr`).

This matches firmware expectation that `STATUS.done` can be polled after a transfer completes.

## Final Results

- Regression: **27/27 pass** (APB, AHB, Wishbone × 9 tests).
- Functional coverage: **121/121 (100.0%)**.

## Conclusion

- TB hardening removes vacuous pass paths; `STATUS.done` is now architecturally visible via sticky latching; FIFO closure sequence fills the last RX level bin.
