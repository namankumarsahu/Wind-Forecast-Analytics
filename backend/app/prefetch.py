"""Warm the on-disk cache for the whole analysis scope.

    python -m app.prefetch

Useful before a demo, in a Docker build/entrypoint, or to prepare a cache that is
then served with ELEXON_OFFLINE=true.
"""

from __future__ import annotations

import logging

from .deps import build_provider
from .config import get_settings


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = get_settings()
    provider = build_provider(settings)
    data = provider.load(settings.analysis_start, settings.analysis_end)
    s = data.status
    print(
        f"Loaded {len(data.actuals_raw)} actual rows and {len(data.forecasts_raw)} forecast rows "
        f"({s.chunks_fetched} chunks fetched, {s.chunks_from_cache} from cache) -> {settings.cache_dir}"
    )


if __name__ == "__main__":
    main()
