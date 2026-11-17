import unittest

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


if __name__ == "__main__":
    unittest.main()
