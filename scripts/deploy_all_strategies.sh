#!/usr/bin/env bash
set -euo pipefail

IMAGE="${IMAGE:-aceest-fitness:local}"
APP_VERSION="${APP_VERSION:-3.2.4}"

declare -A NS=(
  [rolling-update]="aceest-rolling"
  [blue-green]="aceest-bluegreen"
  [canary]="aceest-canary"
  [ab-testing]="aceest-ab"
  [shadow]="aceest-shadow"
)
declare -A PORT=(
  [rolling-update]=30081
  [blue-green]=30082
  [canary]=30083
  [ab-testing]=30084
  [shadow]=30085
)

command -v minikube >/dev/null || { echo "minikube not installed"; exit 1; }
command -v kubectl  >/dev/null || { echo "kubectl not installed";  exit 1; }
command -v docker   >/dev/null || { echo "docker not installed";   exit 1; }

if ! minikube status >/dev/null 2>&1; then
  echo "==> Starting Minikube"
  minikube start --cpus=4 --memory=4096 --driver=docker
fi

if [[ "$IMAGE" == "aceest-fitness:local" ]]; then
  echo "==> Building image inside Minikube"
  eval "$(minikube docker-env)"
  docker build --build-arg APP_VERSION="$APP_VERSION" -t "$IMAGE" .
  eval "$(minikube docker-env --unset)"
fi

for strategy in "${!NS[@]}"; do
  ns="${NS[$strategy]}"
  port="${PORT[$strategy]}"
  echo
  echo "============================================================"
  echo "  Strategy:  $strategy"
  echo "  Namespace: $ns   Port: $port"
  echo "============================================================"

  kubectl create ns "$ns" --dry-run=client -o yaml | kubectl apply -f -

  case "$strategy" in
    blue-green|canary|ab-testing|shadow) base="" ;;
    *)                                    base="k8s/base/service.yaml" ;;
  esac

  tmp=$(mktemp -d)
  for f in $base "k8s/${strategy}"/*.yaml; do
    [ -f "$f" ] || continue
    sed -e "s|IMAGE_PLACEHOLDER|${IMAGE}|g" \
        -e "s|namespace: aceest\b|namespace: ${ns}|g" \
        -e "s|namespace: aceest }|namespace: ${ns} }|g" \
        -e "s|nodePort: 30080|nodePort: ${port}|g" "$f" > "$tmp/$(basename "$f")"
  done
  kubectl -n "$ns" apply -f "$tmp/"
  rm -rf "$tmp"
  kubectl -n "$ns" wait --for=condition=Available deploy --all --timeout=120s || true
done

IP=$(minikube ip)
echo
echo "============================================================"
echo "  SUBMISSION ENDPOINTS"
echo "============================================================"
for s in rolling-update blue-green canary ab-testing shadow; do
  printf "  %-15s  http://%s:%s/\n" "$s" "$IP" "${PORT[$s]}"
done
