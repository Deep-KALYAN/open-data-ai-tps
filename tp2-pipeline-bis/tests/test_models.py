"""Tests pour les modèles Pydantic."""
import pytest
from datetime import datetime
from pipeline.models import Product, GeocodingResult, QualityMetrics


class TestProductModel:
    """Tests pour le modèle Product."""
    
    def test_create_product_valid(self):
        """Test création d'un produit valide."""
        product = Product(
            code="1234567890123",
            product_name="Chocolat Noir",
            brands="Lindt",
            categories="chocolats",
            nutriscore_grade="A",
            nova_group=4,
            energy_100g=500.0,
            sugars_100g=40.0
        )
        
        assert product.code == "1234567890123"
        assert product.product_name == "Chocolat Noir"
        assert product.nutriscore_grade == "a"  # Converti en minuscule
        assert isinstance(product.fetched_at, datetime)
    
    def test_nutriscore_validation_valid(self):
        """Test validation des notes NutriScore valides."""
        for grade in ['A', 'B', 'C', 'D', 'E', 'a', 'b', 'c', 'd', 'e']:
            product = Product(code="123", nutriscore_grade=grade)
            assert product.nutriscore_grade == grade.lower()
    
    def test_nutriscore_validation_invalid(self):
        """Test validation des notes NutriScore invalides."""
        product = Product(code="123", nutriscore_grade="F")
        assert product.nutriscore_grade is None
    
    def test_positive_values_validation(self):
        """Test validation des valeurs positives."""
        product = Product(
            code="123",
            energy_100g=-100,  # Valeur négative
            sugars_100g=50
        )
        
        assert product.energy_100g is None  # Devrait être None
        assert product.sugars_100g == 50    # Devrait rester 50
    
    def test_enrichment_fields(self):
        """Test des champs d'enrichissement."""
        product = Product(
            code="123",
            store_address="Carrefour Paris",
            latitude=48.8566,
            longitude=2.3522,
            city="Paris",
            postal_code="75015",
            geocoding_score=0.8
        )
        
        assert product.city == "Paris"
        assert product.geocoding_score == 0.8


class TestGeocodingResultModel:
    """Tests pour le modèle GeocodingResult."""
    
    def test_create_geocoding_result(self):
        """Test création d'un résultat de géocodage."""
        result = GeocodingResult(
            original_address="20 avenue de ségur Paris",
            label="20 Avenue de Ségur, 75007 Paris",
            latitude=48.8566,
            longitude=2.3522,
            score=0.9,
            postal_code="75007",
            city_code="75107",
            city="Paris"
        )
        
        assert result.original_address == "20 avenue de ségur Paris"
        assert result.score == 0.9
        assert result.is_valid is True
    
    def test_is_valid_property(self):
        """Test de la propriété is_valid."""
        # Score >= 0.5 et coordonnées non nulles = valide
        result1 = GeocodingResult(
            original_address="test",
            score=0.6,
            latitude=48.0,
            longitude=2.0
        )
        assert result1.is_valid is True
        
        # Score < 0.5 = invalide
        result2 = GeocodingResult(
            original_address="test",
            score=0.4,
            latitude=48.0,
            longitude=2.0
        )
        assert result2.is_valid is False
        
        # Coordonnées nulles = invalide
        result3 = GeocodingResult(
            original_address="test",
            score=0.8,
            latitude=None,
            longitude=2.0
        )
        assert result3.is_valid is False
    
    def test_default_values(self):
        """Test des valeurs par défaut."""
        result = GeocodingResult(original_address="test")
        
        assert result.score == 0.0
        assert result.label is None
        assert result.latitude is None
        assert result.longitude is None


class TestQualityMetricsModel:
    """Tests pour le modèle QualityMetrics."""
    
    def test_create_quality_metrics(self):
        """Test création de métriques de qualité."""
        metrics = QualityMetrics(
            total_records=1000,
            valid_records=950,
            completeness_score=0.85,
            duplicates_count=50,
            duplicates_pct=5.0,
            geocoding_success_rate=60.0,
            avg_geocoding_score=0.7,
            null_counts={"col1": 10, "col2": 5},
            quality_grade="B"
        )
        
        assert metrics.total_records == 1000
        assert metrics.valid_records == 950
        assert metrics.completeness_score == 0.85
        assert metrics.quality_grade == "B"
    
    def test_is_acceptable_property(self):
        """Test de la propriété is_acceptable."""
        # Notes acceptables
        for grade in ['A', 'B', 'C']:
            metrics = QualityMetrics(
                total_records=100,
                valid_records=100,
                completeness_score=1.0,
                duplicates_count=0,
                duplicates_pct=0.0,
                geocoding_success_rate=100.0,
                avg_geocoding_score=1.0,
                null_counts={},
                quality_grade=grade
            )
            assert metrics.is_acceptable is True
        
        # Notes inacceptables
        for grade in ['D', 'F']:
            metrics = QualityMetrics(
                total_records=100,
                valid_records=100,
                completeness_score=1.0,
                duplicates_count=0,
                duplicates_pct=0.0,
                geocoding_success_rate=100.0,
                avg_geocoding_score=1.0,
                null_counts={},
                quality_grade=grade
            )
            assert metrics.is_acceptable is False