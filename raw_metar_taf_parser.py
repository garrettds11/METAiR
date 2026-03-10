import re
from typing import Any, Dict, List, Optional


REPORT_START_RE = re.compile(r'^(METAR|SPECI|TAF)$')
ICAO_RE = re.compile(r'^[A-Z]{4}$')
TIME_RE = re.compile(r'^\d{6}Z$')
VALIDITY_RE = re.compile(r'^\d{4}/\d{4}$')

WIND_RE = re.compile(
    r'^(?P<dir>\d{3}|VRB)(?P<speed>\d{2,3})(G(?P<gust>\d{2,3}))?(?P<unit>KT|KMH|MPS)$'
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

TAF_CHANGE_RE = re.compile(r'^(BECMG|TEMPO|FM\d{4,6}|PROB\d{2})$')
TAF_RANGE_RE = re.compile(r'^\d{4}/\d{4}$')

INTENSITIES = {"+", "-"}
DESCRIPTORS = {"MI", "PR", "BC", "DR", "BL", "SH", "TS", "FZ"}
PRECIP = {"DZ", "RA", "SN", "SG", "IC", "PL", "GR", "GS", "UP"}
OBSCURATION = {"BR", "FG", "FU", "VA", "DU", "SA", "HZ"}
OTHER = {"PO", "SQ", "FC", "SS", "DS"}
SPECIAL_WEATHER = {"NSW", "CAVOK"}

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


def parse_wind(token: str) -> Optional[Dict[str, Any]]:
    m = WIND_RE.match(token)
    if not m:
        return None
    d = m.group("dir")
    return {
        "raw": token,
        "direction_degrees": None if d == "VRB" else int(d),
        "variable": d == "VRB",
        "speed": int(m.group("speed")),
        "gust": int(m.group("gust")) if m.group("gust") else None,
        "unit": m.group("unit"),
    }


def parse_visibility(token: str) -> Optional[Dict[str, Any]]:
    m = VIS_SM_RE.match(token)
    if m:
        return {"raw": token, "unit": "SM", "value": m.group("value")}
    if token == "9999":
        return {"raw": token, "unit": "m", "value": 9999, "meaning": "10km_or_more"}
    if VIS_M_RE.match(token):
        return {"raw": token, "unit": "m", "value": int(token)}
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
        return {"raw": token, "special": token}

    intensity = None
    s = token

    if s and s[0] in INTENSITIES:
        intensity = s[0]
        s = s[1:]

    proximity = None
    if s.startswith("VC"):
        proximity = "VC"
        s = s[2:]

    parts = []
    i = 0
    while i < len(s):
        parts.append(s[i:i+2])
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
            vis = parse_visibility(token)
            if vis:
                out["visibility"] = vis
                continue

        wx = parse_weather(token)
        if wx:
            out["weather"].append(wx)
            continue

        sky = parse_sky(token)
        if sky:
            out["sky"].append(sky)
            continue

        if out["temperature"] is None:
            td = parse_temp_dew(token)
            if td:
                out["temperature"] = td
                continue

        if out["altimeter"] is None:
            alt = parse_altimeter(token)
            if alt:
                out["altimeter"] = alt
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
        "temps": [],
        "unparsed_tokens": [],
    }

    for token in tokens:
        if conditions["wind"] is None:
            wind = parse_wind(token)
            if wind:
                conditions["wind"] = wind
                continue

        if conditions["visibility"] is None:
            vis = parse_visibility(token)
            if vis:
                conditions["visibility"] = vis
                continue

        wx = parse_weather(token)
        if wx:
            conditions["weather"].append(wx)
            continue

        sky = parse_sky(token)
        if sky:
            conditions["sky"].append(sky)
            continue

        alt = parse_altimeter(token)
        if alt and conditions["altimeter"] is None:
            conditions["altimeter"] = alt
            continue

        if token.startswith("TX") or token.startswith("TN"):
            conditions["temps"].append(token)
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
        "unparsed_tokens": [],
    }

    i = 0
    if tokens[i] == "TAF":
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
    current_tokens = []

    def flush():
        nonlocal current_tokens, current_type, current_range
        if current_tokens or current_type == "INITIAL":
            out["segments"].append({
                "change_type": current_type,
                "time_range": current_range,
                "conditions": parse_taf_conditions(current_tokens),
            })
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