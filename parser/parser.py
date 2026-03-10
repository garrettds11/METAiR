import re
from fractions import Fraction
from typing import Any, Dict, List, Optional


REPORT_START_RE = re.compile(r'^(METAR|SPECI|TAF)$')
ICAO_RE = re.compile(r'^[A-Z]{4}$')
TIME_RE = re.compile(r'^\d{6}Z$')
VALIDITY_RE = re.compile(r'^\d{4}/\d{4}$')

WIND_RE = re.compile(r'^(?P<dir>\d{3}|VRB)(?P<speed>\d{2,3})(G(?P<gust>\d{2,3}))?(?P<unit>KT)$')
RVR_RE = re.compile(
    r'^R(?P<runway>\d{2}[LRC]?)/(?P<lower_qualifier>[MP])?(?P<lower>\d{4})'
    r'(?:V(?P<upper_qualifier>[MP])?(?P<upper>\d{4}))?(?P<unit>FT)?$'
)

VIS_SM_RE = re.compile(r'^(?P<qualifier>P)?(?P<value>\d{1,2}(?:/\d)?|\d+\s\d/\d)SM$')
VIS_FRACTION_TOKEN_RE = re.compile(r'^\d/\dSM$')
VIS_M_RE = re.compile(r'^\d{4}$')

TAF_PREFIX_MODIFIERS = {"AMD", "COR", "CCA", "CCB"}

TEMP_DEW_RE = re.compile(r'^(M?\d{2})/(M?\d{2})$')
ALT_A_RE = re.compile(r'^A(\d{4})$')
ALT_Q_RE = re.compile(r'^Q(\d{4})$')
ALT_QNH_INS_RE = re.compile(r'^QNH(\d{4})INS$')

SKY_RE = re.compile(r'^(?P<cov>SKC|CLR|NSC|FEW|SCT|BKN|OVC|VV)(?P<height>\d{3}|///)?(?P<ctype>CB|TCU)?$')

TAF_RANGE_RE = re.compile(r'^\d{4}/\d{4}$')
TEMP_EXTREME_RE = re.compile(r'^(?P<kind>TX|TN)(?P<temp>M?\d{2})/(?P<time>\d{4}Z)$')

SLP_RE = re.compile(r'^SLP(?P<value>\d{3})$')
HOURLY_PRECIP_RE = re.compile(r'^P(?P<value>\d{4})$')
PRECIP_3_6_RE = re.compile(r'^6(?P<value>\d{4})$')
PRECIP_24_RE = re.compile(r'^7(?P<value>\d{4})$')
TEMP_REMARK_RE = re.compile(r'^(?P<kind>[12])(?P<sign>[01])(?P<value>\d{3})$')
TEMP_24H_RE = re.compile(r'^4(?P<max_sign>[01])(?P<max_value>\d{3})(?P<min_sign>[01])(?P<min_value>\d{3})$')
PK_WND_VALUE_RE = re.compile(r'^(?P<dir>\d{3})(?P<speed>\d{2,3})/(?P<time>\d{2,4})$')
WSHFT_RE = re.compile(r'^(?P<time>\d{2,4})$')

INTENSITIES = {"+", "-"}
DESCRIPTORS = {"MI", "PR", "BC", "DR", "BL", "SH", "TS", "FZ"}
PRECIP = {"DZ", "RA", "SN", "SG", "IC", "PL", "GR", "GS", "UP"}
OBSCURATION = {"BR", "FG", "FU", "VA", "DU", "SA", "HZ"}
OTHER = {"PO", "SQ", "FC", "SS", "DS"}
SPECIAL_WEATHER = {
    "NSW": "no_significant_weather",
    "CAVOK": "ceiling_and_visibility_ok",
}

COVERAGE_TEXT = {
    "SKC": "sky_clear",
    "CLR": "clear",
    "NSC": "no_significant_clouds",
    "FEW": "few",
    "SCT": "scattered",
    "BKN": "broken",
    "OVC": "overcast",
    "VV": "vertical_visibility",
}


def parse_signed_temp(value: str) -> int:
    return -int(value[1:]) if value.startswith("M") else int(value)


def parse_signed_tenths(sign: str, digits: str) -> float:
    value = int(digits) / 10
    return -value if sign == "1" else value


