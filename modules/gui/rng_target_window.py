"""Input dialog for FireRed starter RNG targets."""
from __future__ import annotations

from typing import Any

from modules.context import context
from modules.rng_manipulation import NATURES


def _parse_ivs(values: list[str]) -> tuple[tuple[int, ...], tuple[int, ...]]:
    minimum: list[int] = []
    maximum: list[int] = []
    labels = ("HP", "Attack", "Defense", "Speed", "Sp. Attack", "Sp. Defense")
    for label, raw in zip(labels, values):
        value = raw.strip().lower()
        if value in ("", "*", "any", "-"):
            minimum.append(0)
            maximum.append(31)
        elif "-" in value:
            parts = value.split("-", 1)
            if len(parts) != 2:
                raise ValueError(f"{label}: use a value, range such as 20-31, or '-' for any")
            low, high = int(parts[0]), int(parts[1])
            if not 0 <= low <= high <= 31:
                raise ValueError(f"{label}: IV range must be within 0-31")
            minimum.append(low)
            maximum.append(high)
        else:
            exact = int(value)
            if not 0 <= exact <= 31:
                raise ValueError(f"{label}: IV must be within 0-31")
            minimum.append(exact)
            maximum.append(exact)
    return tuple(minimum), tuple(maximum)


def ask_for_starter_rng_target(species_name: str, abilities: list[str]) -> dict[str, Any] | None:
    """Ask for shiny/nature/IV/gender/ability target; supports GUI and headless mode."""
    if context.gui.is_headless:
        from rich.prompt import Prompt

        shiny_text = Prompt.ask("Shiny", choices=["yes", "no", "any"], default="yes").lower()
        nature = Prompt.ask("Nature (or Any)", default="Any").strip().title()
        if nature == "Any":
            nature = None
        elif nature not in NATURES:
            raise ValueError(f"Unknown nature: {nature}")
        iv_text = [
            Prompt.ask(f"{label} IV (0-31, range such as 20-31, or '-' for any)", default="-")
            for label in ("HP", "Attack", "Defense", "Speed", "Sp. Attack", "Sp. Defense")
        ]
        gender_text = Prompt.ask("Gender", choices=["male", "female", "any"], default="any").lower()
        ability_text = Prompt.ask("Ability", choices=["any", *abilities], default="any")
        minimum, maximum = _parse_ivs(iv_text)
        return {
            "shiny": {"yes": True, "no": False, "any": None}[shiny_text],
            "nature": nature,
            "min_ivs": minimum,
            "max_ivs": maximum,
            "gender": None if gender_text == "any" else gender_text,
            "ability": None if ability_text == "any" else ability_text,
        }

    import tkinter as tk
    from tkinter import messagebox, ttk

    window = tk.Toplevel(context.gui.window)
    window.title(f"RNG target — {species_name}")
    window.transient(context.gui.window)
    window.grab_set()
    result: dict[str, Any] | None = None

    shiny_var = tk.StringVar(value="yes")
    nature_var = tk.StringVar(value="Any")
    gender_var = tk.StringVar(value="Any")
    ability_var = tk.StringVar(value="Any")
    iv_vars = [tk.StringVar(value="-") for _ in range(6)]

    frame = ttk.Frame(window, padding=12)
    frame.grid(sticky="nsew")
    ttk.Label(frame, text=f"Target for {species_name}", font=("", 11, "bold")).grid(
        row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
    )

    def add_combo(row: int, label: str, variable: tk.StringVar, values: list[str]) -> None:
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=3)
        ttk.Combobox(frame, textvariable=variable, values=values, state="readonly", width=22).grid(
            row=row, column=1, sticky="ew", pady=3
        )

    add_combo(1, "Shiny", shiny_var, ["yes", "no", "any"])
    add_combo(2, "Nature", nature_var, ["Any", *NATURES])
    add_combo(3, "Gender", gender_var, ["Any", "male", "female"])
    add_combo(4, "Ability", ability_var, ["Any", *abilities])
    ttk.Label(frame, text="IVs (exact, range e.g. 20-31, or '-' for any)").grid(
        row=5, column=0, columnspan=2, sticky="w", pady=(8, 3)
    )
    for row, (label, variable) in enumerate(
        zip(("HP", "Attack", "Defense", "Speed", "Sp. Attack", "Sp. Defense"), iv_vars), start=6
    ):
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=2)
        ttk.Entry(frame, textvariable=variable, width=24).grid(row=row, column=1, sticky="ew", pady=2)

    ttk.Label(
        frame,
        text="The selected ability must be available to the chosen starter.",
        wraplength=330,
    ).grid(row=12, column=0, columnspan=2, sticky="w", pady=(8, 4))

    def submit() -> None:
        nonlocal result
        try:
            nature = nature_var.get()
            nature = None if nature == "Any" else nature
            if nature is not None and nature not in NATURES:
                raise ValueError(f"Unknown nature: {nature}")
            minimum, maximum = _parse_ivs([variable.get() for variable in iv_vars])
            result = {
                "shiny": {"yes": True, "no": False, "any": None}[shiny_var.get()],
                "nature": nature,
                "min_ivs": minimum,
                "max_ivs": maximum,
                "gender": None if gender_var.get() == "Any" else gender_var.get(),
                "ability": None if ability_var.get() == "Any" else ability_var.get(),
            }
            window.destroy()
        except (ValueError, KeyError) as error:
            messagebox.showerror("Invalid RNG target", str(error), parent=window)

    buttons = ttk.Frame(frame)
    buttons.grid(row=13, column=0, columnspan=2, sticky="e", pady=(10, 0))
    ttk.Button(buttons, text="Cancel", command=window.destroy).grid(row=0, column=0, padx=4)
    ttk.Button(buttons, text="Start", command=submit).grid(row=0, column=1, padx=4)
    window.protocol("WM_DELETE_WINDOW", window.destroy)
    window.wait_window()
    return result
