# METAR / TAF v1 Parsing Rules

This document summarizes the deterministic parsing rules the current v1 parser actually needs to support. It is intentionally narrower than a full aviation weather decoding guide.

## General Rules

- Treat parsing as token based, not inference based.
- Preserve the original raw token where practical.
- If a token is not confidently supported, place it in `unparsed_tokens` instead of guessing.
- Normalize multiline reports by splitting on report starts: `METAR`, `SPECI`, and `TAF`.

## Report Splitting

- A new report starts when the first token on a non-empty line is `METAR`, `SPECI`, or `TAF`.
- Wrapped TAF continuation lines belong to the current report until the next report start.
- A bundle may contain one METAR or SPECI plus one TAF, or multiple reports in sequence.

## METAR / SPECI Rules

- Parse the report type from the opening token.
- Parse the station as a four-letter ICAO identifier.
- Parse issuance time in `DDHHMMZ` form.
- Support the modifiers `AUTO` and `COR`.
- Parse wind tokens such as:
  - `18012KT`
  - `VRB03KT`
  - `35015G25KT`
- Parse visibility tokens such as:
  - `10SM`
  - `6SM`
  - `1SM`
  - `9999`
  - plain four-digit meter visibility values
- Parse present weather only when the token can be safely decomposed into:
  - optional intensity: `+` or `-`
  - optional proximity: `VC`
  - optional descriptor such as `SH`, `TS`, `FZ`
  - precipitation, obscuration, and other phenomena groups
- Recognize special weather tokens `NSW` and `CAVOK` without over-expanding them.
- Parse sky groups with these coverage codes:
  - `SKC`
  - `CLR`
  - `NSC`
  - `FEW`
  - `SCT`
  - `BKN`
  - `OVC`
  - `VV`
- Parse sky heights as hundreds of feet when numeric and preserve cloud suffixes like `CB` and `TCU`.
- Parse temperature and dew point pairs like `26/21` and `M02/M05`.
- Parse altimeters in these forms:
  - `A2992`
  - `Q1013`
  - `QNH2993INS`
- After `RMK`, preserve all remaining tokens as raw remarks.

## TAF Rules

- Parse `TAF` report type, station, issuance time, and validity range `DDHH/DDHH`.
- Parse the initial forecast block before any change group token.
- Start a new segment on:
  - `BECMG`
  - `TEMPO`
  - `FMxxxx` or `FMxxxxxx`
  - `PROB30`
  - `PROB40`
- For `BECMG`, `TEMPO`, `PROB30`, and `PROB40`, parse an immediate following `DDHH/DDHH` token as that segment's time range.
- For `FM`, store the `from` time from the token suffix and leave `to` unset.
- Within each segment, reuse the same deterministic token parsers used for METAR fields:
  - wind
  - visibility
  - weather
  - sky
  - altimeter
- Parse TAF max and min temperature groups:
  - `TX25/0922Z`
  - `TN21/1012Z`

## Bundle Output Rules

- When the input contains more than one report, return a top-level bundle result.
- Preserve the report order in `reports`.
- Populate convenience fields for the first parsed METAR or SPECI and the first parsed TAF when present.

## Out of Scope for v1

- Full semantic remarks decoding
- Runway visual range
- Directional wind variation groups such as `180V240`
- Rich airport metadata
- Calendar-aware timestamp conversion
- Narrative explanation