def parse_sm_value(value: str) -> float | int:
    if " " in value:
        whole, frac = value.split()
        result = int(whole) + float(Fraction(frac))
    elif "/" in value:
        result = float(Fraction(value))
    else:
        result = int(value)

    return int(result) if float(result).is_integer() else result


def parse_temp_extreme(token: str) -> Optional[Dict[str, Any]]:
    match = TEMP_EXTREME_RE.match(token)
    if not match:
        return None

    return {
        "raw": token,
        "c": parse_signed_temp(match.group("temp")),
        "at_utc": match.group("time"),
    }


def parse_remark_sea_level_pressure(token: str) -> Optional[Dict[str, Any]]:
    match = SLP_RE.match(token)
    if not match:
        return None

    tenths_hpa = int(match.group("value")) / 10
    value_hpa = 900 + tenths_hpa if tenths_hpa >= 50 else 1000 + tenths_hpa
    return {"raw": token, "value_hpa": value_hpa}


def parse_remark_precipitation(token: str, pattern: re.Pattern[str]) -> Optional[Dict[str, Any]]:
    match = pattern.match(token)
    if not match:
        return None
    return {"raw": token, "amount_in": int(match.group("value")) / 100}


def parse_remark_temperature_group(token: str) -> Optional[Dict[str, Any]]:
    match = TEMP_REMARK_RE.match(token)
    if not match:
        return None
    return {"raw": token, "c": parse_signed_tenths(match.group("sign"), match.group("value"))}


def parse_remark_max_min_group(token: str) -> Optional[Dict[str, Any]]:
    match = TEMP_24H_RE.match(token)
    if not match:
        return None
    return {
        "raw": token,
        "max_c": parse_signed_tenths(match.group("max_sign"), match.group("max_value")),
        "min_c": parse_signed_tenths(match.group("min_sign"), match.group("min_value")),
    }


def parse_wind(token: str) -> Optional[Dict[str, Any]]:
    match = WIND_RE.match(token)
    if not match:
        return None
    direction = match.group("dir")
    return {
        "raw": token,
        "direction_degrees": None if direction == "VRB" else int(direction),
        "variable": direction == "VRB",
        "speed_kt": int(match.group("speed")),
        "gust_kt": int(match.group("gust")) if match.group("gust") else None,
        "unit": match.group("unit"),
        "variation": None,
    }


def parse_runway_visual_range(token: str) -> Optional[Dict[str, Any]]:
    match = RVR_RE.match(token)
    if not match:
        return None

    lower_qualifier = match.group("lower_qualifier")
    upper_qualifier = match.group("upper_qualifier")
    upper = match.group("upper")
    variable = upper is not None

    return {
        "raw": token,
        "runway_designator": match.group("runway"),
        "lower_value_ft": int(match.group("lower")),
        "upper_value_ft": int(upper) if upper else None,
        "variable": variable,
        "qualifier": lower_qualifier if not variable else None,
        "lower_qualifier": lower_qualifier if variable else None,
        "upper_qualifier": upper_qualifier if variable else None,
        "unit": match.group("unit") or None,
    }


def parse_visibility_tokens(tokens: List[str], index: int) -> tuple[Optional[Dict[str, Any]], int]:
    token = tokens[index]

    if index + 1 < len(tokens) and token.isdigit() and VIS_FRACTION_TOKEN_RE.match(tokens[index + 1]):
        combined = f"{token} {tokens[index + 1]}"
        visibility = parse_visibility(combined)
        if visibility:
            return visibility, 2

    return parse_visibility(token), 1


def parse_visibility(token: str) -> Optional[Dict[str, Any]]:
    match = VIS_SM_RE.match(token)
    if match:
        return {
            "raw": token,
            "value": parse_sm_value(match.group("value")),
            "unit": "SM",
            "qualifier": match.group("qualifier"),
        }
    if token == "9999":
        return {"raw": token, "value_m": 9999, "meaning": "10km_or_more"}
    if VIS_M_RE.match(token):
        return {"raw": token, "value_m": int(token), "unit": "m"}
    return None


