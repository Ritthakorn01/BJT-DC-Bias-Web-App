import unittest

from spice_engine import AcSweep, Transient
from spice_plots import ac_png, tran_png


class PlotTests(unittest.TestCase):
    def test_ac_plot_returns_png_bytes(self):
        ac = AcSweep(freq=(10.0, 100.0, 1000.0), gain_db=(4.7, 4.8, 4.9),
                     phase_deg=(-167.0, -179.0, -179.9),
                     midband_gain_db=4.9, gain_at_1khz_db=4.9)
        png = ac_png(ac)
        self.assertTrue(png.startswith(b"\x89PNG"))
        self.assertGreater(len(png), 3000)

    def test_single_point_still_renders(self):
        ac = AcSweep(freq=(1000.0,), gain_db=(4.9,), phase_deg=(-180.0,),
                     midband_gain_db=4.9, gain_at_1khz_db=4.9)
        self.assertTrue(ac_png(ac).startswith(b"\x89PNG"))

    def test_tran_plot_returns_png_bytes(self):
        tr = Transient(time=(0.0, 1e-3, 2e-3), vin=(0.0, 0.01, 0.0),
                       vout=(0.0, -0.0176, 0.0),
                       vin_pp=0.02, vout_pp=0.0351, inverted=True)
        png = tran_png(tr)
        self.assertTrue(png.startswith(b"\x89PNG"))
        self.assertGreater(len(png), 3000)
