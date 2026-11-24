"""DC bias calculations for NPN common-emitter bias circuits.

Three modes: Voltage Divider, Fixed Bias and Emitter Bias (single supply).
Pure engineering module: no HTML, no HTTP, no Flask imports.
All values inside BiasResult are in SI units (volts, amps, ohms);
BiasResult.to_dict() converts to the display units Flask uses.
"""

from dataclasses import dataclass
import math

VCE_SAT = 0.2
"""Collector-emitter saturation threshold used for the region warning [V]."""


class ValidationError(Exception):
    """Raised when an input value cannot be used by the DC bias model."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def to_float(text: str, name: str) -> float:
    """Convert form text to float.

    Accepts surrounding whitespace and comma thousands separators.
    """
    cleaned = (text or "").strip().replace(",", "")
    if not cleaned:
        raise ValidationError(f"กรุณากรอกค่า {name} เป็นตัวเลข")
    try:
        value = float(cleaned)
    except ValueError:
        raise ValidationError(f"กรุณากรอกค่า {name} เป็นตัวเลข") from None
    if not math.isfinite(value):
        raise ValidationError(f"กรุณากรอกค่า {name} เป็นจำนวนจำกัด")
    return value


def validate_common(vcc: float, beta: float, vbe: float) -> None:
    """ตรวจค่าที่ทุกโหมดใช้ร่วมกัน (VCC, β, VBE)."""
    for name, value in (("VCC", vcc), ("β", beta), ("VBE", vbe)):
        if not math.isfinite(value):
            raise ValidationError(f"ค่า {name} ต้องเป็นจำนวนจำกัด")
    if vcc <= 0:
        raise ValidationError("VCC ต้องมากกว่า 0 V")
    if beta <= 0:
        raise ValidationError("β ต้องมากกว่า 0")
    if vbe <= 0:
        raise ValidationError("VBE ต้องมากกว่า 0 V")


def validate_resistors(**resistors: float) -> None:
    """ตรวจเฉพาะตัวต้านทานที่โหมดนั้นใช้ เช่น Fixed Bias ส่งมาแค่ RB."""
    for name, value in resistors.items():
        if not math.isfinite(value) or value <= 0:
            raise ValidationError(f"ค่า {name} ต้องมากกว่า 0 Ω")


def validate_inputs(
    vcc: float,
    r1: float,
    r2: float,
    rc: float,
    re: float,
    beta: float,
    vbe: float,
) -> None:
    """ตรวจอินพุตของ Voltage-Divider Bias (โหมดเดิมของ Lab 2)."""
    validate_common(vcc, beta, vbe)
    validate_resistors(R1=r1, R2=r2, RC=rc, RE=re)


def classify_region(vce: float) -> str:
    """คืนชื่อเขตทำงานจาก VCE ตามเกณฑ์ VCE ≤ VCE_SAT ของใบงาน Lab 03."""
    return "Saturation" if vce <= VCE_SAT else "Forward Active"


@dataclass(frozen=True)
class BiasResult:
    ib: float
    ic: float
    ie: float
    ve: float
    vb: float
    vc: float
    vce: float
    region: str
    warnings: tuple[str, ...]
    vth: float | None = None
    rth: float | None = None

    def to_dict(self) -> dict:
        """คืนผลสำหรับ Flask ด้วยคีย์และหน่วยที่ตกลงร่วมกันทั้งสามโหมด."""
        return {
            "vb_v": self.vb,
            "ve_v": self.ve,
            "vc_v": self.vc,
            "vce_v": self.vce,
            "ic_ma": self.ic * 1000.0,
            "ib_ua": self.ib * 1_000_000.0,
            "ie_ma": self.ie * 1000.0,
            "region": self.region,
            "warnings": list(self.warnings),
        }


def _cutoff(vb: float, vc: float, vce: float, *, vth: float | None = None,
            rth: float | None = None) -> BiasResult:
    return BiasResult(
        ib=0.0,
        ic=0.0,
        ie=0.0,
        ve=0.0,
        vb=vb,
        vc=vc,
        vce=vce,
        region="Cutoff",
        warnings=(
            "วงจรอยู่ในช่วง Cutoff — IB ≤ 0 และแบบจำลอง Forward-Active ใช้ไม่ได้",
        ),
        vth=vth,
        rth=rth,
    )


def _finish(ib: float, ic: float, ie: float, ve: float, vb: float, vc: float,
            vce: float, *, vth: float | None = None,
            rth: float | None = None) -> BiasResult:
    warnings = []
    region = classify_region(vce)
    if region == "Saturation":
        warnings.append(
            "VCE ต่ำกว่าหรือเท่ากับ VCE(sat) ≈ 0.2 V — วงจรอยู่ใน Saturation "
            "และแบบจำลอง Forward-Active ใช้ไม่ได้"
        )
    if vc < 0:
        warnings.append(
            "VC ติดลบ แสดงว่า RC ใหญ่เกินกว่าที่วงจรจะอยู่ใน Active Region"
        )
    return BiasResult(
        ib=ib,
        ic=ic,
        ie=ie,
        ve=ve,
        vb=vb,
        vc=vc,
        vce=vce,
        region=region,
        warnings=tuple(warnings),
        vth=vth,
        rth=rth,
    )


def calculate_fixed(vcc: float, rb: float, rc: float, beta: float,
                    vbe: float) -> BiasResult:
    """Fixed Bias: RB จาก VCC ไป Base และ Emitter ต่อกราวด์ (VE = 0)."""
    validate_common(vcc, beta, vbe)
    validate_resistors(RB=rb, RC=rc)

    if vbe >= vcc:
        return _cutoff(vb=vcc, vc=vcc, vce=vcc)

    ib = (vcc - vbe) / rb
    ic = beta * ib
    ie = (beta + 1) * ib
    ve = 0.0
    vb = vbe
    vc = vcc - ic * rc
    vce = vc
    return _finish(ib, ic, ie, ve, vb, vc, vce)


def calculate_emitter(vcc: float, rb: float, rc: float, re: float, beta: float,
                      vbe: float) -> BiasResult:
    """Emitter Bias แหล่งจ่ายเดียว: RB จาก VCC ไป Base และ RE จาก Emitter ลงกราวด์."""
    validate_common(vcc, beta, vbe)
    validate_resistors(RB=rb, RC=rc, RE=re)

    if vbe >= vcc:
        return _cutoff(vb=vcc, vc=vcc, vce=vcc)

    # หารเศษและส่วนด้วย β เพื่อกัน (β + 1)·RE ล้นเป็น infinity เมื่อ β สูงมาก
    inv_beta = 1.0 / beta
    ic = (vcc - vbe) / (rb * inv_beta + re * (1.0 + inv_beta))
    ib = ic / beta
    ie = ic * (1.0 + inv_beta)
    ve = ie * re
    vb = ve + vbe
    vc = vcc - ic * rc
    vce = vc - ve
    return _finish(ib, ic, ie, ve, vb, vc, vce)


def calculate_divider(
    vcc: float,
    r1: float,
    r2: float,
    rc: float,
    re: float,
    beta: float,
    vbe: float,
) -> BiasResult:
    validate_common(vcc, beta, vbe)
    validate_resistors(R1=r1, R2=r2, RC=rc, RE=re)

    vth = vcc * r2 / (r1 + r2)
    rth = r1 * r2 / (r1 + r2)

    if vth <= vbe:
        return _cutoff(vb=vth, vc=vcc, vce=vcc, vth=vth, rth=rth)

    # หารเศษและส่วนด้วย β เพื่อกัน (β + 1)·RE ล้นเป็น infinity เมื่อ β สูงมาก
    # IC = (VTH − VBE) / [RTH/β + RE·(1 + 1/β)] ซึ่งเท่ากับ β(VTH − VBE)/(RTH + (β+1)RE)
    inv_beta = 1.0 / beta
    ic = (vth - vbe) / (rth * inv_beta + re * (1.0 + inv_beta))
    ib = ic / beta
    ie = ic * (1.0 + inv_beta)
    ve = ie * re
    vb = ve + vbe
    vc = vcc - ic * rc
    vce = vc - ve

    return _finish(ib, ic, ie, ve, vb, vc, vce, vth=vth, rth=rth)


# ชื่อเดิมของ Lab 02 — คงไว้ให้โค้ด/เทสต์เดิมเรียกได้
calculate = calculate_divider
