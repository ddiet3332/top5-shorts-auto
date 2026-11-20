#!/usr/bin/env bash
set -euo pipefail

work="$(mktemp -d "$RUNNER_TEMP/top5-tools.XXXXXX")"
download() {
    local url="$1" checksum="$2" target="$3"
    curl --fail --silent --show-error --location --retry 2 --retry-max-time 75 \
        --connect-timeout 10 --max-time 45 "$url" -o "$target"
    printf '%s  %s\n' "$checksum" "$target" | sha256sum --check
}

if ! command -v ffmpeg >/dev/null || ! command -v ffprobe >/dev/null; then
    mkdir -p "$work/bin"
    release="https://github.com/eugeneware/ffmpeg-static/releases/download/b6.0"
    download "$release/ffmpeg-linux-x64.gz" \
        17c1ae10b52ac499180679fe6ba77e17642390c4eedb0f1e3b0ac045da55128f "$work/ffmpeg.gz"
    download "$release/ffprobe-linux-x64.gz" \
        88ca6818d82a70e87de2bb6166026ad411528c72eda0e4e11ed25d185116ee17 "$work/ffprobe.gz"
    for executable in ffmpeg ffprobe; do
        gzip -dc "$work/$executable.gz" > "$work/bin/$executable"
        chmod 755 "$work/bin/$executable"
    done
    export PATH="$work/bin:$PATH"
    printf '%s\n' "$work/bin" >> "$GITHUB_PATH"
fi

if [[ "$TOP5_INSTALL_FONTS" == "true" ]]; then
    if [[ ! -f /usr/share/fonts/truetype/nanum/NanumGothicBold.ttf ]]; then
        download "https://deb.debian.org/debian/pool/main/f/fonts-nanum/fonts-nanum_20200506-1_all.deb" \
            5e86c346e6485b694e1f0ebd27132892fcf014d1b975de4fd21d1654ddf37043 "$work/nanum.deb"
        sudo dpkg-deb --extract "$work/nanum.deb" /
    fi
    if [[ ! -f /usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc ]]; then
        download "https://deb.debian.org/debian/pool/main/f/fonts-noto-cjk/fonts-noto-cjk_20240730+repack1-1_all.deb" \
            f5dc28a754e17327d99f0a612134d92c8dd6187314ae967cb77f25df60860139 "$work/noto.deb"
        sudo dpkg-deb --extract "$work/noto.deb" /
    fi
    fc-cache -f
    ffmpeg -hide_banner -filters | awk '$2 == "ass" { found = 1 } END { exit !found }'
fi
ffmpeg -version | sed -n '1p'
ffprobe -version | sed -n '1p'
