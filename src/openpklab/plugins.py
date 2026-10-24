"""Small deterministic plugins; third-party plugins use Python entry points."""
from __future__ import annotations
import io
import platform
import threading
from importlib.metadata import entry_points, version
from typing import Protocol

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import linregress

from .datasets import quality

PLOT_LOCK = threading.Lock()
TIME_UNITS = {"h", "min", "s"}
CONCENTRATION_UNITS = {"mg/L", "ug/mL", "ng/mL", "ug/L", "mg/mL", "nmol/L", "umol/L"}


class Plugin(Protocol):
    name: str
    version: str
    def run(self, frame: pd.DataFrame, options: dict) -> dict: ...


class DataQuality:
    name = "data_quality"
    version = "1.0"
    def run(self, frame, options):
        return quality(frame)


def profile(frame, options):
    tcol, ccol = options.get("time_column", "time"), options.get("concentration_column", "concentration")
    if tcol not in frame or ccol not in frame:
        raise ValueError("Specify existing time_column and concentration_column")
    if options.get("time_unit") not in TIME_UNITS or options.get("concentration_unit") not in CONCENTRATION_UNITS:
        raise ValueError(f"Explicit units required: time {sorted(TIME_UNITS)}, concentration {sorted(CONCENTRATION_UNITS)}")
    if any(str(c).lower().endswith(("unit", "units")) and frame[c].dropna().astype(str).nunique() > 1 for c in frame):
        raise ValueError("Mixed units in dataset; provide a consistent profile without silently converting originals")
    for col, unit in ((tcol, options["time_unit"]), (ccol, options["concentration_unit"])):
        for candidate in (f"{col}_unit", f"{col}_units"):
            if candidate in frame and (frame[candidate].isna().any() or set(frame[candidate].astype(str)) != {unit}):
                raise ValueError(f"Unit metadata conflicts with {candidate}")
    try:
        times = np.asarray(pd.to_numeric(frame[tcol], errors="raise"), dtype=float)
        conc = np.asarray(pd.to_numeric(frame[ccol], errors="raise"), dtype=float)
    except (ValueError, TypeError) as exc:
        raise ValueError("PK profiles require numeric time and concentration") from exc
    if len(times) < 2 or not np.isfinite(times).all() or not np.isfinite(conc).all():
        raise ValueError("At least two finite complete observations are required; missing values are not dropped")
    if np.any(times < 0) or np.any(conc < 0) or np.any(np.diff(times) <= 0):
        raise ValueError("Times must be nonnegative, unique and strictly increasing; concentrations must be nonnegative")
    return times, conc


class NCA:
    name = "nca"
    version = "1.0"
    def run(self, frame, options):
        # A profile is one individual, group, occasion and dose interval.
        for col in ("subject", "group", "occasion", "dose_interval"):
            if col in frame and frame[col].nunique(dropna=False) > 1:
                raise ValueError(f"NCA requires one profile; split data by {col}")
        t, c = profile(frame, options)
        peak = int(np.argmax(c))
        result = {
            "status": "partial", "cmax": float(c[peak]), "tmax": float(t[peak]),
            "auclast": float(np.trapezoid(c, t)), "lambda_z": None, "half_life": None,
            "units": {"cmax": options["concentration_unit"], "tmax": options["time_unit"], "auclast": f'{options["concentration_unit"]}*{options["time_unit"]}', "lambda_z": f'1/{options["time_unit"]}', "half_life": options["time_unit"]},
            "methods": {"auc": "linear trapezoidal, first to last observed time; no extrapolation to zero or infinity", "tmax": "first observed maximum", "terminal": "OLS log concentration on last 3 post-peak positive points; R² >= 0.90 and span >= one estimated half-life"},
            "assumptions": ["Single profile; no BLQ substitution", "Times and concentrations supplied in consistent explicit units", "Terminal screening is exploratory and requires human review"],
            "terminal_points": [], "terminal_r_squared": None, "uncertainty": "Terminal elimination is not estimable from this profile",
        }
        candidates = np.flatnonzero((np.arange(len(t)) > peak) & (c > 0))
        # Zeros in the tail are not silently omitted from regression.
        if len(candidates) >= 3 and np.all(c[-3:] > 0) and np.all(candidates[-3:] == np.arange(len(t) - 3, len(t))):
            idx = candidates[-3:]
            fit = linregress(t[idx], np.log(c[idx]))
            r2 = float(fit.rvalue ** 2)
            if not np.isfinite(r2):
                return result
            result["terminal_r_squared"] = r2
            result["terminal_points"] = idx.tolist()
            if fit.slope < 0 and r2 >= 0.9:
                half_life = float(np.log(2) / -fit.slope)
                if t[idx[-1]] - t[idx[0]] >= half_life:
                    result.update(status="estimated", lambda_z=float(-fit.slope), half_life=half_life, uncertainty="Exploratory last-three-point terminal estimate; no automatic optimal-window selection or clinical validation")
        return result


