import math

from flask import Flask, render_template, request

import spice_engine
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
    "amp": "CE Amplifier (SPICE)",
}

DEFAULT_FORMS = {
    "divider": {"vcc": "12", "vbe": "0.70", "rc": "2.2", "r1": "100",
                "r2": "22", "re": "1", "beta": "100", "r_unit": "k"},
    "fixed": {"vcc": "12", "vbe": "0.70", "rc": "2.2", "rb": "1000",
              "beta": "100", "r_unit": "k"},
    "emitter": {"vcc": "12", "vbe": "0.70", "rc": "2.2", "rb": "1000",
                "re": "1", "beta": "100", "r_unit": "k"},
    "amp": {"vcc": "12", "vbe": "0.70", "rc": "2.2", "r1": "100",
            "r2": "22", "re": "1", "rl": "10", "cin": "10", "cout": "10",
            "vs_mv": "10", "freq": "1000", "beta": "100", "r_unit": "k"},
}


def _parse_amp_form(form: dict) -> spice_engine.AmpInputs:
    """Validate the amplifier form and convert it to SI values."""
    unit = form.get("r_unit", "k")
    if unit not in ("k", ""):
        raise ValidationError("หน่วยตัวต้านทานต้องเป็น kΩ หรือ Ω")
    scale = 1000.0 if unit == "k" else 1.0

    vcc = to_float(form.get("vcc"), "VCC")
    vbe = to_float(form.get("vbe"), "VBE")
    beta = to_float(form.get("beta"), "β")
    rc = to_float(form.get("rc"), "RC") * scale
    r1 = to_float(form.get("r1"), "R1") * scale
    r2 = to_float(form.get("r2"), "R2") * scale
    re = to_float(form.get("re"), "RE") * scale
    rl = to_float(form.get("rl"), "RL") * scale
    cin = to_float(form.get("cin"), "CIN") * 1e-6
    cout = to_float(form.get("cout"), "COUT") * 1e-6
    vs_peak = to_float(form.get("vs_mv"), "Vs") * 1e-3
    freq = to_float(form.get("freq"), "f")

    validate_common(vcc, beta, vbe)
    validate_resistors(R1=r1, R2=r2, RC=rc, RE=re, RL=rl)
    for name, value in (("CIN", cin), ("COUT", cout)):
        if value <= 0:
            raise ValidationError(f"ค่า {name} ต้องมากกว่า 0 µF")
    if freq <= 0:
        raise ValidationError("ค่า f ต้องมากกว่า 0 Hz")
    if vs_peak <= 0:
        raise ValidationError("ค่า Vs ต้องมากกว่า 0 V")

    return spice_engine.AmpInputs(
        vcc=vcc, r1=r1, r2=r2, rc=rc, re=re, rl=rl, cin=cin, cout=cout,
        vs_peak=vs_peak, freq=freq, beta_ref=beta, vbe_ref=vbe,
    )


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

            if mode == "amp":
                inputs = _parse_amp_form(form)
                try:
                    run = spice_engine.analyze(inputs)
                except spice_engine.SpiceError as exc:
                    return render_page(mode, form, errors=[exc.message])
                result = spice_engine.to_display(run)
                ref = calculate_divider(inputs.vcc, inputs.r1, inputs.r2,
                                        inputs.rc, inputs.re,
                                        inputs.beta_ref, inputs.vbe_ref).to_dict()
                keys = (("vb_v", "vb_v"), ("ve_v", "ve_v"), ("vc_v", "vc_v"),
                        ("vce_v", "vce_v"), ("ic_ma", "ic_ma"))
                result["analytical"] = {key: ref[ref_key] for key, ref_key in keys}
                result["analytical"]["region"] = ref["region"]
                result["deltas"] = {}
                for key, ref_key in keys:
                    baseline = ref[ref_key]
                    result["deltas"][key] = (
                        (result["op"][key] - baseline) / abs(baseline) * 100.0
                        if baseline else None
                    )
                warnings = list(ref["warnings"])
                if any(d is not None and abs(d) > 15.0
                       for d in result["deltas"].values()):
                    warnings.append(
                        "ต่างจากการคำนวณมือเกิน 15% (model BF ≠ β ในฟอร์ม)"
                    )
                return render_page(mode, form, result=result, warnings=warnings)

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
