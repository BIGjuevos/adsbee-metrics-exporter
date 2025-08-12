#!/usr/bin/env bash

set -Eeuo pipefail

# Release script for building and publishing Docker images to Docker Hub.
# Default repo: bigjuevos/adsbee-metrics-exporter

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

IMAGE_REPO="bigjuevos/adsbee-metrics-exporter"
IMAGE_TAG=""        # If empty, inferred from tag or timestamp
PUBLISH_LATEST=true  # Also tag and push :latest by default
PLATFORMS="linux/amd64,linux/arm64"
PUSH=true
PERFORM_LOGIN=false
DRY_RUN=false

red() { printf "\033[31m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
yellow() { printf "\033[33m%s\033[0m\n" "$*"; }

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

Build and publish multi-arch Docker images for adsbee-metrics-exporter.

Options:
  -r, --repo <name>        Docker Hub repo (default: ${IMAGE_REPO})
  -t, --tag  <tag>         Image tag to publish (e.g., v0.1.0 or 0.1.0)
      --no-latest          Do not also tag/push :latest
  -p, --platforms <list>   Platforms for buildx (default: ${PLATFORMS})
      --no-push            Build but do not push (implies --load for single-arch)
      --login              Run 'docker login' using DOCKERHUB_USERNAME/DOCKERHUB_TOKEN
      --dry-run            Print the commands without executing
  -h, --help               Show this help

Environment:
  DOCKERHUB_USERNAME   Username for Docker Hub (used with --login)
  DOCKERHUB_TOKEN      Access token or password for Docker Hub (used with --login)

Examples:
  # Publish with inferred tag from current git tag (or timestamp fallback)
  $(basename "$0") --login

  # Publish a specific version and latest
  $(basename "$0") -t v0.1.0 --login

  # Publish to a different repository
  $(basename "$0") -r myuser/adsbee-metrics-exporter -t 0.1.0 --login
EOF
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -r|--repo)
        IMAGE_REPO="$2"; shift 2;;
      -t|--tag)
        IMAGE_TAG="$2"; shift 2;;
      --no-latest)
        PUBLISH_LATEST=false; shift;;
      -p|--platforms)
        PLATFORMS="$2"; shift 2;;
      --no-push)
        PUSH=false; shift;;
      --login)
        PERFORM_LOGIN=true; shift;;
      --dry-run)
        DRY_RUN=true; shift;;
      -h|--help)
        usage; exit 0;;
      *)
        red "Unknown option: $1"; echo; usage; exit 1;;
    esac
  done
}

cmd() {
  if [[ "$DRY_RUN" == true ]]; then
    echo "+ $*"
  else
    eval "$@"
  fi
}

ensure_requirements() {
  command -v docker >/dev/null 2>&1 || { red "docker is required"; exit 1; }
  if ! docker buildx version >/dev/null 2>&1; then
    yellow "docker buildx not found; attempting to enable..."
    # On modern Docker Desktop, buildx is included. If not available, user must install.
    red "docker buildx is required. Please install/enable Buildx and try again."; exit 1
  fi

  # Ensure a builder exists and is active
  if ! docker buildx inspect >/dev/null 2>&1; then
    yellow "No active buildx builder; creating one..."
    cmd "docker buildx create --name multiarch --use"
  fi
}

infer_tag() {
  if [[ -n "${IMAGE_TAG}" ]]; then
    return
  fi
  # Prefer exact git tag on HEAD
  local git_tag
  git_tag=$(git -C "${REPO_ROOT}" describe --tags --exact-match 2>/dev/null || true)
  if [[ -z "$git_tag" ]]; then
    # Fallback to latest tag
    git_tag=$(git -C "${REPO_ROOT}" describe --tags --abbrev=0 2>/dev/null || true)
  fi
  if [[ -n "$git_tag" ]]; then
    IMAGE_TAG="$git_tag"
  else
    # Timestamp fallback
    IMAGE_TAG="$(date +%Y.%m.%d-%H%M%S)"
    yellow "No git tag found; using timestamp tag: ${IMAGE_TAG}"
  fi
}

normalize_tag() {
  # Strip a leading 'v' to avoid duplicates like v0.1.0 vs 0.1.0 if desired;
  # Docker tags allow both, but we'll keep exactly what user provided or inferred.
  IMAGE_TAG="${IMAGE_TAG}"
}

login_if_requested() {
  if [[ "$PERFORM_LOGIN" == true ]]; then
    if [[ -z "${DOCKERHUB_USERNAME:-}" || -z "${DOCKERHUB_TOKEN:-}" ]]; then
      red "--login requires DOCKERHUB_USERNAME and DOCKERHUB_TOKEN to be set"; exit 1
    fi
    yellow "Logging in to Docker Hub as ${DOCKERHUB_USERNAME}..."
    cmd "echo \"${DOCKERHUB_TOKEN}\" | docker login -u \"${DOCKERHUB_USERNAME}\" --password-stdin"
  fi
}

main() {
  parse_args "$@"
  ensure_requirements
  infer_tag
  normalize_tag

  local build_cmd=(
    docker buildx build
    "${REPO_ROOT}"
    -f "${REPO_ROOT}/Dockerfile"
    --platform "${PLATFORMS}"
    -t "${IMAGE_REPO}:${IMAGE_TAG}"
  )

  if [[ "$PUBLISH_LATEST" == true ]]; then
    build_cmd+=( -t "${IMAGE_REPO}:latest" )
  fi

  if [[ "$PUSH" == true ]]; then
    build_cmd+=( --push )
  else
    # --load only supports single-arch. If multiple platforms requested, warn the user.
    if [[ "$PLATFORMS" == *","* ]]; then
      yellow "--no-push with multiple platforms won't load into local Docker. Consider setting -p linux/amd64."
    fi
    build_cmd+=( --load )
  fi

  green "Building image for repo: ${IMAGE_REPO}"
  green "Tag: ${IMAGE_TAG}${PUBLISH_LATEST:+ and latest}"
  green "Platforms: ${PLATFORMS}"

  login_if_requested

  cmd "${build_cmd[@]}"

  if [[ "$PUSH" == true ]]; then
    green "Published: ${IMAGE_REPO}:${IMAGE_TAG}"
    if [[ "$PUBLISH_LATEST" == true ]]; then
      green "Published: ${IMAGE_REPO}:latest"
    fi
  else
    green "Build complete (not pushed)."
  fi
}

main "$@"


