"""Ranking metrics used by the MTRS test.

All metrics operate on rank vectors. Ranks are 1-based and ties receive
the average of the ranks they span, so the metrics stay well defined for
tied scenario scores.
"""

from __future__ import annotations

from typing import Sequence


def rank_vector(scores: Sequence[float], descending: bool = True) -> "list[float]":
    """Return 1-based ranks for a sequence of scores.

    With ``descending=True`` (the default) the largest score receives
    rank 1, matching the convention "best scenario first". Ties are
    assigned the average of the ranks they span.

    >>> rank_vector([3.0, 1.0, 2.0])
    [1.0, 3.0, 2.0]
    >>> rank_vector([2.0, 2.0, 1.0])
    [1.5, 1.5, 3.0]
    """
    n = len(scores)
    indexed = sorted(range(n), key=lambda i: scores[i], reverse=descending)
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and scores[indexed[j + 1]] == scores[indexed[i]]:
            j += 1
        avg = (i + 1 + j + 1) / 2.0
        for k in range(i, j + 1):
            ranks[indexed[k]] = avg
        i = j + 1
    return ranks


def rank_displacement(a: Sequence[float], b: Sequence[float]) -> float:
    """Sum of absolute rank differences between two rank vectors.

    Zero when the rankings are identical; at most
    :func:`max_displacement` for a complete reversal.
    """
    if len(a) != len(b):
        raise ValueError("rank vectors must have equal length")
    return sum(abs(x - y) for x, y in zip(a, b))


def max_displacement(n: int) -> float:
    """Maximum sum of absolute rank differences between two permutations
    of ``n`` items, i.e. the displacement between a ranking and its exact
    reversal: ``floor(n^2 / 2)``.

    >>> max_displacement(4)
    8.0
    >>> max_displacement(5)
    12.0
    """
    if n < 1:
        raise ValueError("n must be positive")
    return float((n * n) // 2)


def kendall_tau_distance(a: Sequence[float], b: Sequence[float]) -> float:
    """Kendall tau distance in [0, 1] between two rank vectors.

    0 for identical orderings, 1 for exact reversal. Pairs tied in both
    vectors are ignored; pairs tied in exactly one vector count as half a
    discordance (tau-b style handling).
    """
    if len(a) != len(b):
        raise ValueError("rank vectors must have equal length")
    n = len(a)
    pairs = 0
    discordant = 0.0
    for i in range(n):
        for j in range(i + 1, n):
            da = a[j] - a[i]
            db = b[j] - b[i]
            if da == 0 and db == 0:
                continue  # tied in both: carries no ordering information
            pairs += 1
            if da == 0 or db == 0:
                discordant += 0.5  # tied in exactly one
            elif da * db < 0:
                discordant += 1.0
    return discordant / pairs if pairs else 0.0
