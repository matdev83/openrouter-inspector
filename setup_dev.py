#!/usr/bin/env python3
"""
Development environment setup script for OpenRouter CLI.

This script creates a virtual environment and installs development dependencies.
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(command: list[str], cwd: Path = None) -> bool:
    """Run a command and return True if successful."""
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True
        )
        print(f"✓ {' '.join(command)}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {' '.join(command)}")
        print(f"Error: {e.stderr}")
        return False


def main():
    """Set up the development environment."""
    project_root = Path(__file__).parent
    venv_path = project_root / ".venv"
    
    print("Setting up OpenRouter CLI development environment...")
    print(f"Project root: {project_root}")
    print(f"Virtual environment: {venv_path}")
    
    # Create virtual environment
    if not venv_path.exists():
        print("\n1. Creating virtual environment...")
        if not run_command([sys.executable, "-m", "venv", str(venv_path)]):
            print("Failed to create virtual environment")
            return 1
    else:
        print("\n1. Virtual environment already exists")
    
    # Determine the correct python executable path
    if os.name == 'nt':  # Windows
        python_exe = venv_path / "Scripts" / "python.exe"
        pip_exe = venv_path / "Scripts" / "pip.exe"
    else:  # Unix-like systems
        python_exe = venv_path / "bin" / "python"
        pip_exe = venv_path / "bin" / "pip"
    
    # Upgrade pip
    print("\n2. Upgrading pip...")
    if not run_command([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"]):
        print("Failed to upgrade pip")
        return 1
    
    # Install the package in development mode with dev dependencies
    print("\n3. Installing package in development mode...")
    if not run_command([str(pip_exe), "install", "-e", ".[dev]"], cwd=project_root):
        print("Failed to install package in development mode")
        return 1
    
    # Install pre-commit hooks (optional)
    print("\n4. Setting up pre-commit hooks...")
    if run_command([str(python_exe), "-m", "pre_commit", "install"], cwd=project_root):
        print("Pre-commit hooks installed successfully")
    else:
        print("Pre-commit hooks installation failed (optional)")
    
    print("\n✓ Development environment setup complete!")
    print("\nTo activate the virtual environment:")
    if os.name == 'nt':  # Windows
        print(f"  {venv_path / 'Scripts' / 'activate.bat'}")
    else:  # Unix-like systems
        print(f"  source {venv_path / 'bin' / 'activate'}")
    
    print("\nTo run tests:")
    print("  pytest")
    
    print("\nTo run quality checks:")
    print("  black .")
    print("  ruff check --fix .")
    print("  mypy openrouter_inspector")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())