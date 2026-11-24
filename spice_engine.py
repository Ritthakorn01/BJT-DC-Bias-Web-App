"""SPICE simulation engine for the CE amplifier mode.

All internal values use SI units (V, A, ohm, F, Hz, s). Unit conversion for
display happens in :func:`to_display` only.
"""

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

MODEL_PATH = Path(__file__).resolve().parent / "spice" / "models" / "2n3904.lib"


class SpiceError(Exception):
    """A user-facing failure from the SPICE engine."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


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


def run_netlist(netlist: str, tag: str, timeout_s: float = 20.0) -> tuple[str, str]:
    """Run one ngspice deck in a fresh temp dir; return (table text, version)."""
    binary = os.environ.get("NGSPICE_BIN", "ngspice")
    model = Path(os.environ.get("SPICE_MODEL_PATH", str(MODEL_PATH)))
    with tempfile.TemporaryDirectory(prefix=f"spice-{tag}-") as tmp:
        work = Path(tmp)
        (work / "deck.cir").write_text(netlist, encoding="ascii")
        shutil.copy(model, work / "model.lib")
        try:
            proc = subprocess.run(
                [binary, "-b", "deck.cir", "-o", "run.log"],
                cwd=work, capture_output=True, text=True, timeout=timeout_s,
            )
        except FileNotFoundError as exc:
            raise SpiceError("ไม่พบ ngspice ในเครื่องนี้ กรุณาติดตั้งและเพิ่มเข้า PATH") from exc
        except subprocess.TimeoutExpired as exc:
            raise SpiceError("ngspice ใช้เวลานานเกินกำหนด") from exc

        if proc.returncode != 0:
            tail = (proc.stderr or "").strip()[-300:]
            detail = f": {tail}" if tail else ""
            raise SpiceError(f"ngspice ทำงานไม่สำเร็จ ({tag}){detail}")

        result = work / "out.txt"
        if not result.is_file():
            raise SpiceError(f"ngspice ไม่คืนผลลัพธ์ ({tag})")
        table = result.read_text(encoding="utf-8", errors="replace")
        if not table.strip():
            raise SpiceError(f"ngspice ไม่คืนผลลัพธ์ ({tag})")

    match = re.search(r"ngspice-(\d+)", proc.stdout or "")
    return table, match.group(1) if match else "unknown"
