# YONT Caisse — sources

Le dossier `public/` à la racine du dépôt est ce que Cloudflare publie (https://caisse.yorsa.workers.dev).
Ce dossier `source/` contient de quoi le reconstruire.

| Fichier | Rôle |
|---|---|
| `resto/index.html` | Le code de l'application (un seul fichier). C'est ici qu'on modifie. |
| `head.html` | Début de page commun (polices, balises). |
| `build.py` | Fabrique `out/YONT_Caisse.html` (version hors ligne, un seul fichier) et augmente le numéro de version quand le code change (`ver_state.json`). |
| `build_pwa.py` | Fabrique l'application installable dans `pwa/` et `out/YONT_Caisse_application.zip`. Les photos, l'outil PDF et l'outil Excel sont des fichiers à part, repérés par l'empreinte de leur contenu. |
| `notes.txt` | Texte affiché dans le bandeau « Nouvelle version disponible ». |
| `tests/test_caisse.py` | Test de bout en bout : deux appareils synchronisés par un faux serveur. |

## Reconstruire et publier

```bash
cd source
npm install                 # xlsx et jspdf, embarqués dans l'application
pip install playwright && python -m playwright install chromium   # pour le test
python3 build.py && python3 build_pwa.py
python3 tests/test_caisse.py   # doit finir par « TOUT EST BON »
rm -rf ../public && mkdir ../public && cp pwa/{index.html,sw.js,bp.js,jspdf.js,xlsx.js,version.json,_headers,manifest.webmanifest,*.png} ../public/
git add -A && git commit -m "Version x.y.z" && git push   # Cloudflare publie tout seul
```

## Serveur (Supabase, schéma `yont`)
- `public.yont_sync` : synchronisation (versions + journal) ; `init` garde une copie de l'ancien contenu avant de le remplacer.
- `public.yont_backup` : sauvegardes (30 nuits, 12 mois, une par an) ; tâche `yont-sauvegarde-nuit` à 02 h (Douala).
- `public.yont_err` : erreurs envoyées par les appareils (500 dernières), visibles dans Développeur → Erreurs des appareils.
- `yont.archive_old()` : chaque nuit à 02 h 30, ce qui a plus de 400 jours part dans `yont.archives` ; `public.yont_archive` pour les lire.
