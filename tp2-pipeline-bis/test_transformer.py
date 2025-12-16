#!/usr/bin/env python3
"""Test du module de transformation."""
import pandas as pd
import numpy as np
from pipeline.transformer import DataTransformer

# Créer un DataFrame de test réaliste
test_data = {
    'code': ['001', '002', '003', '001', '005'],  # Doublon sur 001
    'product_name': ['  Chocolat Noir  ', None, 'Chocolat Au Lait', 'Chocolat Noir', 'Chocolat Blanc'],
    'brands': ['Lindt', 'Lindt', 'Milka', 'Lindt', None],
    'categories': ['chocolats', 'chocolats', 'chocolats', 'chocolats', 'chocolats'],
    'nutriscore_grade': ['A', 'B', 'C', 'A', None],
    'energy_100g': [500.0, None, 450.0, 500.0, 600.0],
    'sugars_100g': [40.0, 35.0, 50.0, 40.0, 100.0],  # 100g = outlier
    'stores': ['Carrefour Paris', '  Leclerc Toulouse  ', None, 'Carrefour Paris', 'Super U'],
    'latitude': [48.8566, None, 43.6045, 48.8566, None],
    'longitude': [2.3522, None, 1.4442, 2.3522, None],
    'geocoding_score': [0.85, 0.45, 0.92, 0.85, 0.1]
}

df = pd.DataFrame(test_data)
print("📊 Dataset initial:")
print(df)
print(f"\nShape: {df.shape}")
print(f"Valeurs nulles totales: {df.isnull().sum().sum()}")

# Appliquer les transformations
print("\n🔧 Application des transformations...")
transformer = DataTransformer(df)
df_clean = (
    transformer
    .remove_duplicates(['code'])
    .handle_missing_values(
        numeric_strategy='median',
        text_strategy='inconnu',
        categorical_strategy='inconnu'
    )
    .clean_address_column('stores', min_length=5)
    .normalize_text_columns(['product_name', 'brands', 'stores'])
    .filter_outliers(['sugars_100g'], method='iqr', threshold=1.5)
    .add_derived_columns()
    .get_result()
)

print("\n" + transformer.get_summary())

print("\n✅ Dataset nettoyé:")
print(df_clean)
print(f"\nShape finale: {df_clean.shape}")
print(f"Valeurs nulles totales: {df_clean.isnull().sum().sum()}")

# Tester les suggestions IA (optionnel)
print("\n🤖 Suggestions IA (preview):")
try:
    suggestions = transformer.get_ai_transformation_suggestions()
    print(suggestions[:300] + "...")
except Exception as e:
    print(f"IA non disponible: {e}")