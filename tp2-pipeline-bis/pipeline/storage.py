"""Module de stockage des données."""
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from .config import RAW_DIR, PROCESSED_DIR


def save_raw_json(data: list[dict], name: str) -> Path:
    """
    Sauvegarde les données brutes en JSON.
    
    Args:
        data: Liste de dictionnaires
        name: Nom du fichier (sans extension)
    
    Returns:
        Chemin du fichier créé
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{name}_{timestamp}.json"
    filepath = RAW_DIR / filename
    
    # Assurer que le dossier existe
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    
    # Sauvegarder
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    
    # Calculer la taille
    size_kb = filepath.stat().st_size / 1024
    print(f"   💾 Brut JSON: {filepath.name} ({size_kb:.1f} KB, {len(data)} enregistrements)")
    
    return filepath


def save_parquet(
    df: pd.DataFrame,
    name: str,
    partition_by: Optional[str] = None,
    compression: str = "snappy"
) -> Path:
    """
    Sauvegarde le DataFrame en Parquet.
    
    Args:
        df: DataFrame à sauvegarder
        name: Nom du dataset
        partition_by: Colonne pour partitionnement (optionnel)
        compression: Compression à utiliser
    
    Returns:
        Chemin du dossier/fichier créé
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{name}_{timestamp}"
    
    # Assurer que le dossier existe
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    
    if partition_by and partition_by in df.columns:
        # Sauvegarde partitionnée
        output_dir = PROCESSED_DIR / filename
        df.to_parquet(
            output_dir,
            partition_cols=[partition_by],
            compression=compression,
            index=False
        )
        
        # Compter les fichiers créés
        parquet_files = list(output_dir.rglob("*.parquet"))
        size_mb = sum(f.stat().st_size for f in parquet_files) / (1024 * 1024)
        
        print(f"   💾 Parquet partitionné: {output_dir.name}/")
        print(f"      - Partitions: {partition_by}")
        print(f"      - Fichiers: {len(parquet_files)}")
        print(f"      - Taille: {size_mb:.1f} MB")
        print(f"      - Enregistrements: {len(df)}")
        
        return output_dir
    
    else:
        # Sauvegarde simple
        filepath = PROCESSED_DIR / f"{filename}.parquet"
        df.to_parquet(filepath, compression=compression, index=False)
        
        size_mb = filepath.stat().st_size / (1024 * 1024)
        print(f"   💾 Parquet: {filepath.name}")
        print(f"      - Taille: {size_mb:.1f} MB")
        print(f"      - Enregistrements: {len(df)}")
        print(f"      - Colonnes: {len(df.columns)}")
        
        return filepath


def load_parquet(filepath: Union[str, Path]) -> pd.DataFrame:
    """
    Charge un fichier Parquet.
    
    Args:
        filepath: Chemin vers le fichier/dossier Parquet
    
    Returns:
        DataFrame chargé
    """
    filepath = Path(filepath)
    
    if not filepath.exists():
        raise FileNotFoundError(f"Fichier non trouvé: {filepath}")
    
    # Chargement simple ou partitionné
    if filepath.is_dir():
        # Dossier partitionné
        df = pd.read_parquet(filepath)
        print(f"📂 Chargement partitionné: {filepath.name} ({len(df)} enregistrements)")
    else:
        # Fichier simple
        df = pd.read_parquet(filepath)
        print(f"📂 Chargement: {filepath.name} ({len(df)} enregistrements)")
    
    return df


def get_latest_parquet(name_pattern: str) -> Optional[Path]:
    """
    Trouve le fichier Parquet le plus récent correspondant au pattern.
    
    Args:
        name_pattern: Pattern de nom (ex: "chocolats_*.parquet")
    
    Returns:
        Chemin du fichier le plus récent ou None
    """
    pattern = PROCESSED_DIR / name_pattern.replace("*", "*")
    files = list(PROCESSED_DIR.glob(name_pattern))
    
    if not files:
        return None
    
    # Trier par date de modification (le plus récent en premier)
    latest = max(files, key=lambda f: f.stat().st_mtime)
    return latest


def get_storage_stats() -> dict:
    """
    Retourne des statistiques sur le stockage.
    
    Returns:
        Dictionnaire avec les statistiques
    """
    stats = {
        'raw': {
            'count': 0,
            'total_size_mb': 0,
            'files': []
        },
        'processed': {
            'count': 0,
            'total_size_mb': 0,
            'files': []
        }
    }
    
    # Analyser raw
    if RAW_DIR.exists():
        raw_files = list(RAW_DIR.glob("*.json"))
        stats['raw']['count'] = len(raw_files)
        stats['raw']['total_size_mb'] = sum(f.stat().st_size for f in raw_files) / (1024 * 1024)
        stats['raw']['files'] = [f.name for f in raw_files[:5]]  # 5 premiers
    
    # Analyser processed
    if PROCESSED_DIR.exists():
        # Fichiers .parquet
        parquet_files = list(PROCESSED_DIR.glob("*.parquet"))
        
        # Dossiers partitionnés
        parquet_dirs = [d for d in PROCESSED_DIR.iterdir() if d.is_dir()]
        
        stats['processed']['count'] = len(parquet_files) + len(parquet_dirs)
        
        # Calculer la taille
        total_size = 0
        for f in parquet_files:
            total_size += f.stat().st_size
        
        for d in parquet_dirs:
            for f in d.rglob("*.parquet"):
                total_size += f.stat().st_size
        
        stats['processed']['total_size_mb'] = total_size / (1024 * 1024)
        
        # Lister les fichiers
        all_files = parquet_files + parquet_dirs
        stats['processed']['files'] = [f.name for f in all_files[:5]]
    
    return stats