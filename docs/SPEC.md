# SPEC.md

## Project Name
METAiR

## Purpose

METAiR is a deterministic Python parser for aviation weather reports, focused on converting raw **METAR**, **SPECI**, and **TAF** text into a stable, machine-friendly JSON structure.

The parser is intended to produce normalized output that can be reliably fed into an LLM for:
- plain-language explanation
- summarization
- highlighting changes over time
- aviation weather interpretation assistance

The parser itself is **not** an LLM component. It should remain rule-based, deterministic, auditable, and conservative.

## Primary Design Goal

Convert raw METAR and TAF text into structured JSON without inventing values.

The parser must:
- extract recognized fields deterministically
- preserve raw values where useful
- preserve unknown or unsupported tokens
- avoid guessing
- remain suitable for downstream LLM consumption

## Core Principles

1. **Deterministic first**
   - The parser must use explicit parsing rules, not AI inference.

2. **Do not invent values**
   - If a field cannot be determined confidently from the raw report, set it to `null` or preserve the raw token in `unparsed_tokens`.

3. **Preserve unsupported input**
   - Unknown tokens must never be silently discarded.

4. **Stable JSON contract**
   - Output structure should remain consistent across reports of the same type.

5. **Readable and extendable**
   - The code should favor maintainable parsing functions over overly clever one-pass logic.

## Supported Report Types

### v1 Supported
- `METAR`
- `SPECI`
- `TAF`

### v1 Bundle Support
The parser should be able to process:
- a single METAR
- a single SPECI
- a single TAF
- a text bundle containing both a METAR and a TAF

If multiple reports are present in one input, the parser should split them and return a combined bundle structure.

## Input Expectations

The parser accepts raw text containing one or more aviation weather reports.

Examples:
- single-line METAR
- multiline TAF
- METAR followed by TAF in one payload
- reports with remarks
- reports with line wrapping

The parser should normalize line breaks and whitespace before parsing.

## Output Contract

The parser should return a top-level object shaped like this:

```json
{
  "report_type": "METAR | SPECI | TAF | BUNDLE",
  "raw": "original raw input",
  "metar": null,
  "taf": null,
  "reports": [],
  "unparsed_tokens": []
}
```

### Notes
- For a single METAR or SPECI, `report_type` may be `"METAR"` or `"SPECI"`.
- For a single TAF, `report_type` may be `"TAF"`.
- For a combined input containing more than one report, `report_type` should be `"BUNDLE"`.
- `reports` may be used to preserve multiple parsed reports in order.
- `metar` and `taf` may be used for convenience when a bundle contains one of each.

If both are used, they must not contradict each other.

## METAR / SPECI JSON Structure

A parsed METAR or SPECI should generally follow this shape:

```json
{
  "type": "METAR",
  "station": "KBAD",
  "issued_at_utc": "092355Z",
  "modifier": "AUTO",
  "wind": {
    "raw": "16004KT",
    "direction_degrees": 160,
    "variable": false,
    "speed_kt": 4,
    "gust_kt": null,
    "unit": "KT",
    "variation": null
  },
  "visibility": {
    "raw": "10SM",
    "value": 10,
    "unit": "SM",
    "qualifier": null
  },
  "weather": [],
  "sky": [
    {
      "raw": "SCT080",
      "coverage": "SCT",
      "altitude_ft": 8000,
      "cloud_type": null
    }
  ],
  "temperature": {
    "air_c": 26,
    "dewpoint_c": 21
  },
  "altimeter": {
    "raw": "A2993",
    "unit": "inHg",
    "value": 29.93
  },
  "remarks": {
    "raw_tokens": ["AO2", "SLP138"]
  },
  "unparsed_tokens": []
}
```

### METAR / SPECI v1 Required Fields
The parser should support these fields when present:

- report type
- station
- issuance time
- modifier:
  - `AUTO`
  - `COR`
- wind
- visibility
- present weather
- sky conditions
- temperature / dew point
- altimeter
- remarks after `RMK`

## TAF JSON Structure

A parsed TAF should generally follow this shape:

```json
{
  "type": "TAF",
  "station": "KBAD",
  "issued_at_utc": "092000Z",
  "validity": {
    "from": "0920",
    "to": "1102"
  },
  "segments": [
    {
      "change_type": "INITIAL",
      "time_range": null,
      "conditions": {
        "wind": {
          "raw": "18010G15KT",
          "direction_degrees": 180,
          "speed_kt": 10,
          "gust_kt": 15,
          "unit": "KT"
        },
        "visibility": {
          "raw": "9999",
          "value_m": 9999,
          "meaning": "10km_or_more"
        },
        "weather": [
          {
            "raw": "-SHRA"
          }
        ],
        "sky": [
          {
            "raw": "OVC020CB",
            "coverage": "OVC",
            "altitude_ft": 2000,
            "cloud_type": "CB"
          }
        ],
        "altimeter": {
          "raw": "QNH2993INS",
          "unit": "inHg",
          "value": 29.93
        },
        "temperatures": [],
        "unparsed_tokens": []
      }
    }
  ],
  "temperatures": {
    "max": null,
    "min": null
  },
  "unparsed_tokens": []
}
```

