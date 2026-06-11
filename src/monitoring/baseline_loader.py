
"""
Load a saved baseline snapshot from disk.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class BaselineLoadError(Exception):
    """Raised when the baseline file cannot be loaded"""


def load_baseline(directory: Path) ->dict:
    """
    Load baseline.json from directory and return the parsed dict.

    Args:
        directory: The folder that contains 'baseline.json' exactly as 
            written by func: 'src.models.baseline_saver.save_baseline'

    Returns:
        The baseline dictionary

    Raises: 
        BaselineLoadError: If the file does not exist or contains invalid JSON.
    
    """

    file_path = directory / "baseline.json"

    if not file_path.exists():
        raise BaselineLoadError(
            f"Baseline file not found: {file_path}"
        )
    
    try:
        with file_path.open(encoding="utf-8") as fh:
            baseline = json.load(fh)
    except json.JSONDecodeError as exc:
        raise BaselineLoadError(
            f"Baseline file at {file_path} is not valid JSON: {exc}"
        ) from exc
    
    logger.info(
        "Loaded baseline from %s (keys: %s)",
        file_path, sorted(baseline.keys()),
    )

    return baseline