def parse_sky(token: str) -> Optional[Dict[str, Any]]:
    match = SKY_RE.match(token)
    if not match:
        return None
    coverage = match.group("cov")
    height = match.group("height")
    cloud_type = match.group("ctype")
    altitude_ft = None
    if height and height.isdigit():
        altitude_ft = int(height) * 100
    return {
        "raw": token,
        "coverage": coverage,
        "coverage_text": COVERAGE_TEXT.get(coverage),
        "altitude_ft": altitude_ft,
        "cloud_type": cloud_type,
    }


def parse_altimeter(token: str) -> Optional[Dict[str, Any]]:
    match = ALT_A_RE.match(token)
    if match:
        raw = match.group(1)
        return {"raw": token, "unit": "inHg", "value": float(raw[:2] + "." + raw[2:])}

    match = ALT_Q_RE.match(token)
    if match:
        return {"raw": token, "unit": "hPa", "value": int(match.group(1))}

    match = ALT_QNH_INS_RE.match(token)
    if match:
        raw = match.group(1)
        return {"raw": token, "unit": "inHg", "value": float(raw[:2] + "." + raw[2:])}

    return None


def parse_temp_dew(token: str) -> Optional[Dict[str, Any]]:
    match = TEMP_DEW_RE.match(token)
    if not match:
        return None
    return {
        "air_c": parse_signed_temp(match.group(1)),
        "dewpoint_c": parse_signed_temp(match.group(2)),
    }


def parse_weather(token: str) -> Optional[Dict[str, Any]]:
    if token in SPECIAL_WEATHER:
        return {"raw": token, "meaning": SPECIAL_WEATHER[token]}

    intensity = None
    remaining = token

    if remaining and remaining[0] in INTENSITIES:
        intensity = remaining[0]
        remaining = remaining[1:]

    proximity = None
    if remaining.startswith("VC"):
        proximity = "VC"
        remaining = remaining[2:]

    parts = []
    i = 0
    while i < len(remaining):
        parts.append(remaining[i:i + 2])
        i += 2

    descriptor = None
    precipitation = []
    obscuration = []
    other = []

    for part in parts:
        if part in DESCRIPTORS and descriptor is None:
            descriptor = part
        elif part in PRECIP:
            precipitation.append(part)
        elif part in OBSCURATION:
            obscuration.append(part)
        elif part in OTHER:
            other.append(part)
        else:
            return None

    return {
        "raw": token,
        "intensity": intensity,
        "proximity": proximity,
        "descriptor": descriptor,
        "precipitation": precipitation,
        "obscuration": obscuration,
        "other": other,
    }


