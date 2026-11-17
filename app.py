import math

from flask import Flask, render_template, request

from dc_bias import (
    ValidationError,
    calculate_divider,
    calculate_emitter,
    calculate_fixed,
    to_float,
    validate_common,
    validate_inputs,
    validate_resistors,
)

MODE_LABELS = {
    "divider": "Voltage Divider Bias",
    "fixed": "Fixed Bias",
    "emitter": "Emitter Bias",
}

DEFAULT_FORMS = {
    "divider": {"vcc": "12", "vbe": "0.70", "rc": "2.2", "r1": "100",
                "r2": "22", "re": "1", "beta": "100", "r_unit": "k"},
    "fixed": {"vcc": "12", "vbe": "0.70", "rc": "2.2", "rb": "1000",
              "beta": "100", "r_unit": "k"},
    "emitter": {"vcc": "12", "vbe": "0.70", "rc": "2.2", "rb": "1000",
                "re": "1", "beta": "100", "r_unit": "k"},
}


def create_app():
    app = Flask(__name__)

    def render_page(mode, form, result=None, errors=(), warnings=()):
        return render_template(
            "index.html",
            mode=mode,
            mode_labels=MODE_LABELS,
            form=form,
            result=result,
            errors=errors,
            warnings=warnings,
        )

    @app.get("/")
    def index():
        mode = request.args.get("mode", "divider")
        errors = [] if mode in MODE_LABELS else ["โหมดวงจรไม่ถูกต้อง"]
        return render_page(mode, dict(DEFAULT_FORMS.get(mode, {})), errors=errors)

    @app.post("/calculate")
    def calculate_bias():
        form = request.form.to_dict()
        form.setdefault("r_unit", "k")
        mode = form.get("mode", "divider")

        try:
            if mode not in MODE_LABELS:
                raise ValidationError("โหมดวงจรไม่ถูกต้อง")
            unit = form["r_unit"]
            if unit not in ("k", ""):
                raise ValidationError("หน่วยตัวต้านทานต้องเป็น kΩ หรือ Ω")
            scale = 1000.0 if unit == "k" else 1.0

            vcc = to_float(form.get("vcc"), "VCC")
            vbe = to_float(form.get("vbe"), "VBE")
            beta = to_float(form.get("beta"), "β")
            rc = to_float(form.get("rc"), "RC") * scale

            if mode == "divider":
                r1 = to_float(form.get("r1"), "R1") * scale
                r2 = to_float(form.get("r2"), "R2") * scale
                re = to_float(form.get("re"), "RE") * scale
                validate_inputs(vcc, r1, r2, rc, re, beta, vbe)
                bias = calculate_divider(vcc, r1, r2, rc, re, beta, vbe)
            elif mode == "fixed":
                rb = to_float(form.get("rb"), "RB") * scale
                validate_common(vcc, beta, vbe)
                validate_resistors(RB=rb, RC=rc)
                bias = calculate_fixed(vcc, rb, rc, beta, vbe)
            else:  # emitter
                rb = to_float(form.get("rb"), "RB") * scale
                re = to_float(form.get("re"), "RE") * scale
                validate_common(vcc, beta, vbe)
                validate_resistors(RB=rb, RC=rc, RE=re)
                bias = calculate_emitter(vcc, rb, rc, re, beta, vbe)

            result = bias.to_dict()
            measured = (
                result["vb_v"], result["ve_v"], result["vc_v"],
                result["vce_v"], result["ic_ma"], result["ib_ua"],
                result["ie_ma"],
            )
            if not all(math.isfinite(value) for value in measured):
                raise ValidationError(
                    "ค่าที่กรอกทำให้ผลลัพธ์ไม่จำกัด กรุณาตรวจสอบค่าอุปกรณ์"
                )
        except ValidationError as exc:
            return render_page(mode, form, errors=[exc.message])

        return render_page(mode, form, result=result,
                           warnings=result["warnings"])

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
