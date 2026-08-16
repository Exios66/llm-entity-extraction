"""Bootstrap confidence intervals — re-export shim.

The CI helpers live in the **llm-dojo-scoring** package
(``llm_dojo_scoring.bootstrap``; byte-identical implementations); this module
re-exports them so every local import site keeps working unchanged. The site
layer keeps its own ``wilson_ci`` copy (``scripts/site/build_site.py``).
"""

from __future__ import annotations

from llm_dojo_scoring.bootstrap import (  # noqa: F401  (re-export shim)
    DEFAULT_ALPHA,
    DEFAULT_N_BOOT,
    DEFAULT_SEED,
    bootstrap_ci,
    delta_significance,
    wilson_ci,
)
