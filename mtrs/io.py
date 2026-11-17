"""CSV input helpers for the toolkit.

Layout conventions
------------------
``load_matrix``
    First row is a header naming the indicators; the first column names
    the scenarios. Every remaining cell is a number.

        scenario,ind_a,ind_b
        Scenario 1,10,5
        Scenario 2,6,9

``load_vector``
    Two columns (name, value).

``load_vintages``
    Like ``load_matrix`` but rows are data-year vintages and cells are
    *relative* shifts applied to each indicator (0.03 means +3%).

``load_stages``
    SDI-BCA stage definitions; ``depends_on`` is a ';'-separated list of
    prerequisite stage names.
"""

from __future__ import annotations

import csv
from typing import Any, Dict, List, Sequence, Tuple


def _clean_rows(path: str) -> List[List[str]]:
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    rows = [r for r in rows if r and any(c.strip() for c in r)]
    if not rows:
        raise ValueError("empty CSV file: %s" % path)
    return rows


def load_matrix(path: str) -> Tuple[List[List[float]], List[str], List[str]]:
    """Read a decision matrix CSV.

    Returns ``(matrix, row_names, column_names)`` where ``matrix`` is a
    list of lists of floats.
    """
    rows = _clean_rows(path)
    if len(rows) < 2:
        raise ValueError("matrix CSV needs a header row and at least one data row: %s" % path)
    column_names = [c.strip() for c in rows[0][1:]]
    if not column_names:
        raise ValueError("matrix CSV needs indicator columns: %s" % path)
    row_names: List[str] = []
    matrix: List[List[float]] = []
    for r in rows[1:]:
        if len(r) - 1 != len(column_names):
            raise ValueError(
                "ragged row in %s: expected %d values, got %d (row %r)"
                % (path, len(column_names), len(r) - 1, r[:1])
            )
        row_names.append(r[0].strip())
        matrix.append([float(c) for c in r[1:]])
    return matrix, row_names, column_names


def load_vector(path: str) -> List[Tuple[str, float]]:
    """Read a two-column CSV (name, value) into a list of tuples.

    An optional header row (whose second cell is not a number) is
    skipped automatically.
    """
    rows = _clean_rows(path)
    data = rows
    try:
        float(rows[0][1])
    except (ValueError, IndexError):
        data = rows[1:]  # header row detected
    if not data:
        raise ValueError("vector CSV needs at least one data row: %s" % path)
    out = []
    for r in data:
        if len(r) < 2:
            raise ValueError("vector CSV needs two columns: %s" % path)
        out.append((r[0].strip(), float(r[1])))
    return out


def load_vintages(path: str) -> Tuple[List[Tuple[str, List[List[float]]]], List[str]]:
    """Read a stacked vintage-shift CSV.

    Layout: ``vintage,scenario,ind_a,ind_b,...`` — one block of rows per
    vintage, each row holding the per-scenario relative shifts for that
    vintage. Returns ``(vintages, indicator_names)`` where each vintage
    is ``(name, shift_matrix)`` and ``shift_matrix`` has the same shape
    as the base decision matrix.
    """
    rows = _clean_rows(path)
    if len(rows) < 3:
        raise ValueError("vintage CSV needs a header and at least two data rows: %s" % path)
    indicator_names = [c.strip() for c in rows[0][2:]]
    vintages: List[Tuple[str, List[List[float]]]] = []
    current: List[List[float]] = []
    current_name = None
    for r in rows[1:]:
        name = r[0].strip()
        if len(r) - 2 != len(indicator_names):
            raise ValueError("ragged vintage row in %s" % path)
        shifts = [float(c) for c in r[2:]]
        if current_name is None:
            current_name = name
        if name != current_name:
            vintages.append((current_name, current))
            current_name = name
            current = []
        current.append(shifts)
    if current_name is not None:
        vintages.append((current_name, current))
    return vintages, indicator_names


def load_stages(path: str) -> List[Dict[str, Any]]:
    """Read SDI-BCA stage definitions.

    Columns: ``name,start_year,duration,annual_cost,annual_benefit,
    ramp_up,handover_lag,depends_on``. ``depends_on`` is a ';'-separated
    list of prerequisite stage names (may be empty).
    """
    rows = _clean_rows(path)
    header = [c.strip() for c in rows[0]]
    required = {"name", "start_year", "duration", "annual_cost", "annual_benefit"}
    missing = required - set(header)
    if missing:
        raise ValueError("stage CSV missing columns: %s" % ", ".join(sorted(missing)))
    stages = []
    for r in rows[1:]:
        d = dict(zip(header, [c.strip() for c in r]))
        stages.append(
            {
                "name": d["name"],
                "start_year": int(float(d["start_year"])),
                "duration": int(float(d["duration"])),
                "annual_cost": float(d["annual_cost"]),
                "annual_benefit": float(d["annual_benefit"]),
                "ramp_up": float(d.get("ramp_up") or 0.0),
                "handover_lag": float(d.get("handover_lag") or 0.0),
                "depends_on": tuple(x for x in d.get("depends_on", "").split(";") if x),
            }
        )
    return stages
