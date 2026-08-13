# Project agent memory

This file is the project's committed home for project-intrinsic agent knowledge: build, test, release, architecture, and sharp-edge notes that should travel with the code.

- The static GitHub Pages site is served from the repository root without a build step; keep site navigation and assets relative so the project-path deployment continues to work.
- The public site has exactly two routes: the annotated Apple Watch screen at `/` and the privacy policy at `/privacy/`; the homepage contract is enforced by `scripts/check_site.py`.
- Run `python3 scripts/check_site.py` and `python3 -m unittest scripts.test_check_site` after changing site content, links, metadata, or deployment files.
- `SITE.md` is authoritative for local preview, privacy-policy maintenance, and the default-branch-only Pages deployment model.

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
