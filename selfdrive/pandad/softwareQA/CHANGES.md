# softwareQA Changes — pandad SPI Edge Cases

**Branch:** `selfdrive/pandad/astra`
**Date:** 11 April 2026
**Author:** Astra

---

## What Was Added

### New File: `pandad_spi/test_pandad_spi_edgecases.py`

Edge case tests for [`selfdrive/pandad/tests/test_pandad_spi.py`](../../tests/test_pandad_spi.py).
The original `test_spi_corruption()` test was missing the following scenarios.

---

## Tests Added

### 1. `test_null_dat_field_in_can_frame`
**Gap in original:** `test_spi_corruption()` only validates received frames against a `sent_msgs` dict. It never sends a CAN frame with an empty `dat` field to check that pandad handles it safely.

**What it tests:**
- Sends a `sendcan` message where `dat = b''` (zero-length payload)
- Asserts pandad does not crash
- Asserts no frames with `src > 4` are returned (guards against buffer overflow / corruption bleed-through)

---

### 2. `test_empty_sendcan_list`
**Gap in original:** `send_random_can_messages()` always sends between 2–20 frames. A `sendcan` message with 0 frames is never exercised.

**What it tests:**
- Sends a valid `sendcan` message containing zero CAN frames
- Asserts `pandaStates` keeps publishing after — proving pandad did not crash or hang
- Asserts all returned `pandaStates` messages are marked `valid`

---

### 3. `test_high_bus_messages_are_filtered`
**Gap in original:** The original does `if msg.src > 4: continue` inside the receive loop, silently skipping high-bus frames. It never explicitly asserts the count of such frames is zero.

**What it tests:**
- Sends 20 random CAN messages over loopback
- Collects all received frames where `src > 4`
- Asserts that list is empty — any leak here means filtering is broken
- Prints the first 5 offending `(src, address)` pairs on failure

---

### 4. `test_fan_speed_rpm_zero_is_valid`
**Gap in original:** The original check is `assert ps.fanSpeedRpm < 10000` — only an upper bound. `fanSpeedRpm = 0` (fan off at cold boot) is never explicitly validated as acceptable.

**What it tests:**
- Collects `peripheralState` messages for 2 seconds
- Asserts every `fanSpeedRpm` value is in `[0, 10000)` — with `0` explicitly allowed
- Prints the min/max RPM values seen for visibility
- Guards against any future regression that adds a `> 0` lower bound check

---

## Files Changed

| File | Change |
|---|---|
| `softwareQA/pandad_spi/test_pandad_spi_edgecases.py` | Created — 4 new edge case tests |
| `softwareQA/CHANGES.md` | Created — this file |

## Original File (not modified)

`selfdrive/pandad/tests/test_pandad_spi.py` — untouched.
All additions are isolated in `softwareQA/pandad_spi/` to keep QA work separate from the main test suite.

---
