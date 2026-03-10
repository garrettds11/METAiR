# AGENTS.md

## Project goal
Build a deterministic Python parser for METAR, SPECI, and TAF that outputs stable JSON for downstream use.

## Required references
Before changing parser logic, read all the files below, including relevant files in sub-directories:
- docs/SPEC.md
- docs/metar_taf_rules.md
- docs/How_to_Decode_METAR_TAF_and_pilot_reports.pdf
- all relevant files under docs/aviation_weather_api/*
- parser/*
- tests/*

## Core engineering rules
- Do not invent weather fields not present in the raw report.
- Preserve unsupported, ambiguous, or unrecognized tokens in `unparsed_tokens`.
- Prefer deterministic parsing over heuristic interpretation.
- Keep the output schema stable and aligned with `docs/SPEC.md`.
- Prefer additive schema changes over breaking changes.
- Preserve raw token values wherever practical.
- Use Python standard library unless explicitly approved otherwise.
- Do not rewrite the project structure unnecessarily.
- Make the smallest safe change that satisfies the task.

## Parsing behavior rules
- If a token cannot be parsed confidently, preserve it rather than guessing.
- Do not silently broaden scope beyond the current spec unless the task explicitly requires it.
- When adding support for new token families, return structured JSON only when confidence is high.
- For partial or ambiguous matches, preserve the raw token and avoid over-normalization.
- Do not remove existing fields without updating the spec and tests.

## Validation
- Run `python tests/tests.py`.
- If tests fail, fix the code and rerun until passing.
- Add or update tests for every parser behavior change.
- Do not consider the task complete if new behavior is untested.

## Documentation
- Update `README.md` if behavior, usage, or supported scope changes.
- Update `docs/SPEC.md` if the output schema changes.