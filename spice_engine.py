"""SPICE simulation engine for the CE amplifier mode.

All internal values use SI units (V, A, ohm, F, Hz, s). Unit conversion for
display happens in :func:`to_display` only.
"""

from dataclasses import dataclass
from pathlib import Path

MODEL_PATH = Path(__file__).resolve().parent / "spice" / "models" / "2n3904.lib"


@dataclass(frozen=True)
class AmpInputs:
    vcc: float
    r1: float
    r2: float
    rc: float
    re: float
    rl: float
    cin: float
    cout: float
    vs_peak: float
    freq: float
    beta_ref: float
    vbe_ref: float


def _fmt(value: float) -> str:
    return f"{value:.12g}"


def _deck(inputs: AmpInputs, analysis: str, vectors: str) -> str:
    return "\n".join([
        "* CE amplifier - " + analysis,
        ".include model.lib",
        f"VCC vcc 0 DC {_fmt(inputs.vcc)}",
        f"R1 vcc vb {_fmt(inputs.r1)}",
        f"R2 vb 0 {_fmt(inputs.r2)}",
        f"RC vcc vc {_fmt(inputs.rc)}",
        f"RE ve 0 {_fmt(inputs.re)}",
        "Q1 vc vb ve Q2N3904",
        f"VS in 0 DC 0 AC 1 SIN(0 {_fmt(inputs.vs_peak)} {_fmt(inputs.freq)})",
        f"CIN in vb {_fmt(inputs.cin)}",
        f"COUT vc out {_fmt(inputs.cout)}",
        f"RL out 0 {_fmt(inputs.rl)}",
        ".control",
        "set wr_singlescale",
        "set wr_vecnames",
        analysis,
        f"wrdata out.txt {vectors}",
        ".endc",
        ".end",
        "",
    ])


def build_op_netlist(inputs: AmpInputs) -> str:
    return _deck(inputs, "op", "v(vb) v(ve) v(vc) v(vcc) @q1[ic] @q1[ib]")


def build_ac_netlist(inputs: AmpInputs) -> str:
    return _deck(inputs, "ac dec 20 10 1meg", "v(out) v(in)")


def build_tran_netlist(inputs: AmpInputs) -> str:
    tstop = 5.0 / inputs.freq
    tstep = tstop / 2000.0
    return _deck(inputs, f"tran {_fmt(tstep)} {_fmt(tstop)}", "v(in) v(out)")
