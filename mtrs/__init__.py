"""MTRS: Multivariate Transport Ranking Stability test.

Reference implementation of the MTRS procedure for assessing the
stability of transport policy scenario rankings under six sources of
uncertainty:

    1. model structure
    2. parameter uncertainty
    3. data-year (vintage) uncertainty
    4. policy-mapping uncertainty
    5. indicator-weight uncertainty
    6. metropolitan-area structure (cross-area transferability)

The test decomposes ranking instability into per-source variance shares
and evaluates three reporting rules: when a ranking may be reported as
stable, when it may reverse, and when it cannot be transferred across
metropolitan-area structures.

Public API
----------
    MTRSAnalysis            configure and run the test
    MTRSResult              result object (decomposition + verdict)
    UncertaintySpec         definitions of the six uncertainty sources
    load_matrix             CSV helpers for decision matrices and inputs
    load_vector
    load_vintages
    rank_vector             ranking helper (ties -> average rank)
    rank_displacement       sum of absolute rank differences
    kendall_tau_distance    normalised Kendall tau distance
    render_text_report      plain-text assessment report
    render_json_report      machine-readable assessment report
"""

__version__ = "1.4.0"

from .metrics import kendall_tau_distance, max_displacement, rank_displacement, rank_vector
from .io import load_matrix, load_vector, load_vintages, load_stages
from .uncertainty import UncertaintySpec
from .core import MTRSAnalysis, MTRSResult, SourceDecomposition, DEFAULT_THRESHOLDS
from .report import render_text_report, render_json_report

__all__ = [
    "MTRSAnalysis",
    "MTRSResult",
    "SourceDecomposition",
    "UncertaintySpec",
    "DEFAULT_THRESHOLDS",
    "rank_vector",
    "rank_displacement",
    "kendall_tau_distance",
    "max_displacement",
    "load_matrix",
    "load_vector",
    "load_vintages",
    "load_stages",
    "render_text_report",
    "render_json_report",
    "__version__",
]
