#!/bin/bash
# macOS-compatible (bash 3.2) - no associative arrays.
set -eu

IMAGE="${IMAGE:-aceest-fitness:local}"
APP_VERSION="${APP_VERSION:-3.2.4}"
STRATEGIES="rolling-update blue-green canary ab-testing shadow"

ns_for() {
  case "$1" in
    rolling-update) echo "aceest-rolling" ;;
    blue-green)     echo "aceest-bluegreen" ;;
    canary)         echo "aceest-canary" ;;
    ab-testing)     echo "aceest-ab" ;;
    shadow)         echo "aceest-shadow" ;;
  esac
}

port_for() {
  case "$1" in
    rolling-update) echo 30081 ;;
    blue-green)     echo 30082 ;;
    canary)         echo 30083 ;;
    ab-testing)     echo 30084 ;;
    shadow)         echo 30085 ;;
  esac
}

command -v minikube >/dev/null || { echo "minikube not installed"; exit 1; }
command -v kubectl  >/dev/null || { echo "kubectl not installed";  exit 1; }
command -v docker   >/dev/null || { echo "docker not installed";   exit 1; }

if ! minikube status >/dev/null 2>&1; then
  echo "==> Starting Minikube"
  minikube start --cpus=4 --memory=4096 --driver=docker
fi

if [ "$IMAGE" = "aceest-fitness:local" ]; then
  echo "==> Building image inside Minikube"
  eval "$(minikube docker-env)"
  docker build --build-arg APP_VERSION="$APP_VERSION" -t "$IMAGE" .
  eval "$(minikube docker-env --unset)"
fi

for strategy in $STRATEGIES; do
  ns=$(ns_for "$strategy")
  port=$(port_for "$strategy")
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
  for f in $base k8s/${strategy}/*.yaml; do
    [ -f "$f" ] || continue
    sed -e "s|IMAGE_PLACEHOLDER|${IMAGE}|g" \
        -e "s|namespace: aceest$|namespace: ${ns}|g" \
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
for s in $STRATEGIES; do
  printf "  %-15s  http://%s:%s/\n" "$s" "$IP" "$(port_for $s)"
done
