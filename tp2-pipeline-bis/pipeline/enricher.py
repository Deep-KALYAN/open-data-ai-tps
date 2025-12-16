"""Module d'enrichissement des données."""
import pandas as pd
from typing import Optional
from tqdm import tqdm

from .fetchers.adresse import AdresseFetcher
from .models import Product, GeocodingResult


class DataEnricher:
    """Enrichit les données en croisant plusieurs sources."""

    def __init__(self):
        self.geocoder = AdresseFetcher()
        self.enrichment_stats = {
            "total_processed": 0,
            "successfully_enriched": 0,
            "failed_enrichment": 0,
        }

    def extract_addresses(
        self,
        products: list[dict],
        address_field: str = "stores"
    ) -> list[str]:
        """
        Extrait les adresses uniques des produits.
        
        Args:
            products: Liste des produits
            address_field: Champ contenant l'adresse/magasin
        
        Returns:
            Liste d'adresses uniques
        """
        addresses = set()

        for product in products:
            addr = product.get(address_field, "")
            if addr and isinstance(addr, str) and addr.strip():
                # Nettoyer et extraire les adresses (peuvent être séparées par virgules)
                for part in addr.split(","):
                    cleaned = part.strip()
                    if len(cleaned) > 3:  # Ignorer les trop courts
                        addresses.add(cleaned)

        return list(addresses)

    def build_geocoding_cache(
        self,
        addresses: list[str]
    ) -> dict[str, GeocodingResult]:
        """
        Construit un cache de géocodage pour éviter les requêtes en double.
        
        Args:
            addresses: Liste d'adresses à géocoder
        
        Returns:
            Dictionnaire adresse -> résultat
        """
        cache = {}

        print(f"🌍 Géocodage de {len(addresses)} adresses uniques...")

        for result in self.geocoder.fetch_all(addresses):
            cache[result.original_address] = result

        success_rate = (
            sum(1 for r in cache.values() if r.is_valid) / len(cache) * 100
            if cache else 0
        )
        print(f"✅ Taux de succès: {success_rate:.1f}%")

        return cache

    def enrich_products(
        self,
        products: list[dict],
        geocoding_cache: dict[str, GeocodingResult],
        address_field: str = "stores"
    ) -> list[dict]:
        """
        Enrichit les produits avec les données de géocodage.
        
        Args:
            products: Liste des produits
            geocoding_cache: Cache de géocodage
            address_field: Champ contenant l'adresse
        
        Returns:
            Liste des produits enrichis
        """
        enriched = []

        for product in tqdm(products, desc="Enrichissement"):
            self.enrichment_stats["total_processed"] += 1

            # Copier le produit
            enriched_product = product.copy()

            # Chercher l'adresse
            addr = product.get(address_field, "")
            if addr and isinstance(addr, str):
                # Prendre la première adresse si plusieurs
                first_addr = addr.split(",")[0].strip()

                if first_addr in geocoding_cache:
                    geo = geocoding_cache[first_addr]

                    enriched_product["store_address"] = geo.label
                    enriched_product["latitude"] = geo.latitude
                    enriched_product["longitude"] = geo.longitude
                    enriched_product["city"] = geo.city
                    enriched_product["postal_code"] = geo.postal_code
                    enriched_product["geocoding_score"] = geo.score

                    if geo.is_valid:
                        self.enrichment_stats["successfully_enriched"] += 1
                    else:
                        self.enrichment_stats["failed_enrichment"] += 1
                else:
                    # Adresse non trouvée dans le cache
                    self.enrichment_stats["failed_enrichment"] += 1

            enriched.append(enriched_product)

        return enriched

    def get_stats(self) -> dict:
        """Retourne les statistiques d'enrichissement."""
        stats = self.enrichment_stats.copy()
        stats["geocoder_stats"] = self.geocoder.get_stats()

        if stats["total_processed"] > 0:
            stats["success_rate"] = (
                stats["successfully_enriched"] / stats["total_processed"] * 100
            )
        else:
            stats["success_rate"] = 0

        return stats