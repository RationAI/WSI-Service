#!/bin/bash
BASEDIR=$(realpath $(dirname $0))
CONTEXT_TARGET=$(dirname $BASEDIR)
cd $CONTEXT_TARGET

#todo submodule pull if detected...

if git submodule status | grep --quiet '^-'; then
    echo "Seems like a new clone: initializing submodules..."
    git submodule init
fi

git submodule update
IMAGE_NAME_TAG="${RAT_IMAGE_WBS:=wsi-service-standalone:v0.15.3}"

echo
echo "Starting build: docker build -t "$IMAGE_NAME_TAG" -f $BASEDIR/Dockerfile ."
echo
docker build -t "$IMAGE_NAME_TAG" -f $BASEDIR/Dockerfile .
cd -
