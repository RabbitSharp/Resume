#!/bin/sh
# Entrypoint of the resume builder image.
#
# The repository is expected to be mounted at /data. All arguments are passed
# straight through to builder/build.py, e.g.:
#   docker run --rm -v ${PWD}:/data rabbitsharp/resume-builder --lang de --engine lualatex

set -e

if [ ! -d /data/content ]; then
    echo "error: /data/content not found." >&2
    echo "       Mount the repository root into /data, for example:" >&2
    echo "       docker run --rm -v \${PWD}:/data rabbitsharp/resume-builder --lang de" >&2
    exit 1
fi

mkdir -p /data/out

exec python3 /opt/resume-builder/builder/build.py --root /data "$@"
