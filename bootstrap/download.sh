# POSIX download helpers; only verified bytes are installed.
ai_dlc_hash() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | cut -d ' ' -f 1
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | cut -d ' ' -f 1
    else
        echo 'A SHA256 implementation (sha256sum or shasum) is required.' >&2
        return 1
    fi
}

ai_dlc_download() {
    ai_dlc_url=$1
    ai_dlc_expected=$2
    ai_dlc_destination=$3
    case "$ai_dlc_url" in https://*) ;; *) echo 'Bootstrap downloads require HTTPS.' >&2; return 1;; esac
    [ "${#ai_dlc_expected}" -eq 64 ] || { echo 'Invalid SHA256 pin.' >&2; return 1; }
    ai_dlc_partial="$ai_dlc_destination.partial"
    curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 "$ai_dlc_url" --output "$ai_dlc_partial" || return 1
    ai_dlc_actual=$(ai_dlc_hash "$ai_dlc_partial") || return 1
    [ "$ai_dlc_actual" = "$ai_dlc_expected" ] || { echo 'Artifact digest mismatch; refusing installation.' >&2; return 1; }
    mv "$ai_dlc_partial" "$ai_dlc_destination"
}
