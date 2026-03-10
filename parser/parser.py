import re
from fractions import Fraction
from typing import Any, Dict, List, Optional


REPORT_START_RE = re.compile(r'^(METAR|SPECI|TAF)$')
ICAO_RE = re.compile(r'^[A-Z]{4}$')
TIME_RE = re.compile(r'^\d{6}Z$')
VALIDITY_RE = re.compile(r'^\d{4}/\d{4}$')

WIND_RE = re.compile(
    r'^(?P<dir>\d{3}|VRB)(?P<speed>\d{2,3})(G(?P<gust>\d{2,3}))?(?P<unit>KT)$'
)

VIS_SM_RE = re.compile(r'^(?P<value>\d{1,2}(?:/\d)?|\d+\s\d/\d)SM$')
VIS_M_RE = re.compile(r'^\d{4}$')

TEMP_DEW_RE = re.compile(r'^(M?\d{2})/(M?\d{2})$')
ALT_A_RE = re.compile(r'^A(\d{4})$')
ALT_Q_RE = re.compile(r'^Q(\d{4})$')
ALT_QNH_INS_RE = re.compile(r'^QNH(\d{4})INS$')

SKY_RE = re.compile(
    r'^(?P<cov>SKC|CLR|NSC|FEW|SCT|BKN|OVC|VV)(?P<height>\d{3}|///)?(?P<ctype>CB|TCU)?$'
)

TAF_RANGE_RE = re.compile(r'^\d{4}/\d{4}$')
TEMP_EXTREME_RE = re.compile(r'^(?P<kind>TX|TN)(?P<temp>M?\d{2})/(?P<time>\d{4}Z)$')

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


def parse_wind(token: str) -> Optional[Dict[str, Any]]:
    m = WIND_RE.match(token)
    if not m:
        return None
    direction = m.group("dir")
    return {
        "raw": token,
        "direction_degrees": None if direction == "VRB" else int(direction),
        "variable": direction == "VRB",
        "speed_kt": int(m.group("speed")),
        "gust_kt": int(m.group("gust")) if m.group("gust") else None,
        "unit": m.group("unit"),
        "variation": None,
    }


def parse_visibility(token: str) -> Optional[Dict[str, Any]]:
    m = VIS_SM_RE.match(token)
    if m:
        return {
            "raw": token,
            "value": parse_sm_value(m.group("value")),
            "unit": "SM",
            "qualifier": None,
        }
    if token == "9999":
        return {"raw": token, "value_m": 9999, "meaning": "10km_or_more"}
    if VIS_M_RE.match(token):
        return {"raw": token, "value_m": int(token), "unit": "m"}
    return None


def parse_sky(token: str) -> Optional[Dict[str, Any]]:
    m = SKY_RE.match(token)
    if not m:
        return None
    cov = m.group("cov")
    height = m.group("height")
    ctype = m.group("ctype")
    altitude_ft = None
    if height and height.isdigit():
        altitude_ft = int(height) * 100
    return {
        "raw": token,
        "coverage": cov,
        "coverage_text": COVERAGE_TEXT.get(cov),
        "altitude_ft": altitude_ft,
        "cloud_type": ctype,
    }


def parse_altimeter(token: str) -> Optional[Dict[str, Any]]:
    m = ALT_A_RE.match(token)
    if m:
        raw = m.group(1)
        return {"raw": token, "unit": "inHg", "value": float(raw[:2] + "." + raw[2:])}

    m = ALT_Q_RE.match(token)
    if m:
        return {"raw": token, "unit": "hPa", "value": int(m.group(1))}

    m = ALT_QNH_INS_RE.match(token)
    if m:
        raw = m.group(1)
        return {"raw": token, "unit": "inHg", "value": float(raw[:2] + "." + raw[2:])}

    return None


def parse_temp_dew(token: str) -> Optional[Dict[str, Any]]:
    m = TEMP_DEW_RE.match(token)
    if not m:
        return None
    return {
        "air_c": parse_signed_temp(m.group(1)),
        "dewpoint_c": parse_signed_temp(m.group(2)),
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
    precip = []
    obsc = []
    other = []

    for part in parts:
        if part in DESCRIPTORS and descriptor is None:
            descriptor = part
        elif part in PRECIP:
            precip.append(part)
        elif part in OBSCURATION:
            obsc.append(part)
        elif part in OTHER:
            other.append(part)
        else:
            return None

    return {
        "raw": token,
        "intensity": intensity,
        "proximity": proximity,
        "descriptor": descriptor,
        "precipitation": precip,
        "obscuration": obsc,
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


def parse_metar(report: str) -> Dict[str, Any]:
    tokens = report.split()
    out = {
        "type": None,
        "station": None,
        "issued_at_utc": None,
        "modifier": None,
        "wind": None,
        "visibility": None,
        "weather": [],
        "sky": [],
        "temperature": None,
        "altimeter": None,
        "remarks": {"raw_tokens": []},
        "unparsed_tokens": [],
    }

    in_remarks = False

    for token in tokens:
        if in_remarks:
            out["remarks"]["raw_tokens"].append(token)
            continue

        if out["type"] is None and token in ("METAR", "SPECI"):
            out["type"] = token
            continue

        if out["station"] is None and ICAO_RE.match(token):
            out["station"] = token
            continue

        if out["issued_at_utc"] is None and TIME_RE.match(token):
            out["issued_at_utc"] = token
            continue

        if token in ("AUTO", "COR") and out["modifier"] is None:
            out["modifier"] = token
            continue

        if out["wind"] is None:
            wind = parse_wind(token)
            if wind:
                out["wind"] = wind
                continue

        if out["visibility"] is None:
            visibility = parse_visibility(token)
            if visibility:
                out["visibility"] = visibility
                continue

        weather = parse_weather(token)
        if weather:
            out["weather"].append(weather)
            continue

        sky = parse_sky(token)
        if sky:
            out["sky"].append(sky)
            continue

        if out["temperature"] is None:
            temp_dew = parse_temp_dew(token)
            if temp_dew:
                out["temperature"] = temp_dew
                continue

        if out["altimeter"] is None:
            altimeter = parse_altimeter(token)
            if altimeter:
                out["altimeter"] = altimeter
                continue

        if token == "RMK":
            in_remarks = True
            continue

        out["unparsed_tokens"].append(token)

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

    for token in tokens:
        if conditions["wind"] is None:
            wind = parse_wind(token)
            if wind:
                conditions["wind"] = wind
                continue

        if conditions["visibility"] is None:
            visibility = parse_visibility(token)
            if visibility:
                conditions["visibility"] = visibility
                continue

        weather = parse_weather(token)
        if weather:
            conditions["weather"].append(weather)
            continue

        sky = parse_sky(token)
        if sky:
            conditions["sky"].append(sky)
            continue

        altimeter = parse_altimeter(token)
        if altimeter and conditions["altimeter"] is None:
            conditions["altimeter"] = altimeter
            continue

        temp_extreme = parse_temp_extreme(token)
        if temp_extreme:
            conditions["temperatures"].append(temp_extreme)
            continue

        conditions["unparsed_tokens"].append(token)

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

