import unittest

from spice_engine import (
    AmpInputs,
    build_ac_netlist,
    build_op_netlist,
    build_tran_netlist,
)


class NetlistTests(unittest.TestCase):
    def setUp(self):
        self.inputs = AmpInputs(vcc=12.0, r1=100e3, r2=22e3, rc=2.2e3, re=1e3,
                                rl=10e3, cin=10e-6, cout=10e-6,
                                vs_peak=10e-3, freq=1e3,
                                beta_ref=100.0, vbe_ref=0.70)

    def test_op_deck_has_components_and_wrdata(self):
        deck = build_op_netlist(self.inputs)
        self.assertIn(".include model.lib", deck)
        self.assertIn("VCC vcc 0 DC 12", deck)
        self.assertIn("R1 vcc vb 100000", deck)
        self.assertIn("RC vcc vc 2200", deck)
        self.assertIn("RE ve 0 1000", deck)
        self.assertIn("Q1 vc vb ve Q2N3904", deck)
        self.assertIn("set wr_singlescale", deck)
        self.assertIn("wrdata out.txt", deck)
        self.assertTrue(deck.isascii())
        self.assertTrue(deck.rstrip().endswith(".end"))

    def test_ac_deck_sweeps_and_saves_both_nodes(self):
        deck = build_ac_netlist(self.inputs)
        self.assertIn("ac dec 20 10 1meg", deck)
        self.assertIn("wrdata out.txt v(out) v(in)", deck)

    def test_tran_deck_uses_five_periods(self):
        deck = build_tran_netlist(self.inputs)
        self.assertIn("tran 2.5e-06 0.005", deck)
        self.assertIn("wrdata out.txt v(in) v(out)", deck)
