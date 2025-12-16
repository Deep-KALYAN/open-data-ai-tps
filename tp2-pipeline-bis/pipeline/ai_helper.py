"""Helper pour les appels IA avec support multi-fournisseurs."""
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class AIHelper:
    """Gère les appels IA avec fallback et configuration flexible."""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.available_providers = self._detect_available_providers()
        
        if verbose:
            print(f"🤖 Fournisseurs IA détectés: {list(self.available_providers.keys())}")
    
    def _detect_available_providers(self) -> dict:
        """Détecte les fournisseurs IA disponibles."""
        providers = {}
        
        # 1. Ollama (local - PRIORITAIRE)
        ollama_models = self._check_ollama_available()
        if ollama_models:
            for model in ollama_models:
                providers[f'ollama_{model}'] = {
                    'name': 'Ollama',
                    'model': f'ollama/{model}',
                    'api_base': 'http://localhost:11434',
                    'type': 'local'
                }
        
        # 2. Groq (avec modèle mis à jour)
        if os.getenv("GROQ_API_KEY"):
            # Utiliser un modèle Groq actuel
            providers['groq'] = {
                'name': 'Groq',
                'model': 'groq/llama-3.3-70b-versatile',
                'api_key': os.getenv("GROQ_API_KEY"),
                'type': 'cloud'
            }
        
        # 3. Gemini
        if os.getenv("GEMINI_API_KEY"):
            providers['gemini'] = {
                'name': 'Gemini',
                'model': 'gemini/gemini-2.0-flash-exp',
                'api_key': os.getenv("GEMINI_API_KEY"),
                'type': 'cloud'
            }
        
        # 4. OpenAI
        if os.getenv("OPENAI_API_KEY"):
            providers['openai'] = {
                'name': 'OpenAI',
                'model': 'gpt-4o-mini',
                'api_key': os.getenv("OPENAI_API_KEY"),
                'type': 'cloud'
            }
        
        return providers
    
    def _check_ollama_available(self) -> list:
        """Vérifie quels modèles Ollama sont disponibles localement."""
        try:
            import httpx
            
            # Tester la connexion à Ollama
            response = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
            if response.status_code == 200:
                models_data = response.json()
                models = [model['name'] for model in models_data.get('models', [])]
                
                # Prioriser mistral, llama2, etc.
                preferred_order = ['mistral', 'llama2', 'codellama', 'neural-chat']
                available = []
                
                for pref in preferred_order:
                    for model in models:
                        if pref in model.lower():
                            available.append(model)
                
                # Ajouter les autres modèles
                for model in models:
                    if model not in available:
                        available.append(model)
                
                return available[:3]  # Limiter à 3 modèles max
                
        except Exception:
            pass
        
        return []
    
    def get_recommendations(self, context: str, max_tokens: int = 500) -> Optional[str]:
        """
        Obtient des recommandations IA.
        
        Args:
            context: Contexte pour l'IA
            max_tokens: Nombre maximum de tokens
        
        Returns:
            Réponse de l'IA ou None
        """
        if not self.available_providers:
            if self.verbose:
                print("⚠️ Aucun fournisseur IA disponible")
            return None
        
        # Priorité: Ollama > Groq > Gemini > OpenAI
        priority_order = [
            ('ollama', 'local'),
            ('groq', 'cloud'),
            ('gemini', 'cloud'),
            ('openai', 'cloud')
        ]
        
        # Trier les fournisseurs par priorité
        sorted_providers = []
        for prefix, ptype in priority_order:
            for provider_id, config in self.available_providers.items():
                if (provider_id.startswith(prefix) or 
                    (ptype == 'local' and config.get('type') == 'local')):
                    sorted_providers.append((provider_id, config))
        
        # Essayer chaque fournisseur dans l'ordre de priorité
        for provider_id, config in sorted_providers:
            try:
                if self.verbose:
                    print(f"🤖 Tentative avec {config['name']} ({config['model']})...")
                
                result = self._call_provider(provider_id, config, context, max_tokens)
                if result:
                    if self.verbose:
                        print(f"✅ Réponse reçue de {config['name']}")
                    return result
                    
            except Exception as e:
                if self.verbose:
                    print(f"⚠️ Erreur avec {config['name']}: {str(e)[:100]}...")
                continue
        
        if self.verbose:
            print("❌ Tous les fournisseurs IA ont échoué")
        return None
    
    def _call_provider(self, provider_id: str, config: dict, context: str, max_tokens: int) -> Optional[str]:
        """Appelle un fournisseur IA spécifique."""
        try:
            from litellm import completion
            
            # Préparer les paramètres communs
            params = {
                "model": config['model'],
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Tu es un expert en qualité des données. "
                            "Donne des recommandations concrètes, actionnables et professionnelles. "
                            "Formate en markdown avec des listes à puces."
                        )
                    },
                    {
                        "role": "user",
                        "content": f"{context}\n\nQuelles sont tes 5 recommandations prioritaires pour améliorer ce dataset ?"
                    }
                ],
                "max_tokens": max_tokens,
                "temperature": 0.3,  # Moins créatif, plus factuel
            }
            
            # Ajouter les paramètres spécifiques
            if provider_id.startswith('ollama'):
                params["api_base"] = config.get('api_base', 'http://localhost:11434')
                params["timeout"] = 30.0  # Plus long pour les modèles locaux
            elif 'api_key' in config:
                params["api_key"] = config['api_key']
            
            # Appel API
            response = completion(**params)
            
            # Extraire la réponse
            if hasattr(response, 'choices') and response.choices:
                return response.choices[0].message.content.strip()
            elif hasattr(response, 'content'):
                return response.content.strip()
            else:
                return str(response).strip()
                
        except Exception as e:
            raise e



