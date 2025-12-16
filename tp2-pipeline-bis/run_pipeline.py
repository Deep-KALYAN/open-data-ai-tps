#!/usr/bin/env python3
"""Script d'exécution simplifié du pipeline."""
import sys
import os

# Ajouter le répertoire courant au chemin Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline.main import main

if __name__ == "__main__":
    main()