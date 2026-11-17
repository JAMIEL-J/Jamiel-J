# Publishing the cards to your GitHub profile

Your profile README lives in the repo **`JAMIEL-J/Jamiel-J`**, at the root of its
default branch. Everything in this folder is what needs to go there.

## First push

From this folder in PowerShell:

```powershell
git init
git remote add origin https://github.com/JAMIEL-J/Jamiel-J.git
git fetch origin
git checkout -B main origin/main   # use master if that is your default branch

git add .gitignore README.md requirements.txt .github scripts cards data
git commit -m "feat: animated profile cards"
git push -u origin main
```

`git add` is explicit on purpose: `assets.zip`, `index.html`, the wedding images
and the browser-tooling files are ignored, so they will not end up in the repo.

## Replace the sample numbers immediately

The `cards/` folder currently holds frames rendered from `--sample`, so the
contribution numbers are fake. Once the push is up:

1. Open `https://github.com/JAMIEL-J/Jamiel-J/actions/workflows/cards.yml`
2. Click **Run workflow**, then **Run workflow** again in the dialog.

The job fetches real contributions, re-renders all 11 cards, and commits them.
The README image URLs stay the same; a new commit simply busts GitHub's image
cache. After that it repeats automatically every day at 04:17 UTC.

If the fetch step fails with an authorization error, add a personal access
token with `read:user` scope as a repository secret named `GH_TOKEN`. The fetch
script already prefers that over the repository token.

## Optional: real portrait

Drop a square-ish photo at `assets/portrait.jpg`. The hero embeds it as a
base64 JPEG automatically the next time the script runs. Without it, the hero
shows the "JJ" monogram. Note that `assets/` is gitignored, so the portrait
will not be committed; add it with `git add -f assets/portrait.jpg` if you want
the Action to see it.

## Local checks

```powershell
python scripts/build_cards.py --sample                    # animated -> cards/
STATIC=1 python scripts/build_cards.py --sample           # final frames -> cards-static/
```
