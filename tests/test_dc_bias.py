import unittest

from dc_bias import calculate


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


if __name__ == "__main__":
    unittest.main()
