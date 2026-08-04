"""Hace que los paquetes de primer nivel del repo (domain, application,
config, adapters) sean importables desde los tests sin instalar el
proyecto como paquete."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
