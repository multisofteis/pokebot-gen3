# FireRed/LeafGreen RNG search (developer notes)

The first implementation adds a deterministic Gen III LCRNG Method 1 search helper in
`modules/rng_manipulation.py`. It is deliberately a backend API rather than an automatic
bot mode until each encounter call site is calibrated.

## Model

The LCRNG state transition is:

`state = (state * 0x41C64E6D + 0x6073) & 0xFFFFFFFF`

For a Method 1 frame, the next four RNG calls supply PID high word, PID low word,
IV word 1, and IV word 2. IVs are decoded in HP / Attack / Defense / Speed /
Special Attack / Special Defense order. A Pokémon is shiny when
`((PID >> 16) ^ (PID & 0xFFFF) ^ TID ^ SID) < 8`.

## API

- `search_method1(seed, max_advances, SearchCriteria(...))`: search from a known state.
- `search_from_live_rng(max_advances, ...)`: take the current state from `gRngValue`.
- `set_live_rng_seed(frame.seed)`: write a selected candidate's pre-generation state.

Example:

```python
from modules.rng_manipulation import SearchCriteria, search_from_live_rng

criteria = SearchCriteria(
    nature="Timid",
    shiny=True,
    tid=12345,
    sid=54321,
    min_ivs=(20, 20, 20, 20, 20, 20),
)
for target in search_from_live_rng(1_000_000, criteria, limit=10):
    print(target.advance, hex(target.seed), hex(target.pid), target.ivs)
```

A returned advance is an RNG-call count, **not a frame count**. A candidate's
seed must only be installed immediately before the actual Method 1 generation
calls. FireRed starters, stationary encounters, and wild encounters can use
different call sequences/methods; don't apply Method 1 blindly to all of them.
The first step toward end-to-end targeting is to validate the generation point
and call count against a known emulator test seed for each encounter type.
