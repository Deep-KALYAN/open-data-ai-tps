#!/usr/bin/env python3
"""Test du module de stockage."""
import pandas as pd
import numpy as np
from pipeline.storage import (
    save_raw_json,
    save_parquet,
    load_parquet,
    get_storage_stats,
    get_latest_parquet
)

print("🧪 Test du module de stockage")

# 1. Créer des données de test
test_data = [
    {"id": i, "name": f"Product {i}", "category": "chocolats", "price": i * 10}
    for i in range(10)
]

print("\n1. Test sauvegarde JSON brut")
json_path = save_raw_json(test_data, "test_data")
print(f"   ✅ Sauvegardé: {json_path}")

# 2. Créer un DataFrame
df = pd.DataFrame({
    "code": [f"P{i:03d}" for i in range(20)],
    "name": [f"Product {i}" for i in range(20)],
    "category": ["chocolats" if i % 2 == 0 else "biscuits" for i in range(20)],
    "price": np.random.uniform(1, 100, 20),
    "quantity": np.random.randint(1, 100, 20),
})

print("\n2. Test sauvegarde Parquet simple")
parquet_path = save_parquet(df, "test_products")
print(f"   ✅ Sauvegardé: {parquet_path}")

print("\n3. Test sauvegarde Parquet partitionné")
parquet_partitioned = save_parquet(df, "test_partitioned", partition_by="category")
print(f"   ✅ Sauvegardé dossier: {parquet_partitioned}")

print("\n4. Test chargement Parquet")
df_loaded = load_parquet(parquet_path)
print(f"   ✅ Chargé: {len(df_loaded)} enregistrements")
print(f"   Colonnes: {list(df_loaded.columns)}")

print("\n5. Test recherche du dernier fichier")
latest = get_latest_parquet("test_products_*.parquet")
if latest:
    print(f"   ✅ Dernier fichier: {latest.name}")
else:
    print("   ℹ️ Aucun fichier trouvé")

print("\n6. Statistiques de stockage")
stats = get_storage_stats()
print(f"   📊 Raw: {stats['raw']['count']} fichiers, {stats['raw']['total_size_mb']:.2f} MB")
print(f"   📊 Processed: {stats['processed']['count']} fichiers, {stats['processed']['total_size_mb']:.2f} MB")

print("\n🎉 Tous les tests de stockage sont passés!")