### TAF v1 Required Fields
The parser should support these fields when present:

- report type
- station
- issuance time
- validity period
- initial conditions block
- change groups:
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
- max/min temperature groups:
  - `TX...`
  - `TN...`

## Bundle Output

When input contains both a METAR and a TAF, the parser should return a bundle object.

Recommended shape:

```json
{
  "report_type": "BUNDLE",
  "raw": "full original text",
  "metar": { "...parsed METAR..." },
  "taf": { "...parsed TAF..." },
  "reports": [
    { "...parsed METAR..." },
    { "...parsed TAF..." }
  ],
  "unparsed_tokens": []
}
```

The parser should preserve report order in `reports`.

## Parsing Scope for v1

### METAR / SPECI v1 Scope

#### Required support
- `METAR` / `SPECI`
- ICAO station identifier
- issuance time like `092355Z`
- modifiers:
  - `AUTO`
  - `COR`
- wind:
  - `18012KT`
  - `VRB03KT`
  - `35015G25KT`
- visibility:
  - `10SM`
  - `6SM`
  - `1SM`
  - `9999`
  - simple meter visibility tokens in TAF
- basic weather groups:
  - `-RA`
  - `+TSRA`
  - `BR`
  - `FG`
  - `HZ`
  - `VCTS`
  - `NSW`
- sky groups:
  - `SKC`
  - `CLR`
  - `NSC`
  - `FEW020`
  - `SCT080`
  - `BKN015`
  - `OVC020`
  - `OVC020CB`
  - `SCT030TCU`
  - `VV003`
- temperature / dew point:
  - `28/18`
  - `M02/M05`
- altimeter:
  - `A2992`
  - `Q1013`
  - `QNH2993INS`
- remarks:
  - everything after `RMK` preserved as raw tokens

### TAF v1 Scope

#### Required support
- `TAF`
- station
- issuance time
- validity period
- initial forecast block
- segmented forecast groups:
  - `BECMG`
  - `TEMPO`
  - `FM`
  - `PROB30`
  - `PROB40`
- conditions parsing inside each segment:
  - wind
  - visibility
  - weather
  - sky
  - altimeter if present
  - temperature groups if present

## v1 Non-Goals

The following are explicitly **not required** for v1 unless already trivial to support safely:

- full semantic decoding of remarks
- runway visual range parsing
- all international format variations
- every possible missing-data form
- every obscure weather or runway-state code
- calendar/date resolution into real timestamps
- timezone conversion
- geographic lookup
- unit conversion beyond obvious normalized values
- English narrative generation
- flight-category determination
- hazard scoring
- airport metadata enrichment

The parser may preserve these unsupported tokens in `unparsed_tokens`.

## Field Behavior Requirements

### Raw token preservation
Where practical, parsed structures should include the original raw token.

Examples:
- wind should include `raw`
- visibility should include `raw`
- sky layers should include `raw`
- weather groups should include `raw`
- altimeter should include `raw`

### Null handling
If a recognized field is absent, use `null` rather than inventing a value.

### Unknown token handling
Any token that cannot be confidently parsed should be added to `unparsed_tokens`.

### Conservative parsing
If a token partially matches a pattern but cannot be confidently interpreted, it is better to preserve it raw than to over-parse it incorrectly.

## Weather Group Representation

Weather groups may be normalized into structured components when safely possible.

Recommended shape:

```json
{
  "raw": "-SHRA",
  "intensity": "-",
  "proximity": null,
  "descriptor": "SH",
  "precipitation": ["RA"],
  "obscuration": [],
  "other": []
}
```

Another example:

```json
{
  "raw": "VCTS",
  "intensity": null,
  "proximity": "VC",
  "descriptor": "TS",
  "precipitation": [],
  "obscuration": [],
  "other": []
}
```

If the parser cannot confidently decompose the token, it may still preserve:

```json
{
  "raw": "TOKEN"
}
```

That is preferable to incorrect decomposition.

## Sky Group Representation

Recommended shape:

```json
{
  "raw": "OVC020CB",
  "coverage": "OVC",
  "altitude_ft": 2000,
  "cloud_type": "CB"
}
```

Supported coverage values should include:
- `SKC`
- `CLR`
- `NSC`
- `FEW`
- `SCT`
- `BKN`
- `OVC`
- `VV`