# # ---------- Solution  Groq avec litellm ----------

# """Helper pour les appels IA avec support multi-fournisseurs."""
# import os
# from typing import Optional
# from dotenv import load_dotenv

# load_dotenv()


# class AIHelper:
#     """Gère les appels IA avec fallback et configuration flexible."""
    
#     def __init__(self):
#         self.available_providers = self._detect_available_providers()
#         print(f"🤖 Fournisseurs IA détectés: {list(self.available_providers.keys())}")
    
#     def _detect_available_providers(self) -> dict:
#         """Détecte les fournisseurs IA disponibles."""
#         providers = {}
        
#         # Vérifier Groq
#         if os.getenv("GROQ_API_KEY"):
#             providers['groq'] = {
#                 'name': 'Groq',
#                 'model': 'groq/llama3-70b-8192',
#                 'api_key': os.getenv("GROQ_API_KEY")
#             }
        
#         # Vérifier Gemini
#         if os.getenv("GEMINI_API_KEY"):
#             providers['gemini'] = {
#                 'name': 'Gemini',
#                 'model': 'gemini/gemini-2.0-flash-exp',
#                 'api_key': os.getenv("GEMINI_API_KEY")
#             }
        
#         # Vérifier OpenAI
#         if os.getenv("OPENAI_API_KEY"):
#             providers['openai'] = {
#                 'name': 'OpenAI',
#                 'model': 'gpt-4o-mini',
#                 'api_key': os.getenv("OPENAI_API_KEY")
#             }
        
#         return providers
    
#     def get_recommendations(self, context: str, max_tokens: int = 500) -> Optional[str]:
#         """
#         Obtient des recommandations IA.
        
#         Args:
#             context: Contexte pour l'IA
#             max_tokens: Nombre maximum de tokens
        
#         Returns:
#             Réponse de l'IA ou None
#         """
#         if not self.available_providers:
#             return None
        
#         # Essayer chaque fournisseur dans l'ordre
#         for provider_id, config in self.available_providers.items():
#             try:
#                 result = self._call_provider(provider_id, config, context, max_tokens)
#                 if result:
#                     return result
#             except Exception as e:
#                 print(f"⚠️ Erreur avec {config['name']}: {e}")
#                 continue
        
#         return None
    
#     def _call_provider(self, provider_id: str, config: dict, context: str, max_tokens: int) -> Optional[str]:
#         """Appelle un fournisseur IA spécifique."""
#         try:
#             from litellm import completion
            
#             if provider_id == 'groq':
#                 response = completion(
#                     model=config['model'],
#                     api_key=config['api_key'],
#                     messages=[
#                         {
#                             "role": "system",
#                             "content": "Tu es un expert en qualité des données. Donne des recommandations concrètes et actionnables."
#                         },
#                         {
#                             "role": "user",
#                             "content": f"{context}\n\nQuelles sont tes 5 recommandations prioritaires pour améliorer ce dataset ?"
#                         }
#                     ],
#                     max_tokens=max_tokens
#                 )
#             else:
#                 # Pour Gemini/OpenAI, utiliser la configuration par défaut de litellm
#                 response = completion(
#                     model=config['model'],
#                     messages=[
#                         {
#                             "role": "system",
#                             "content": "Tu es un expert en qualité des données. Donne des recommandations concrètes et actionnables."
#                         },
#                         {
#                             "role": "user",
#                             "content": f"{context}\n\nQuelles sont tes 5 recommandations prioritaires pour améliorer ce dataset ?"
#                         }
#                     ],
#                     max_tokens=max_tokens
#                 )
            
#             return response.choices[0].message.content
            
#         except Exception as e:
#             print(f"⚠️ Erreur détaillée avec {config['name']}: {e}")
#             return None