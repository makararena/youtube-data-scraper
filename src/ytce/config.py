"""Configuration management for ytce."""

from __future__ import annotations

import os
import platform
from typing import Any, Optional

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


DEFAULT_CONFIG = {
    "output_dir": "data",
    "language": "en",
    "comment_sort": "recent",
}

CONFIG_FILE = "ytce.yaml"
CHANNELS_FILE = "channels.txt"
VIDEOS_FILE = "videos.txt"

CHANNELS_TEMPLATE = """# List of YouTube channels to scrape
# One channel per line
# Supported formats:
#   - @handle
#   - https://www.youtube.com/@handle
#   - https://www.youtube.com/channel/UC...
#   - /channel/UC...
#   - UC... (channel ID)
#
# Lines starting with # are comments and will be ignored
# Empty lines are ignored

@skryp
@errornil
"""

VIDEOS_TEMPLATE = """# List of YouTube videos to scrape
# One video per line
# Supported formats:
#   - Video ID (11 characters, e.g., dQw4w9WgXcQ)
#   - https://www.youtube.com/watch?v=VIDEO_ID
#   - https://youtu.be/VIDEO_ID
#   - https://www.youtube.com/watch?v=VIDEO_ID&t=123s
#
# Lines starting with # are comments and will be ignored
# Empty lines are ignored

dQw4w9WgXcQ
jNQXAC9IVRw
"""


def load_config(config_path: Optional[str] = None) -> dict[str, Any]:
    """
    Load configuration.

    Behavior:
    - If config_path is provided: load ONLY that file (no global fallback).
    - Otherwise: merge defaults <- global config <- local ./ytce.yaml
    """
    if config_path is not None:
        return _load_single_config_file(config_path)

    config: dict[str, Any] = DEFAULT_CONFIG.copy()

    # Merge global config first
    global_path = get_global_config_path()
    if global_path and os.path.exists(global_path):
        config.update(_load_yaml_or_empty(global_path))

    # Merge local project config (overrides global)
    local_path = CONFIG_FILE
    if os.path.exists(local_path):
        config.update(_load_yaml_or_empty(local_path))

    return config


def save_config(config: dict[str, Any], config_path: Optional[str] = None) -> None:
    """Save configuration to ytce.yaml."""
    path = config_path or CONFIG_FILE
    
    if not HAS_YAML:
        # Fallback: write as simple key=value format
        with open(path, "w", encoding="utf-8") as f:
            f.write("# ytce configuration\n")
            f.write("# Note: PyYAML not installed. Using simple format.\n\n")
            for key, value in config.items():
                f.write(f"{key}: {value}\n")
        return
    
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def get_global_config_path() -> Optional[str]:
    """
    Return user-level config path (per-machine), for storing secrets like API keys.

    - macOS/Linux: ~/.config/ytce/ytce.yaml
    - Windows: %APPDATA%\\ytce\\ytce.yaml (fallback to ~\\AppData\\Roaming\\ytce\\ytce.yaml if APPDATA missing)
    """
    system = platform.system()
    if system == "Windows":
        base = os.environ.get("APPDATA")
        if not base:
            home = os.path.expanduser("~")
            base = os.path.join(home, "AppData", "Roaming")
        return os.path.join(base, "ytce", "ytce.yaml")

    home = os.path.expanduser("~")
    return os.path.join(home, ".config", "ytce", "ytce.yaml")


def save_global_config(config: dict[str, Any]) -> None:
    """Save configuration to the user-level global config path."""
    path = get_global_config_path()
    if not path:
        raise RuntimeError("Unable to resolve global config path")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    save_config(config, config_path=path)


def _load_single_config_file(path: str) -> dict[str, Any]:
    """Load ONLY a single config file, merging it over defaults."""
    if not os.path.exists(path):
        return DEFAULT_CONFIG.copy()
    config = DEFAULT_CONFIG.copy()
    config.update(_load_yaml_or_empty(path))
    return config


def _load_yaml_or_empty(path: str) -> dict[str, Any]:
    if not HAS_YAML:
        print("Warning: PyYAML not installed, using defaults. Install with: pip install pyyaml")
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if not isinstance(data, dict):
            print(f"Warning: {path} is not a mapping; ignoring.")
            return {}
        return data
    except Exception as e:
        print(f"Warning: Failed to load {path}: {e}. Ignoring.")
        return {}


def init_project(output_dir: Optional[str] = None) -> None:
    """Initialize a new ytce project with config and directories."""
    config = DEFAULT_CONFIG.copy()
    
    if output_dir:
        config["output_dir"] = output_dir
    
    # Create output directory
    data_dir = config["output_dir"]
    os.makedirs(data_dir, exist_ok=True)
    
    # Save config file (if it doesn't exist)
    if not os.path.exists(CONFIG_FILE):
        save_config(config)
        print(f"✔ Config file: ./{CONFIG_FILE}")
    else:
        print(f"⚠️  Config file already exists: ./{CONFIG_FILE}")
    
    # Create channels.txt template (if it doesn't exist)
    if not os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
            f.write(CHANNELS_TEMPLATE)
        print(f"✔ Channels file: ./{CHANNELS_FILE}")
    else:
        print(f"⚠️  Channels file already exists: ./{CHANNELS_FILE}")
    
    # Create videos.txt template (if it doesn't exist)
    if not os.path.exists(VIDEOS_FILE):
        with open(VIDEOS_FILE, "w", encoding="utf-8") as f:
            f.write(VIDEOS_TEMPLATE)
        print(f"✔ Videos file: ./{VIDEOS_FILE}")
    else:
        print(f"⚠️  Videos file already exists: ./{VIDEOS_FILE}")
    
    # Success messages
    print("✔ Project initialized")
    print(f"✔ Output directory: ./{data_dir}")

