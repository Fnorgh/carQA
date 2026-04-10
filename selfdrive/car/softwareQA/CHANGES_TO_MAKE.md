# Changes To Make

## `car_specific.py`

- Split the brand logic into helper functions or brand handlers so each brand rule has its own clear place instead of being buried in one long update method.
- Rename short names like `CP`, `CS`, and `CC` so someone reading the file can understand the state faster without already knowing the project naming style.
- Replace magic numbers like `0.5`, `1.0`, `2.0`, `0.3`, `20`, and `0.001` with named constants.
- Move brand-only special cases into clearly named helper methods so Honda, Toyota, GM, and Hyundai behavior is easier to find and change.


## `card.py`

- Break up `Car` into smaller pieces with clearer jobs so setup, CAN reading, publishing, and control logic are not all mixed into one class.
- Move out of `__init__`.
- Replace `except Exception` with more specific exceptions so real errors are not hidden by a catch-all block.
- Rename short names like `CI`, `RI`, `CP`, `CS`, `CC`, `RD`, `t`, and `e` so the file is easier to follow.

