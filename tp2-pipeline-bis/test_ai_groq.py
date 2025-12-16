#!/usr/bin/env python3
"""Test de l'intégration Groq."""
import os
from dotenv import load_dotenv
from pipeline.ai_helper import AIHelper

load_dotenv()

print("🧪 Test de l'intégration Groq")

# Vérifier la clé API
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print("❌ GROQ_API_KEY non trouvée dans .env")
    print("   Créez un fichier .env avec: GROQ_API_KEY=votre_clé")
    exit(1)

print(f"✅ GROQ_API_KEY trouvée: {api_key[:10]}...")

# Tester l'AI helper
ai_helper = AIHelper()
print(f"\n📋 Fournisseurs disponibles: {list(ai_helper.available_providers.keys())}")

# Tester une requête simple
if 'groq' in ai_helper.available_providers:
    print("\n🤖 Test d'une requête IA simple...")
    context = "Dataset de produits alimentaires avec 1000 enregistrements. Complétude: 85%. Doublons: 3%."
    
    try:
        response = ai_helper.get_recommendations(context, max_tokens=200)
        if response:
            print("✅ Réponse IA reçue!")
            print(f"\n📝 Extrait (100 premiers caractères):")
            print(response[:100] + "...")
        else:
            print("⚠️ Aucune réponse de l'IA")
    except Exception as e:
        print(f"❌ Erreur: {e}")
else:
    print("\n⚠️ Groq non disponible, vérifiez votre clé API")