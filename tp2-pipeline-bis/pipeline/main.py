#!/usr/bin/env python3
"""Script principal du pipeline."""
import argparse
import sys
from datetime import datetime
from pathlib import Path
import pandas as pd
import traceback

from .fetchers.openfoodfacts import OpenFoodFactsFetcher
from .enricher import DataEnricher
from .transformer import DataTransformer
from .quality import QualityAnalyzer
from .storage import save_raw_json, save_parquet
from .config import MAX_ITEMS


class PipelineOrchestrator:
    """Orchestrateur du pipeline complet."""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.stats = {
            "start_time": None,
            "end_time": None,
            "duration_seconds": 0,
            "success": False,
            "error": None,
            "stages": {}
        }
    
    def log(self, message: str, level: str = "INFO"):
        """Journalisation conditionnelle."""
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S")
            prefix = {
                "INFO": "ℹ️",
                "SUCCESS": "✅",
                "WARNING": "⚠️",
                "ERROR": "❌",
                "STEP": "🚀"
            }.get(level, "📝")
            print(f"{prefix} [{timestamp}] {message}")
    
    def run_pipeline(
        self,
        category: str,
        max_items: int = MAX_ITEMS,
        skip_enrichment: bool = False,
        skip_ai: bool = False,
        partition_by: str = None
    ) -> dict:
        """
        Exécute le pipeline complet.
        
        Args:
            category: Catégorie de produits (ex: "chocolats")
            max_items: Nombre maximum d'items à récupérer
            skip_enrichment: Passer l'enrichissement géocodage
            skip_ai: Ne pas utiliser l'IA pour les recommandations
            partition_by: Colonne pour partitionnement Parquet
        
        Returns:
            Statistiques du pipeline
        """
        self.stats["start_time"] = datetime.now()
        self.stats["category"] = category
        self.stats["max_items"] = max_items
        
        try:
            self._print_header(category)
            
            # === ÉTAPE 1 : Acquisition ===
            products = self._stage_1_acquisition(category, max_items)
            if not products:
                raise ValueError("Aucun produit récupéré")
            
            # === ÉTAPE 2 : Enrichissement ===
            if not skip_enrichment:
                products = self._stage_2_enrichment(products)
            else:
                self.log("Enrichissement ignoré (option --skip-enrichment)", "WARNING")
            
            # === ÉTAPE 3 : Transformation ===
            df_clean = self._stage_3_transformation(products)
            
            # === ÉTAPE 4 : Qualité ===
            quality_grade = self._stage_4_quality(df_clean, skip_ai)
            
            # === ÉTAPE 5 : Stockage ===
            output_path = self._stage_5_storage(df_clean, category, partition_by)
            
            # === SUCCÈS ===
            self.stats["success"] = True
            self.stats["output_path"] = str(output_path)
            self.stats["quality_grade"] = quality_grade
            
            self._print_footer()
            
            return self.stats
            
        except Exception as e:
            self.stats["success"] = False
            self.stats["error"] = str(e)
            self.log(f"Erreur du pipeline: {e}", "ERROR")
            
            if self.verbose:
                traceback.print_exc()
            
            return self.stats
    
    def _print_header(self, category: str):
        """Affiche l'en-tête du pipeline."""
        print("\n" + "="*70)
        print("🚀 PIPELINE OPEN DATA - PRODUCTION".center(70))
        print("="*70)
        print(f"📁 Catégorie: {category}")
        print(f"⏰ Début: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70 + "\n")
    
    def _stage_1_acquisition(self, category: str, max_items: int) -> list[dict]:
        """Étape 1: Acquisition des données."""
        self.log(f"ÉTAPE 1: Acquisition depuis OpenFoodFacts", "STEP")
        
        fetcher = OpenFoodFactsFetcher()
        products = list(fetcher.fetch_all(category, max_items, self.verbose))
        
        if not products:
            raise ValueError(f"Aucun produit trouvé pour la catégorie '{category}'")
        
        # Sauvegarde des données brutes
        json_path = save_raw_json(products, f"{category}_raw")
        
        self.stats["stages"]["acquisition"] = {
            "products_fetched": len(products),
            "raw_json_path": str(json_path),
            "fetcher_stats": fetcher.get_stats()
        }
        
        self.log(f"✅ {len(products)} produits récupérés", "SUCCESS")
        self.log(f"💾 Données brutes: {json_path.name}", "INFO")
        
        return products
    
    def _stage_2_enrichment(self, products: list[dict]) -> list[dict]:
        """Étape 2: Enrichissement par géocodage."""
        self.log("ÉTAPE 2: Enrichissement (géocodage des magasins)", "STEP")
        
        enricher = DataEnricher()
        
        # Extraire les adresses uniques
        addresses = enricher.extract_addresses(products, "stores")
        
        if not addresses:
            self.log("⚠️ Aucune adresse trouvée dans les produits", "WARNING")
            return products
        
        self.log(f"📍 {len(addresses)} adresses uniques extraites", "INFO")
        
        # Limiter à 50 adresses pour éviter les dépassements de quota
        max_addresses = min(50, len(addresses))
        if len(addresses) > max_addresses:
            self.log(f"⚠️ Limité à {max_addresses} adresses (performance)", "WARNING")
            addresses = addresses[:max_addresses]
        
        # Construire le cache de géocodage
        geo_cache = enricher.build_geocoding_cache(addresses)
        
        # Enrichir les produits
        enriched_products = enricher.enrich_products(products, geo_cache, "stores")
        
        self.stats["stages"]["enrichment"] = enricher.get_stats()
        
        success_rate = self.stats["stages"]["enrichment"].get("success_rate", 0)
        self.log(f"✅ Enrichissement terminé (taux de succès: {success_rate:.1f}%)", "SUCCESS")
        
        return enriched_products
    
    def _stage_3_transformation(self, products: list[dict]) -> pd.DataFrame:
        """Étape 3: Transformation et nettoyage."""
        self.log("ÉTAPE 3: Transformation et nettoyage", "STEP")
        
        df = pd.DataFrame(products)
        
        transformer = DataTransformer(df, verbose=self.verbose)
        df_clean = (
            transformer
            .remove_duplicates(['code'])
            .handle_missing_values(
                numeric_strategy='median',
                text_strategy='inconnu'
            )
            .clean_address_column('stores', min_length=5)
            .normalize_text_columns(['product_name', 'brands', 'categories', 'stores'])
            .add_derived_columns()
            .get_result()
        )
        
        self.stats["stages"]["transformation"] = {
            "initial_rows": len(df),
            "final_rows": len(df_clean),
            "transformations_applied": transformer.transformations_applied,
            "columns_added": [col for col in df_clean.columns if col not in df.columns]
        }
        
        self.log(f"✅ Transformation terminée", "SUCCESS")
        self.log(f"   Lignes: {len(df)} → {len(df_clean)}", "INFO")
        self.log(f"   Colonnes: {len(df.columns)} → {len(df_clean.columns)}", "INFO")
        
        # Afficher un résumé des transformations
        if self.verbose and transformer.transformations_applied:
            print("   📋 Transformations appliquées:")
            for trans in transformer.transformations_applied[:5]:  # Limiter à 5
                print(f"     • {trans}")
            if len(transformer.transformations_applied) > 5:
                print(f"     • ... et {len(transformer.transformations_applied) - 5} autres")
        
        return df_clean
    
    def _stage_4_quality(self, df_clean: pd.DataFrame, skip_ai: bool) -> str:
        """Étape 4: Analyse de qualité."""
        self.log("ÉTAPE 4: Analyse de qualité", "STEP")
        
        analyzer = QualityAnalyzer(df_clean)
        metrics = analyzer.analyze()
        
        # Générer le rapport
        report_path = analyzer.generate_report(
            output_name=f"{self.stats['category']}_quality",
            include_ai=not skip_ai
        )
        
        self.stats["stages"]["quality"] = {
            "metrics": metrics.dict(),
            "report_path": str(report_path),
            "is_acceptable": metrics.is_acceptable
        }
        
        self.log(f"✅ Analyse de qualité terminée", "SUCCESS")
        self.log(f"   Note: {metrics.quality_grade}", "INFO")
        self.log(f"   Acceptable: {'✅ Oui' if metrics.is_acceptable else '❌ Non'}", "INFO")
        self.log(f"   Rapport: {report_path.name}", "INFO")
        
        return metrics.quality_grade
    
    def _stage_5_storage(
        self,
        df_clean: pd.DataFrame,
        category: str,
        partition_by: str
    ) -> Path:
        """Étape 5: Stockage final."""
        self.log("ÉTAPE 5: Stockage final (Parquet)", "STEP")
        
        output_path = save_parquet(df_clean, category, partition_by=partition_by)
        
        self.stats["stages"]["storage"] = {
            "output_path": str(output_path),
            "format": "parquet",
            "partition_by": partition_by,
            "rows": len(df_clean),
            "columns": len(df_clean.columns)
        }
        
        self.log(f"✅ Stockage terminé", "SUCCESS")
        self.log(f"   Fichier: {output_path}", "INFO")
        
        return output_path
    
    def _print_footer(self):
        """Affiche le pied de page avec les résultats."""
        self.stats["end_time"] = datetime.now()
        self.stats["duration_seconds"] = (
            self.stats["end_time"] - self.stats["start_time"]
        ).seconds
        
        duration = self.stats["duration_seconds"]
        category = self.stats["category"]
        quality_grade = self.stats.get("quality_grade", "N/A")
        output_path = self.stats.get("output_path", "N/A")
        
        print("\n" + "="*70)
        print("✅ PIPELINE TERMINÉ AVEC SUCCÈS".center(70))
        print("="*70)
        print(f"📊 Résultats:")
        print(f"   • Catégorie: {category}")
        print(f"   • Durée totale: {duration} secondes")
        print(f"   • Note qualité: {quality_grade}")
        print(f"   • Fichier de sortie: {output_path}")
        
        # Résumé par étape
        print(f"\n📈 Résumé des étapes:")
        stages = self.stats.get("stages", {})
        
        if "acquisition" in stages:
            acq = stages["acquisition"]
            print(f"   1. 📥 Acquisition: {acq.get('products_fetched', 0)} produits")
        
        if "enrichment" in stages:
            enrich = stages["enrichment"]
            success_rate = enrich.get("success_rate", 0)
            print(f"   2. 🌍 Enrichissement: {success_rate:.1f}% de succès")
        
        if "transformation" in stages:
            trans = stages["transformation"]
            print(f"   3. 🔧 Transformation: {trans.get('initial_rows', 0)} → {trans.get('final_rows', 0)} lignes")
        
        if "quality" in stages:
            quality = stages["quality"]
            metrics = quality.get("metrics", {})
            print(f"   4. 📊 Qualité: Note {metrics.get('quality_grade', 'N/A')}")
        
        if "storage" in stages:
            storage = stages["storage"]
            print(f"   5. 💾 Stockage: {storage.get('rows', 0)} lignes dans Parquet")
        
        print("="*70)


def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description="Pipeline Open Data - Acquisition, enrichissement et qualité",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  %(prog)s --category chocolats
  %(prog)s --category biscuits --max-items 200 --skip-enrichment
  %(prog)s --category boissons --partition-by categories --verbose
        """
    )
    
    parser.add_argument(
        "--category", "-c",
        default="chocolats",
        help="Catégorie de produits (ex: chocolats, biscuits, boissons)"
    )
    
    parser.add_argument(
        "--max-items", "-m",
        type=int,
        default=MAX_ITEMS,
        help=f"Nombre maximum d'items à récupérer (défaut: {MAX_ITEMS})"
    )
    
    parser.add_argument(
        "--skip-enrichment", "-s",
        action="store_true",
        help="Ignorer l'enrichissement géocodage (plus rapide)"
    )
    
    parser.add_argument(
        "--skip-ai",
        action="store_true",
        help="Ne pas utiliser l'IA pour les recommandations"
    )
    
    parser.add_argument(
        "--partition-by",
        help="Colonne pour partitionnement Parquet (ex: 'categories')"
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Mode silencieux (moins de sortie)"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="Pipeline Open Data v1.0.0"
    )
    
    args = parser.parse_args()
    
    # Exécuter le pipeline
    orchestrator = PipelineOrchestrator(verbose=not args.quiet)
    stats = orchestrator.run_pipeline(
        category=args.category,
        max_items=args.max_items,
        skip_enrichment=args.skip_enrichment,
        skip_ai=args.skip_ai,
        partition_by=args.partition_by
    )
    
    # Code de sortie
    sys.exit(0 if stats["success"] else 1)


if __name__ == "__main__":
    main()