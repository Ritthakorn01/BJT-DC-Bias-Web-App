import unittest
from dataclasses import replace
from unittest import mock

import app as app_module
import spice_engine
from app import create_app


class WebIndexTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_index_returns_form(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Calculate DC Bias", response.data)
        self.assertIn(b'name="vcc"', response.data)
        self.assertIn(b'name="r1"', response.data)


REFERENCE_FORM = {
    "vcc": "12", "r1": "100", "r2": "22", "rc": "2.2", "re": "1",
    "beta": "100", "vbe": "0.70", "r_unit": "k",
}


class CalculateRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def post(self, **overrides):
        data = dict(REFERENCE_FORM)
        data.update(overrides)
        return self.client.post("/calculate", data=data)

    def test_reference_inputs_render_results(self):
        response = self.post()
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("9.294", body)
        self.assertIn("8.052", body)
        self.assertIn("Forward Active", body)

    def test_invalid_input_shows_error_not_crash(self):
        response = self.post(r1="0")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("มากกว่า 0", body)
        self.assertNotIn("Traceback", body)

    def test_non_numeric_input_shows_error(self):
        response = self.post(vcc="abc")
        self.assertEqual(response.status_code, 200)
        self.assertIn("ตัวเลข", response.get_data(as_text=True))

    def test_resistor_unit_converts_kilo_ohm(self):
        kilo = self.post().get_data(as_text=True)
        ohm = self.post(r_unit="", r1="100000", r2="22000", rc="2200", re="1000").get_data(as_text=True)

        for body in (kilo, ohm):
            self.assertIn("9.294", body)
            self.assertIn("1.230 mA", body)
            self.assertIn("12.299 µA", body)
            self.assertIn("1.242 mA", body)

    def test_ohm_unit_is_not_scaled(self):
        body = self.post(r_unit="", r1="100", r2="22", rc="2.2", re="1").get_data(as_text=True)
        self.assertIn("1229.858 mA", body)

    def test_extreme_beta_does_not_show_nan(self):
        body = self.post(beta="1e12").get_data(as_text=True).lower()
        self.assertNotIn("nan", body)
        self.assertNotIn("inf", body)

    def test_unknown_resistor_unit_is_rejected(self):
        body = self.post(r_unit="M").get_data(as_text=True)
        self.assertIn("ต้องเป็น kΩ หรือ Ω", body)
        self.assertNotIn("Region:", body)

    def test_thai_messages_are_utf8(self):
        response = self.post(r1="0")
        self.assertIn("charset=utf-8", response.headers.get("Content-Type", "").lower())
        self.assertIn("มากกว่า 0", response.get_data(as_text=True))


FIXED_FORM = {
    "mode": "fixed", "vcc": "12", "vbe": "0.70", "beta": "100",
    "rc": "2.2", "rb": "1000", "r_unit": "k",
}
EMITTER_FORM = dict(FIXED_FORM, mode="emitter", re="1")


class ModeCalculateTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_fixed_mode_calculates(self):
        body = self.client.post("/calculate", data=FIXED_FORM).get_data(as_text=True)

        self.assertIn("Fixed Bias", body)
        self.assertIn("9.514", body)
        self.assertIn("1.130 mA", body)
        self.assertIn("Forward Active", body)

    def test_emitter_mode_uses_re(self):
        body = self.client.post("/calculate", data=EMITTER_FORM).get_data(as_text=True)

        self.assertIn("Emitter Bias", body)
        self.assertIn("1.026 mA", body)
        self.assertIn("8.705", body)

    def test_larger_re_changes_the_result(self):
        body = self.client.post(
            "/calculate", data=dict(EMITTER_FORM, re="2")
        ).get_data(as_text=True)

        self.assertIn("0.940 mA", body)
        self.assertIn("8.033", body)

    def test_unknown_mode_is_error(self):
        body = self.client.post(
            "/calculate", data=dict(FIXED_FORM, mode="mystery")
        ).get_data(as_text=True)

        self.assertIn("โหมดวงจรไม่ถูกต้อง", body)
        self.assertNotIn("Region:", body)

    def test_zero_rb_names_the_field(self):
        body = self.client.post(
            "/calculate", data=dict(FIXED_FORM, rb="0")
        ).get_data(as_text=True)

        self.assertIn("RB", body)
        self.assertNotIn("Region:", body)


class ModeSelectionTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_default_page_is_divider_with_divider_fields(self):
        body = self.client.get("/").get_data(as_text=True)

        self.assertIn('value="divider" selected', body)
        self.assertIn('id="r1"', body)
        self.assertNotIn('id="rb"', body)

    def test_fixed_mode_shows_rb_only(self):
        body = self.client.get("/?mode=fixed").get_data(as_text=True)

        self.assertIn('id="rb"', body)
        self.assertNotIn('id="r1"', body)
        self.assertIn('value="fixed" selected', body)

    def test_emitter_mode_shows_rb_and_re(self):
        body = self.client.get("/?mode=emitter").get_data(as_text=True)

        self.assertIn('id="rb"', body)
        self.assertIn('id="re"', body)
        self.assertNotIn('id="r1"', body)

    def test_unknown_mode_on_get_is_error(self):
        body = self.client.get("/?mode=mystery").get_data(as_text=True)

        self.assertIn("โหมดวงจรไม่ถูกต้อง", body)


class DefaultFormTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_divider_defaults(self):
        body = self.client.get("/").get_data(as_text=True)
        for field, value in (("vcc", "12"), ("vbe", "0.70"), ("rc", "2.2"),
                             ("r1", "100"), ("r2", "22"), ("re", "1"),
                             ("beta", "100")):
            self.assertIn(f'name="{field}" value="{value}"', body)

    def test_fixed_defaults_have_no_divider_fields(self):
        body = self.client.get("/?mode=fixed").get_data(as_text=True)
        self.assertIn('name="rb" value="1000"', body)
        self.assertIn('name="vcc" value="12"', body)
        self.assertNotIn('name="r1"', body)

    def test_emitter_defaults_have_re(self):
        body = self.client.get("/?mode=emitter").get_data(as_text=True)
        self.assertIn('name="rb" value="1000"', body)
        self.assertIn('name="re" value="1"', body)
        self.assertNotIn('name="r1"', body)

    def test_error_keeps_submitted_values(self):
        form = {"mode": "fixed", "vcc": "99", "vbe": "0.70", "beta": "100",
                "rc": "2.2", "rb": "0", "r_unit": "k"}
        body = self.client.post("/calculate", data=form).get_data(as_text=True)
        self.assertIn('name="vcc" value="99"', body)
        self.assertIn('name="rb" value="0"', body)

    def test_unknown_mode_has_no_defaults(self):
        body = self.client.get("/?mode=mystery").get_data(as_text=True)
        self.assertIn("โหมดวงจรไม่ถูกต้อง", body)
        self.assertNotIn('name="vcc"', body)


FAKE_RUN = spice_engine.SpiceRun(
    op=spice_engine.OpPoint(vb=2.0, ve=1.3, vc=9.1, vce=7.8, ic=1.3e-3,
                            ib=9e-6, region="Forward Active"),
    ac=spice_engine.AcSweep(freq=(1000.0,), gain_db=(4.89,), phase_deg=(-179.9,),
                            midband_gain_db=4.89, gain_at_1khz_db=4.89),
    tran=spice_engine.Transient(time=(0.0,), vin=(0.01,), vout=(-0.0176,),
                                vin_pp=0.02, vout_pp=0.035, inverted=True),
    ac_png=b"\x89PNG-fake", tran_png=b"\x89PNG-fake", engine_version="47")

VALID_AMP_FORM = dict(app_module.DEFAULT_FORMS["amp"], mode="amp")


class AmpModeTests(unittest.TestCase):
    def setUp(self):
        self.client = app_module.create_app().test_client()

    def test_get_amp_shows_spice_form_with_lab_defaults(self):
        html = self.client.get("/?mode=amp").get_data(as_text=True)
        self.assertIn('name="rl"', html)
        self.assertIn('name="vs_mv"', html)
        self.assertIn('value="10"', html)
        self.assertIn("CE Amplifier (SPICE)", html)

    def test_missing_value_keeps_form_and_reports_error(self):
        resp = self.client.post("/calculate", data={"mode": "amp", "vcc": "12", "r_unit": "k"})
        html = resp.get_data(as_text=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("ไม่สามารถคำนวณได้", html)
        self.assertNotIn("data:image/png", html)

    def test_zero_capacitance_is_rejected(self):
        data = dict(VALID_AMP_FORM, cin="0")
        html = self.client.post("/calculate", data=data).get_data(as_text=True)
        self.assertIn("ค่า CIN ต้องมากกว่า 0 µF", html)

    def test_comma_and_exponent_inputs_are_accepted(self):
        inputs = app_module._parse_amp_form(dict(VALID_AMP_FORM, vcc="1,2", freq="1e3"))
        self.assertAlmostEqual(inputs.vcc, 12.0)
        self.assertAlmostEqual(inputs.freq, 1000.0)

    def test_engine_failure_shows_error_and_no_plots(self):
        with mock.patch("spice_engine.analyze",
                        side_effect=spice_engine.SpiceError("ไม่พบ ngspice ในเครื่องนี้")):
            html = self.client.post("/calculate", data=VALID_AMP_FORM).get_data(as_text=True)
        self.assertIn("ไม่พบ ngspice", html)
        self.assertNotIn("data:image/png", html)

    def test_success_renders_both_labels_and_plots(self):
        with mock.patch("spice_engine.analyze", return_value=FAKE_RUN):
            html = self.client.post("/calculate", data=VALID_AMP_FORM).get_data(as_text=True)
        self.assertIn("ngspice 47", html)
        self.assertIn("Analytical", html)
        self.assertEqual(html.count("data:image/png"), 2)

    def test_large_gap_emits_soft_warning(self):
        far = replace(FAKE_RUN, op=replace(FAKE_RUN.op, ic=2.5e-3))
        with mock.patch("spice_engine.analyze", return_value=far):
            html = self.client.post("/calculate", data=VALID_AMP_FORM).get_data(as_text=True)
        self.assertIn("ต่างจากการคำนวณมือเกิน 15%", html)


class AmpTemplateTests(unittest.TestCase):
    def test_amp_page_has_all_fields_and_no_script(self):
        html = app_module.create_app().test_client().get("/?mode=amp").get_data(as_text=True)
        for name in ("vcc", "r1", "r2", "rc", "re", "rl", "cin", "cout", "vs_mv", "freq"):
            self.assertIn(f'name="{name}"', html)
        self.assertNotIn("<script", html)

    def test_result_page_shows_three_cards_with_badges(self):
        with mock.patch("spice_engine.analyze", return_value=FAKE_RUN):
            html = app_module.create_app().test_client().post(
                "/calculate", data=VALID_AMP_FORM).get_data(as_text=True)
        self.assertIn("DC Operating Point", html)
        self.assertIn("AC Bode", html)
        self.assertIn("Transient", html)
        self.assertIn("ngspice 47", html)
        self.assertIn("dc_bias.py", html)
        self.assertEqual(html.count("<img"), 2)

    def test_result_shows_region_for_both_sources(self):
        with mock.patch("spice_engine.analyze", return_value=FAKE_RUN):
            html = app_module.create_app().test_client().post(
                "/calculate", data=VALID_AMP_FORM).get_data(as_text=True)
        self.assertGreaterEqual(html.count("Forward Active"), 2)


class AmpPolishTests(unittest.TestCase):
    def test_get_amp_groups_fields_and_offers_skip_link(self):
        html = app_module.create_app().test_client().get("/?mode=amp").get_data(as_text=True)
        for label in ("DC Bias", "AC Coupling", "Input Source"):
            self.assertIn(f'class="group-label">{label}', html)
        self.assertIn('class="skip-results"', html)
        self.assertIn("รัน DC + AC + Transient", html)

    def test_result_has_top_summary_and_anchor(self):
        with mock.patch("spice_engine.analyze", return_value=FAKE_RUN):
            html = app_module.create_app().test_client().post(
                "/calculate", data=VALID_AMP_FORM).get_data(as_text=True)
        self.assertIn('class="result-strip" role="status"', html)
        self.assertIn("ผลลัพธ์ล่าสุด", html)
        self.assertIn("7.800 V", html)
        self.assertIn("1.300 mA", html)
        self.assertIn('id="results"', html)

    def test_error_box_is_assertive_and_focused(self):
        html = app_module.create_app().test_client().post(
            "/calculate", data=dict(VALID_AMP_FORM, cin="0")).get_data(as_text=True)
        self.assertIn('aria-live="assertive"', html)
        self.assertIn("autofocus", html)

    def test_compare_table_has_caption_and_column_scope(self):
        with mock.patch("spice_engine.analyze", return_value=FAKE_RUN):
            html = app_module.create_app().test_client().post(
                "/calculate", data=VALID_AMP_FORM).get_data(as_text=True)
        self.assertIn("<caption", html)
        self.assertIn('scope="col"', html)


if __name__ == "__main__":
    unittest.main()

