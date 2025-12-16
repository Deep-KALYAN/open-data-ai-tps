#!/usr/bin/env python3
"""Test de l'intégration Ollama."""
import os
from dotenv import load_dotenv
from pipeline.ai_helper import AIHelper

load_dotenv()

print("🧪 Test de l'intégration Ollama")

# Tester l'AI helper
print("\n1. Initialisation de l'AI Helper...")
ai_helper = AIHelper(verbose=True)

print(f"\n2. Fournisseurs disponibles: {list(ai_helper.available_providers.keys())}")

# Tester une requête simple
print("\n3. Test d'une requête IA...")
context = """
Analyse de qualité d'un dataset de produits alimentaires:
- Total: 1000 enregistrements
- Complétude: 85%
- Doublons: 3%
- Géocodage réussi: 60%
- Note globale: B

Valeurs manquantes:
- product_name: 5%
- stores: 15%
- geocoding_score: 40%
"""

try:
    response = ai_helper.get_recommendations(context, max_tokens=300)
    if response:
        print("✅ Réponse IA reçue!")
        print("\n" + "="*60)
        print("📝 Réponse complète:")
        print("="*60)
        print(response)
        print("="*60)
        
        # Sauvegarder pour référence
        with open("test_ai_response.md", "w", encoding="utf-8") as f:
            f.write(response)
        print("\n💾 Réponse sauvegardée dans: test_ai_response.md")
    else:
        print("⚠️ Aucune réponse de l'IA")
        
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()