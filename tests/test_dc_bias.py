import unittest
import math

from dc_bias import (
    ValidationError,
    calculate,
    calculate_divider,
    calculate_emitter,
    calculate_fixed,
    classify_region,
    to_float,
    validate_common,
    validate_inputs,
    validate_resistors,
)


class ReferencePointTests(unittest.TestCase):
    def setUp(self):
        # VCC=12, R1=100k, R2=22k, RC=2.2k, RE=1k, beta=100, VBE=0.70
        self.result = calculate(12.0, 100_000.0, 22_000.0, 2_200.0, 1_000.0, 100.0, 0.70)

    def test_voltages_match_hand_calculation(self):
        self.assertAlmostEqual(self.result.vth, 2.164, delta=0.01)
        self.assertAlmostEqual(self.result.vb, 1.942, delta=0.01)
        self.assertAlmostEqual(self.result.ve, 1.242, delta=0.01)
        self.assertAlmostEqual(self.result.vc, 9.294, delta=0.01)
        self.assertAlmostEqual(self.result.vce, 8.052, delta=0.01)

    def test_currents_match_hand_calculation(self):
        self.assertAlmostEqual(self.result.ic * 1000, 1.230, delta=0.01)
        self.assertAlmostEqual(self.result.ie * 1000, 1.242, delta=0.01)
        self.assertAlmostEqual(self.result.ib * 1_000_000, 12.299, delta=0.01)

    def test_reference_point_is_forward_active(self):
        self.assertEqual(self.result.region, "Forward Active")
        self.assertEqual(self.result.warnings, ())

    def test_huge_beta_keeps_ic_at_forward_active_limit(self):
        # เมื่อ β → ∞: IB → 0 และ IC → (VTH − VBE)/RE = 1.4639 mA (คำนวณมือ)
        result = calculate(12.0, 100_000.0, 22_000.0, 2_200.0, 1_000.0, 1e308, 0.70)

        self.assertEqual(result.region, "Forward Active")
        self.assertAlmostEqual(result.ic * 1000, 1.4639, delta=0.01)
        for value in (result.ib, result.ic, result.ie, result.ve, result.vb,
                      result.vc, result.vce):
            self.assertTrue(math.isfinite(value), f"ค่าที่ได้ต้องเป็นจำนวนจำกัด: {value}")


class InputParsingTests(unittest.TestCase):
    def test_accepts_surrounding_whitespace(self):
        self.assertEqual(to_float("  100 ", "R1"), 100.0)

    def test_accepts_thousands_separator(self):
        self.assertEqual(to_float("1,000", "R1"), 1000.0)

    def test_rejects_empty(self):
        with self.assertRaises(ValidationError):
            to_float("   ", "R1")

    def test_rejects_non_numeric(self):
        with self.assertRaises(ValidationError):
            to_float("abc", "R1")

    def test_rejects_non_finite(self):
        for text in ("nan", "inf", "-inf", "1e400"):
            with self.subTest(text=text):
                with self.assertRaises(ValidationError) as ctx:
                    to_float(text, "R1")
                self.assertIn("R1", ctx.exception.message)


class ValidationTests(unittest.TestCase):
    def test_rejects_zero_resistance(self):
        with self.assertRaises(ValidationError):
            validate_inputs(12.0, 0.0, 22_000.0, 2_200.0, 1_000.0, 100.0, 0.70)

    def test_rejects_non_positive_beta(self):
        with self.assertRaises(ValidationError):
            validate_inputs(12.0, 100_000.0, 22_000.0, 2_200.0, 1_000.0, 0.0, 0.70)

    def test_accepts_vbe_at_vcc_so_model_reports_cutoff(self):
        # ใบงาน Lab 03: อินพุตถูกต้องแต่ IB ≤ 0 → warning ของแบบจำลอง ไม่ใช่ input error
        validate_inputs(12.0, 100_000.0, 22_000.0, 2_200.0, 1_000.0, 100.0, 12.0)
        result = calculate(12.0, 100_000.0, 22_000.0, 2_200.0, 1_000.0, 100.0, 12.0)
        self.assertEqual(result.region, "Cutoff")
        self.assertTrue(any("Forward-Active" in w for w in result.warnings))


