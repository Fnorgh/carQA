# softwareQA Changes — pandad SPI Edge Cases

**Branch:** `selfdrive/pandad/astra`
**Date:** 21 April 2026
**Author:** Astra

---

## File Added
`pandad_spi/test_pandad_spi_edgecases.py`
Edge case tests for `selfdrive/pandad/tests/test_pandad_spi.py`

---

## Tests Added

### 1. `test_null_dat_field_in_can_frame`
**Missing from:** `test_pandad_spi.py` — no equivalent test exists.
**Nearest code:** line 41 — `send_random_can_messages(sendcan, random.randrange(2, 20))` always sends frames with populated `dat`; empty `dat` is never exercised.
**Checks:** pandad doesn't crash, no corrupted `src > 4` frames returned.
**Why it matters:** A zero-length `dat` is a legal edge case in the CAN spec. If pandad doesn't guard against it, it can attempt to read/copy 0 bytes in a way that triggers undefined behaviour in the SPI serialisation layer, causing a silent crash or a malformed frame being forwarded downstream to the controls stack, which could act on garbage data.

### 2. `test_empty_sendcan_list`
**Missing from:** `test_pandad_spi.py` — no equivalent test exists.
**Nearest code:** line 41 — `random.randrange(2, 20)` lower bound is 2, so zero frames are never sent.
**Checks:** pandad keeps publishing `pandaStates` after receiving 0-frame sendcan.
**Why it matters:** `sendcan` with 0 frames is a valid message, since it controls may legitimately send it when there is nothing to transmit. If pandad treats an empty list as an error condition and exits or stalls, the entire driving stack loses its CAN output path, which is a safety-critical failure.

### 3. `test_high_bus_messages_are_filtered`
**Missing from:** `test_pandad_spi.py` line 57 — `if msg.src > 4: continue` silently skips high-bus frames with no assertion. A broken filter would still pass.
**Also missing:** no frame with `src > 4` is ever injected to verify the filter actively blocks it.
**Checks:** Explicitly counts and asserts zero high-bus frames leaked through.
**Why it matters:** Bus numbers above 4 do not correspond to any physical CAN bus on the panda hardware. A frame with `src > 4` is either corrupted data or a spoofed injection. If it leaks through to the controls stack, it could be interpreted as a real sensor reading and influence steering, braking, or throttle decisions.

### 4. `test_fan_speed_rpm_zero_is_valid`
**Missing from:** `test_pandad_spi.py` line 75 — `assert ps.fanSpeedRpm < 10000` has no lower bound.
**Checks:** `0 <= fanSpeedRpm < 10000` — zero is valid (fan off / cold start).
**Why it matters:** `fanSpeedRpm = 0` is the reading when the fan is off (cold start, low-load state). If a future regression adds a `> 0` guard, it would raise a false alarm every time the device boots cold, flooding logs with phantom hardware faults and potentially triggering unnecessary thermal shutdowns.

### 5. `test_voltage_boundary_values`
**Missing from:** `test_pandad_spi.py` lines 67 and 72 — `assert 4000 < ps.voltage < 14000` uses strict bounds on both `pandaStates` and `peripheralState`.
**Checks:** `4000 <= voltage <= 14000` using inclusive bounds.
**Why it matters:** The strict `<` / `>` means a reading of exactly 4000 mV or 14000 mV — both physically valid — would fail the assertion and be reported as a hardware fault. This is a spec error: the boundary values are defined as acceptable in the panda hardware documentation, so the test should match that definition exactly.

### 6. `test_panda_uptime_is_nonzero`
**Missing from:** `test_pandad_spi.py` line 65 — `assert ps.uptime < 1000` has no lower bound.
**Checks:** `0 < uptime < 1000`.
**Why it matters:** `uptime = 0` means the panda either never started or its timer register was never read correctly. The original test would pass this silently. In practice, a zero uptime means all subsequent state (ignition, voltage, CAN) is also unreliable, therefore the test should reject this as an invalid initialisation state.

### 7. `test_can_packet_drop_ratio`
**Missing from:** `test_pandad_spi.py` line 107 — `assert total_recv_count > 20` is a flat count with no relation to how many were sent.
**Checks:** `recv / sent >= 0.80` — drop rate must stay under 20%.
**Why it matters:** Receiving 21 frames out of 500 sent would pass the original assertion, yet that is a 96% drop rate — catastrophic for a safety system. The controls stack depends on continuous CAN feedback - a high drop rate means actuator commands go unacknowledged and sensor data is missing, both of which can cause the vehicle to behave unexpectedly.

### 8. `test_spi_zero_error_rate_baseline`
**Missing from:** `test_pandad_spi.py` lines 18–19 — `SPI_ERR_PROB=0.001` is hardcoded in `setup_class` and never overridden to 0.
**Checks:** With `SPI_ERR_PROB=0`, delivery ratio must be `>= 95%`.
**Why it matters:** All existing tests run with a non-zero error probability, so they can never distinguish between drops caused by injected SPI corruption and drops caused by a genuine bug in the clean-path logic. A zero error baseline isolates the nominal code path. If delivery falls below 95% with no faults injected, there is a real bug in pandad's normal operation, not just expected degradation under corruption.

---

## Files Changed

| File | Change |
|---|---|
| `softwareQA/pandad_spi/test_pandad_spi_edgecases.py` | Created — 8 new edge case tests |
| `softwareQA/CHANGES.md` | Created — this file |

## Original File (not modified)

`selfdrive/pandad/tests/test_pandad_spi.py` — untouched.
All additions are isolated in `softwareQA/pandad_spi/` to keep QA work separate from the main test suite.
