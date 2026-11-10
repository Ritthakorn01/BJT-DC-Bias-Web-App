"""DC bias calculations for an NPN common-emitter voltage-divider bias circuit.

Pure engineering module: no HTML, no HTTP, no Flask imports.
All values inside BiasResult are in SI units (volts, amps, ohms).
"""

from dataclasses import dataclass


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
