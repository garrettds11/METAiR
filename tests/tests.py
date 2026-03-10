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

    def test_rvr_fixed_group(self) -> None:
        report = "METAR KJFK 121651Z 18012KT 10SM R36/2400FT FEW020 28/18 A2992"
        parsed = parse_metar(report)

        self.assertEqual(
            parsed["runway_visual_range"][0],
            {
                "raw": "R36/2400FT",
                "runway_designator": "36",
                "lower_value_ft": 2400,
                "upper_value_ft": None,
                "variable": False,
                "qualifier": None,
                "lower_qualifier": None,
                "upper_qualifier": None,
                "unit": "FT",
            },
        )
        self.assertEqual(parsed["visibility"]["value"], 10)

    def test_rvr_variable_group(self) -> None:
        report = "METAR KJFK 121651Z 18012KT 10SM R04L/0600V1000FT FEW020 28/18 A2992"
        parsed = parse_metar(report)

        self.assertEqual(parsed["runway_visual_range"][0]["runway_designator"], "04L")
        self.assertEqual(parsed["runway_visual_range"][0]["lower_value_ft"], 600)
        self.assertEqual(parsed["runway_visual_range"][0]["upper_value_ft"], 1000)
        self.assertTrue(parsed["runway_visual_range"][0]["variable"])
        self.assertIsNone(parsed["runway_visual_range"][0]["qualifier"])
        self.assertIsNone(parsed["runway_visual_range"][0]["lower_qualifier"])
        self.assertIsNone(parsed["runway_visual_range"][0]["upper_qualifier"])

    def test_rvr_above_range_group(self) -> None:
        report = "METAR KJFK 121651Z 18012KT 10SM R27/P6000FT FEW020 28/18 A2992"
        parsed = parse_metar(report)

        self.assertEqual(parsed["runway_visual_range"][0]["qualifier"], "P")
        self.assertEqual(parsed["runway_visual_range"][0]["lower_value_ft"], 6000)

    def test_rvr_below_range_group(self) -> None:
        report = "METAR KJFK 121651Z 18012KT 10SM R18/M0600FT FEW020 28/18 A2992"
        parsed = parse_metar(report)

        self.assertEqual(parsed["runway_visual_range"][0]["qualifier"], "M")
        self.assertEqual(parsed["runway_visual_range"][0]["lower_value_ft"], 600)

    def test_multiple_rvr_groups(self) -> None:
        report = "METAR KJFK 121651Z 18012KT 10SM R36/2400FT R04L/0600V1000FT FEW020 28/18 A2992"
        parsed = parse_metar(report)

        self.assertEqual(len(parsed["runway_visual_range"]), 2)
        self.assertEqual(parsed["runway_visual_range"][1]["runway_designator"], "04L")

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


    def test_variant_whitespace_bundle_normalization(self) -> None:
        raw = """  METAR   KJFK 121651Z  18012KT 10SM FEW020 28/18 A2992  

   TAF   KJFK 121720Z 1218/1324  18010KT 9999 SCT020  """
        parsed = parse_text(raw)

        self.assertEqual(parsed["report_type"], "BUNDLE")
        self.assertEqual(parsed["metar"]["station"], "KJFK")
        self.assertEqual(parsed["taf"]["station"], "KJFK")

    def test_variant_missing_optional_groups_metar(self) -> None:
        report = "METAR KJFK 121651Z AUTO 18012KT A2992"
        parsed = parse_metar(report)

        self.assertEqual(parsed["modifier"], "AUTO")
        self.assertIsNone(parsed["visibility"])
        self.assertEqual(parsed["sky"], [])
        self.assertIsNone(parsed["temperature"])
        self.assertEqual(parsed["altimeter"]["value"], 29.92)
        self.assertEqual(parsed["unparsed_tokens"], [])

    def test_variant_metar_cor_modifier(self) -> None:
        report = "METAR KDEN 121653Z COR 35015G25KT 10SM FEW030 18/M02 A3010"
        parsed = parse_metar(report)

        self.assertEqual(parsed["modifier"], "COR")
        self.assertEqual(parsed["wind"]["gust_kt"], 25)
        self.assertEqual(parsed["temperature"]["dewpoint_c"], -2)

    def test_variant_fractional_visibility_from_samples(self) -> None:
        report = "SPECI KBAD 080454Z AUTO 24007KT 1 3/8SM +RA BR SCT002 BKN044 OVC055 18/17 A3011"
        parsed = parse_metar(report)

        self.assertEqual(parsed["visibility"], {"raw": "1 3/8SM", "value": 1.375, "unit": "SM", "qualifier": None})

    def test_variant_p6sm_visibility_from_authoritative_doc(self) -> None:
        report = "TAF KORD 032320Z 0400/0506 VRB05KT P6SM FEW050 SCT080 OVC110"
        parsed = parse_taf(report)

        visibility = parsed["segments"][0]["conditions"]["visibility"]
        self.assertEqual(visibility, {"raw": "P6SM", "value": 6, "unit": "SM", "qualifier": "P"})

    def test_variant_missing_temperature_value_is_preserved(self) -> None:
        report = "METAR KJFK 121651Z 18012KT 10SM FEW020 M02/ A2992"
        parsed = parse_metar(report)

        self.assertIsNone(parsed["temperature"])
        self.assertIn("M02/", parsed["unparsed_tokens"])

    def test_variant_taf_prefix_modifiers_are_gracefully_tolerated(self) -> None:
        for modifier in ("AMD", "COR", "CCA", "CCB"):
            with self.subTest(modifier=modifier):
                report = f"TAF {modifier} KJFK 121720Z 1218/1324 18010KT 9999 SCT020"
                parsed = parse_taf(report)

                self.assertEqual(parsed["station"], "KJFK")
                self.assertEqual(parsed["issued_at_utc"], "121720Z")
                self.assertEqual(parsed["validity"], {"from": "1218", "to": "1324"})
                self.assertEqual(parsed["unparsed_tokens"], [modifier])
                self.assertEqual(parsed["segments"][0]["conditions"]["wind"]["speed_kt"], 10)

    def test_variant_taf_nil_is_preserved_without_breaking_metadata(self) -> None:
        report = "TAF KJFK 121720Z NIL"
        parsed = parse_taf(report)

        self.assertEqual(parsed["station"], "KJFK")
        self.assertEqual(parsed["issued_at_utc"], "121720Z")
        self.assertEqual(parsed["segments"][0]["conditions"]["unparsed_tokens"], ["NIL"])


if __name__ == "__main__":
    unittest.main()
