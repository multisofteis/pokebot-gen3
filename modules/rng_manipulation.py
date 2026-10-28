"""Generation III LCRNG search helpers.

The search operates on the RNG state immediately *before* the first PID call.
For Method 1 encounters, four successive RNG calls produce PID-low, PID-high,
IV-word 1 and IV-word 2. The module is deliberately independent of encounter
automation so that the call site can be calibrated for each FireRed encounter.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from modules.context import context
from modules.memory import pack_uint32, read_symbol, unpack_uint32, write_symbol

LCRNG_MULTIPLIER = 0x41C64E6D
LCRNG_ADDEND = 0x6073
UINT32_MASK = 0xFFFFFFFF
LCRNG_MULTIPLIER_INVERSE = pow(LCRNG_MULTIPLIER, -1, 1 << 32)

NATURES = (
    "Hardy", "Lonely", "Brave", "Adamant", "Naughty",
    "Bold", "Docile", "Relaxed", "Impish", "Lax",
    "Timid", "Hasty", "Serious", "Jolly", "Naive",
    "Modest", "Mild", "Quiet", "Bashful", "Rash",
    "Calm", "Gentle", "Sassy", "Careful", "Quirky",
)


def next_seed(seed: int) -> int:
    """Return the state after one Gen III Random() call."""
    return (seed * LCRNG_MULTIPLIER + LCRNG_ADDEND) & UINT32_MASK


def previous_seed(seed: int) -> int:
    """Invert one Gen III LCRNG call (the multiplier is odd, so invertible mod 2**32)."""
    return ((seed - LCRNG_ADDEND) * LCRNG_MULTIPLIER_INVERSE) & UINT32_MASK


def advance_seed(seed: int, advances: int) -> int:
    """Advance a seed by N calls; negative advances are also supported."""
    if advances >= 0:
        for _ in range(advances):
            seed = next_seed(seed)
    else:
        for _ in range(-advances):
            seed = previous_seed(seed)
    return seed & UINT32_MASK


def _next_u16(state: int) -> tuple[int, int]:
    state = next_seed(state)
    return state, state >> 16


@dataclass(frozen=True)
class Method1Frame:
    """A Method 1 candidate; seed is the state immediately before PID generation."""

    seed: int
    advance: int
    pid: int
    nature: str
    ivs: tuple[int, int, int, int, int, int]  # HP, Atk, Def, Speed, SpA, SpD
    shiny_xor: int

    @property
    def is_shiny(self) -> bool:
        return self.shiny_xor < 8


@dataclass(frozen=True)
class SearchCriteria:
    """Optional filters for a Method 1 search."""

    nature: str | None = None
    shiny: bool | None = None
    tid: int | None = None
    sid: int | None = None
    min_ivs: tuple[int, int, int, int, int, int] = (0, 0, 0, 0, 0, 0)
    max_ivs: tuple[int, int, int, int, int, int] = (31, 31, 31, 31, 31, 31)
    pid: int | None = None
    gender: str | None = None
    ability: str | None = None
    species_abilities: tuple[str, ...] = ()
    gender_ratio: int = 31

    def __post_init__(self) -> None:
        if self.nature is not None and self.nature not in NATURES:
            raise ValueError(f"Unknown nature: {self.nature}")
        if self.gender not in (None, "male", "female"):
            raise ValueError("Gender must be 'male', 'female', or None")
        if self.ability is not None and self.species_abilities and self.ability not in self.species_abilities:
            raise ValueError(f"Ability {self.ability!r} is not available for this species")
        if not 0 <= self.gender_ratio <= 255:
            raise ValueError("Gender ratio must be between 0 and 255")
        if (self.tid is None) != (self.sid is None):
            raise ValueError("TID and SID must either both be provided or both omitted")
        if self.shiny is not None and self.tid is None:
            raise ValueError("A shiny filter requires both TID and SID")
        if self.tid is not None and not (0 <= self.tid <= 0xFFFF):
            raise ValueError("TID must be a 16-bit unsigned integer")
        if self.sid is not None and not (0 <= self.sid <= 0xFFFF):
            raise ValueError("SID must be a 16-bit unsigned integer")
        if len(self.min_ivs) != 6 or len(self.max_ivs) != 6:
            raise ValueError("IV bounds must contain six values in HP/Atk/Def/Speed/SpA/SpD order")
        if any(not 0 <= value <= 31 for value in (*self.min_ivs, *self.max_ivs)):
            raise ValueError("IV bounds must be between 0 and 31")
        if any(low > high for low, high in zip(self.min_ivs, self.max_ivs)):
            raise ValueError("Each minimum IV must be less than or equal to its maximum")


def generate_method1(seed: int, advance: int = 0, tid: int = 0, sid: int = 0) -> Method1Frame:
    """Generate a Method 1 PID/IV frame from its pre-generation RNG state."""
    # Gen III consumes the first PID half as the low word, then the high word.
    state, pid_low = _next_u16(seed)
    state, pid_high = _next_u16(state)
    state, iv_word_1 = _next_u16(state)
    state, iv_word_2 = _next_u16(state)

    pid = (pid_high << 16) | pid_low
    ivs = (
        iv_word_1 & 31,
        (iv_word_1 >> 5) & 31,
        (iv_word_1 >> 10) & 31,
        iv_word_2 & 31,
        (iv_word_2 >> 5) & 31,
        (iv_word_2 >> 10) & 31,
    )
    shiny_xor = (pid >> 16) ^ (pid & 0xFFFF) ^ tid ^ sid
    return Method1Frame(
        seed=seed & UINT32_MASK,
        advance=advance,
        pid=pid,
        nature=NATURES[pid % 25],
        ivs=ivs,
        shiny_xor=shiny_xor,
    )


def _matches(frame: Method1Frame, criteria: SearchCriteria) -> bool:
    if criteria.nature is not None and frame.nature != criteria.nature:
        return False
    if criteria.pid is not None and frame.pid != criteria.pid:
        return False
    if criteria.shiny is not None:
        if criteria.tid is None or criteria.sid is None:
            raise ValueError("A shiny filter requires both TID and SID")
        if frame.is_shiny != criteria.shiny:
            return False
    if criteria.gender is not None:
        if criteria.gender_ratio == 0:
            gender = "male"
        elif criteria.gender_ratio == 254:
            gender = "female"
        elif criteria.gender_ratio == 255:
            gender = None
        else:
            gender = "male" if (frame.pid & 0xFF) >= criteria.gender_ratio else "female"
        if gender != criteria.gender:
            return False
    if criteria.ability is not None:
        if not criteria.species_abilities or criteria.ability not in criteria.species_abilities:
            return False
        if len(criteria.species_abilities) > 1:
            ability_slot = frame.pid & 1
            if criteria.species_abilities[ability_slot] != criteria.ability:
                return False
    return all(
        low <= iv <= high
        for iv, low, high in zip(frame.ivs, criteria.min_ivs, criteria.max_ivs)
    )


def search_method1(
    seed: int,
    max_advances: int,
    criteria: SearchCriteria = SearchCriteria(),
    *,
    start_advance: int = 0,
    limit: int | None = 100,
    tid: int = 0,
    sid: int = 0,
) -> Iterator[Method1Frame]:
    """Search inclusive advances [start_advance, max_advances] from a known seed.

    The returned frame.seed is the exact state to install immediately before the
    encounter's Method 1 PID/IV calls. It is not a frame count and must not be
    applied at an arbitrary point in the game's script.
    """
    if start_advance < 0 or max_advances < start_advance:
        raise ValueError("Expected 0 <= start_advance <= max_advances")
    if limit is not None and limit < 1:
        raise ValueError("limit must be positive or None")
    if not 0 <= tid <= 0xFFFF or not 0 <= sid <= 0xFFFF:
        raise ValueError("TID and SID must be 16-bit unsigned integers")
    if criteria.tid is not None:
        tid, sid = criteria.tid, criteria.sid

    state = advance_seed(seed & UINT32_MASK, start_advance)
    found = 0
    for advance in range(start_advance, max_advances + 1):
        frame = generate_method1(state, advance, tid, sid)
        if _matches(frame, criteria):
            yield frame
            found += 1
            if limit is not None and found >= limit:
                return
        state = next_seed(state)


def read_live_rng_seed() -> int:
    """Read the current game's gRngValue state."""
    return unpack_uint32(read_symbol("gRngValue"))


