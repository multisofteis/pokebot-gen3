# Predictive hunting: intended architecture

This feature is a general-purpose Generation III RNG search and execution system, not a species-specific hunt script.

## User-facing goal

Let the user play to a desired location and select a hunting method. The tool should use the active game's state, the user's trainer IDs, the chosen game's encounter table, and the selected method to:

1. Define a target Pokémon profile (species, shiny status, nature, IVs, gender, ability, and other supported traits).
2. Search candidate RNG states/outcomes in bulk, like a Gen III RNG research tool.
3. Translate a chosen outcome into a method-specific action plan and execute it only after the prediction model has been validated.
4. Report the target outcome and the actual work performed: game frames/seed advances where meaningful, total encounters, target-species encounters, elapsed time, and shiny-phase statistics.
5. Keep predicted results separate from actual encountered Pokémon and clearly label any mode that injects or edits Pokémon rather than generating them through normal game mechanics.

## Important terminology

- **RNG calls / seed advances** are not the same thing as game frames.
- **PID candidate index** is not automatically an encounter count.
- **Encounter count** must be incremented from actual encounter events and should use PokéBot's existing stats database.
- **Prediction** means a simulated outcome. It must not be reported as an actual encounter until the game produces and the bot observes that Pokémon.
- **Execution/manipulation** means the bot attempts to reproduce the required state through validated game inputs and RNG advances. It needs method-specific modeling and verification.

## Current prototype

`modules/predictive_rng.py` contains the Gen III LCRNG primitive, logarithmic fast-forwarding, shiny-value calculation, a live RNG/TID/SID snapshot reader, and generic PID-only target filters (shiny, nature index, gender, and ability slot).

This is deliberately only a foundation. The simplified consecutive-PID stream does not model exact wild encounter generation and must not yet be treated as a PokéFinder-equivalent frame search. IV filtering, encounter tables, levels, and accurate encounter counts require the exact generation method and all intervening RNG calls to be modeled.

### Live diagnostics

At startup, and every 30 seconds while running, the bot attempts a read-only snapshot and prints the active game, `gRngValue` seed, TID, SID, and emulator frame to the console (including in headless mode). If the GUI is enabled, `Debug > Read Live RNG Snapshot` performs another on-demand read and displays the same values in the console and status message. A failed read is reported as an error instead of being presented as valid data. These diagnostics confirm that the read path runs; they do not validate future encounter predictions.

## Implementation milestones

1. **Validate RNG primitives** against known Gen III test vectors and live emulator snapshots.
2. **Implement generation methods** separately for FireRed/LeafGreen and Ruby/Sapphire/Emerald, including PID/IV generation and method-specific RNG call order.
3. **Implement encounter resolvers** for grass, surfing, fishing, Safari Zone, static/gift encounters, and other supported methods; resolve encounter slot and level from the active map/table.
4. **Build a generic target search** with shiny, nature, IVs, gender, ability, species/slot, level, and optional stat/Hidden Power constraints.
5. **Calibrate predictions** against actual observed encounters from the emulator, with tests for supported games/methods.
6. **Add a preview UI** showing candidate outcomes and confidence/validation status before any automated execution.
7. **Add verified execution** that attempts the selected outcome through normal game behavior where feasible, then verifies the resulting Pokémon's PID/IVs.
8. **Use existing encounter statistics** for actual encounter counts and shiny-phase summaries; add a separate search/execution report for predicted candidates, RNG advances, time, and success/failure.

## Safety and data integrity

Never write to a save file or alter a Pokémon as an unannounced side effect. Any non-natural injection/editing mode, if ever added, must be explicit and separate from normal RNG manipulation. Keep this prototype isolated on its own branch until tests and calibration pass.
