#!/bin/bash
set -eu

# Example usage:
# export PROMOTE_FROM="1.10/edge"
# export PROMOTE_TO="1.10/beta 1.10/candidate edge beta candidate"
# snaps/promote.sh

scripts_path=$(dirname "$0")
ARCH=${KUBE_ARCH:-"amd64"}

GH_USER="${GH_USER:-}"
GH_TOKEN="${GH_TOKEN:-}"
SNAPS="${SNAPS:-kubectl kube-apiserver kube-controller-manager kube-scheduler kubelet kube-proxy kubeadm kubernetes-test}"

echo PROMOTE_FROM="$PROMOTE_FROM"
echo PROMOTE_TO="$PROMOTE_TO"
echo SNAPS="$SNAPS"
echo ARCH="$ARCH"

. $scripts_path/retry.sh
. $scripts_path/utilities.sh

# Ensure we are the correct user (jenkins job does a 'snapcraft login $token')
if [[ "${SNAPS}" =~ "-eks" ]]; then
  if ! $(snapcraft whoami | grep -q canonical-cloud-snaps); then
    echo "Cannot release CPC snaps (wrong user)"
    exit 1
  fi
else
  if ! $(snapcraft whoami | grep -q cdkbot); then
    echo "Cannot release cdkbot snaps (wrong user)"
    exit 1
  fi
fi

create_git_branch_if_not_exists () {
  if ! git ls-remote --exit-code --heads https://github.com/juju-solutions/cdk-addons.git release-${1}
  then
    if [ -z "$GH_USER" ] || [ -z $GH_TOKEN ]; then
      echo "GH_USER or GH_TOKEN not set, not creating branch for stable promotion release-${1}."
    else
      echo "Creating new branch for release-${1}."
      create_branch "juju-solutions" "cdk-addons" ${GH_USER} ${GH_TOKEN} release-$1
    fi
  fi
}

# Create a branch for any stable promotion that doesn't have one.
for branch in $PROMOTE_TO; do
  if [[ $branch = *"/stable"* ]]; then
    IFS='/' read -ra VER <<< "$branch"
    create_git_branch_if_not_exists $VER
  fi
done

# Release the snaps
declare -A kube_arch_to_snap_arch=(
    [ppc64le]=ppc64el
    [arm]=armhf
)
for snap in $SNAPS; do
  revisions="$(snapcraft revisions $snap | grep "${kube_arch_to_snap_arch[$ARCH]:-$ARCH}" | grep " ${PROMOTE_FROM}\*" | cut -d " " -f 1)"
  for rev in $revisions; do
    for target in $PROMOTE_TO; do
      echo snapcraft release $snap $rev $target
      retry snapcraft release $snap $rev $target
    done
  done
done