class PKVisualization:
    name = "pk_visualization"
    version = "1.0"
    def run(self, frame, options):
        group_col = options.get("group_column")
        individual_col = options.get("individual_column")
        columns = [c for c in (group_col, individual_col) if c]
        if any(c not in frame for c in columns):
            raise ValueError("Unknown grouping column")
        if columns and frame[columns].isna().any().any():
            raise ValueError("Grouping columns must be complete")
        groups = list(frame.groupby(columns, sort=False)) if columns else [("profile", frame)]
        if len(groups) > 100:
            raise ValueError("At most 100 plotted profiles")
        scale = options.get("scale", "linear")
        if scale not in {"linear", "log"}:
            raise ValueError("scale must be linear or log")
        with PLOT_LOCK:
            fig, ax = plt.subplots(figsize=(7, 4))
            try:
                for label, group in groups:
                    t, c = profile(group, options)
                    if scale == "log" and np.any(c <= 0):
                        raise ValueError("Log plots require positive concentrations; no values are dropped")
                    ax.plot(t, c, "o-", label=str(label))
                ax.set(xlabel=f'Time ({options["time_unit"]})', ylabel=f'Concentration ({options["concentration_unit"]})', yscale=scale)
                if columns:
                    ax.legend()
                fig.tight_layout()
                out = io.BytesIO()
                fig.savefig(out, format="png", dpi=140, metadata={"Software": "OpenPKLab"})
                return {"image_bytes": out.getvalue(), "profiles": len(groups), "scale": scale, "units": {"time": options["time_unit"], "concentration": options["concentration_unit"]}, "method": "observed points joined by straight lines; no fitted model"}
            finally:
                plt.close(fig)


class Registry:
    def __init__(self, load_external: bool = True):
        self.plugins = {}
        for plugin in (DataQuality(), PKVisualization(), NCA()):
            self.register(plugin)
        if load_external:
            for ep in entry_points(group="openpklab.plugins"):
                self.register(ep.load()())

    def register(self, plugin: Plugin):
        if not getattr(plugin, "name", "") or not getattr(plugin, "version", "") or not callable(getattr(plugin, "run", None)):
            raise ValueError("Plugin must define name, version and run(frame, options)")
        if plugin.name in self.plugins:
            raise ValueError(f"Duplicate plugin: {plugin.name}")
        self.plugins[plugin.name] = plugin

    def run(self, name: str, frame: pd.DataFrame, options: dict):
        if name not in self.plugins:
            raise ValueError(f"Unknown plugin; available: {sorted(self.plugins)}")
        p = self.plugins[name]
        return {"plugin": name, "plugin_version": p.version, "runtime": {"python": platform.python_version(), **{k: version(k) for k in ("numpy", "scipy", "pandas", "matplotlib", "openpklab")}}, "options": options, "findings": p.run(frame.copy(deep=True), options)}
