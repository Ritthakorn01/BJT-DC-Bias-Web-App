import os
import shutil
import subprocess
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

from spice_engine import (
    MODEL_PATH,
    AmpInputs,
    SpiceError,
    build_ac_netlist,
    build_op_netlist,
    build_tran_netlist,
    parse_ac,
    parse_op,
    parse_tran,
    run_netlist,
    analyze,
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


class RunnerTests(unittest.TestCase):
    def test_missing_binary_reports_thai_error(self):
        with mock.patch.dict(os.environ, {"NGSPICE_BIN": "no-such-ngspice-xyz"}):
            with self.assertRaises(SpiceError) as ctx:
                run_netlist("* t\n.end\n", "op")
        self.assertIn("ไม่พบ ngspice", ctx.exception.message)

    def test_timeout_reports_thai_error(self):
        with mock.patch("spice_engine.subprocess.run",
                        side_effect=subprocess.TimeoutExpired("ngspice", 20)):
            with self.assertRaises(SpiceError) as ctx:
                run_netlist("* t\n.end\n", "op")
        self.assertIn("นานเกินกำหนด", ctx.exception.message)

    def test_nonzero_exit_includes_stderr_tail(self):
        fake = mock.Mock(returncode=1, stdout="", stderr="Error: singular matrix")
        with mock.patch("spice_engine.subprocess.run", return_value=fake):
            with self.assertRaises(SpiceError) as ctx:
                run_netlist("* t\n.end\n", "op")
        self.assertIn("ไม่สำเร็จ", ctx.exception.message)
        self.assertIn("singular matrix", ctx.exception.message)

    def test_missing_output_file_is_empty_error(self):
        fake = mock.Mock(returncode=0,
                         stdout="** ngspice-47 : Circuit level simulation program", stderr="")
        with mock.patch("spice_engine.subprocess.run", return_value=fake):
            with self.assertRaises(SpiceError) as ctx:
                run_netlist("* t\n.end\n", "op")
        self.assertIn("ไม่คืนผลลัพธ์", ctx.exception.message)

    def test_success_returns_table_and_version(self):
        def fake_run(cmd, **kwargs):
            Path(kwargs["cwd"], "out.txt").write_text("time v(in)\n0 0\n", encoding="ascii")
            return mock.Mock(returncode=0,
                             stdout="** ngspice-47 : Circuit level simulation program",
                             stderr="")

        with mock.patch("spice_engine.subprocess.run", side_effect=fake_run):
            table, version = run_netlist("* t\n.end\n", "op")
        self.assertIn("time v(in)", table)
        self.assertEqual(version, "47")


OP_TABLE = """ vcc             v(vb)           v(ve)           v(vc)           v(vcc)          @q1[ic]         @q1[ib]
 1.20000000e+01  2.00367450e+00  1.33287974e+00  9.08721626e+00  1.20000000e+01  1.32403477e-03  8.88736584e-06
"""

AC_TABLE = """ frequency       v(out)          v(out)          v(in)           v(in)
 1.00000000e+01 -1.68825586e+00 -3.90396170e-01  1.00000000e+00  0.00000000e+00
 1.00000000e+03 -1.75560000e+00 -2.00000000e-02  1.00000000e+00  0.00000000e+00
"""

TRAN_TABLE = """ time            v(in)           v(out)
 0.00000000e+00  0.00000000e+00  0.00000000e+00
 2.50000000e-07  1.57079632e-03 -4.66643146e-03
"""


class ParserTests(unittest.TestCase):
    def test_op_reads_node_voltages_and_device_currents(self):
        op = parse_op(OP_TABLE)
        self.assertAlmostEqual(op.vb, 2.00367450, places=6)
        self.assertAlmostEqual(op.vc, 9.08721626, places=6)
        self.assertAlmostEqual(op.vce, 9.08721626 - 1.33287974, places=6)
        self.assertAlmostEqual(op.ic, 1.32403477e-03, places=9)
        self.assertEqual(op.region, "Forward Active")

    def test_ac_pairs_real_and_imag_columns(self):
        ac = parse_ac(AC_TABLE)
        self.assertEqual(len(ac.freq), 2)
        self.assertAlmostEqual(ac.freq[0], 10.0)
        self.assertAlmostEqual(ac.gain_db[0], 4.7747, places=3)
        self.assertAlmostEqual(abs(ac.phase_deg[0]), 166.98, places=1)

    def test_tran_computes_peak_to_peak_and_inversion(self):
        tr = parse_tran(TRAN_TABLE, 1e3)
        self.assertEqual(len(tr.time), 2)
        self.assertAlmostEqual(tr.vin_pp, 1.57079632e-03, places=9)
        self.assertTrue(tr.inverted)

    def test_malformed_table_raises_spice_error(self):
        with self.assertRaises(SpiceError) as ctx:
            parse_ac("garbage\n")
        self.assertIn("อ่านผลลัพธ์", ctx.exception.message)

    def test_header_only_table_is_rejected(self):
        with self.assertRaises(SpiceError):
            parse_tran(" time v(in) v(out)\n")


HAS_NGSPICE = shutil.which(os.environ.get("NGSPICE_BIN", "ngspice")) is not None


@unittest.skipUnless(HAS_NGSPICE, "ngspice not installed")
class AnalyzeIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.inputs = AmpInputs(vcc=12.0, r1=100e3, r2=22e3, rc=2.2e3, re=1e3,
                                rl=10e3, cin=10e-6, cout=10e-6,
                                vs_peak=10e-3, freq=1e3,
                                beta_ref=100.0, vbe_ref=0.70)

    def test_baseline_matches_measured_values(self):
        run = analyze(self.inputs)
        self.assertAlmostEqual(run.op.vb, 2.0037, delta=0.01)
        self.assertAlmostEqual(run.op.ve, 1.3329, delta=0.01)
        self.assertAlmostEqual(run.op.vc, 9.0872, delta=0.02)
        self.assertAlmostEqual(run.op.ic, 1.3240e-3, delta=1e-5)
        self.assertEqual(run.op.region, "Forward Active")
        self.assertEqual(len(run.ac.freq), 101)
        self.assertAlmostEqual(run.ac.midband_gain_db, 4.890, delta=0.05)
        self.assertLess(abs(abs(run.ac.phase_deg[-1]) - 180.0), 5.0)
        self.assertEqual(len(run.tran.time), 2008)
        self.assertAlmostEqual(run.tran.vin_pp, 0.0200, delta=1e-4)
        self.assertAlmostEqual(run.tran.vout_pp, 0.0351, delta=5e-4)
        self.assertTrue(run.tran.inverted)
        self.assertEqual(run.engine_version, "47")

    def test_larger_re_lowers_collector_current(self):
        higher = analyze(replace(self.inputs, re=2e3))
        self.assertLess(higher.op.ic, 1.3240e-3)

    def test_doubling_source_doubles_output_swing(self):
        louder = analyze(replace(self.inputs, vs_peak=20e-3))
        self.assertAlmostEqual(louder.tran.vout_pp, 0.0702, delta=2e-3)

    def test_model_path_with_thai_and_space_still_runs(self):
        with tempfile.TemporaryDirectory(prefix="โมเดล ทดสอบ ") as tmp:
            target = Path(tmp, "โมเดล 2n3904.lib")
            shutil.copy(MODEL_PATH, target)
            with mock.patch.dict(os.environ, {"SPICE_MODEL_PATH": str(target)}):
                run = analyze(self.inputs)
        self.assertEqual(run.op.region, "Forward Active")

    def test_extreme_values_never_raise_unexpected_exception(self):
        for bad in (replace(self.inputs, re=1e-3), replace(self.inputs, vs_peak=50.0)):
            try:
                analyze(bad)
            except SpiceError:
                pass
