#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
shell_path="$repo_root/.tools/aihubshell"

ensure_aihub_shell() {
  if [[ -x "$shell_path" ]]; then
    return
  fi

  mkdir -p "$repo_root/.tools"
  if curl -L --fail --show-error --silent -o "$shell_path" https://api.aihub.or.kr/api/aihubshell.do; then
    chmod +x "$shell_path"
  else
    printf '%s\n' "Warning: could not refresh aihubshell; falling back to AI-Hub download API v0.6." >&2
  fi
}

aihub_download_version() {
  if [[ -n "${AIHUB_DOWNLOAD_VERSION:-}" ]]; then
    printf '%s\n' "$AIHUB_DOWNLOAD_VERSION"
    return
  fi

  if [[ -r "$shell_path" ]]; then
    local version
    version="$(awk -F'"' '/^VER=/ { print $2; exit }' "$shell_path")"
    printf '%s\n' "${version:-0.6}"
    return
  fi

  printf '%s\n' "0.6"
}

remove_stale_empty_zips() {
  local target_dir="$1"
  local zip_file

  while IFS= read -r zip_file; do
    printf '%s\n' "Removing stale empty zip: $zip_file"
    rm "$zip_file"
  done < <(find "$target_dir" -type f -name '*.zip' -size 0 -print 2>/dev/null)
}

merge_part_files() {
  local root="$1"
  local prefix
  local part_file
  local suffix
  local part_files
  local part_count

  while IFS= read -r prefix; do
    part_files=()
    while IFS= read -r part_file; do
      part_files+=("$part_file")
    done < <(
      for part_file in "$prefix".part*; do
        [[ -e "$part_file" ]] || continue
        suffix="${part_file##*.part}"
        [[ "$suffix" =~ ^[0-9]+$ ]] || continue
        printf '%s\t%s\n' "$suffix" "$part_file"
      done | sort -n -k1,1 | cut -f2-
    )

    part_count="${#part_files[@]}"
    if [[ "$part_count" -eq 0 ]]; then
      printf '%s\n' "No part files found for merge prefix: $prefix" >&2
      return 1
    fi

    printf '%s\n' "Merging $part_count part file(s): $prefix"
    cat "${part_files[@]}" > "$prefix"
    if [[ ! -s "$prefix" ]]; then
      printf '%s\n' "Merged file is empty: $prefix" >&2
      return 1
    fi
    rm "${part_files[@]}"
  done < <(find "$root" -type f -name '*.part[0-9]*' -print | sed -E 's/\.part[0-9]+$//' | sort -u)
}

validate_download_artifacts() {
  local target_dir="$1"
  local empty_zip
  local remaining_part
  local zip_file
  local zip_count
  local zip_size

  empty_zip="$(find "$target_dir" -type f -name '*.zip' -size 0 -print -quit)"
  if [[ -n "$empty_zip" ]]; then
    printf '%s\n' "AI-Hub created an empty zip; download did not complete: $empty_zip" >&2
    return 1
  fi

  remaining_part="$(find "$target_dir" -type f -name '*.part[0-9]*' -print -quit)"
  if [[ -n "$remaining_part" ]]; then
    printf '%s\n' "AI-Hub part files remain after merge; download did not complete: $remaining_part" >&2
    return 1
  fi

  zip_count=0
  while IFS= read -r zip_file; do
    zip_count=$((zip_count + 1))
    if ! unzip -tq "$zip_file" >/dev/null; then
      printf '%s\n' "Downloaded zip failed integrity check: $zip_file" >&2
      return 1
    fi
    zip_size="$(wc -c < "$zip_file" | tr -d ' ')"
    printf '%s\n' "Validated zip: $zip_file (${zip_size} bytes)"
  done < <(find "$target_dir" -type f -name '*.zip' ! -size 0 -print)

  if [[ "$zip_count" -eq 0 ]]; then
    printf '%s\n' "No zip files were produced under: $target_dir" >&2
    return 1
  fi
}

