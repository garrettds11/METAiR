# METAiR

METAiR is a deterministic Python parser for aviation weather reports. Its purpose is to convert raw **METAR**, **SPECI**, and **TAF** text into stable, machine-friendly JSON that can be safely passed into downstream applications or LLM workflows.

The parser is intended to be a preprocessing layer, not an AI interpreter. It should remain rule-based, conservative, and auditable.

## Current Goal

Build a v1 parser that:

- parses common METAR and TAF structures deterministically
- preserves unsupported or unknown tokens instead of discarding them
- outputs stable JSON structures
- supports downstream plain-language explanation by an LLM without depending on the LLM for parsing

## Supported Report Types

- `METAR`
- `SPECI`
- `TAF`
- combined bundles containing both METAR and TAF text

## v1 Parsing Scope

### METAR / SPECI

- report type
- station
- issuance time
- modifiers such as `AUTO` and `COR`
- wind
- visibility
- present weather
- sky conditions
- temperature / dew point
- altimeter
- remarks after `RMK` with raw token preservation plus structured support for common groups such as `SLP`, `P`, `6`, `7`, `1`, `2`, `4`, `PK WND`, and `WSHFT`

### TAF

- report type
- station
- issuance time
- validity period
- initial forecast block
- segmented change groups such as:
  - `BECMG`
  - `TEMPO`
  - `FM`
  - `PROB30`
  - `PROB40`
- wind
- visibility
- weather
- sky
- altimeter / QNH token if present
- temperature groups such as `TX...` and `TN...`

## Design Principles

- deterministic parsing first
- do not invent values
- preserve unknown tokens in `unparsed_tokens`
- include raw token values where useful
- keep the JSON contract stable
- prefer simple, testable helper functions over one giant regex

## Example Input

### METAR

```text
METAR KBAD 092355Z AUTO 16004KT 10SM SCT080 26/21 A2993 RMK AO2 SLP138 60001 T02570209 10270 20240 55007 $
```

### TAF

```text
TAF KBAD 092000Z 0920/1102 18010G15KT 9999 -SHRA VCTS OVC020CB QNH2993INS
  BECMG 1000/1001 19012G20KT 9999 NSW BKN010 QNH2991INS
  BECMG 1005/1006 16010G15KT 9999 BKN015 QNH2997INS
  BECMG 1010/1011 17010G15KT 9999 BKN025 QNH2996INS
  BECMG 1100/1101 17012KT 9999 SCT025 QNH3000INS TX25/0922Z TN21/1012Z
```

## Expected Output Style

The parser should produce structured JSON rather than prose. A top-level response may look like this:

```json
{
  "report_type": "BUNDLE",
  "raw": "...original input...",
  "metar": { "...parsed METAR..." },
  "taf": { "...parsed TAF..." },
  "reports": [
    { "...parsed METAR..." },
    { "...parsed TAF..." }
  ],
  "unparsed_tokens": []
}
```

See `docs/SPEC.md` for the full parsing contract and expected field shapes.

## Repository Files

The current repository is organized around files such as:

- `parser/parser.py` - parser implementation
- `tests/tests.py` - automated tests
- `docs/SPEC.md` - parser contract and v1 requirements
- `AGENTS.md` - agent guidance for Codex
- `samples/` - sample input files and reference data used for validation

## How To Run

Run the parser from the repository root by importing the parser module.

Example bundle parse:

```python
from parser.parser import parse_text

raw = """METAR KBAD 092355Z AUTO 16004KT 10SM SCT080 26/21 A2993 RMK AO2

TAF KBAD 092000Z 0920/1102 18010G15KT 9999 -SHRA VCTS OVC020CB QNH2993INS"""

parsed = parse_text(raw)
print(parsed["report_type"])
```

If you want to parse a single report directly, import `parse_metar()` or `parse_taf()` from `parser/parser.py`.

## How To Test

```bash
python tests/tests.py
```

## Current Limitations

This project is still in active development. The following are not required for v1 unless implemented safely:

- full semantic decoding of remarks
- runway visual range parsing
- every international format variation
- every missing-data variant
- full timestamp normalization into real calendar dates
- narrative weather explanation
- flight-category derivation
- hazard scoring
- airport metadata enrichment

Unsupported tokens should be preserved rather than dropped.

## Development Workflow

The intended workflow is:

1. define parsing behavior in `docs/SPEC.md`
2. implement deterministic parsing logic
3. add or improve tests
4. run tests and fix failures
5. extend support incrementally without breaking the JSON contract

## Roadmap

Potential v2 enhancements include:

- wind variation groups like `180V240`
- split fractional visibility such as `1 1/2SM`
- `CAVOK`
- richer present weather decomposition
- more detailed remarks parsing
- CLI or API wrapper
- downstream formatting helpers for LLM prompts

## Project Intent

METAiR should become a reliable preprocessing layer for aviation weather interpretation.

The parser’s job is to:

- normalize
- structure
- preserve
- validate

The LLM’s later job is to:

- explain
- summarize
- narrate
- assist the user

The parser should not depend on the LLM to understand the raw weather report.
