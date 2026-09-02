"""
Skills Package for Agent Skill Marketplace.
Provides dynamic loader for hyphenated skill folder structures with relative import support.
"""

import sys
import importlib.util
import importlib.machinery
from pathlib import Path

SKILLS_DIR = Path(__file__).parent

def load_skill_module(skill_folder_name: str, script_name: str = "audit.py"):
    """
    Dynamically loads a skill script module from hyphenated skill directories.
    Sets up synthetic package mappings so relative imports within skill folders work seamlessly.
    Example: load_skill_module("crawl-render-audit", "audit.py")
    """
    scripts_dir = SKILLS_DIR / skill_folder_name / "scripts"
    script_path = scripts_dir / script_name
    if not script_path.exists():
        raise FileNotFoundError(f"Skill script not found at {script_path}")

    pkg_name = f"skills.{skill_folder_name.replace('-', '_')}.scripts"
    if pkg_name not in sys.modules:
        pkg_spec = importlib.machinery.ModuleSpec(pkg_name, None, is_package=True)
        pkg_module = importlib.util.module_from_spec(pkg_spec)
        pkg_module.__path__ = [str(scripts_dir)]
        sys.modules[pkg_name] = pkg_module

    module_name = f"{pkg_name}.{script_name.replace('.py', '')}"
    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load spec for module {module_name}")

    module = importlib.util.module_from_spec(spec)
    module.__package__ = pkg_name
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
