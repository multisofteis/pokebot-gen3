# FireRed/LeafGreen RNG search (developer notes)

The branch now includes a FireRed starter-targeting workflow in `modules/modes/starters.py`.
It asks for shiny status, nature, IV bounds, gender and ability, searches Method 1 candidates
from the live RNG seed, times the first starter input against a candidate state, then uses
the resulting PID and IVs to estimate a timing offset for subsequent resets.

## Model

The LCRNG state transition is:

`state = (state * 0x41C64E6D + 0x6073) & 0xFFFFFFFF`

For a Method 1 frame, the next four RNG calls supply PID low word, PID high word,
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

A returned advance is an RNG-call count, **not a frame count**. The starter mode uses the
frame count as an estimate and checks the live RNG state before pressing A; if the target
state is skipped, it replans. After the starter is generated, it attempts to recover the
pre-PID state using the observed PID and IVs, then updates the offset for later resets.
This is an experimental timing controller and still needs validation against real FireRed
emulator runs: the exact starter script call sequence, menu timing, and frame-to-RNG-call
relationship can vary. It currently targets the Method 1 model only.
