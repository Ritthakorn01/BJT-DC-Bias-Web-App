"""DC bias calculations for an NPN common-emitter voltage-divider bias circuit.

Pure engineering module: no HTML, no HTTP, no Flask imports.
All values inside BiasResult are in SI units (volts, amps, ohms).
"""

from dataclasses import dataclass


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
        return float(cleaned)
    except ValueError:
        raise ValidationError(f"กรุณากรอกค่า {name} เป็นตัวเลข") from None


def validate_inputs(
    vcc: float,
    r1: float,
    r2: float,
    rc: float,
    re: float,
    beta: float,
    vbe: float,
) -> None:
    if vcc <= 0:
        raise ValidationError("VCC ต้องมากกว่า 0 V")
    for name, value in (("R1", r1), ("R2", r2), ("RC", rc), ("RE", re)):
        if value <= 0:
            raise ValidationError(f"ค่า {name} ต้องมากกว่า 0 Ω")
    if beta <= 0:
        raise ValidationError("β ต้องมากกว่า 0")
    if vbe <= 0 or vbe >= vcc:
        raise ValidationError("VBE ต้องอยู่ระหว่าง 0 กับ VCC")


@dataclass(frozen=True)
class BiasResult:
    vth: float
    rth: float
    ib: float
    ic: float
    ie: float
    ve: float
    vb: float
    vc: float
    vce: float
    region: str
    warnings: tuple[str, ...]


def calculate(
    vcc: float,
    r1: float,
    r2: float,
    rc: float,
    re: float,
    beta: float,
    vbe: float,
) -> BiasResult:
    vth = vcc * r2 / (r1 + r2)
    rth = r1 * r2 / (r1 + r2)
    ib = (vth - vbe) / (rth + (beta + 1) * re)
    ic = beta * ib
    ie = (beta + 1) * ib
    ve = ie * re
    vb = ve + vbe
    vc = vcc - ic * rc
    vce = vc - ve

    return BiasResult(
        vth=vth,
        rth=rth,
        ib=ib,
        ic=ic,
        ie=ie,
        ve=ve,
        vb=vb,
        vc=vc,
        vce=vce,
        region="Forward Active",
        warnings=(),
    )
