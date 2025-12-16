"""Module de transformation et nettoyage."""
import pandas as pd
import numpy as np
from typing import Callable, Optional
from litellm import completion
from dotenv import load_dotenv

from .models import Product

load_dotenv()


class DataTransformer:
    """Transforme et nettoie les données."""

    def __init__(self, df: pd.DataFrame, verbose: bool = True):
        self.df = df.copy()
        self.transformations_applied = []
        self.verbose = verbose

    # def __init__(self, df: pd.DataFrame):
    #     self.df = df.copy()
    #     self.transformations_applied = []

    def remove_duplicates(
        self,
        subset: Optional[list[str]] = None
    ) -> 'DataTransformer':
        """
        Supprime les doublons.
        
        Args:
            subset: Colonnes pour détection de doublons
        
        Returns:
            self (pour chaînage)
        """
        initial = len(self.df)

        if subset is None:
            subset = ['code'] if 'code' in self.df.columns else [self.df.columns[0]]

        self.df = self.df.drop_duplicates(subset=subset, keep='first')
        removed = initial - len(self.df)

        if removed > 0:
            self.transformations_applied.append(f"Doublons supprimés: {removed}")

        return self

    def handle_missing_values(
        self,
        numeric_strategy: str = 'median',
        text_strategy: str = 'unknown',
        categorical_strategy: str = 'unknown'
    ) -> 'DataTransformer':
        """
        Gère les valeurs manquantes.
        
        Args:
            numeric_strategy: 'median', 'mean', 'zero', or None
            text_strategy: valeur de remplacement pour texte
            categorical_strategy: valeur de remplacement pour catégories
        
        Returns:
            self (pour chaînage)
        """
        # Colonnes numériques
        num_cols = self.df.select_dtypes(include=[np.number]).columns
        for col in num_cols:
            null_count = self.df[col].isnull().sum()
            if null_count > 0:
                if numeric_strategy == 'median':
                    fill_value = self.df[col].median()
                elif numeric_strategy == 'mean':
                    fill_value = self.df[col].mean()
                elif numeric_strategy == 'zero':
                    fill_value = 0
                else:
                    fill_value = None

                if fill_value is not None:
                    self.df[col] = self.df[col].fillna(fill_value)
                    self.transformations_applied.append(
                        f"{col}: {null_count} nulls → {fill_value:.2f}"
                    )

        # Colonnes texte
        text_cols = self.df.select_dtypes(include=['object']).columns
        for col in text_cols:
            null_count = self.df[col].isnull().sum()
            if null_count > 0:
                self.df[col] = self.df[col].fillna(text_strategy)
                self.transformations_applied.append(
                    f"{col}: {null_count} nulls → '{text_strategy}'"
                )

        return self

    def normalize_text_columns(
        self,
        columns: Optional[list[str]] = None
    ) -> 'DataTransformer':
        """
        Normalise les colonnes texte (strip, lower).
        
        Args:
            columns: Liste des colonnes à normaliser
        
        Returns:
            self (pour chaînage)
        """
        if columns is None:
            columns = self.df.select_dtypes(include=['object']).columns.tolist()

        for col in columns:
            if col in self.df.columns:
                self.df[col] = (
                    self.df[col]
                    .astype(str)
                    .str.strip()
                    .str.normalize('NFKD')  # Normalise les caractères spéciaux
                    .str.encode('ascii', errors='ignore')
                    .str.decode('ascii')
                    .str.lower()
                )

        self.transformations_applied.append(f"Normalisation texte: {len(columns)} colonnes")
        return self

    def clean_address_column(
        self,
        address_col: str = 'stores',
        min_length: int = 5
    ) -> 'DataTransformer':
        """
        Nettoie les colonnes d'adresses pour améliorer le géocodage.
        
        Args:
            address_col: Colonne contenant les adresses
            min_length: Longueur minimale pour une adresse valide
        
        Returns:
            self (pour chaînage)
        """
        if address_col not in self.df.columns:
            return self

        initial_count = self.df[address_col].notna().sum()

        # Nettoyage basique
        self.df[address_col] = (
            self.df[address_col]
            .astype(str)
            .str.strip()
            .str.replace(r'\s+', ' ', regex=True)  # Espaces multiples
            .str.replace(r'[^\w\s,.-]', '', regex=True)  # Caractères spéciaux
        )

        # Filtrer les adresses trop courtes
        mask = self.df[address_col].str.len() >= min_length
        self.df.loc[~mask, address_col] = None

        cleaned_count = self.df[address_col].notna().sum()
        removed = initial_count - cleaned_count

        if removed > 0:
            self.transformations_applied.append(
                f"Adresses nettoyées: {removed} invalidées (<{min_length} chars)"
            )

        return self

    def filter_outliers(
        self,
        columns: list[str],
        method: str = 'iqr',
        threshold: float = 1.5
    ) -> 'DataTransformer':
        """
        Filtre les outliers.
        
        Args:
            columns: Colonnes à vérifier
            method: 'iqr' ou 'zscore'
            threshold: Seuil pour la détection
        
        Returns:
            self (pour chaînage)
        """
        initial = len(self.df)

        for col in columns:
            if col not in self.df.columns:
                continue

            if method == 'iqr' and self.df[col].notna().sum() > 0:
                Q1 = self.df[col].quantile(0.25)
                Q3 = self.df[col].quantile(0.75)
                IQR = Q3 - Q1

                if IQR > 0:  # Évite division par zéro
                    lower = Q1 - threshold * IQR
                    upper = Q3 + threshold * IQR
                    self.df = self.df[
                        (self.df[col] >= lower) & (self.df[col] <= upper)
                    ]

            elif method == 'zscore' and self.df[col].notna().sum() > 0:
                mean = self.df[col].mean()
                std = self.df[col].std()

                if std > 0:  # Évite division par zéro
                    self.df = self.df[
                        np.abs((self.df[col] - mean) / std) < threshold
                    ]

        removed = initial - len(self.df)
        if removed > 0:
            self.transformations_applied.append(
                f"Outliers filtrés ({method}): {removed}"
            )

        return self
    
    def add_derived_columns(self) -> 'DataTransformer':
        """
        Ajoute des colonnes dérivées.
        
        Returns:
            self (pour chaînage)
        """
        # Catégorie de sucres - VÉRIFIER LE TYPE D'ABORD
        if 'sugars_100g' in self.df.columns:
            try:
                # Convertir en numérique si nécessaire
                if not pd.api.types.is_numeric_dtype(self.df['sugars_100g']):
                    self.df['sugars_100g'] = pd.to_numeric(self.df['sugars_100g'], errors='coerce')
                
                # Créer les catégories uniquement si nous avons des données numériques
                if pd.api.types.is_numeric_dtype(self.df['sugars_100g']):
                    bins = [-float('inf'), 5, 15, 30, float('inf')]
                    labels = ['faible', 'modéré', 'élevé', 'très_élevé']
                    self.df['sugar_category'] = pd.cut(
                        self.df['sugars_100g'],
                        bins=bins,
                        labels=labels
                    )
                    self.transformations_applied.append("Ajout: sugar_category")
                    
            except Exception as e:
                # En cas d'erreur, ignorer cette transformation
                if self.verbose:
                    print(f"⚠️ Impossible d'ajouter sugar_category: {e}")
        
        # Catégorie nutritionnelle simplifiée
        if 'nutriscore_grade' in self.df.columns:
            try:
                # Nettoyer les valeurs
                self.df['nutriscore_grade'] = (
                    self.df['nutriscore_grade']
                    .astype(str)
                    .str.lower()
                    .str.strip()
                )
                
                mapping = {
                    'a': 'excellent',
                    'b': 'bon',
                    'c': 'moyen',
                    'd': 'mauvais',
                    'e': 'très_mauvais'
                }
                
                self.df['nutriscore_simple'] = self.df['nutriscore_grade'].map(mapping)
                self.transformations_applied.append("Ajout: nutriscore_simple")
                
            except Exception as e:
                if self.verbose:
                    print(f"⚠️ Impossible d'ajouter nutriscore_simple: {e}")
        
        # Flag géocodé
        if 'geocoding_score' in self.df.columns:
            try:
                # Convertir en numérique si nécessaire
                if not pd.api.types.is_numeric_dtype(self.df['geocoding_score']):
                    self.df['geocoding_score'] = pd.to_numeric(
                        self.df['geocoding_score'], 
                        errors='coerce'
                    )
                
                self.df['is_geocoded'] = self.df['geocoding_score'] >= 0.5
                self.transformations_applied.append("Ajout: is_geocoded")
                
            except Exception as e:
                if self.verbose:
                    print(f"⚠️ Impossible d'ajouter is_geocoded: {e}")
        
        # Adresse valide (basique)
        if 'stores' in self.df.columns:
            try:
                self.df['has_valid_store'] = (
                    self.df['stores'].notna() &
                    (self.df['stores'].astype(str).str.len() >= 10)
                )
                self.transformations_applied.append("Ajout: has_valid_store")
                
            except Exception as e:
                if self.verbose:
                    print(f"⚠️ Impossible d'ajouter has_valid_store: {e}")
        
        return self
    # def add_derived_columns(self) -> 'DataTransformer':
    #     """
    #     Ajoute des colonnes dérivées.
        
    #     Returns:
    #         self (pour chaînage)
    #     """
    #     # Catégorie de sucres
    #     if 'sugars_100g' in self.df.columns:
    #         bins = [-float('inf'), 5, 15, 30, float('inf')]
    #         labels = ['faible', 'modéré', 'élevé', 'très_élevé']
    #         self.df['sugar_category'] = pd.cut(
    #             self.df['sugars_100g'],
    #             bins=bins,
    #             labels=labels
    #         )
    #         self.transformations_applied.append("Ajout: sugar_category")

    #     # Catégorie nutritionnelle simplifiée
    #     if 'nutriscore_grade' in self.df.columns:
    #         self.df['nutriscore_simple'] = self.df['nutriscore_grade'].map({
    #             'a': 'excellent',
    #             'b': 'bon',
    #             'c': 'moyen',
    #             'd': 'mauvais',
    #             'e': 'très_mauvais'
    #         })
    #         self.transformations_applied.append("Ajout: nutriscore_simple")

    #     # Flag géocodé
    #     if 'geocoding_score' in self.df.columns:
    #         self.df['is_geocoded'] = self.df['geocoding_score'] >= 0.5
    #         self.transformations_applied.append("Ajout: is_geocoded")

    #     # Adresse valide (basique)
    #     if 'stores' in self.df.columns:
    #         self.df['has_valid_store'] = (
    #             self.df['stores'].notna() &
    #             (self.df['stores'].str.len() >= 10)
    #         )
    #         self.transformations_applied.append("Ajout: has_valid_store")

    #     return self

    def get_ai_transformation_suggestions(self) -> str:
        """
        Demande à l'IA des transformations supplémentaires.
        
        Returns:
            Suggestions de code Python
        """
        context = f"""
        Dataset avec {len(self.df)} lignes et {len(self.df.columns)} colonnes.
        Colonnes: {list(self.df.columns)}
        Types: {self.df.dtypes.to_dict()}
        
        Transformations déjà appliquées:
        {self.transformations_applied}
        
        Exemple de données (premières lignes):
        {self.df.head(3).to_string()}
        """

        try:
            response = completion(
                model= "ollama/mistral",#"gemini/gemini-2.0-flash-exp",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Tu es un expert en data engineering. "
                            "Génère du code Python pandas exécutable pour "
                            "améliorer un dataset. Sois concret et précis."
                        )
                    },
                    {
                        "role": "user",
                        "content": (
                            f"{context}\n\n"
                            "Quelles transformations pandas supplémentaires "
                            "recommandes-tu pour ce dataset ? "
                            "Génère uniquement du code Python exécutable, "
                            "sans explications."
                        )
                    }
                ]
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"# Erreur lors de la requête IA: {e}"

    def apply_custom(
        self,
        func: Callable[[pd.DataFrame], pd.DataFrame],
        name: str
    ) -> 'DataTransformer':
        """
        Applique une transformation personnalisée.
        
        Args:
            func: Fonction prenant un DataFrame et retournant un DataFrame
            name: Nom de la transformation
        
        Returns:
            self (pour chaînage)
        """
        self.df = func(self.df)
        self.transformations_applied.append(f"Custom: {name}")
        return self

    def get_result(self) -> pd.DataFrame:
        """
        Retourne le DataFrame transformé.
        
        Returns:
            DataFrame nettoyé
        """
        return self.df.copy()

    def get_summary(self) -> str:
        """
        Retourne un résumé des transformations.
        
        Returns:
            Chaîne de caractères formatée
        """
        if not self.transformations_applied:
            return "Aucune transformation appliquée."

        summary = "Transformations appliquées:\n"
        for i, trans in enumerate(self.transformations_applied, 1):
            summary += f"  {i}. {trans}\n"
        return summary