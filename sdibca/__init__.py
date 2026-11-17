"""SDI-BCA: Staged-Delay-Inclusive Benefit-Cost Analysis.

Reference implementation of the staged-delay-inclusive benefit-cost
analysis procedure for staged transport programmes.

Public API
----------
    Stage           stage definition (cost, benefit, dependencies)
    SDIBCAModel     programme model: delay propagation, cash flows
    SDIBCAResult    outcome of a base-vs-delayed comparison
    npv, bcr        discounting helpers
"""

__version__ = "1.4.0"

from .metrics import bcr, npv
from .model import Stage, SDIBCAModel, SDIBCAResult

__all__ = ["Stage", "SDIBCAModel", "SDIBCAResult", "npv", "bcr", "__version__"]