def split_reports(text: str) -> List[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    reports = []
    current = []

    for line in lines:
        first = line.split()[0]
        if REPORT_START_RE.match(first):
            if current:
                reports.append(" ".join(current))
            current = [line]
        else:
            current.append(line)

    if current:
        reports.append(" ".join(current))

    return reports


def parse_remarks(tokens: List[str]) -> Dict[str, Any]:
    remarks = {
        "raw_tokens": list(tokens),
        "sea_level_pressure": None,
        "hourly_precipitation": None,
        "precipitation_3_6_hour": None,
        "precipitation_24_hour": None,
        "temperature_6_hour_max": None,
        "temperature_6_hour_min": None,
        "temperature_24_hour_extremes": None,
        "peak_wind": None,
        "wind_shift": None,
        "unparsed_tokens": [],
    }

    i = 0
    while i < len(tokens):
        token = tokens[i]

        if token == "PK" and i + 2 < len(tokens) and tokens[i + 1] == "WND":
            match = PK_WND_VALUE_RE.match(tokens[i + 2])
            if match:
                remarks["peak_wind"] = {
                    "raw": f"PK WND {tokens[i + 2]}",
                    "direction_degrees": int(match.group("dir")),
                    "speed_kt": int(match.group("speed")),
                    "at_utc": match.group("time"),
                }
                i += 3
                continue

        if token == "WSHFT" and i + 1 < len(tokens):
            match = WSHFT_RE.match(tokens[i + 1])
            if match:
                remarks["wind_shift"] = {
                    "raw": f"WSHFT {tokens[i + 1]}",
                    "at_utc": match.group("time"),
                }
                i += 2
                continue

        sea_level_pressure = parse_remark_sea_level_pressure(token)
        if sea_level_pressure:
            remarks["sea_level_pressure"] = sea_level_pressure
            i += 1
            continue

        hourly_precipitation = parse_remark_precipitation(token, HOURLY_PRECIP_RE)
        if hourly_precipitation:
            remarks["hourly_precipitation"] = hourly_precipitation
            i += 1
            continue

        precipitation_3_6_hour = parse_remark_precipitation(token, PRECIP_3_6_RE)
        if precipitation_3_6_hour:
            remarks["precipitation_3_6_hour"] = precipitation_3_6_hour
            i += 1
            continue

        precipitation_24_hour = parse_remark_precipitation(token, PRECIP_24_RE)
        if precipitation_24_hour:
            remarks["precipitation_24_hour"] = precipitation_24_hour
            i += 1
            continue

        temperature_group = parse_remark_temperature_group(token)
        if temperature_group:
            if token.startswith("1"):
                remarks["temperature_6_hour_max"] = temperature_group
            elif token.startswith("2"):
                remarks["temperature_6_hour_min"] = temperature_group
            i += 1
            continue

        temperature_24_hour_extremes = parse_remark_max_min_group(token)
        if temperature_24_hour_extremes:
            remarks["temperature_24_hour_extremes"] = temperature_24_hour_extremes
            i += 1
            continue

        remarks["unparsed_tokens"].append(token)
        i += 1

    return remarks


def parse_metar(report: str) -> Dict[str, Any]:
    tokens = report.split()
    remark_tokens: List[str] = []
    out = {
        "type": None,
        "station": None,
        "issued_at_utc": None,
        "modifier": None,
        "wind": None,
        "visibility": None,
        "runway_visual_range": [],
        "weather": [],
        "sky": [],
        "temperature": None,
        "altimeter": None,
        "remarks": None,
        "unparsed_tokens": [],
    }

    in_remarks = False
    i = 0

    while i < len(tokens):
        token = tokens[i]

        if in_remarks:
            remark_tokens.append(token)
            i += 1
            continue

        if out["type"] is None and token in ("METAR", "SPECI"):
            out["type"] = token
            i += 1
            continue

        if out["station"] is None and ICAO_RE.match(token):
            out["station"] = token
            i += 1
            continue

        if out["issued_at_utc"] is None and TIME_RE.match(token):
            out["issued_at_utc"] = token
            i += 1
            continue

        if token in ("AUTO", "COR") and out["modifier"] is None:
            out["modifier"] = token
            i += 1
            continue

        if out["wind"] is None:
            wind = parse_wind(token)
            if wind:
                out["wind"] = wind
                i += 1
                continue

        if out["visibility"] is None:
            visibility, consumed = parse_visibility_tokens(tokens, i)
            if visibility:
                out["visibility"] = visibility
                i += consumed
                continue

        runway_visual_range = parse_runway_visual_range(token)
        if runway_visual_range:
            out["runway_visual_range"].append(runway_visual_range)
            i += 1
            continue

        weather = parse_weather(token)
        if weather:
            out["weather"].append(weather)
            i += 1
            continue

        sky = parse_sky(token)
        if sky:
            out["sky"].append(sky)
            i += 1
            continue

        if out["temperature"] is None:
            temp_dew = parse_temp_dew(token)
            if temp_dew:
                out["temperature"] = temp_dew
                i += 1
                continue

        if out["altimeter"] is None:
            altimeter = parse_altimeter(token)
            if altimeter:
                out["altimeter"] = altimeter
                i += 1
                continue

        if token == "RMK":
            in_remarks = True
            i += 1
            continue

        out["unparsed_tokens"].append(token)
        i += 1

    out["remarks"] = parse_remarks(remark_tokens)
    return out


def parse_taf_conditions(tokens: List[str]) -> Dict[str, Any]:
    conditions = {
        "wind": None,
        "visibility": None,
        "weather": [],
        "sky": [],
        "altimeter": None,
        "temperatures": [],
        "unparsed_tokens": [],
    }

    i = 0
    while i < len(tokens):
        token = tokens[i]

        if conditions["wind"] is None:
            wind = parse_wind(token)
            if wind:
                conditions["wind"] = wind
                i += 1
                continue

        if conditions["visibility"] is None:
            visibility, consumed = parse_visibility_tokens(tokens, i)
            if visibility:
                conditions["visibility"] = visibility
                i += consumed
                continue

        weather = parse_weather(token)
        if weather:
            conditions["weather"].append(weather)
            i += 1
            continue

        sky = parse_sky(token)
        if sky:
            conditions["sky"].append(sky)
            i += 1
            continue

        altimeter = parse_altimeter(token)
        if altimeter and conditions["altimeter"] is None:
            conditions["altimeter"] = altimeter
            i += 1
            continue

        temp_extreme = parse_temp_extreme(token)
        if temp_extreme:
            conditions["temperatures"].append(temp_extreme)
            i += 1
            continue

        conditions["unparsed_tokens"].append(token)
        i += 1

    return conditions


def parse_taf(report: str) -> Dict[str, Any]:
    tokens = report.split()
    out = {
        "type": "TAF",
        "station": None,
        "issued_at_utc": None,
        "validity": None,
        "segments": [],
        "temperatures": {"max": None, "min": None},
        "unparsed_tokens": [],
    }

    i = 0
    if tokens and tokens[i] == "TAF":
        i += 1

    while i < len(tokens) and tokens[i] in TAF_PREFIX_MODIFIERS:
        out["unparsed_tokens"].append(tokens[i])
        i += 1

    if i < len(tokens) and ICAO_RE.match(tokens[i]):
        out["station"] = tokens[i]
        i += 1

    if i < len(tokens) and TIME_RE.match(tokens[i]):
        out["issued_at_utc"] = tokens[i]
        i += 1

    if i < len(tokens) and VALIDITY_RE.match(tokens[i]):
        out["validity"] = {"from": tokens[i][:4], "to": tokens[i][5:]}
        i += 1

    current_type = "INITIAL"
    current_range = None
    current_tokens: List[str] = []

    def flush() -> None:
        nonlocal current_tokens, current_type, current_range
        if current_tokens or current_type == "INITIAL":
            segment = {
                "change_type": current_type,
                "time_range": current_range,
                "conditions": parse_taf_conditions(current_tokens),
            }
            out["segments"].append(segment)
            for temp_extreme in segment["conditions"]["temperatures"]:
                if temp_extreme["raw"].startswith("TX"):
                    out["temperatures"]["max"] = temp_extreme
                elif temp_extreme["raw"].startswith("TN"):
                    out["temperatures"]["min"] = temp_extreme
        current_tokens = []

    while i < len(tokens):
        token = tokens[i]

        if token in ("BECMG", "TEMPO"):
            flush()
            current_type = token
            current_range = None
            i += 1
            if i < len(tokens) and TAF_RANGE_RE.match(tokens[i]):
                current_range = {"from": tokens[i][:4], "to": tokens[i][5:]}
                i += 1
            continue

        if token.startswith("FM"):
            flush()
            current_type = "FM"
            current_range = {"from": token[2:], "to": None}
            i += 1
            continue

        if token.startswith("PROB"):
            flush()
            current_type = token
            current_range = None
            i += 1
            if i < len(tokens) and TAF_RANGE_RE.match(tokens[i]):
                current_range = {"from": tokens[i][:4], "to": tokens[i][5:]}
                i += 1
            continue

        current_tokens.append(token)
        i += 1

    flush()
    return out


def parse_report(report: str) -> Dict[str, Any]:
    first_token = report.split()[0]
    if first_token == "TAF":
        return parse_taf(report)
    if first_token in {"METAR", "SPECI"}:
        return parse_metar(report)
    raise ValueError(f"Unsupported report type: {first_token}")


def parse_text(text: str) -> Dict[str, Any]:
    reports = [parse_report(report) for report in split_reports(text)]

    if len(reports) == 1:
        report = reports[0]
        return {
            "report_type": report["type"],
            "raw": text,
            "metar": report if report["type"] in {"METAR", "SPECI"} else None,
            "taf": report if report["type"] == "TAF" else None,
            "reports": reports,
            "unparsed_tokens": [],
        }

    bundle = {
        "report_type": "BUNDLE",
        "raw": text,
        "metar": None,
        "taf": None,
        "reports": reports,
        "unparsed_tokens": [],
    }

    for report in reports:
        if report["type"] in {"METAR", "SPECI"} and bundle["metar"] is None:
            bundle["metar"] = report
        elif report["type"] == "TAF" and bundle["taf"] is None:
            bundle["taf"] = report

    return bundle
