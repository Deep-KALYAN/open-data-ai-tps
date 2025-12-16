#!/usr/bin/env python3
"""Test du pipeline complet (mode test rapide)."""
import sys
from pipeline.main import PipelineOrchestrator

print("🧪 Test du pipeline complet (mode rapide)")

# Configuration de test
config = {
    "category": "chocolats",
    "max_items": 20,  # Petit pour le test
    "skip_enrichment": False,
    "skip_ai": False,  # Utiliser Groq pour l'IA
    "partition_by": None,
}

print(f"\n🔧 Configuration:")
for key, value in config.items():
    print(f"   {key}: {value}")

# Exécuter le pipeline (verbose=True dans le constructeur)
print("\n" + "="*50)
print("🚀 Démarrage du pipeline...")
print("="*50)

orchestrator = PipelineOrchestrator(verbose=True)  # verbose ici
stats = orchestrator.run_pipeline(**config)

print("\n" + "="*50)
print("📊 Résultats du test:")
print("="*50)

if stats["success"]:
    print("✅ Pipeline exécuté avec succès!")
    print(f"   Durée: {stats['duration_seconds']} secondes")
    print(f"   Note qualité: {stats.get('quality_grade', 'N/A')}")
    
    if "output_path" in stats:
        print(f"   Fichier de sortie: {stats['output_path']}")
    
    # Afficher quelques stats par étape
    stages = stats.get("stages", {})
    for stage_name, stage_data in stages.items():
        if stage_name == "acquisition":
            print(f"   📥 Produits récupérés: {stage_data.get('products_fetched', 0)}")
        elif stage_name == "quality":
            grade = stage_data.get('metrics', {}).get('quality_grade', 'N/A')
            print(f"   📊 Note qualité: {grade}")
    
else:
    print("❌ Pipeline a échoué")
    print(f"   Erreur: {stats.get('error', 'Inconnue')}")
    sys.exit(1)


# #!/usr/bin/env python3
# """Test du pipeline complet (mode test rapide)."""
# import sys
# from pipeline.main import PipelineOrchestrator

# print("🧪 Test du pipeline complet (mode rapide)")

# # Configuration de test
# config = {
#     "category": "chocolats",
#     "max_items": 20,  # Petit pour le test
#     "skip_enrichment": False,
#     "skip_ai": False,  # Utiliser Groq pour l'IA
#     "partition_by": None,
#     "verbose": True
# }

# print(f"\n🔧 Configuration:")
# for key, value in config.items():
#     print(f"   {key}: {value}")

# # Exécuter le pipeline
# print("\n" + "="*50)
# print("🚀 Démarrage du pipeline...")
# print("="*50)

# orchestrator = PipelineOrchestrator(verbose=config["verbose"])
# stats = orchestrator.run_pipeline(**config)

# print("\n" + "="*50)
# print("📊 Résultats du test:")
# print("="*50)

# if stats["success"]:
#     print("✅ Pipeline exécuté avec succès!")
#     print(f"   Durée: {stats['duration_seconds']} secondes")
#     print(f"   Note qualité: {stats.get('quality_grade', 'N/A')}")
    
#     if "output_path" in stats:
#         print(f"   Fichier de sortie: {stats['output_path']}")
    
#     # Afficher quelques stats par étape
#     stages = stats.get("stages", {})
#     for stage_name, stage_data in stages.items():
#         if stage_name == "acquisition":
#             print(f"   📥 Produits récupérés: {stage_data.get('products_fetched', 0)}")
#         elif stage_name == "quality":
#             grade = stage_data.get('metrics', {}).get('quality_grade', 'N/A')
#             print(f"   📊 Note qualité: {grade}")
    
# else:
#     print("❌ Pipeline a échoué")
#     print(f"   Erreur: {stats.get('error', 'Inconnue')}")
#     sys.exit(1)