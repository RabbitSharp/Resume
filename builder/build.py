#!/usr/bin/env python3
"""Render the resume from YAML content + style into LaTeX and compile it.

Content lives in content/<lang>.yaml, translatable labels in
content/labels.yaml and everything style related in style/style.yaml.
The LaTeX presentation logic is in latex/templates/resume.tex.j2.

Examples
--------
    py builder/build.py --lang de --no-compile
    python3 builder/build.py --lang de --lang en --engine lualatex
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - environment problem, not logic
    sys.exit("PyYAML is missing. Install it with: py -m pip install -r builder/requirements.txt")

try:
    from jinja2 import Environment, FileSystemLoader, StrictUndefined
except ImportError:  # pragma: no cover
    sys.exit("Jinja2 is missing. Install it with: py -m pip install -r builder/requirements.txt")


REPO_ROOT = Path(__file__).resolve().parent.parent

SUPPORTED_ENGINES = ("xelatex", "lualatex")

# Label keys that resume.cls expects as LaTeX macros.
LABEL_MACROS = {
    "headlineProjectSum": "project_summary",
    "headlineSoftwareEnv": "software_env",
}

LABEL_REF = re.compile(r"@\{([A-Za-z_][A-Za-z0-9_]*)\}")

CONTACT_LINK_TYPES = {"homepage", "linkedin", "github", "xing", "orcid", "ads"}
CONTACT_VALUE_TYPES = {"birthdate", "email", "phone", "location", "address"}

# Required keys per block type. "entries"/"groups"/"items" are the payload.
BLOCK_SCHEMA = {
    "contact": {"required": ["title", "groups"]},
    "rated-skills": {"required": ["title", "groups"]},
    "simple-skills": {"required": ["title", "items"]},
    "tag-groups": {"required": ["title", "groups"]},
    "jobs": {"required": ["entries"]},
    "projects": {"required": ["entries"]},
    "wheelchart": {"required": ["outer", "inner", "slices"]},
    "raw": {"required": ["latex"]},
}


class ContentError(Exception):
    """Raised when the YAML input is inconsistent or incomplete."""


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------

def load_yaml(path: Path):
    if not path.is_file():
        raise ContentError(f"file not found: {path}")
    with path.open(encoding="utf-8") as handle:
        try:
            return yaml.safe_load(handle)
        except yaml.YAMLError as exc:
            raise ContentError(f"{path}: invalid YAML\n{exc}") from exc


def resolve_labels(value, labels, lang, path="", origin=""):
    """Recursively replace @{key} references with the label for *lang*."""
    if isinstance(value, dict):
        return {k: resolve_labels(v, labels, lang, f"{path}.{k}", origin) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve_labels(v, labels, lang, f"{path}[{i}]", origin) for i, v in enumerate(value)]
    if isinstance(value, str):
        def replace(match):
            key = match.group(1)
            entry = labels.get(key)
            if entry is None:
                raise ContentError(
                    f"{origin}: unknown label '@{{{key}}}' at {path.lstrip('.')} "
                    f"- add it to content/labels.yaml"
                )
            if lang not in entry:
                raise ContentError(
                    f"content/labels.yaml: label '{key}' has no '{lang}' translation "
                    f"(referenced from {origin} at {path.lstrip('.')})"
                )
            return str(entry[lang])
        return LABEL_REF.sub(replace, value)
    return value


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------

def validate(content, style, origin):
    sections = content.get("sections")
    if not isinstance(sections, dict):
        raise ContentError(f"{origin}: missing top level 'sections' mapping")

    header = content.get("header") or {}
    for key in ("name", "tagline"):
        if not header.get(key):
            raise ContentError(f"{origin}: header.{key} is required")

    for section_id, section in sections.items():
        if not isinstance(section, dict):
            raise ContentError(f"{origin}: section '{section_id}' must be a mapping")
        block_type = section.get("type")
        if block_type not in BLOCK_SCHEMA:
            known = ", ".join(sorted(BLOCK_SCHEMA))
            raise ContentError(
                f"{origin}: section '{section_id}' has unknown type '{block_type}'. Known types: {known}"
            )
        for key in BLOCK_SCHEMA[block_type]["required"]:
            if section.get(key) in (None, "", [], {}):
                raise ContentError(
                    f"{origin}: section '{section_id}' (type {block_type}) is missing required key '{key}'"
                )
        if block_type == "contact":
            validate_contact(section, section_id, origin)
        elif block_type == "wheelchart":
            validate_wheelchart(section, section_id, origin)

    pages = (style.get("layout") or {}).get("pages")
    if not pages:
        raise ContentError("style/style.yaml: layout.pages is empty")

    used = set()
    for index, page in enumerate(pages, start=1):
        for column in ("highlight", "main"):
            for section_id in page.get(column) or []:
                if section_id not in sections:
                    raise ContentError(
                        f"style/style.yaml: page {index} {column} references unknown section "
                        f"'{section_id}' - not defined in {origin}"
                    )
                if section_id in used:
                    raise ContentError(
                        f"style/style.yaml: section '{section_id}' is placed more than once"
                    )
                used.add(section_id)

    unused = sorted(set(sections) - used)
    if unused:
        print(
            f"  note: {origin} defines section(s) not placed by style.yaml: {', '.join(unused)}",
            file=sys.stderr,
        )


def validate_contact(section, section_id, origin):
    for group_index, group in enumerate(section["groups"]):
        for item in group.get("items") or []:
            item_type = item.get("type")
            where = f"{origin}: section '{section_id}' group {group_index + 1}"
            if item_type in CONTACT_VALUE_TYPES:
                if not item.get("value"):
                    raise ContentError(f"{where}: contact item '{item_type}' needs a 'value'")
            elif item_type in CONTACT_LINK_TYPES:
                if not item.get("label") or not item.get("url"):
                    raise ContentError(f"{where}: contact item '{item_type}' needs 'label' and 'url'")
            else:
                known = ", ".join(sorted(CONTACT_VALUE_TYPES | CONTACT_LINK_TYPES))
                raise ContentError(f"{where}: unknown contact item type '{item_type}'. Known: {known}")


def validate_wheelchart(section, section_id, origin):
    for index, slice_ in enumerate(section["slices"], start=1):
        for key in ("value", "width", "label"):
            if slice_.get(key) in (None, ""):
                raise ContentError(
                    f"{origin}: section '{section_id}' slice {index} is missing '{key}'"
                )
        shade = slice_.get("shade", 100)
        if not isinstance(shade, int) or not 0 < shade <= 100:
            raise ContentError(
                f"{origin}: section '{section_id}' slice {index} has invalid shade '{shade}' "
                f"(expected an integer between 1 and 100)"
            )


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

TEX_ESCAPES = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def tex_escape(value):
    if value is None:
        return ""
    return "".join(TEX_ESCAPES.get(char, char) for char in str(value))


def shade_filter(shade):
    """Turn a 1..100 shade into an accent color expression."""
    shade = 100 if shade is None else int(shade)
    return "accent" if shade >= 100 else f"accent!{shade}"


def color_definitions(colors):
    lines = []
    for name, value in colors.items():
        value = str(value)
        if value.startswith("#"):
            lines.append(f"\\definecolor{{{name}}}{{HTML}}{{{value[1:].upper()}}}")
        else:
            lines.append(f"\\colorlet{{{name}}}{{{value}}}")
    return lines


def build_environment(template_dir: Path) -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        block_start_string="((*",
        block_end_string="*))",
        variable_start_string="(((",
        variable_end_string=")))",
        comment_start_string="((=",
        comment_end_string="=))",
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        autoescape=False,
        undefined=StrictUndefined,
    )
    env.filters["tex"] = tex_escape
    env.filters["shade"] = shade_filter
    return env


def render(lang, content, style, labels, env, template_name):
    content = resolve_labels(content, labels, lang, origin=f"content/{lang}.yaml")

    label_macros = []
    for macro_name, key in LABEL_MACROS.items():
        entry = labels.get(key)
        if entry is None or lang not in entry:
            raise ContentError(
                f"content/labels.yaml: '{key}' is required for the '{lang}' build "
                f"(used by \\{macro_name} in latex/resume.cls)"
            )
        label_macros.append((macro_name, entry[lang]))

    template = env.get_template(template_name)
    return template.render(
        lang=lang,
        style=style,
        content=content,
        header=content["header"],
        sections=content["sections"],
        labels=labels,
        label_macros=label_macros,
        color_definitions=color_definitions(style.get("colors") or {}),
    )


# --------------------------------------------------------------------------
# compilation
# --------------------------------------------------------------------------

def compile_pdf(engine, tex_path: Path, out_dir: Path, class_dir: Path, workdir: Path):
    """Run the LaTeX engine twice; the layered page styles need a second pass."""
    binary = shutil.which(engine)
    if binary is None:
        raise ContentError(
            f"LaTeX engine '{engine}' was not found on PATH.\n"
            f"  The generated source is in {tex_path}.\n"
            f"  Compile it with Docker instead:\n"
            f"    docker run --rm -v ${{PWD}}:/data rabbitsharp/resume-builder --lang <lang>\n"
            f"  or re-run with --no-compile to only generate the .tex file."
        )

    env = os.environ.copy()
    separator = ";" if os.name == "nt" else ":"
    # Trailing separator keeps the default search paths in place.
    env["TEXINPUTS"] = separator.join([str(class_dir), str(workdir), ""])

    command = [
        binary,
        "-interaction=nonstopmode",
        "-halt-on-error",
        f"-output-directory={out_dir}",
        str(tex_path),
    ]

    for run in (1, 2):
        result = subprocess.run(
            command, cwd=str(workdir), env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding="utf-8", errors="replace",
        )
        if result.returncode != 0:
            log = out_dir / (tex_path.stem + ".log")
            sys.stderr.write(result.stdout[-4000:])
            raise ContentError(
                f"{engine} failed on pass {run} for {tex_path.name}. Full log: {log}"
            )


# --------------------------------------------------------------------------
# cli
# --------------------------------------------------------------------------

def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Build the resume PDF from YAML content and style definitions.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--lang", action="append", metavar="CODE",
        help="language to build; repeat for several. Defaults to 'de'.",
    )
    parser.add_argument(
        "--engine", choices=SUPPORTED_ENGINES,
        help="LaTeX engine; overrides document.engine from the style file.",
    )
    parser.add_argument(
        "--root", type=Path, default=REPO_ROOT,
        help="project root all other paths default to (the image mounts it at /data).",
    )
    parser.add_argument("--content-dir", type=Path, help="default: <root>/content")
    parser.add_argument("--style", type=Path, help="default: <root>/style/style.yaml")
    parser.add_argument("--template", type=Path, help="default: <root>/latex/templates/resume.tex.j2")
    parser.add_argument("--class-dir", type=Path, help="default: <root>/latex")
    parser.add_argument("--out", type=Path, help="default: <root>/out")
    parser.add_argument(
        "--no-compile", action="store_true",
        help="only generate the .tex file, do not run the LaTeX engine.",
    )

    args = parser.parse_args(argv)
    root = args.root.resolve()
    args.root = root
    defaults = {
        "content_dir": root / "content",
        "style": root / "style" / "style.yaml",
        "template": root / "latex" / "templates" / "resume.tex.j2",
        "class_dir": root / "latex",
        "out": root / "out",
    }
    for name, default in defaults.items():
        if getattr(args, name) is None:
            setattr(args, name, default)
    return args


def display(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def main(argv=None):
    args = parse_args(argv)
    languages = args.lang or ["de"]

    try:
        style = load_yaml(args.style)
        labels = load_yaml(args.content_dir / "labels.yaml")
    except ContentError as exc:
        sys.exit(f"error: {exc}")

    engine = args.engine or (style.get("document") or {}).get("engine", "xelatex")
    if engine not in SUPPORTED_ENGINES:
        sys.exit(f"error: unsupported engine '{engine}'. Choose one of: {', '.join(SUPPORTED_ENGINES)}")

    args.out.mkdir(parents=True, exist_ok=True)
    env = build_environment(args.template.parent)

    for lang in languages:
        origin = f"content/{lang}.yaml"
        try:
            content = load_yaml(args.content_dir / f"{lang}.yaml")
            validate(content, style, origin)
            document = render(lang, content, style, labels, env, args.template.name)

            tex_path = args.out / f"resume-{lang}.tex"
            tex_path.write_text(document, encoding="utf-8")
            print(f"generated {display(tex_path, args.root)}")

            if not args.no_compile:
                compile_pdf(engine, tex_path, args.out, args.class_dir, args.root)
                pdf_path = args.out / f"resume-{lang}.pdf"
                print(f"compiled  {display(pdf_path, args.root)} ({engine})")
        except ContentError as exc:
            sys.exit(f"error: {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
