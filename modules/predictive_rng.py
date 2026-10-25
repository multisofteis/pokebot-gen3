"""Generation III RNG primitives for the experimental predictive-hunting prototype.

Important: this module models the Gen III LCRNG and PID/shiny math only.
It does NOT yet predict the exact next wild encounter. FireRed/LeafGreen consume
random numbers for encounter checks, slots, levels, and other game logic between
Pokémon generation calls. Exact predictions require modeling those calls (and
validating against live emulator memory) before this can be treated as reliable.
"""

from dataclasses import dataclass
from typing import Iterator

# Pokémon Ruby/Sapphire/Emerald/FireRed/LeafGreen use this 32-bit LCRNG.
_MULTIPLIER = 0x41C64E6D
_INCREMENT = 0x6073
_MASK_32 = 0xFFFFFFFF
_MASK_16 = 0xFFFF


@dataclass
class Gen3Rng:
    """A copyable state for the Generation III 32-bit linear congruential RNG."""

    state: int

    def __post_init__(self) -> None:
        self.state &= _MASK_32

    def copy(self) -> "Gen3Rng":
        return Gen3Rng(self.state)

    def next_u16(self) -> int:
        """Advance the RNG once and return the upper 16 bits of the new state."""
        self.state = (_MULTIPLIER * self.state + _INCREMENT) & _MASK_32
        return self.state >> 16

    def next_u32(self) -> int:
        """Return two consecutive RNG outputs combined as a Pokémon PID."""
        high = self.next_u16()
        low = self.next_u16()
        return (high << 16) | low

    def advance(self, calls: int) -> int:
        """Advance by an arbitrary number of RNG calls in O(log(calls)) time.

        Returns the resulting 32-bit state. The original instance is updated.
        """
        if calls < 0:
            raise ValueError("calls must be non-negative")

        # Exponentiate the affine transform x -> a*x + c modulo 2**32.
        acc_mult = 1
        acc_plus = 0
        cur_mult = _MULTIPLIER
        cur_plus = _INCREMENT
        remaining = calls

        while remaining:
            if remaining & 1:
                acc_mult = (acc_mult * cur_mult) & _MASK_32
                acc_plus = (acc_plus * cur_mult + cur_plus) & _MASK_32
            cur_plus = ((cur_mult + 1) * cur_plus) & _MASK_32
            cur_mult = (cur_mult * cur_mult) & _MASK_32
            remaining >>= 1

        self.state = (acc_mult * self.state + acc_plus) & _MASK_32
        return self.state


def shiny_value(personality_value: int, trainer_id: int, secret_id: int) -> int:
    """Calculate the Gen III shiny value (0-65535) for a PID and trainer IDs."""
    pid = personality_value & _MASK_32
    return (
        (trainer_id & _MASK_16)
        ^ (secret_id & _MASK_16)
        ^ (pid & _MASK_16)
        ^ ((pid >> 16) & _MASK_16)
    )


def is_shiny_pid(personality_value: int, trainer_id: int, secret_id: int) -> bool:
    """Return whether this PID is shiny under the Generation III threshold."""
    return shiny_value(personality_value, trainer_id, secret_id) < 8


@dataclass(frozen=True)
class PidCandidate:
    """A candidate from a simplified consecutive-PID stream, not an encounter timeline."""

    pid_index: int
    personality_value: int
    shiny_value: int

    @property
    def is_shiny(self) -> bool:
        return self.shiny_value < 8


def iter_pid_candidates(
    initial_seed: int,
    trainer_id: int,
    secret_id: int,
    count: int,
) -> Iterator[PidCandidate]:
    """Yield PIDs made from consecutive RNG pairs.

    This is useful for validating the RNG primitive and exploring candidate
    streams. It is NOT an exact future-encounter predictor until intervening
    game RNG calls are modeled for the selected game and encounter method.
    """
    if count < 0:
        raise ValueError("count must be non-negative")

    rng = Gen3Rng(initial_seed)
    for index in range(count):
        pid = rng.next_u32()
        yield PidCandidate(
            pid_index=index,
            personality_value=pid,
            shiny_value=shiny_value(pid, trainer_id, secret_id),
        )


def find_shiny_pids(
    initial_seed: int,
    trainer_id: int,
    secret_id: int,
    count: int,
) -> list[PidCandidate]:
    """Return shiny PIDs from the simplified consecutive-PID stream."""
    return [
        candidate
        for candidate in iter_pid_candidates(initial_seed, trainer_id, secret_id, count)
        if candidate.is_shiny
    ]


