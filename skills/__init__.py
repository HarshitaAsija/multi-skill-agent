"""
Skills Package for Agent Skill Marketplace.
Provides clean import paths for hyphenated skill folder structures.
"""

import sys
import importlib.util
from pathlib import Path

SKILLS_DIR = Path(__file__).parent

def load_skill_module(skill_folder_name: str, script_name: str = "audit.py"):
    """
    Dynamically loads a skill script module from hyphenated skill directories.
    Example: load_skill_module("crawl-render-audit", "audit.py")
    """
    script_path = SKILLS_DIR / skill_folder_name / "scripts" / script_name
    if not script_path.exists():
        raise FileNotFoundError(f"Skill script not found at {script_path}")

    module_name = f"skills.{skill_folder_name.replace('-', '_')}.scripts.{script_name.replace('.py', '')}"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load spec for module {module_name}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
