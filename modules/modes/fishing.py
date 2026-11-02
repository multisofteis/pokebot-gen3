from typing import Generator

from modules.battle_state import BattleOutcome
from modules.context import context
from modules.gui.multi_select_window import Selection, ask_for_choice
from modules.items import get_item_bag, get_item_by_name
from modules.player import get_player, get_player_avatar
from modules.pokemon_party import get_opponent_party
from modules.rng_manipulation import calibrate_generation_offset, read_live_rng_seed
from modules.runtime import get_sprites_path
from ._asserts import assert_item_exists_in_bag, assert_player_has_poke_balls, assert_boxes_or_party_can_fit_pokemon
from ._interface import BotMode
from .util import fish, register_key_item


class FishingMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Fishing"

    @staticmethod
    def is_selectable() -> bool:
        player = get_player_avatar()
        targeted_tile = player.map_location_in_front
        return targeted_tile is not None and targeted_tile.is_surfable

    def on_battle_ended(self, outcome: "BattleOutcome") -> None:
        if context.rom.is_frlg and self._last_fishing_trigger_seed is not None:
            opponent_party = get_opponent_party()
            if opponent_party is not None and len(opponent_party) > 0:
                pokemon = opponent_party[0]
                ivs = pokemon.ivs
                offset = calibrate_generation_offset(
                    self._last_fishing_trigger_seed,
                    pokemon.personality_value,
                    (ivs.hp, ivs.attack, ivs.defence, ivs.speed, ivs.special_attack, ivs.special_defence),
                    method="FRLG Fishing",
                )
                if offset is not None:
                    if self._fishing_calibration_offsets and offset != self._fishing_calibration_offsets[-1]:
                        self._fishing_calibration_offsets = [offset]
                    else:
                        self._fishing_calibration_offsets.append(offset)
                    if len(self._fishing_calibration_offsets) >= 3:
                        self._calibrated_fishing_trigger_offset = offset
                        context.message = (
                            f"Fishing RNG timing calibrated from 3 matching encounters "
                            f"(trigger offset {offset:+d})."
                        )
            self._last_fishing_trigger_seed = None

        if outcome is not BattleOutcome.Lost:
            assert_player_has_poke_balls()
            assert_boxes_or_party_can_fit_pokemon()

    def run(self) -> Generator:
        assert_player_has_poke_balls()
        assert_boxes_or_party_can_fit_pokemon()

        # Ask player to register a rod if they have one
        rod_names = ["Old Rod", "Good Rod", "Super Rod"]
        assert_item_exists_in_bag(rod_names, "You do not own any fishing rod, so you cannot fish.")

        if get_player().registered_item is None or get_player().registered_item.name not in rod_names:
            possible_rods = [
                rod_name for rod_name in rod_names if get_item_bag().quantity_of(get_item_by_name(rod_name)) > 0
            ]
            if len(possible_rods) == 1:
                rod_to_use = get_item_by_name(possible_rods[0])
            else:
                choices = [Selection(rod, get_sprites_path() / "items" / f"{rod}.png") for rod in possible_rods]
                rod_to_use = get_item_by_name(ask_for_choice(choices, window_title="Choose which rod to use"))

            yield from register_key_item(rod_to_use)

        self._last_fishing_trigger_seed: int | None = None
        self._fishing_calibration_offsets: list[int] = []
        self._calibrated_fishing_trigger_offset: int | None = None

        yield from fish(loop=True, before_cast=self._capture_fishing_trigger_seed)

    def _capture_fishing_trigger_seed(self) -> None:
        self._last_fishing_trigger_seed = read_live_rng_seed()
