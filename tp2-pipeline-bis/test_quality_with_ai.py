#!/usr/bin/env python3
"""Test complet du module qualité avec IA."""
import pandas as pd
import numpy as np
from pipeline.quality import QualityAnalyzer

print("🧪 Test complet du module qualité avec IA")

# Créer un dataset de test réaliste
np.random.seed(42)
n_rows = 50

test_data = {
    'code': [f'PROD_{i:04d}' for i in range(n_rows)],
    'product_name': [f'Product {i}' if i % 10 != 0 else None for i in range(n_rows)],
    'brands': ['Brand A' if i % 3 == 0 else 'Brand B' if i % 3 == 1 else 'Brand C' for i in range(n_rows)],
    'categories': ['chocolats' if i % 2 == 0 else 'biscuits' for i in range(n_rows)],
    'nutriscore_grade': np.random.choice(['A', 'B', 'C', 'D', 'E', None], n_rows, p=[0.2, 0.2, 0.2, 0.15, 0.15, 0.1]),
    'energy_100g': np.random.normal(500, 100, n_rows),
    'sugars_100g': np.random.normal(30, 15, n_rows),
    'stores': [f'Store {i}' if i % 5 != 0 else None for i in range(n_rows)],
    'geocoding_score': np.random.uniform(0, 1, n_rows),
}

df = pd.DataFrame(test_data)

print(f"📊 Dataset créé: {len(df)} lignes, {len(df.columns)} colonnes")

# Analyser la qualité
print("\n🔍 Analyse de qualité...")
analyzer = QualityAnalyzer(df)
metrics = analyzer.analyze()

print(f"\n📈 Note qualité: {metrics.quality_grade}")
print(f"   Acceptable: {'✅ Oui' if metrics.is_acceptable else '❌ Non'}")

# Générer le rapport AVEC IA
print("\n📄 Génération du rapport avec IA...")
report_path = analyzer.generate_report(
    output_name="test_quality_ai",
    include_ai=True
)

print(f"\n✅ Rapport généré: {report_path}")

# Afficher un extrait
print("\n📋 Extrait du rapport (lignes 40-60):")
with open(report_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i, line in enumerate(lines[40:60], 41):
        print(f"{i:3}: {line.rstrip()}")