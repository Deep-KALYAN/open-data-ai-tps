"""Module de scoring et rapport de qualité."""
import pandas as pd
from datetime import datetime
from pathlib import Path
import json
from typing import Optional
from .ai_helper import AIHelper
from dotenv import load_dotenv

from .config import QUALITY_THRESHOLDS, REPORTS_DIR
from .models import QualityMetrics

load_dotenv()


class QualityAnalyzer:
    """Analyse et score la qualité des données."""

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.metrics: Optional[QualityMetrics] = None

    def calculate_completeness(self) -> float:
        """Calcule le score de complétude (% de valeurs non-nulles)."""
        if self.df.empty:
            return 0.0

        total_cells = self.df.size
        non_null_cells = self.df.notna().sum().sum()
        return non_null_cells / total_cells

    def count_duplicates(self, id_columns: Optional[list[str]] = None) -> tuple[int, float]:
        """Compte les doublons."""
        if self.df.empty:
            return 0, 0.0

        if id_columns is None:
            # Trouver automatiquement les colonnes d'ID
            possible_ids = ['code', 'id', 'product_id', 'siret', 'uuid']
            id_columns = [col for col in possible_ids if col in self.df.columns]
            
            if not id_columns:
                id_columns = [self.df.columns[0]]  # Fallback: première colonne

        if not id_columns:
            return 0, 0.0

        # Compter les doublons
        duplicates = self.df.duplicated(subset=id_columns).sum()
        pct = (duplicates / len(self.df)) * 100 if len(self.df) > 0 else 0.0

        return duplicates, pct

    def calculate_geocoding_stats(self) -> tuple[float, float]:
        """Calcule les stats de géocodage si applicable."""
        if self.df.empty or 'geocoding_score' not in self.df.columns:
            return 0.0, 0.0

        valid_geo = self.df['geocoding_score'].notna() & (self.df['geocoding_score'] >= 0.5)
        
        if len(self.df) == 0:
            return 0.0, 0.0

        success_rate = (valid_geo.sum() / len(self.df)) * 100
        
        if valid_geo.any():
            avg_score = self.df.loc[valid_geo, 'geocoding_score'].mean()
        else:
            avg_score = 0.0

        return success_rate, avg_score

    def calculate_null_counts(self) -> dict:
        """Compte les valeurs nulles par colonne."""
        if self.df.empty:
            return {}

        null_counts = self.df.isnull().sum().to_dict()
        
        # Ajouter les pourcentages
        null_pct = {}
        for col, count in null_counts.items():
            pct = (count / len(self.df)) * 100 if len(self.df) > 0 else 0.0
            null_pct[col] = {
                'count': count,
                'pct': round(pct, 2)
            }
        
        return null_pct

    def determine_quality_grade(
        self,
        completeness: float,
        duplicates_pct: float,
        geo_rate: float
    ) -> str:
        """Détermine la note de qualité globale (A-F)."""
        score = 0.0

        # Complétude (40 points max)
        score += min(completeness * 40, 40)

        # Doublons (30 points max)
        if duplicates_pct <= 1:
            score += 30
        elif duplicates_pct <= 5:
            score += 20
        elif duplicates_pct <= 10:
            score += 10
        # > 10: 0 points

        # Géocodage (30 points max) - si applicable
        if 'geocoding_score' in self.df.columns:
            score += min(geo_rate / 100 * 30, 30)
        else:
            score += 30  # Pas de pénalité si pas de géocodage

        # Note finale
        if score >= 90:
            return 'A'
        elif score >= 75:
            return 'B'
        elif score >= 60:
            return 'C'
        elif score >= 40:
            return 'D'
        else:
            return 'F'
        
    def generate_ai_recommendations(self) -> str:
        """
        Génère des recommandations via l'IA.
        Si l'IA n'est pas disponible, retourne des recommandations standard.
        """
        if not self.metrics:
            self.analyze()
        
        # Créer le contexte
        context = f"""
        Analyse de qualité d'un dataset :
        - Total enregistrements: {self.metrics.total_records}
        - Enregistrements valides: {self.metrics.valid_records}
        - Score de complétude: {self.metrics.completeness_score * 100:.1f}%
        - Taux de doublons: {self.metrics.duplicates_pct:.1f}%
        - Géocodage réussi: {self.metrics.geocoding_success_rate:.1f}%
        - Score géocodage moyen: {self.metrics.avg_geocoding_score:.2f}
        - Note globale: {self.metrics.quality_grade}
        
        Valeurs manquantes par colonne:
        {json.dumps(self.metrics.null_counts, indent=2, ensure_ascii=False)}
        
        Veuillez donner 5 recommandations concrètes et actionnables pour améliorer ce dataset.
        Formatez en Markdown avec des listes à puces.
        """
        
        # Essayer l'IA
        ai_helper = AIHelper()
        ai_response = ai_helper.get_recommendations(context)
        
        if ai_response:
            # Nettoyer la réponse si nécessaire
            ai_response = ai_response.strip()
            if not ai_response.startswith("#"):
                ai_response = f"## 🤖 Recommandations IA\n\n{ai_response}"
            return ai_response
        else:
            # Fallback aux recommandations standards
            return self._generate_standard_recommendations()

    # def generate_ai_recommendations(self) -> str:
    #     """
    #     Génère des recommandations via l'IA.
    #     Si l'IA n'est pas disponible, retourne des recommandations standard.
    #     """
    #     if not self.metrics:
    #         self.analyze()

    #     try:
    #         # Tenter d'importer litellm
    #         from litellm import completion
            
    #         context = f"""
    #         Analyse de qualité d'un dataset :
    #         - Total: {self.metrics.total_records} enregistrements
    #         - Valides: {self.metrics.valid_records} enregistrements
    #         - Complétude: {self.metrics.completeness_score * 100:.1f}%
    #         - Doublons: {self.metrics.duplicates_pct:.1f}%
    #         - Géocodage réussi: {self.metrics.geocoding_success_rate:.1f}%
    #         - Note globale: {self.metrics.quality_grade}
    #         """
            
    #         response = completion(
    #             model="gemini/gemini-2.0-flash-exp",
    #             messages=[
    #                 {
    #                     "role": "system",
    #                     "content": (
    #                         "Tu es un expert en qualité des données. "
    #                         "Donne des recommandations concrètes, actionnables et professionnelles. "
    #                         "Formate en markdown avec des listes à puces."
    #                     )
    #                 },
    #                 {
    #                     "role": "user",
    #                     "content": (
    #                         f"{context}\n\n"
    #                         "Quelles sont tes 5 recommandations prioritaires "
    #                         "pour améliorer ce dataset ?"
    #                     )
    #                 }
    #             ]
    #         )
            
    #         return response.choices[0].message.content
            
    #     except Exception:
    #         # Fallback: recommandations standards
    #         return self._generate_standard_recommendations()

    def _generate_standard_recommendations(self) -> str:
        """Génère des recommandations standards sans IA."""
        if not self.metrics:
            self.analyze()

        recommendations = []
        
        # 1. Complétude
        if self.metrics.completeness_score < QUALITY_THRESHOLDS['completeness_min']:
            recommendations.append(
                "**Améliorer la complétude** : Les données contiennent trop de valeurs manquantes. "
                "Considérer des sources supplémentaires ou des techniques d'imputation."
            )
        
        # 2. Doublons
        if self.metrics.duplicates_pct > QUALITY_THRESHOLDS['duplicates_max_pct']:
            recommendations.append(
                "**Supprimer les doublons** : Plus de 5% des enregistrements sont des doublons. "
                "Implémenter une vérification des doublons avant l'insertion."
            )
        
        # 3. Géocodage
        if 'geocoding_score' in self.df.columns:
            if self.metrics.geocoding_success_rate < 50:
                recommendations.append(
                    "**Améliorer le géocodage** : Le taux de succès est faible. "
                    "Nettoyer les adresses avant géocodage ou utiliser un service plus performant."
                )
        
        # 4. Colonnes avec trop de nulls
        null_counts = self.calculate_null_counts()
        for col, stats in null_counts.items():
            if stats['pct'] > 30:  # > 30% de nulls
                recommendations.append(
                    f"**Colonne '{col}'** : {stats['pct']}% de valeurs manquantes. "
                    "Évaluer si cette colonne est nécessaire ou si elle peut être enrichie."
                )
        
        # 5. Recommandation générale
        if not recommendations:
            recommendations.append(
                "**Maintenir la qualité** : Le dataset est de bonne qualité. "
                "Continuer à surveiller les métriques et implémenter des contrôles automatisés."
            )
        
        # Formater en markdown
        markdown = "## Recommandations pour améliorer la qualité des données\n\n"
        for i, rec in enumerate(recommendations[:5], 1):
            markdown += f"{i}. {rec}\n\n"
        
        return markdown

    def analyze(self) -> QualityMetrics:
        """Effectue l'analyse complète de qualité."""
        # Calculer les métriques
        completeness = self.calculate_completeness()
        duplicates, duplicates_pct = self.count_duplicates()
        geo_rate, geo_avg = self.calculate_geocoding_stats()
        null_counts = self.calculate_null_counts()
        
        # Compter les enregistrements valides
        valid_records = len(self.df) - duplicates
        
        # Déterminer la note
        grade = self.determine_quality_grade(
            completeness,
            duplicates_pct,
            geo_rate
        )
        
        # Créer l'objet QualityMetrics
        self.metrics = QualityMetrics(
            total_records=len(self.df),
            valid_records=valid_records,
            completeness_score=round(completeness, 3),
            duplicates_count=duplicates,
            duplicates_pct=round(duplicates_pct, 2),
            geocoding_success_rate=round(geo_rate, 2),
            avg_geocoding_score=round(geo_avg, 3),
            null_counts=null_counts,
            quality_grade=grade,
        )
        
        return self.metrics

    def generate_report(
        self,
        output_name: str = "quality_report",
        include_ai: bool = True
    ) -> Path:
        """
        Génère un rapport de qualité complet en Markdown.
        
        Args:
            output_name: Nom du fichier (sans extension)
            include_ai: Inclure les recommandations IA
        
        Returns:
            Chemin du fichier généré
        """
        if not self.metrics:
            self.analyze()

        # Générer les recommandations
        if include_ai:
            try:
                recommendations = self.generate_ai_recommendations()
            except Exception:
                recommendations = self._generate_standard_recommendations()
        else:
            recommendations = self._generate_standard_recommendations()

        # Construire le rapport
        report = f"""# 📊 Rapport de Qualité des Données

**Généré le** : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Dataset** : {output_name}
**Nombre d'enregistrements** : {self.metrics.total_records}

---

## 📈 Métriques Globales

| Métrique | Valeur | Seuil Recommandé | Statut |
|----------|--------|------------------|--------|
| **Note globale** | **{self.metrics.quality_grade}** | A-B-C | {"✅ Acceptable" if self.metrics.is_acceptable else "⚠️ Nécessite attention"} |
| Enregistrements valides | {self.metrics.valid_records} | - | - |
| Score de complétude | {self.metrics.completeness_score * 100:.1f}% | ≥ 70% | {"✅" if self.metrics.completeness_score >= QUALITY_THRESHOLDS['completeness_min'] else "⚠️"} |
| Taux de doublons | {self.metrics.duplicates_pct:.1f}% | ≤ 5% | {"✅" if self.metrics.duplicates_pct <= QUALITY_THRESHOLDS['duplicates_max_pct'] else "⚠️"} |
| Géocodage réussi | {self.metrics.geocoding_success_rate:.1f}% | ≥ 50% | {"✅" if self.metrics.geocoding_success_rate >= 50 else "⚠️"} |
| Score géocodage moyen | {self.metrics.avg_geocoding_score:.2f} | ≥ 0.5 | {"✅" if self.metrics.avg_geocoding_score >= QUALITY_THRESHOLDS['geocoding_score_min'] else "⚠️"} |

---

## 📋 Analyse des Valeurs Manquantes

| Colonne | Valeurs nulles | % | Priorité |
|---------|----------------|---|----------|
"""
        
        # Trier par pourcentage décroissant
        sorted_nulls = sorted(
            self.metrics.null_counts.items(),
            key=lambda x: x[1]['pct'],
            reverse=True
        )
        
        for col, stats in sorted_nulls:
            pct = stats['pct']
            priority = "🔴 Haute" if pct > 30 else "🟡 Moyenne" if pct > 10 else "🟢 Basse"
            report += f"| {col} | {stats['count']} | {pct:.1f}% | {priority} |\n"

        report += f"""

---

## 🎯 Conclusion Qualité

**Verdict** : {"✅ **Dataset acceptable** pour l'analyse." if self.metrics.is_acceptable else "⚠️ **Dataset nécessite des corrections** avant utilisation."}

**Score final** : {self.metrics.quality_grade} (sur une échelle A-F)

---

{recommendations}

---

*Rapport généré automatiquement par le pipeline Open Data*
*Date : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        # Sauvegarder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{output_name}_{timestamp}.md"
        filepath = REPORTS_DIR / filename
        
        # Assurer que le dossier existe
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Écrire le fichier
        filepath.write_text(report, encoding='utf-8')
        
        print(f"📄 Rapport sauvegardé : {filepath}")
        print(f"   - Note qualité: {self.metrics.quality_grade}")
        print(f"   - Taille: {len(report.splitlines())} lignes")
        
        return filepath