def search_from_live_rng(
    max_advances: int,
    criteria: SearchCriteria = SearchCriteria(),
    *,
    start_advance: int = 0,
    limit: int | None = 100,
    tid: int = 0,
    sid: int = 0,
) -> Iterator[Method1Frame]:
    """Search Method 1 candidates relative to the live emulator RNG state."""
    return search_method1(
        read_live_rng_seed(),
        max_advances,
        criteria,
        start_advance=start_advance,
        limit=limit,
        tid=tid,
        sid=sid,
    )


def set_live_rng_seed(seed: int) -> None:
    """Set gRngValue to a searched pre-generation state.

    Callers must only use this immediately before the matching encounter's RNG
    calls. Writing the state at the wrong point can desynchronise the game's RNG
    and does not make an arbitrary encounter Method 1.
    """
    if not 0 <= seed <= UINT32_MASK:
        raise ValueError("Seed must be a 32-bit unsigned integer")
    if not (context.rom.is_frlg):
        raise RuntimeError("Live RNG targeting is currently enabled only for FireRed/LeafGreen")
    write_symbol("gRngValue", pack_uint32(seed))



def recover_method1_pre_pid_seed(
    pid: int, ivs: tuple[int, int, int, int, int, int] | None = None
) -> int | None:
    """Recover the pre-PID RNG state from a Method 1 PID, optionally disambiguating with IVs.

    The PID gives two consecutive upper-16-bit outputs, low word first. Several lower-word
    candidates can occasionally fit those outputs, so the six observed IVs are
    used when available to select the actual Method 1 frame.
    """
    pid_high = (pid >> 16) & 0xFFFF
    pid_low = pid & 0xFFFF
    matches: list[int] = []
    # The first Random() output supplies PID-low; the second supplies PID-high.
    for lower in range(0x10000):
        first_state = (pid_low << 16) | lower
        if (next_seed(first_state) >> 16) != pid_high:
            continue
        pre_pid_seed = previous_seed(first_state)
        if ivs is not None:
            frame = generate_method1(pre_pid_seed)
            if frame.pid != pid or frame.ivs != ivs:
                continue
        matches.append(pre_pid_seed)
        if len(matches) > 1:
            return None
    return matches[0] if matches else None