If coverage is `VV`, altitude should represent vertical visibility in feet where possible.

## Wind Representation

Recommended shape:

```json
{
  "raw": "18010G15KT",
  "direction_degrees": 180,
  "variable": false,
  "speed_kt": 10,
  "gust_kt": 15,
  "unit": "KT",
  "variation": null
}
```

Supported v1 forms:
- fixed direction
- variable direction with `VRB`
- gusts with `G`

Not required for v1:
- separate directional variation groups like `180V240`

Those may be supported later.

## Visibility Representation

Recommended shape for statute miles:

```json
{
  "raw": "10SM",
  "value": 10,
  "unit": "SM",
  "qualifier": null
}
```

Recommended shape for TAF visibility meters:

```json
{
  "raw": "9999",
  "value_m": 9999,
  "meaning": "10km_or_more"
}
```

Split fractional visibility like `1 1/2SM` is not required for v1 unless implemented safely.

## Temperature Representation

### METAR temperature/dew point
```json
{
  "air_c": 26,
  "dewpoint_c": 21
}
```

### TAF max/min temperatures
```json
{
  "max": {
    "raw": "TX25/0922Z",
    "c": 25,
    "at_utc": "0922Z"
  },
  "min": {
    "raw": "TN21/1012Z",
    "c": 21,
    "at_utc": "1012Z"
  }
}
```

## Altimeter Representation

Supported v1 forms:
- `A2992` → inches of mercury
- `Q1013` → hPa
- `QNH2993INS` → inches of mercury

Recommended shape:

```json
{
  "raw": "A2992",
  "unit": "inHg",
  "value": 29.92
}
```

## Example Input

### Example METAR
```text
METAR KBAD 092355Z AUTO 16004KT 10SM SCT080 26/21 A2993 RMK AO2 SLP138 60001 T02570209 10270 20240 55007 $
```

### Example TAF
```text
TAF KBAD 092000Z 0920/1102 18010G15KT 9999 -SHRA VCTS OVC020CB QNH2993INS
  BECMG 1000/1001 19012G20KT 9999 NSW BKN010 QNH2991INS
  BECMG 1005/1006 16010G15KT 9999 BKN015 QNH2997INS
  BECMG 1010/1011 17010G15KT 9999 BKN025 QNH2996INS
  BECMG 1100/1101 17012KT 9999 SCT025 QNH3000INS TX25/0922Z TN21/1012Z
```

## Expected Behavior for Example Bundle

When given the combined KBAD METAR + TAF payload, the parser should:
- identify two separate reports
- parse the METAR into a METAR object
- parse the TAF into a TAF object
- return a bundle object containing both
- preserve unsupported remark tokens as raw remarks
- preserve any unsupported forecast tokens in `unparsed_tokens`

## Testing Requirements

The repo should include automated tests.

### Minimum expected tests
- one basic METAR
- one METAR with gusting wind
- one METAR with remarks
- one METAR with negative temperatures
- one TAF with `BECMG`
- one TAF with cloud type suffix like `CB`
- one combined METAR + TAF bundle case
- KBAD example fixture test

### Test philosophy
Tests should assert exact field values when possible, not only object existence.

Examples:
- station equals expected ICAO
- wind direction equals expected integer
- gust equals expected integer or null
- altimeter equals expected numeric value
- sky layer altitude matches expected feet
- report segmentation count matches expected TAF change groups

## Definition of Done for v1

The parser is considered v1 complete when:

1. It parses the required METAR and TAF fields in this spec.
2. It returns stable JSON structures.
3. It preserves unsupported data instead of silently dropping it.
4. Automated tests pass.
5. README explains:
   - what the project does
   - how to run it
   - how to run tests
   - current limitations

## Future v2 Candidates

These are possible next-phase enhancements, not required for v1:

- `180V240` wind variation groups
- split fractional visibility like `1 1/2SM`
- `CAVOK`
- runway visual range
- richer weather token decomposition
- detailed remarks parsing
- full international format expansion
- flight category derivation
- hazard highlighting
- canonical time normalization into full dates
- CLI / API wrapper
- direct JSON-to-LLM formatting helpers

## Implementation Guidance

Preferred implementation style:
- plain Python
- standard library first
- token-based parsing
- helper functions by token type
- separate report splitting from report parsing
- separate METAR parsing from TAF parsing
- small, testable parsing functions

Avoid:
- one giant full-report regex
- over-parsing ambiguous tokens
- silently discarding unknown data
- mixing deterministic parsing with LLM inference

## Final Project Intent

METAiR should become a trustworthy preprocessing layer for aviation weather interpretation.

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

The parser should never depend on the LLM to understand the raw report.
