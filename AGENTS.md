# AGENTS.md

## Project goal
Build a deterministic Python parser for METAR, SPECI, and TAF that outputs stable JSON for downstream LLM use.

## Required references
Before changing parser logic, read all the files below, including all those in located in sub-directories of docs:
- docs/SPEC.md
- docs/metar_taf_rules.md
- docs/How_to_Decode_METAR_TAF_and_pilot_reports.pdf
- all relevant files under docs/aviation_weather_api/*

## Working rules
- Do not invent weather fields not present in the raw report.
- Preserve unsupported or unrecognized tokens in `unparsed_tokens`.
- Prefer deterministic parsing over heuristic interpretation.
- Keep the output schema stable and aligned with `SPEC.md`.
- Preserve raw tokens where practical.
- Use Python standard library unless explicitly approved otherwise.
- Do not rewrite the project structure unnecessarily.
- Make the smallest safe change that satisfies the task.

## Validation
- Run `python tests/tests.py`
- If tests fail, fix the code and rerun until passing.

## When changing parser behavior
- Add or update tests to cover the behavior change.
- Do not silently broaden scope beyond the current spec.
- If a token cannot be parsed confidently, preserve it rather than guessing.

## Documentation
- Update `README.md` if behavior, usage, or supported scope changes.