require_free_space() {
  local target_dir="$1"
  local required_bytes="$2"
  local label="$3"
  local free_kib
  local free_bytes

  mkdir -p "$target_dir"
  free_kib="$(df -Pk "$target_dir" | awk 'NR == 2 { print $4 }')"
  free_bytes=$((free_kib * 1024))
  if [[ "$free_bytes" -lt "$required_bytes" ]]; then
    printf '%s\n' "Not enough free space for $label." >&2
    printf '%s\n' "Available: $free_bytes bytes; required: $required_bytes bytes." >&2
    printf '%s\n' "Use AIHUB_TARGET_DIR=/path/on/larger/disk or free more space, then rerun." >&2
    return 1
  fi
}

download_target() {
  local target_dir="$1"
  local dataset_key="$2"
  local file_keys="$3"
  local version
  local download_url
  local http_status
  local curl_exit

  mkdir -p "$target_dir"
  remove_stale_empty_zips "$target_dir"
  cd "$target_dir"

  if [[ -e "download.tar" ]]; then
    mv "download.tar" "download_$(date +"%Y%m%d_%H%M%S").tar"
    printf '%s\n' "Existing download.tar was backed up before retry."
  fi

  version="$(aihub_download_version)"
  download_url="https://api.aihub.or.kr/down/$version/$dataset_key.do?fileSn=$file_keys"

  set +e
  http_status="$(
    curl -L -C - -o "download.tar" -H "apikey:$AIHUB_API_KEY" -w "%{http_code}" "$download_url"
  )"
  curl_exit="$?"
  set -e

  if [[ "$curl_exit" -ne 0 ]]; then
    printf '%s\n' "AI-Hub curl download failed with exit code $curl_exit." >&2
    return "$curl_exit"
  fi

  if [[ "$http_status" != "200" ]]; then
    printf '%s\n' "AI-Hub download failed with HTTP status $http_status." >&2
    if [[ -s "download.tar" ]]; then
      sed -n '1,80p' "download.tar" >&2
    fi
    rm "download.tar"
    return 1
  fi

  if [[ ! -s "download.tar" ]]; then
    printf '%s\n' "AI-Hub response body is empty." >&2
    rm "download.tar"
    return 1
  fi

  if ! tar -tf "download.tar" >/dev/null; then
    printf '%s\n' "AI-Hub response is not a tar archive." >&2
    sed -n '1,80p' "download.tar" >&2
    rm "download.tar"
    return 1
  fi

  tar -xvf "download.tar"
  merge_part_files "$PWD"
  rm "download.tar"
  validate_download_artifacts "$target_dir"
}

if [[ -z "${AIHUB_API_KEY:-}" ]]; then
  printf '%s\n' "AIHUB_API_KEY is missing. Export it first, then rerun."
  exit 2
fi

ensure_aihub_shell

target="${1:-dataset119-validation-labels}"
target_dir=""
case "$target" in
  dataset119-validation-labels)
    target_dir="$repo_root/data/raw/aihub_gyeongsang_119"
    download_target "$target_dir" 119 "572713"
    ;;
  dataset119-all-labels)
    target_dir="$repo_root/data/raw/aihub_gyeongsang_119"
    download_target "$target_dir" 119 "572713,572701"
    ;;
  dataset119-validation-source-audio | dataset119-validation-audio)
    target_dir="${AIHUB_TARGET_DIR:-$repo_root/data/raw/aihub_gyeongsang_119_validation_audio}"
    require_free_space "$target_dir" $((90 * 1024 * 1024 * 1024)) "AI-Hub 119 validation source audio"
    download_target "$target_dir" 119 "572714"
    ;;
  senior-gyeongsang-validation-labels)
    target_dir="$repo_root/data/raw/aihub_senior_gangwon_gyeongsang_71517"
    download_target "$target_dir" 71517 "538325,538326,538327"
    ;;
  *)
    printf '%s\n' "Unknown target: $target"
    printf '%s\n' "Targets: dataset119-validation-labels, dataset119-all-labels, dataset119-validation-source-audio, senior-gyeongsang-validation-labels"
    exit 2
    ;;
esac

printf '%s\n' "AI-Hub download target completed: $target_dir"
