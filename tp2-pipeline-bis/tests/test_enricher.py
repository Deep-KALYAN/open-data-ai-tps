"""Tests pour le module d'enrichissement."""
import pytest
from unittest.mock import Mock, patch
from pipeline.enricher import DataEnricher
from pipeline.models import GeocodingResult


class TestDataEnricher:
    """Tests pour DataEnricher."""
    
    @pytest.fixture
    def sample_products(self):
        """Produits de test."""
        return [
            {"code": "001", "stores": "Carrefour Paris, Auchan"},
            {"code": "002", "stores": "Leclerc Toulouse"},
            {"code": "003", "stores": None},
            {"code": "004", "stores": "Carrefour Paris"},  # Doublon
        ]
    
    def test_init(self):
        """Test l'initialisation."""
        enricher = DataEnricher()
        assert enricher.geocoder is not None
        assert enricher.enrichment_stats["total_processed"] == 0
    
    def test_extract_addresses(self, sample_products):
        """Test l'extraction d'adresses uniques."""
        enricher = DataEnricher()
        addresses = enricher.extract_addresses(sample_products)
        
        # Devrait extraire 3 adresses uniques (Carrefour Paris, Auchan, Leclerc Toulouse)
        assert len(addresses) == 3
        assert "Carrefour Paris" in addresses
        assert "Leclerc Toulouse" in addresses
        assert "Auchan" in addresses
    
    def test_extract_addresses_empty(self):
        """Test extraction avec produits sans adresses."""
        products = [{"code": "001"}, {"code": "002", "stores": ""}]
        enricher = DataEnricher()
        addresses = enricher.extract_addresses(products)
        
        assert addresses == []
    
    def test_build_geocoding_cache(self):
        """Test construction du cache de géocodage."""
        enricher = DataEnricher()
        
        # Mock le fetcher pour éviter les appels API
        mock_result = GeocodingResult(
            original_address="Paris",
            score=0.9,
            latitude=48.8566,
            longitude=2.3522
        )
        
        with patch.object(enricher.geocoder, 'fetch_all') as mock_fetch:
            mock_fetch.return_value = [mock_result]
            
            addresses = ["Paris"]
            cache = enricher.build_geocoding_cache(addresses)
            
            assert len(cache) == 1
            assert "Paris" in cache
            assert cache["Paris"].score == 0.9
    
    def test_enrich_products(self, sample_products):
        """Test l'enrichissement des produits."""
        enricher = DataEnricher()
        
        # Créer un cache mock
        geo_cache = {
            "Carrefour Paris": GeocodingResult(
                original_address="Carrefour Paris",
                label="Carrefour Paris Store",
                score=0.8,
                latitude=48.8566,
                longitude=2.3522,
                city="Paris",
                postal_code="75015"
            ),
            "Leclerc Toulouse": GeocodingResult(
                original_address="Leclerc Toulouse",
                label="Leclerc Toulouse Store",
                score=0.4,  # Score bas
                latitude=43.6045,
                longitude=1.4442,
                city="Toulouse",
                postal_code="31000"
            )
        }
        
        enriched = enricher.enrich_products(sample_products, geo_cache)
        
        assert len(enriched) == 4
        
        # Premier produit avec adresse valide dans le cache
        assert enriched[0]["store_address"] == "Carrefour Paris Store"
        assert enriched[0]["geocoding_score"] == 0.8
        
        # Produit sans adresse
        assert enriched[2].get("store_address") is None
        
        # Vérifier les statistiques
        assert enricher.enrichment_stats["total_processed"] == 4
        assert enricher.enrichment_stats["successfully_enriched"] >= 1
    
    def test_get_stats(self):
        """Test la récupération des statistiques."""
        enricher = DataEnricher()
        stats = enricher.get_stats()
        
        assert isinstance(stats, dict)
        assert "total_processed" in stats
        assert "success_rate" in stats
        assert "geocoder_stats" in stats