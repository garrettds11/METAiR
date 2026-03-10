import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from parser.parser import parse_metar, parse_taf, parse_text


class ParserTests(unittest.TestCase):
    def parse_metar_with_remarks(self, remarks: str):
        report = f"METAR KJFK 121651Z 18012KT 10SM FEW020 28/18 A2992 RMK {remarks}"
        return parse_metar(report)

    def test_simple_metar(self) -> None:
        report = "METAR KJFK 121651Z 18012KT 10SM FEW020 28/18 A2992"
        parsed = parse_metar(report)

        self.assertEqual(parsed["type"], "METAR")
        self.assertEqual(parsed["station"], "KJFK")
        self.assertEqual(parsed["issued_at_utc"], "121651Z")
        self.assertEqual(parsed["wind"]["direction_degrees"], 180)
        self.assertEqual(parsed["wind"]["speed_kt"], 12)
        self.assertIsNone(parsed["wind"]["gust_kt"])
        self.assertEqual(parsed["visibility"]["value"], 10)
        self.assertEqual(parsed["sky"][0]["altitude_ft"], 2000)
        self.assertEqual(parsed["temperature"]["air_c"], 28)
        self.assertEqual(parsed["altimeter"]["value"], 29.92)
        self.assertEqual(parsed["unparsed_tokens"], [])

    def test_non_kt_wind_remains_unparsed(self) -> None:
        report = "METAR KJFK 121651Z 18012KMH 10SM FEW020 28/18 A2992"
        parsed = parse_metar(report)

        self.assertIsNone(parsed["wind"])
        self.assertIn("18012KMH", parsed["unparsed_tokens"])

    def test_metar_with_remarks(self) -> None:
        parsed = self.parse_metar_with_remarks("AO2 SLP138")

        self.assertEqual(parsed["remarks"]["raw_tokens"], ["AO2", "SLP138"])
        self.assertEqual(parsed["remarks"]["sea_level_pressure"]["value_hpa"], 1013.8)
        self.assertEqual(parsed["remarks"]["unparsed_tokens"], ["AO2"])

    def test_metar_with_gusting_wind(self) -> None:
        report = "METAR KDEN 121653Z 35015G25KT 10SM FEW030 18/M02 A3010"
        parsed = parse_metar(report)

        self.assertEqual(parsed["wind"]["direction_degrees"], 350)
        self.assertEqual(parsed["wind"]["speed_kt"], 15)
        self.assertEqual(parsed["wind"]["gust_kt"], 25)
        self.assertEqual(parsed["temperature"]["dewpoint_c"], -2)

    def test_metar_with_negative_temperatures(self) -> None:
        report = "METAR PANC 121653Z VRB03KT 6SM BKN015 M02/M05 A2988"
        parsed = parse_metar(report)

        self.assertTrue(parsed["wind"]["variable"])
        self.assertEqual(parsed["temperature"]["air_c"], -2)
        self.assertEqual(parsed["temperature"]["dewpoint_c"], -5)
        self.assertEqual(parsed["visibility"]["value"], 6)

    def test_remark_hourly_precipitation(self) -> None:
        parsed = self.parse_metar_with_remarks("P0001")
        self.assertEqual(parsed["remarks"]["hourly_precipitation"], {"raw": "P0001", "amount_in": 0.01})

    def test_remark_three_six_hour_precipitation(self) -> None:
        parsed = self.parse_metar_with_remarks("60045")
        self.assertEqual(parsed["remarks"]["precipitation_3_6_hour"], {"raw": "60045", "amount_in": 0.45})

    def test_remark_twenty_four_hour_precipitation(self) -> None:
        parsed = self.parse_metar_with_remarks("70068")
        self.assertEqual(parsed["remarks"]["precipitation_24_hour"], {"raw": "70068", "amount_in": 0.68})

    def test_remark_six_hour_max_temperature(self) -> None:
        parsed = self.parse_metar_with_remarks("10270")
        self.assertEqual(parsed["remarks"]["temperature_6_hour_max"], {"raw": "10270", "c": 27.0})

    def test_remark_six_hour_min_temperature(self) -> None:
        parsed = self.parse_metar_with_remarks("21015")
        self.assertEqual(parsed["remarks"]["temperature_6_hour_min"], {"raw": "21015", "c": -1.5})

    def test_remark_twenty_four_hour_temperature_extremes(self) -> None:
        parsed = self.parse_metar_with_remarks("402400147")
        self.assertEqual(
            parsed["remarks"]["temperature_24_hour_extremes"],
            {"raw": "402400147", "max_c": 24.0, "min_c": 14.7},
        )

    def test_remark_peak_wind(self) -> None:
        parsed = self.parse_metar_with_remarks("PK WND 32031/1756")
        self.assertEqual(
            parsed["remarks"]["peak_wind"],
            {"raw": "PK WND 32031/1756", "direction_degrees": 320, "speed_kt": 31, "at_utc": "1756"},
        )

    def test_remark_wind_shift(self) -> None:
        parsed = self.parse_metar_with_remarks("WSHFT 15")
        self.assertEqual(parsed["remarks"]["wind_shift"], {"raw": "WSHFT 15", "at_utc": "15"})

    def test_taf_with_becmg(self) -> None:
        report = (
            "TAF KJFK 121720Z 1218/1324 18010KT 9999 SCT020 "
            "BECMG 1220/1222 22015KT 8000 -RA BKN015"
        )
        parsed = parse_taf(report)

        self.assertEqual(parsed["type"], "TAF")
        self.assertEqual(parsed["station"], "KJFK")
        self.assertEqual(parsed["validity"], {"from": "1218", "to": "1324"})
        self.assertEqual(len(parsed["segments"]), 2)
        self.assertEqual(parsed["segments"][1]["change_type"], "BECMG")
        self.assertEqual(parsed["segments"][1]["time_range"], {"from": "1220", "to": "1222"})
        self.assertEqual(parsed["segments"][1]["conditions"]["wind"]["speed_kt"], 15)

    def test_taf_with_cb_cloud_type(self) -> None:
        report = "TAF KBAD 092000Z 0920/1102 18010G15KT 9999 -SHRA VCTS OVC020CB QNH2993INS"
        parsed = parse_taf(report)
        initial = parsed["segments"][0]["conditions"]

        self.assertEqual(initial["sky"][0]["cloud_type"], "CB")
        self.assertEqual(initial["altimeter"]["value"], 29.93)
        self.assertEqual(initial["weather"][0]["raw"], "-SHRA")
        self.assertEqual(initial["weather"][1]["raw"], "VCTS")

    def test_combined_metar_and_taf_bundle(self) -> None:
        raw = (
            "METAR KJFK 121651Z 18012KT 10SM FEW020 28/18 A2992\n\n"
            "TAF KJFK 121720Z 1218/1324 18010KT 9999 SCT020"
        )
        parsed = parse_text(raw)

        self.assertEqual(parsed["report_type"], "BUNDLE")
        self.assertEqual(len(parsed["reports"]), 2)
        self.assertEqual(parsed["metar"]["type"], "METAR")
        self.assertEqual(parsed["taf"]["type"], "TAF")

    def test_kbad_example_fixture(self) -> None:
        sample_path = ROOT / "samples" / "sample_metar_1.txt"
        parsed = parse_text(sample_path.read_text(encoding="utf-8"))

        self.assertEqual(parsed["report_type"], "BUNDLE")
        self.assertEqual(parsed["metar"]["station"], "KBAD")
        self.assertEqual(parsed["metar"]["remarks"]["sea_level_pressure"], {"raw": "SLP138", "value_hpa": 1013.8})
        self.assertEqual(parsed["metar"]["remarks"]["precipitation_3_6_hour"], {"raw": "60001", "amount_in": 0.01})
        self.assertEqual(parsed["metar"]["remarks"]["temperature_6_hour_max"], {"raw": "10270", "c": 27.0})
        self.assertEqual(parsed["metar"]["remarks"]["temperature_6_hour_min"], {"raw": "20240", "c": 24.0})
        self.assertEqual(parsed["taf"]["segments"][0]["conditions"]["sky"][0]["cloud_type"], "CB")
        self.assertEqual(parsed["taf"]["segments"][1]["conditions"]["weather"][0], {"raw": "NSW", "meaning": "no_significant_weather"})
        self.assertEqual(parsed["taf"]["temperatures"]["max"]["c"], 25)
        self.assertEqual(parsed["taf"]["temperatures"]["min"]["at_utc"], "1012Z")

    def test_sample_metar_9_real_remark_coverage(self) -> None:
        sample_path = ROOT / "samples" / "sample_metar_9.txt"
        parsed = parse_text(sample_path.read_text(encoding="utf-8"))

        reports = [report for report in parsed["reports"] if report["type"] in {"METAR", "SPECI"}]

        self.assertTrue(any(report["remarks"]["hourly_precipitation"] for report in reports))
        self.assertTrue(any(report["remarks"]["precipitation_3_6_hour"] for report in reports))
        self.assertTrue(any(report["remarks"]["precipitation_24_hour"] for report in reports))
        self.assertTrue(any(report["remarks"]["temperature_24_hour_extremes"] for report in reports))
        self.assertTrue(any(report["remarks"]["peak_wind"] for report in reports))
        self.assertTrue(any(report["remarks"]["wind_shift"] for report in reports))
        self.assertTrue(any(any(token.startswith("T") and len(token) == 9 for token in report["remarks"]["unparsed_tokens"]) for report in reports))
        self.assertTrue(any(any(token.startswith("5") and len(token) == 5 for token in report["remarks"]["unparsed_tokens"]) for report in reports))


if __name__ == "__main__":
    unittest.main()
