# Loop Alarm website

This public repository contains only the static website for Loop Alarm, including its home page, privacy policy, support documentation, and site validation.

The Loop Alarm Apple Watch app source remains private and is not copied here.

## Local checks and preview

```sh
python3 scripts/check_site.py
python3 -m unittest scripts.test_check_site
python3 -m http.server 8000
```

Then open <http://127.0.0.1:8000/>. See [SITE.md](SITE.md) for website maintenance and deployment details.
