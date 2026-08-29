# Self-contained resume builder: renders the YAML content into LaTeX and
# compiles it to PDF.
#
# Build from the repository root:
#   docker build -f docker/Dockerfile -t rabbitsharp/resume-builder .
#
# Run from the repository root:
#   docker run --rm -v ${PWD}:/data rabbitsharp/resume-builder --lang de

FROM ubuntu:24.04

ENV TZ=Europe/Berlin \
    DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1

# TeX Live is installed as a curated subset instead of texlive-full:
# ~2.2 GB instead of ~8 GB, while still providing everything resume.cls
# needs (KOMA-Script, TikZ, tcolorbox, fontawesome, academicons, fontspec).
# Both xelatex and lualatex are available; pick one via style.yaml or --engine.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        fontconfig \
        fonts-crosextra-carlito \
        fonts-font-awesome \
        python3 \
        python3-jinja2 \
        python3-yaml \
        texlive-fonts-extra \
        texlive-fonts-recommended \
        texlive-lang-german \
        texlive-latex-extra \
        texlive-luatex \
        texlive-xetex \
        tzdata && \
    rm -rf /var/lib/apt/lists/*

# fontspec resolves FontAwesome and academicons by font name, so the TeX Live
# font trees have to be visible to fontconfig. The type1 tree is deliberately
# left out: its FontAwesome.pfb would shadow the OTF from fonts-font-awesome
# and produce empty boxes instead of icons.
RUN printf '%s\n' \
        '<?xml version="1.0"?>' \
        '<!DOCTYPE fontconfig SYSTEM "fonts.dtd">' \
        '<fontconfig>' \
        '  <dir>/usr/share/texlive/texmf-dist/fonts/opentype</dir>' \
        '  <dir>/usr/share/texlive/texmf-dist/fonts/truetype</dir>' \
        '</fontconfig>' > /etc/fonts/conf.d/09-texlive-fonts.conf && \
    fc-cache -fs

COPY builder/ /opt/resume-builder/builder/
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# The repository is expected to be mounted here.
WORKDIR /data
VOLUME ["/data"]

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["--lang", "de"]
