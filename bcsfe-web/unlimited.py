"""Battle Cats Unlimited: the game's limits are lifted.

Every amount can go up to the largest number its slot in the save file can hold (going past that
would wrap around and corrupt the save), and character levels can go past each character's own
limit. The game was never made for these values: they can crash it, get reset by the game server,
or get the account banned.
"""
from __future__ import annotations

from typing import Any

I32_MAX = 2_147_483_647  # 4-byte number slots: Cat Food, XP, tickets, items, materials...
I16_MAX = 32_767  # 2-byte number slots: Leadership, talent orbs, labyrinth medals
U16_MAX = 65_535  # character base and plus levels
LEVEL_MAX = U16_MAX + 1  # base levels are shown one higher than they are stored

# Largest value each amount's slot in the save can hold (BCSFE's max-value names).
STORAGE_MAX = {
    "catfood": I32_MAX,
    "xp": I32_MAX,
    "normal_tickets": I32_MAX,
    "hundred_million_tickets": I32_MAX,
    "rare_tickets": I32_MAX,
    "platinum_tickets": I32_MAX,
    "legend_tickets": I32_MAX,
    "np": I32_MAX,
    "leadership": I16_MAX,
    "battle_items": I32_MAX,
    "catamins": I32_MAX,
    "catseyes": I32_MAX,
    "catfruit_old": I32_MAX,
    "catfruit_new": I32_MAX,
    "base_materials": I32_MAX,
    "labyrinth_medals": I16_MAX,
    "talent_orbs": I16_MAX,
    "treasure_chests": I32_MAX,
}


def install(core: Any) -> None:
    """Make BCSFE's max-value table hand out the storage limits instead of the game's."""
    helper_cls = core.MaxValueHelper
    if getattr(helper_cls, "_unlimited", False):
        return
    original = helper_cls.from_file

    def from_file(*args: Any, **kwargs: Any) -> Any:
        helper = original(*args, **kwargs)
        for key, value in STORAGE_MAX.items():
            setattr(helper, key, value)
        return helper

    helper_cls.from_file = staticmethod(from_file)
    helper_cls._unlimited = True
    data = getattr(core, "core_data", None)
    if data is not None and getattr(data, "max_value_manager", None) is not None:
        for key, value in STORAGE_MAX.items():
            setattr(data.max_value_manager, key, value)
