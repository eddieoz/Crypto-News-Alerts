"""
Configuration loader utility.
"""
import os
import re
from pathlib import Path
from typing import Any, Dict

import yaml


def load_config(path: Path) -> Dict[str, Any]:
    """
    Load a YAML configuration file with environment variable substitution.
    
    Supports ${VAR:-default} syntax for environment variables.
    """
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    
    with open(path, 'r') as f:
        content = f.read()
    
    # Substitute environment variables
    content = _substitute_env_vars(content)
    
    return yaml.safe_load(content)


def _substitute_env_vars(content: str) -> str:
    """
    Substitute ${VAR:-default} patterns with environment variable values.
    """
    pattern = r'\$\{([^}:]+)(?::-([^}]*))?\}'
    
    def replacer(match):
        var_name = match.group(1)
        default = match.group(2) or ""
        return os.environ.get(var_name, default)
    
    return re.sub(pattern, replacer, content)
