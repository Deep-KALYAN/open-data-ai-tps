#!/usr/bin/env python3
"""Test du module de qualité."""
import pandas as pd
import numpy as np
from pipeline.quality import QualityAnalyzer

# Créer un dataset de test réaliste
np.random.seed(42)
n_rows = 100

test_data = {
    'code': [f'PROD_{i:04d}' for i in range(n_rows)] + ['PROD_0000'],  # Un doublon
    'product_name': [f'Product {i}' if i % 10 != 0 else None for i in range(n_rows + 1)],
    'brands': ['Brand A' if i % 3 == 0 else 'Brand B' if i % 3 == 1 else 'Brand C' for i in range(n_rows + 1)],
    'categories': ['chocolats' if i % 2 == 0 else 'biscuits' for i in range(n_rows + 1)],
    'nutriscore_grade': np.random.choice(['A', 'B', 'C', 'D', 'E', None], n_rows + 1, p=[0.2, 0.2, 0.2, 0.15, 0.15, 0.1]),
    'energy_100g': np.random.normal(500, 100, n_rows + 1),
    'sugars_100g': np.random.normal(30, 15, n_rows + 1),
    'stores': [f'Store {i}' if i % 5 != 0 else None for i in range(n_rows + 1)],
    'geocoding_score': np.random.uniform(0, 1, n_rows + 1),
}

# Ajouter quelques outliers
test_data['energy_100g'][10] = 2000  # Outlier
test_data['sugars_100g'][20] = -5    # Valeur négative

# Créer le DataFrame
df = pd.DataFrame(test_data)
print("📊 Dataset de test créé:")
print(f"   - Lignes: {len(df)}")
print(f"   - Colonnes: {len(df.columns)}")
print(f"   - Valeurs nulles: {df.isnull().sum().sum()}")

# Analyser la qualité
print("\n🔍 Analyse de qualité...")
analyzer = QualityAnalyzer(df)
metrics = analyzer.analyze()

print("\n📈 Résultats de l'analyse:")
print(f"   Note globale: {metrics.quality_grade}")
print(f"   Acceptable: {'✅ Oui' if metrics.is_acceptable else '❌ Non'}")
print(f"   Enregistrements: {metrics.total_records} total, {metrics.valid_records} valides")
print(f"   Complétude: {metrics.completeness_score * 100:.1f}%")
print(f"   Doublons: {metrics.duplicates_pct:.1f}% ({metrics.duplicates_count} doublons)")
print(f"   Géocodage réussi: {metrics.geocoding_success_rate:.1f}%")

# Générer le rapport (sans IA)
print("\n📄 Génération du rapport...")
report_path = analyzer.generate_report(
    output_name="test_quality",
    include_ai=False  # Pas d'IA pour le test
)

print(f"\n✅ Rapport généré: {report_path}")

# Afficher un extrait du rapport
print("\n📋 Extrait du rapport:")
with open(report_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()[:20]
    for line in lines:
        print(line.rstrip())