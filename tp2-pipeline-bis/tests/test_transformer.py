"""Tests pour le transformer."""
import pytest
import pandas as pd
import numpy as np
from pipeline.transformer import DataTransformer


class TestDataTransformer:
    """Tests pour DataTransformer."""
    
    @pytest.fixture
    def sample_df(self):
        """DataFrame de test."""
        return pd.DataFrame({
            'code': ['001', '002', '003', '001', '005'],
            'product_name': ['  Chocolat Noir  ', None, 'Chocolat Au Lait', 'Chocolat Noir', 'Chocolat Blanc'],
            'brands': ['Lindt', 'Lindt', 'Milka', 'Lindt', None],
            'categories': ['chocolats', 'chocolats', 'chocolats', 'chocolats', 'chocolats'],
            'nutriscore_grade': ['A', 'B', 'C', 'A', None],
            'energy_100g': [500.0, None, 450.0, 500.0, 600.0],
            'sugars_100g': [40.0, 35.0, 50.0, 40.0, 100.0],
            'stores': ['Carrefour Paris', '  Leclerc Toulouse  ', None, 'Carrefour Paris', 'Super U'],
            'geocoding_score': [0.85, 0.45, 0.92, 0.85, 0.1]
        })
    
    def test_init(self):
        """Test l'initialisation."""
        df = pd.DataFrame({'col': [1, 2, 3]})
        transformer = DataTransformer(df)
        assert len(transformer.df) == 3
        assert transformer.verbose is True
        assert transformer.transformations_applied == []
    
    def test_remove_duplicates(self, sample_df):
        """Test la suppression des doublons."""
        transformer = DataTransformer(sample_df)
        result = transformer.remove_duplicates(['code']).get_result()
        
        assert len(result) == 4  # Un doublon supprimé
        assert result['code'].nunique() == 4
        assert 'Doublons supprimés' in transformer.transformations_applied[0]
    
    def test_handle_missing_values_median(self, sample_df):
        """Test le remplacement par la médiane."""
        transformer = DataTransformer(sample_df, verbose=False)
        result = transformer.handle_missing_values(numeric_strategy='median').get_result()
        
        # Vérifier que energy_100g n'a plus de nulls
        assert result['energy_100g'].isnull().sum() == 0
        # La médiane devrait être 500.0
        assert result.loc[1, 'energy_100g'] == 500.0
    
    def test_handle_missing_values_text(self, sample_df):
        """Test le remplacement des valeurs texte manquantes."""
        transformer = DataTransformer(sample_df, verbose=False)
        result = transformer.handle_missing_values(text_strategy='unknown').get_result()
        
        # Vérifier que product_name a 'unknown' pour les nulls
        assert result.loc[1, 'product_name'] == 'unknown'
        assert result.loc[4, 'brands'] == 'unknown'
    
    def test_normalize_text_columns(self, sample_df):
        """Test la normalisation du texte."""
        transformer = DataTransformer(sample_df, verbose=False)
        result = transformer.normalize_text_columns(['product_name', 'brands']).get_result()
        
        # Vérifier que les espaces sont supprimés et en minuscules
        assert 'chocolat noir' in result['product_name'].values
        assert 'lindt' in result['brands'].values
    
    def test_clean_address_column(self, sample_df):
        """Test le nettoyage des adresses."""
        transformer = DataTransformer(sample_df, verbose=False)
        result = transformer.clean_address_column('stores', min_length=5).get_result()
        
        # Vérifier que les espaces multiples sont supprimés
        assert 'Leclerc Toulouse' in result['stores'].values
        # L'adresse None devrait être inchangée
        assert pd.isna(result.loc[2, 'stores'])
    
    # def test_add_derived_columns(self, sample_df):
    #     """Test l'ajout de colonnes dérivées."""
    #     transformer = DataTransformer(sample_df, verbose=False)
    #     result = transformer.add_derived_columns().get_result()
        
    #     # Vérifier les nouvelles colonnes
    #     assert 'sugar_category' in result.columns
    #     assert 'nutriscore_simple' in result.columns
    #     assert 'is_geocoded' in result.columns
    #     assert 'has_valid_store' in result.columns
        
    #     # Vérifier les valeurs
    #     assert result.loc[0, 'is_geocoded'] is True  # score 0.85 > 0.5
    #     assert result.loc[4, 'is_geocoded'] is False  # score 0.1 < 0.5
    
    def test_filter_outliers_iqr(self, sample_df):
        """Test le filtrage des outliers avec IQR."""
        transformer = DataTransformer(sample_df, verbose=False)
        initial_len = len(sample_df)
        
        result = transformer.filter_outliers(['sugars_100g'], method='iqr').get_result()
        
        # sugars_100g = 100 est un outlier, devrait être filtré
        assert len(result) < initial_len
        assert 100 not in result['sugars_100g'].values
    
    def test_chaining(self, sample_df):
        """Test le chaînage des transformations."""
        transformer = DataTransformer(sample_df, verbose=False)
        result = (
            transformer
            .remove_duplicates(['code'])
            .handle_missing_values(numeric_strategy='median')
            .normalize_text_columns(['product_name'])
            .get_result()
        )
        
        assert len(transformer.transformations_applied) >= 3
        assert 'Doublons supprimés' in transformer.transformations_applied[0]
    
    def test_get_summary(self, sample_df):
        """Test le résumé des transformations."""
        transformer = DataTransformer(sample_df, verbose=False)
        transformer.remove_duplicates()
        
        summary = transformer.get_summary()
        assert isinstance(summary, str)
        assert 'Doublons supprimés' in summary
    
    # def test_get_result_is_copy(self, sample_df):
    #     """Test que get_result retourne une copie."""
    #     transformer = DataTransformer(sample_df)
    #     result1 = transformer.get_result()
    #     result2 = transformer.get_result()
        
    #     # Modifier result1 ne devrait pas affecter result2
    #     result1.loc[0, 'code'] = '999'
    #     assert result2.loc[0, 'code'] == '001'

    def test_add_derived_columns(self, sample_df):
        """Test l'ajout de colonnes dérivées."""
        transformer = DataTransformer(sample_df, verbose=False)
        result = transformer.add_derived_columns().get_result()
        
        # Vérifier les nouvelles colonnes
        assert 'sugar_category' in result.columns
        assert 'nutriscore_simple' in result.columns
        assert 'is_geocoded' in result.columns
        assert 'has_valid_store' in result.columns
        
        # Vérifier les valeurs - utiliser bool() pour numpy boolean
        assert bool(result.loc[0, 'is_geocoded']) == True  # score 0.85 > 0.5
        assert bool(result.loc[4, 'is_geocoded']) == False  # score 0.1 < 0.5
    
    def test_get_result_is_copy(self, sample_df):
        """Test que get_result retourne une copie."""
        transformer = DataTransformer(sample_df)
        result1 = transformer.get_result()
        result2 = transformer.get_result()
        
        # Vérifier que ce sont des copies distinctes
        assert result1 is not result2
        assert result1.equals(result2)  # Mêmes données au début
        
        # Modifier result1
        result1.loc[0, 'code'] = '999'
        
        # Vérifier que result2 est inchangé
        assert result2.loc[0, 'code'] == '001'
        
        # Vérifier que le DataFrame interne n'est pas modifié
        assert transformer.df.loc[0, 'code'] == '001'