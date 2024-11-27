#!/bin/bash
BASEDIR=$(realpath $(dirname $0))
CONTEXT_TARGET=$(dirname $BASEDIR)

if git submodule status | grep --quiet '^-'; then
    echo "Seems like a new clone: initializing submodules..."
    git submodule init
fi

git submodule update

IMAGE_NAME_TAG="${RAT_IMAGE_WBS:=cerit.io/rationai/production/wsi-service-auth:v0.13.3}"

echo
echo "Starting build: docker build -t "$IMAGE_NAME_TAG" -f Dockerfile $CONTEXT_TARGET"
echo
docker build -t "$IMAGE_NAME_TAG" -f Dockerfile $CONTEXT_TARGET