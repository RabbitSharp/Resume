# Resume

A two-column LaTeX resume where **content**, **style** and **presentation logic** are separated.

You edit YAML. A small Python generator renders it through a Jinja2 template into LaTeX, and a
Docker image compiles it to PDF. See [`assets/example-resume.pdf`](assets/example-resume.pdf) for
the result.

```
content/*.yaml  ─┐
style.yaml      ─┼─► builder/build.py ─► out/resume-<lang>.tex ─► xelatex ─► out/resume-<lang>.pdf
resume.tex.j2   ─┘                                                (or lualatex)
```

## Quick start

```powershell
# build the image once
.\docker\build-and-publish.ps1 -SkipPush

# build the PDF
.\build-resume.ps1                      # German, opens out/resume-de.pdf
.\build-resume.ps1 -Language de, en     # both languages
.\build-resume.ps1 -Engine lualatex     # use LuaLaTeX instead of XeLaTeX
```

Or directly:

```powershell
docker run --rm -v "${PWD}:/data" rabbitsharp/resume-builder --lang de --lang en
```

## Repository layout

| Path | Purpose |
|---|---|
| `content/de.yaml`, `content/en.yaml` | **What** the CV says — one file per language |
| `content/labels.yaml` | Translatable section headlines and recurring terms |
| `style/style.yaml` | **How** it looks: colors, fonts, geometry, photo, engine, page layout |
| `latex/resume.cls` | LaTeX macros (`\job`, `\skill`, `\project`, `\wheelchart`, …) |
| `latex/templates/resume.tex.j2` | Jinja2 template mapping content blocks onto those macros |
| `builder/build.py` | Generator: validate → render → compile |
| `assets/` | Photo and other images |
| `docker/` | Builder image and publish script |
| `out/` | Generated `.tex` and `.pdf` (git-ignored) |

`out/resume-<lang>.tex` is generated — never edit it.

## Editing content

Each entry under `sections:` is a typed block with an id. The id is what `style.yaml` uses to place
the block on a page.

```yaml
sections:
  work:
    type: jobs
    title: "@{work}"        # label lookup, see content/labels.yaml
    icon: faGears           # any fontawesome macro name, optional
    entries:
      - period: "03/2019 - @{today}"
        place: "Carroteers, Hamburg"
        position: Feel-Good Manager
        note: ""            # optional
```

`@{key}` is replaced by the translation of `key` for the language being built. References may be
embedded in longer strings. Unknown keys or missing translations abort the build with a precise
error message.

### Block types

| `type` | Required keys | Renders |
|---|---|---|
| `contact` | `title`, `groups[].items[]` | Contact lines; groups are separated by a small gap |
| `rated-skills` | `title`, `groups[].skills[]` (`name`, `level` 1–5) | Skill name plus a five-dot rating |
| `simple-skills` | `title`, `items[]` | Plain bold entries, e.g. certificates |
| `tag-groups` | `title`, `groups[]` (`name`, `tags[]`) | Rounded, outlined tags per subsection |
| `jobs` | `entries[]` (`period`, `place`, `position`, `note?`) | Two-column CV entries; `title` and `icon` optional |
| `projects` | `entries[]` (`title`, `client`, `period`, `industry`, `role`, `team`, `link?`, `environment`, `summary`) | Project block with metadata icons and description |
| `wheelchart` | `outer`, `inner`, `slices[]` (`value`, `width`, `label`, `shade?`) | Donut chart; `shade` 1–100 shades the accent color |
| `raw` | `latex` | Escape hatch for arbitrary LaTeX |

Contact item types: `birthdate`, `email`, `phone`, `location`, `address` (need `value`) and
`homepage`, `linkedin`, `github`, `xing`, `orcid`, `ads` (need `label` and `url`).

All content strings are LaTeX-escaped automatically — write `&`, `%` or `_` as-is. Use a `raw`
block if you deliberately need LaTeX markup.

### Adding a language

1. Add the translations to `content/labels.yaml` under a new key, e.g. `fr:`.
2. Copy `content/de.yaml` to `content/fr.yaml`, keeping the **same section ids**.
3. Build with `--lang fr`.
4. If the language needs hyphenation patterns, add the matching `texlive-lang-*` package to
   `docker/Dockerfile`.

## Editing style and layout

`style/style.yaml` holds everything visual. `layout.pages` decides which sections appear on which
page and in which column:

```yaml
layout:
  pages:
    - header: true
      pagestyle: headerhighlightmain
      highlight: [contact, skills-highlight, languages, certificates]
      main:      [work, work-wheel, university, education]
```

Every id must exist in the content file, and no id may be placed twice. Sections defined in the
content but not placed are reported as a note and simply omitted, which makes it easy to keep
optional blocks around.

Colors accept either a name defined in `latex/resume.cls` (`the-green`, `darkgray`, …) or a hex
literal such as `"#357A52"`.

## Working without Docker

The rendering step runs anywhere Python is available; only the PDF compilation needs a LaTeX engine.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r builder\requirements.txt
.\.venv\Scripts\python.exe builder\build.py --lang de --no-compile
```

This validates the YAML and writes `out/resume-de.tex` in a second — useful while iterating.
If no LaTeX engine is on `PATH`, `build.py` says so and points you back to Docker.

### `build.py` options

| Option | Meaning |
|---|---|
| `--lang CODE` | Language to build; repeat for several. Default `de` |
| `--engine xelatex\|lualatex` | Overrides `document.engine` from `style.yaml` |
| `--no-compile` | Only write the `.tex` file |
| `--root PATH` | Project root all other paths default to (the image mounts it at `/data`) |
| `--content-dir`, `--style`, `--template`, `--class-dir`, `--out` | Individual path overrides |

## The Docker image

`docker/Dockerfile` builds on `ubuntu:24.04` and installs a curated TeX Live subset instead of
`texlive-full`: roughly **2.2 GB instead of 8 GB**, while still providing KOMA-Script, TikZ,
tcolorbox, fontspec, fontawesome and academicons. Both `xelatex` and `lualatex` are included.

Not included, and easy to add back as a single `apt-get` line if you ever need it: language packs
beyond German, `texlive-science`, `texlive-publishers`, humanities/music/games, PSTricks, `biber`
and extra BibTeX styles, `latexdiff`/`texcount`/`epstopdf`, ConTeXt/Asymptote/MetaPost, and all
documentation packages.

The build context is the repository root because `builder/` is baked into the image:

```powershell
docker build -f docker/Dockerfile -t rabbitsharp/resume-builder .
```

The template, class file and content are read from the mounted volume, so you can change them
without rebuilding the image.

## Credits

The wheel chart and tag macros in `latex/resume.cls` are adapted from
[AltaCV](https://github.com/liantze/AltaCV).