def seed_was_passed(
    previous_seed_value: int,
    current_seed: int,
    target_seed: int,
    max_steps: int = 256,
) -> bool | None:
    """Check whether target_seed was skipped between two observed RNG states.

    Returns True if the target appears before current_seed in the forward LCRNG
    sequence, False if current_seed is reached first, or None if the observed
    state transition exceeds max_steps. This makes per-frame trigger monitoring
    proportional to RNG calls since the previous poll rather than a fixed 20k scan.
    """
    if max_steps < 1:
        return None
    state = previous_seed_value & UINT32_MASK
    current_seed &= UINT32_MASK
    target_seed &= UINT32_MASK
    target_seen = False
    for _ in range(max_steps):
        state = next_seed(state)
        if state == current_seed:
            return target_seen
        if state == target_seed:
            target_seen = True
    return None


def seed_distance(start_seed: int, target_seed: int, max_steps: int = 20000) -> int | None:
    """Return signed LCRNG calls from start_seed to target_seed, within max_steps."""
    state = start_seed & UINT32_MASK
    if state == (target_seed & UINT32_MASK):
        return 0
    forward = state
    backward = state
    for distance in range(1, max_steps + 1):
        forward = next_seed(forward)
        if forward == (target_seed & UINT32_MASK):
            return distance
        backward = previous_seed(backward)
        if backward == (target_seed & UINT32_MASK):
            return -distance
    return None