class ModeValidationTests(unittest.TestCase):
    def test_common_fields_accept_valid_values(self):
        validate_common(12.0, 100.0, 0.70)

    def test_common_fields_reject_non_positive_vcc(self):
        with self.assertRaises(ValidationError):
            validate_common(0.0, 100.0, 0.70)

    def test_resistors_need_only_the_fields_of_the_selected_mode(self):
        # Fixed Bias มีแค่ RB — ต้องไม่บังคับ R1, R2, RE
        validate_resistors(RB=1_000_000.0)

    def test_resistors_report_the_field_name(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_resistors(RB=0.0)
        self.assertIn("RB", ctx.exception.message)


class RegionThresholdTests(unittest.TestCase):
    def test_vce_at_exact_threshold_is_saturation(self):
        self.assertEqual(classify_region(0.2), "Saturation")

    def test_vce_just_above_threshold_is_forward_active(self):
        self.assertEqual(classify_region(0.2001), "Forward Active")


class FixedBiasTests(unittest.TestCase):
    def test_reference_point_matches_hand_calculation(self):
        # VCC=12, RB=1M, RC=2.2k, β=100, VBE=0.70 → A2
        result = calculate_fixed(12.0, 1_000_000.0, 2_200.0, 100.0, 0.70)

        self.assertAlmostEqual(result.ib * 1e6, 11.300, delta=0.01)
        self.assertAlmostEqual(result.ic * 1e3, 1.130, delta=0.01)
        self.assertAlmostEqual(result.ie * 1e3, 1.141, delta=0.01)
        self.assertEqual(result.ve, 0.0)
        self.assertAlmostEqual(result.vb, 0.70, delta=0.01)
        self.assertAlmostEqual(result.vc, 9.514, delta=0.01)
        self.assertAlmostEqual(result.vce, 9.514, delta=0.01)
        self.assertEqual(result.region, "Forward Active")
        self.assertEqual(result.warnings, ())

    def test_cutoff_when_vbe_reaches_vcc(self):
        result = calculate_fixed(12.0, 1_000_000.0, 2_200.0, 100.0, 12.0)

        self.assertEqual(result.region, "Cutoff")
        self.assertEqual(result.ic, 0.0)
        self.assertGreater(len(result.warnings), 0)


class EmitterBiasTests(unittest.TestCase):
    def test_reference_point_matches_hand_calculation(self):
        # VCC=12, RB=1M, RC=2.2k, RE=1k, β=100, VBE=0.70 → A3
        result = calculate_emitter(12.0, 1_000_000.0, 2_200.0, 1_000.0, 100.0, 0.70)

        self.assertAlmostEqual(result.ib * 1e6, 10.263, delta=0.01)
        self.assertAlmostEqual(result.ic * 1e3, 1.0263, delta=0.01)
        self.assertAlmostEqual(result.ie * 1e3, 1.0366, delta=0.01)
        self.assertAlmostEqual(result.ve, 1.0366, delta=0.01)
        self.assertAlmostEqual(result.vb, 1.7366, delta=0.01)
        self.assertAlmostEqual(result.vc, 9.7421, delta=0.01)
        self.assertAlmostEqual(result.vce, 8.7054, delta=0.01)

    def test_larger_re_lowers_ic(self):
        # A4: RE 1k → 2k ทำให้ IC ลด
        result = calculate_emitter(12.0, 1_000_000.0, 2_200.0, 2_000.0, 100.0, 0.70)

        self.assertAlmostEqual(result.ic * 1e3, 0.9401, delta=0.01)
        self.assertAlmostEqual(result.vce, 8.0328, delta=0.01)

    def test_cutoff_when_vbe_reaches_vcc(self):
        result = calculate_emitter(12.0, 1_000_000.0, 2_200.0, 1_000.0, 100.0, 12.0)

        self.assertEqual(result.region, "Cutoff")
        self.assertEqual(result.ic, 0.0)


class ResultDictTests(unittest.TestCase):
    def test_shared_keys_and_units(self):
        data = calculate_fixed(12.0, 1_000_000.0, 2_200.0, 100.0, 0.70).to_dict()

        self.assertEqual(
            set(data),
            {"vb_v", "ve_v", "vc_v", "vce_v", "ic_ma", "ib_ua", "ie_ma",
             "region", "warnings"},
        )
        self.assertAlmostEqual(data["ic_ma"], 1.130, delta=0.01)
        self.assertAlmostEqual(data["vce_v"], 9.514, delta=0.01)
        self.assertEqual(data["region"], "Forward Active")
        self.assertEqual(data["warnings"], [])

    def test_divider_alias_still_works(self):
        self.assertEqual(
            calculate_divider(12.0, 100_000.0, 22_000.0, 2_200.0, 1_000.0, 100.0, 0.70),
            calculate(12.0, 100_000.0, 22_000.0, 2_200.0, 1_000.0, 100.0, 0.70),
        )


class CalculatorInputTests(unittest.TestCase):
    """ฟังก์ชันคำนวณต้องไม่ปล่อย traceback หรือผลติดลบเมื่อถูกเรียกตรง."""

    def test_fixed_rejects_zero_rb(self):
        with self.assertRaises(ValidationError) as ctx:
            calculate_fixed(12.0, 0.0, 2_200.0, 100.0, 0.70)

        self.assertIn("RB", ctx.exception.message)

    def test_fixed_rejects_negative_rb(self):
        with self.assertRaises(ValidationError) as ctx:
            calculate_fixed(12.0, -1_000_000.0, 2_200.0, 100.0, 0.70)

        self.assertIn("RB", ctx.exception.message)

    def test_emitter_rejects_zero_rb(self):
        with self.assertRaises(ValidationError) as ctx:
            calculate_emitter(12.0, 0.0, 2_200.0, 1_000.0, 100.0, 0.70)

        self.assertIn("RB", ctx.exception.message)

    def test_divider_rejects_zero_r1(self):
        with self.assertRaises(ValidationError) as ctx:
            calculate_divider(12.0, 0.0, 22_000.0, 2_200.0, 1_000.0, 100.0, 0.70)

        self.assertIn("R1", ctx.exception.message)


class RegionTests(unittest.TestCase):
    def test_cutoff_when_base_divider_below_vbe(self):
        result = calculate(12.0, 100_000.0, 1_000.0, 2_200.0, 1_000.0, 100.0, 0.70)
        self.assertEqual(result.region, "Cutoff")
        self.assertGreater(len(result.warnings), 0)
        self.assertEqual(result.ic, 0.0)
        self.assertEqual(result.ve, 0.0)

    def test_saturation_when_collector_resistor_too_large(self):
        result = calculate(12.0, 100_000.0, 22_000.0, 50_000.0, 1_000.0, 100.0, 0.70)
        self.assertEqual(result.region, "Saturation")
        self.assertEqual(len(result.warnings), 2)

    def test_reference_point_has_no_warning(self):
        result = calculate(12.0, 100_000.0, 22_000.0, 2_200.0, 1_000.0, 100.0, 0.70)
        self.assertEqual(result.region, "Forward Active")
        self.assertEqual(result.warnings, ())


if __name__ == "__main__":
    unittest.main()
