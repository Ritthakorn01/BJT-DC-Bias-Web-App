import math

from flask import Flask, render_template, request

from dc_bias import ValidationError, calculate, to_float, validate_inputs


def create_app():
    app = Flask(__name__)

    @app.get("/")
    def index():
        return render_template(
            "index.html",
            form={"r_unit": "k"},
            result=None,
            errors=[],
            warnings=[],
        )

    @app.post("/calculate")
    def calculate_bias():
        form = request.form.to_dict()
        if "r_unit" not in form:
            form["r_unit"] = "k"

        try:
            scale = 1000.0 if form["r_unit"] == "k" else 1.0
            vcc = to_float(form.get("vcc"), "VCC")
            vbe = to_float(form.get("vbe"), "VBE")
            beta = to_float(form.get("beta"), "β")
            r1 = to_float(form.get("r1"), "R1") * scale
            r2 = to_float(form.get("r2"), "R2") * scale
            rc = to_float(form.get("rc"), "RC") * scale
            re = to_float(form.get("re"), "RE") * scale

            validate_inputs(vcc, r1, r2, rc, re, beta, vbe)
            result = calculate(vcc, r1, r2, rc, re, beta, vbe)

            measured = (result.vb, result.ve, result.vc, result.vce,
                        result.ic, result.ib, result.ie)
            if not all(math.isfinite(value) for value in measured):
                raise ValidationError(
                    "ค่าที่กรอกทำให้ผลลัพธ์ไม่จำกัด กรุณาตรวจสอบค่าอุปกรณ์"
                )
        except ValidationError as exc:
            return render_template(
                "index.html",
                form=form,
                result=None,
                errors=[exc.message],
                warnings=[],
            )

        return render_template(
            "index.html",
            form=form,
            result=result,
            errors=[],
            warnings=list(result.warnings),
        )

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
