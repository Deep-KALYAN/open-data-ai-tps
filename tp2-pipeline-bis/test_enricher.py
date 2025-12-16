#!/usr/bin/env python3
"""Test rapide du module d'enrichissement."""
from pipeline.fetchers.openfoodfacts import OpenFoodFactsFetcher
from pipeline.enricher import DataEnricher

# 1. Récupérer quelques produits
print("📥 Acquisition de produits...")
fetcher = OpenFoodFactsFetcher()
products = list(fetcher.fetch_all("chocolats", max_items=10, verbose=False))
print(f"✅ {len(products)} produits récupérés")

# 2. Extraire les adresses
enricher = DataEnricher()
addresses = enricher.extract_addresses(products)
print(f"📍 {len(addresses)} adresses uniques extraites")

if addresses:
    # 3. Géocodage (limité à 3 pour le test)
    print("🌍 Géocodage des adresses...")
    limited_addresses = addresses[:3]
    geo_cache = enricher.build_geocoding_cache(limited_addresses)
    
    # 4. Enrichissement
    print("🔗 Enrichissement des produits...")
    enriched_products = enricher.enrich_products(products, geo_cache)
    
    # 5. Vérification
    stats = enricher.get_stats()
    print(f"\n📊 Statistiques d'enrichissement:")
    print(f"   Produits traités: {stats['total_processed']}")
    print(f"   Enrichis avec succès: {stats['successfully_enriched']}")
    print(f"   Taux de succès: {stats['success_rate']:.1f}%")
    
    # Afficher le premier produit enrichi
    if enriched_products:
        first = enriched_products[0]
        print(f"\n🔍 Premier produit enrichi:")
        print(f"   Nom: {first.get('product_name', 'N/A')[:30]}...")
        print(f"   Adresse magasin: {first.get('store_address', 'N/A')}")
        print(f"   Score géocodage: {first.get('geocoding_score', 'N/A')}")
else:
    print("⚠️ Aucune adresse trouvée dans les produits")