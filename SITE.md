# Loop Alarm website operations

## Public URLs

- <https://jamesc0ry.github.io/loop-alarm-site/>
- <https://jamesc0ry.github.io/loop-alarm-site/privacy/>
- <https://jamesc0ry.github.io/loop-alarm-site/support/>

All links between site files are relative so the pages work locally and below the `loop-alarm-site/` GitHub project path. Canonical metadata and the sitemap use the public URLs above.

## Local preview and checks

From the repository root, run:

```sh
python3 scripts/check_site.py
python3 -m unittest scripts.test_check_site
python3 -m http.server 8000
```

Then open <http://127.0.0.1:8000/>. The validator checks page structure and accessibility metadata, canonical URLs, every local link and fragment, privacy wording, the exact approved email, and the absence of scripts, forms, trackers, unapproved contacts, stale pre-publication wording, and root-relative links.

## Privacy policy maintenance

The policy describes the current app behavior: reminder configuration is stored locally on Apple Watch, and the app has no accounts, analytics, advertising, network service, tracking, or third-party SDK. The website has no JavaScript, forms, analytics, advertising, cookies set by site code, or remote assets. GitHub Pages hosting is disclosed separately because GitHub states that it logs visitor IP addresses for security.

Before changing the privacy policy, verify it against the app release being documented. Change the effective date when the policy changes, then run the checks and inspect narrow and wide layouts.

## Deployment

The [Pages workflow](.github/workflows/pages.yml) validates pull requests without publishing. A push to `main` validates again, packages the static root, and deploys through the `github-pages` environment. The deployment job alone receives `pages: write` and `id-token: write`; all actions are pinned to full commit SHAs.

Repository Pages settings are managed separately from this repository. Do not add manual deployment triggers without reviewing the publication controls.

## Official references

- [GitHub Pages custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [GitHub Pages data collection](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages#data-collection)
- [GitHub Actions secure use](https://docs.github.com/en/actions/reference/security/secure-use#using-third-party-actions)