@dataclass(frozen=True)
class LiveRngSnapshot:
    """RNG and trainer IDs read from the currently running PokéBot emulator."""

    seed: int
    trainer_id: int
    secret_id: int


def read_live_rng_snapshot() -> LiveRngSnapshot:
    """Read the current Gen III RNG state and player IDs from PokéBot's emulator.

    Call this only after a profile and emulator have been initialized. The seed is
    a snapshot of the RNG at that instant; it does not by itself identify which
    future RNG calls will produce the next encounter.
    """
    from modules.memory import read_symbol, unpack_uint32
    from modules.player import get_player

    seed = unpack_uint32(read_symbol("gRngValue", size=4))
    player = get_player()
    return LiveRngSnapshot(
        seed=seed,
        trainer_id=player.trainer_id,
        secret_id=player.secret_id,
    )


@dataclass(frozen=True)
class PidTarget:
    """Optional target constraints that can be evaluated from a PID alone.

    Values are generation-agnostic filters over the PID stream. IVs, encounter
    slot/species, levels, and exact encounter counts require encounter-method
    modeling and are intentionally not inferred here.
    """

    shiny: bool | None = None
    nature_index: int | None = None
    gender: str | None = None
    gender_ratio: int | None = None
    ability_slot: int | None = None

    def __post_init__(self) -> None:
        if self.nature_index is not None and not 0 <= self.nature_index < 25:
            raise ValueError("nature_index must be in the range 0..24")
        if self.gender is not None and self.gender not in ("male", "female", "genderless"):
            raise ValueError("gender must be 'male', 'female', or 'genderless'")
        if self.gender_ratio is not None and not 0 <= self.gender_ratio <= 255:
            raise ValueError("gender_ratio must be in the range 0..255")
        if self.ability_slot is not None and self.ability_slot not in (0, 1):
            raise ValueError("ability_slot must be 0 or 1")
        if self.gender is not None and self.gender_ratio is None:
            raise ValueError("gender_ratio is required when filtering by gender")

    def matches(self, pid: int, trainer_id: int, secret_id: int) -> bool:
        pid &= _MASK_32
        if self.shiny is not None and is_shiny_pid(pid, trainer_id, secret_id) != self.shiny:
            return False
        if self.nature_index is not None and pid % 25 != self.nature_index:
            return False
        if self.ability_slot is not None and (pid & 1) != self.ability_slot:
            return False
        if self.gender is not None:
            ratio = self.gender_ratio
            assert ratio is not None
            if ratio == 255:
                actual_gender = "genderless"
            elif ratio == 0:
                actual_gender = "male"
            elif ratio == 254:
                actual_gender = "female"
            else:
                actual_gender = "male" if (pid & 0xFF) >= ratio else "female"
            if actual_gender != self.gender:
                return False
        return True


@dataclass(frozen=True)
class PidSearchResult:
    """A PID-stream match; index is NOT a game frame or encounter count."""

    pid_candidate_index: int
    personality_value: int
    shiny_value: int
    nature_index: int
    ability_slot: int


def search_pid_targets(
    initial_seed: int,
    trainer_id: int,
    secret_id: int,
    target: PidTarget,
    candidate_limit: int,
    result_limit: int = 100,
) -> list[PidSearchResult]:
    """Search a simplified consecutive PID stream for arbitrary PID traits.

    The result index counts candidate PID pairs in this model. It must not be
    displayed as a game frame or number of encounters without a verified
    encounter-method-specific RNG-call model.
    """
    if candidate_limit < 0:
        raise ValueError("candidate_limit must be non-negative")
    if result_limit < 0:
        raise ValueError("result_limit must be non-negative")

    matches: list[PidSearchResult] = []
    for candidate in iter_pid_candidates(initial_seed, trainer_id, secret_id, candidate_limit):
        pid = candidate.personality_value
        if target.matches(pid, trainer_id, secret_id):
            matches.append(
                PidSearchResult(
                    pid_candidate_index=candidate.pid_index,
                    personality_value=pid,
                    shiny_value=candidate.shiny_value,
                    nature_index=pid % 25,
                    ability_slot=pid & 1,
                )
            )
            if len(matches) >= result_limit:
                break
    return matches
