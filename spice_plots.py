"""Render SPICE results as PNG bytes using matplotlib's Agg backend."""

from io import BytesIO

import matplotlib

matplotlib.use("Agg")

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from spice_engine import AcSweep, Transient


def _save(fig: Figure) -> bytes:
    FigureCanvasAgg(fig)
    fig.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=110)
    return buf.getvalue()


def ac_png(ac: AcSweep) -> bytes:
    fig = Figure(figsize=(7.2, 5.2), dpi=110)
    gain_ax, phase_ax = fig.subplots(2, 1, sharex=True)
    gain_ax.semilogx(ac.freq, ac.gain_db, color="#1f77b4", linewidth=1.8)
    gain_ax.set_ylabel("Gain (dB)")
    gain_ax.set_title("AC frequency response (ngspice)")
    gain_ax.grid(True, which="both", alpha=0.3)

    phase_ax.semilogx(ac.freq, ac.phase_deg, color="#d62728", linewidth=1.8)
    phase_ax.set_xlabel("Frequency (Hz)")
    phase_ax.set_ylabel("Phase (deg)")
    phase_ax.grid(True, which="both", alpha=0.3)
    return _save(fig)


def tran_png(tran: Transient) -> bytes:
    fig = Figure(figsize=(7.2, 4.2), dpi=110)
    ax = fig.subplots()
    t_ms = [value * 1e3 for value in tran.time]
    ax.plot(t_ms, [v * 1e3 for v in tran.vin], label="Vin (mV)", linewidth=1.6)
    ax.plot(t_ms, [v * 1e3 for v in tran.vout], label="Vout (mV)", linewidth=1.6)
    ax.set_xlabel("Time (ms)")
    ax.set_ylabel("Voltage (mV)")
    ax.set_title("Transient waveform (ngspice)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right")
    return _save(fig)
