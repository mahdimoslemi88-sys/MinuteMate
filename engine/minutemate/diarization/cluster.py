"""Agglomerative clustering helpers for speaker embeddings."""

from __future__ import annotations

import numpy as np


def silhouette(X: np.ndarray, labels: np.ndarray) -> float:
    labels = np.asarray(labels)
    uniques = np.unique(labels)
    if len(uniques) < 2 or len(X) < len(uniques) + 1:
        return -1.0
    distances = 1.0 - X @ X.T
    np.fill_diagonal(distances, 0.0)
    scores = []
    for i in range(len(X)):
        own = labels == labels[i]
        own[i] = False
        a = distances[i, own].mean() if own.any() else 0.0
        b = min(distances[i, labels == c].mean() for c in uniques if c != labels[i])
        scores.append((b - a) / max(a, b, 1e-9))
    return float(np.mean(scores))


def choose_k(Z: np.ndarray, min_share: float = 0.02, max_k: int = 12):
    from scipy.cluster.hierarchy import fcluster, linkage
    from scipy.spatial.distance import squareform

    distances = np.clip(1.0 - Z @ Z.T, 0.0, 2.0)
    linkage_matrix = linkage(squareform(distances, checks=False), method="average")
    best = None
    for k in range(2, min(max_k, len(Z) - 1) + 1):
        labels = fcluster(linkage_matrix, k, criterion="maxclust")
        counts = np.bincount(labels)[1:]
        share = counts.sum() and counts.min() / counts.sum()
        if share < min_share:
            continue
        score = silhouette(Z, labels)
        if best is None or score > best[0]:
            best = (score, k, labels)
    if best is None:
        ones = np.ones(len(Z), dtype=int) + 1
        best = (silhouette(Z, ones), 1, ones)
    return best[1], best[2], best[0], linkage_matrix
