#!/usr/bin/env python3
"""Script pour résoudre automatiquement les conflits de merge simples.

Usage:
    python3 scripts/resolve-conflicts.py [--dry-run] [--files file1.py file2.py]

Ce script résout automatiquement les conflits qui sont uniquement des différences
de formatage (espaces, sauts de ligne, etc.) et garde la version mieux formatée.
"""

import argparse
import re
import sys
from pathlib import Path


def resolve_conflict(head: str, main: str) -> str:
    """Résout un conflit en choisissant la meilleure version.
    
    Args:
        head: Contenu de HEAD
        main: Contenu de origin/main
        
    Returns:
        Version résolue du conflit
    """
    # Normaliser les espaces pour comparer
    head_norm = re.sub(r'\s+', ' ', head.strip())
    main_norm = re.sub(r'\s+', ' ', main.strip())
    
    # Si identique (sauf formatage), garder main (généralement mieux formaté)
    if head_norm == main_norm:
        return main
    
    # Si head est vide, garder main
    if not head.strip():
        return main
    
    # Si main est vide, garder head
    if not main.strip():
        return head
    
    # Pour les imports: préférer formatage multi-lignes
    if 'import' in head and 'import' in main:
        head_lines = [l for l in head.split('\n') if l.strip()]
        main_lines = [l for l in main.split('\n') if l.strip()]
        if len(head_lines) == len(main_lines):
            # Même nombre d'imports, préférer formatage multi-lignes
            if '\n' in main:
                return main
    
    # Pour les appels de fonction longues: préférer formatage multi-lignes
    if len(main) > len(head) and '\n' in main:
        return main
    
    # Par défaut, garder main (version origin/main généralement mieux formatée)
    return main


def resolve_file(filepath: Path, dry_run: bool = False) -> tuple[bool, int]:
    """Résout les conflits dans un fichier.
    
    Args:
        filepath: Chemin du fichier
        dry_run: Si True, ne modifie pas le fichier
        
    Returns:
        (has_conflicts, conflicts_resolved)
    """
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        print(f"⚠️  Erreur lecture {filepath}: {e}", file=sys.stderr)
        return False, 0
    
    if '<<<<<<< HEAD' not in content:
        return False, 0
    
    original_content = content
    conflicts_resolved = 0
    
    # Pattern pour détecter les conflits
    pattern = r'<<<<<<< HEAD\n(.*?)\n=======\n(.*?)\n>>>>>>> origin/main'
    
    def replace_conflict(match):
        nonlocal conflicts_resolved
        conflicts_resolved += 1
        return resolve_conflict(match.group(1), match.group(2))
    
    new_content = re.sub(pattern, replace_conflict, content, flags=re.DOTALL)
    
    # Nettoyer les marqueurs orphelins
    new_content = re.sub(r'<<<<<<< HEAD\n', '', new_content)
    new_content = re.sub(r'=======\n', '', new_content)
    new_content = re.sub(r'>>>>>>> origin/main\n', '', new_content)
    
    if new_content != original_content:
        if not dry_run:
            filepath.write_text(new_content, encoding='utf-8')
        return True, conflicts_resolved
    
    return True, 0


def main():
    parser = argparse.ArgumentParser(description='Résout automatiquement les conflits de merge')
    parser.add_argument('--dry-run', action='store_true', help='Mode simulation (ne modifie pas les fichiers)')
    parser.add_argument('--files', nargs='+', help='Fichiers spécifiques à traiter')
    args = parser.parse_args()
    
    if args.files:
        files_to_process = [Path(f) for f in args.files if Path(f).exists()]
    else:
        # Chercher tous les fichiers avec conflits
        files_to_process = []
        for ext in ['*.py', '*.toml', '*.yml', '*.yaml']:
            files_to_process.extend(Path('.').rglob(ext))
    
    resolved_files = 0
    total_conflicts = 0
    
    for filepath in files_to_process:
        has_conflicts, conflicts_count = resolve_file(filepath, dry_run=args.dry_run)
        if has_conflicts:
            if conflicts_count > 0:
                mode = "🔍 [DRY-RUN] " if args.dry_run else "✅"
                print(f"{mode} {filepath}: {conflicts_count} conflit(s) résolu(s)")
                resolved_files += 1
                total_conflicts += conflicts_count
            else:
                print(f"⚠️  {filepath}: conflits détectés mais non résolus automatiquement (nécessite résolution manuelle)")
    
    if resolved_files > 0:
        print(f"\n{'[DRY-RUN] ' if args.dry_run else ''}✅ {resolved_files} fichier(s) traité(s), {total_conflicts} conflit(s) résolu(s)")
        if args.dry_run:
            print("💡 Relancer sans --dry-run pour appliquer les changements")
    else:
        print("✅ Aucun conflit à résoudre automatiquement")


if __name__ == '__main__':
    main()
