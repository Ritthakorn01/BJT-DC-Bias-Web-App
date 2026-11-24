"""SPICE simulation engine for the CE amplifier mode.

All internal values use SI units (V, A, ohm, F, Hz, s). Unit conversion for
display happens in :func:`to_display` only.
"""

import math
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from dc_bias import classify_region

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


@dataclass(frozen=True)
class OpPoint:
    vb: float
    ve: float
    vc: float
    vce: float
    ic: float
    ib: float
    region: str


@dataclass(frozen=True)
class AcSweep:
    freq: tuple[float, ...]
    gain_db: tuple[float, ...]
    phase_deg: tuple[float, ...]
    midband_gain_db: float
    gain_at_1khz_db: float


@dataclass(frozen=True)
class Transient:
    time: tuple[float, ...]
    vin: tuple[float, ...]
    vout: tuple[float, ...]
    vin_pp: float
    vout_pp: float
    inverted: bool


def _table_rows(table: str) -> tuple[list[str], list[list[float]]]:
    lines = [line for line in table.splitlines() if line.strip()]
    if len(lines) < 2:
        raise SpiceError("อ่านผลลัพธ์จาก ngspice ไม่ได้")
    header = lines[0].split()
    rows: list[list[float]] = []
    for line in lines[1:]:
        parts = line.split()
        if len(parts) != len(header):
            raise SpiceError("อ่านผลลัพธ์จาก ngspice ไม่ได้")
        try:
            rows.append([float(x) for x in parts])
        except ValueError as exc:
            raise SpiceError("อ่านผลลัพธ์จาก ngspice ไม่ได้") from exc
    return header, rows


def parse_op(table: str) -> OpPoint:
    header, rows = _table_rows(table)
    # wrdata writes a leading scale column with no matching name.
    names = header[1:]
    values = dict(zip(names, rows[0][1:]))
    try:
        vb, ve, vc = values["v(vb)"], values["v(ve)"], values["v(vc)"]
        ic, ib = values["@q1[ic]"], values["@q1[ib]"]
    except KeyError as exc:
        raise SpiceError("อ่านผลลัพธ์จาก ngspice ไม่ได้") from exc
    vce = vc - ve
    return OpPoint(vb, ve, vc, vce, ic, ib, classify_region(vce))


def parse_ac(table: str) -> AcSweep:
    header, rows = _table_rows(table)
    # Complex vectors appear as two adjacent columns with the same name.
    def pair(name: str) -> tuple[int, int]:
        idx = [i for i, h in enumerate(header) if h == name]
        if len(idx) != 2:
            raise SpiceError("อ่านผลลัพธ์จาก ngspice ไม่ได้")
        return idx[0], idx[1]

    try:
        out_r, out_i = pair("v(out)")
        in_r, in_i = pair("v(in)")
    except SpiceError:
        raise
    freqs, gains, phases = [], [], []
    previous = None
    for row in rows:
        f = row[0]
        out = complex(row[out_r], row[out_i])
        vin = complex(row[in_r], row[in_i])
        if abs(vin) == 0.0:
            raise SpiceError("อ่านผลลัพธ์จาก ngspice ไม่ได้")
        gains.append(20.0 * math.log10(abs(out) / abs(vin)))
        raw = math.degrees(math.atan2(out.imag, out.real)
                           - math.atan2(vin.imag, vin.real))
        if previous is not None:
            while raw - previous > 180.0:
                raw -= 360.0
            while raw - previous < -180.0:
                raw += 360.0
        previous = raw
        freqs.append(f)
        phases.append(raw)
    if not freqs:
        raise SpiceError("อ่านผลลัพธ์จาก ngspice ไม่ได้")
    midband = [g for f, g in zip(freqs, gains) if 100.0 <= f <= 10000.0] or gains
    nearest = min(range(len(freqs)), key=lambda i: abs(freqs[i] - 1000.0))
    return AcSweep(tuple(freqs), tuple(gains), tuple(phases),
                   max(midband), gains[nearest])


def parse_tran(table: str, freq: float = 1.0) -> Transient:
    header, rows = _table_rows(table)
    if header != ["time", "v(in)", "v(out)"] or freq <= 0:
        raise SpiceError("อ่านผลลัพธ์จาก ngspice ไม่ได้")
    t = tuple(row[0] for row in rows)
    vin = tuple(row[1] for row in rows)
    vout = tuple(row[2] for row in rows)
    start = t[-1] - 1.0 / freq
    segment = [i for i, value in enumerate(t) if value >= start] or list(range(len(t)))
    in_seg = [vin[i] for i in segment]
    out_seg = [vout[i] for i in segment]
    vin_pp = max(in_seg) - min(in_seg)
    vout_pp = max(out_seg) - min(out_seg)
    in_mean = sum(in_seg) / len(in_seg)
    out_mean = sum(out_seg) / len(out_seg)
    cov = sum((a - in_mean) * (b - out_mean) for a, b in zip(in_seg, out_seg))
    inverted = cov < 0.0
    return Transient(t, vin, vout, vin_pp, vout_pp, inverted)


@dataclass(frozen=True)
class SpiceRun:
    op: OpPoint
    ac: AcSweep
    tran: Transient
    ac_png: bytes
    tran_png: bytes
    engine_version: str


def analyze(inputs: AmpInputs) -> SpiceRun:
    op_table, version = run_netlist(build_op_netlist(inputs), "op")
    ac_table, _ = run_netlist(build_ac_netlist(inputs), "ac")
    tran_table, _ = run_netlist(build_tran_netlist(inputs), "tran")
    return SpiceRun(
        op=parse_op(op_table),
        ac=parse_ac(ac_table),
        tran=parse_tran(tran_table, inputs.freq),
        ac_png=b"",
        tran_png=b"",
        engine_version=version,
    )
