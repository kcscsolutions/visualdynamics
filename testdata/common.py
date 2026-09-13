"""Shared helpers for the test-data generators."""

import numpy as np


def recompress(*paths):
    """Rewrite .npz files with compression.

    Test data lives in the repository, and these arrays are smooth enough
    to shrink by nearly half. sdynpy writes them uncompressed; numpy reads
    either kind without being told which.
    """
    for path in paths:
        with np.load(path, allow_pickle=True) as handle:
            arrays = dict(handle)
        np.savez_compressed(path, **arrays)
