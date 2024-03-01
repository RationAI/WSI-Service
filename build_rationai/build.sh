#!/bin/bash
BASEDIR=$(realpath $(dirname $0))
CONTEXT_TARGET=$(dirname $BASEDIR)

cd $CONTEXT_TARGET

if git submodule status | grep --quiet '^-'; then
    echo "Seems like a new clone: initializing submodules..."
    git submodule init
fi

git submodule update

echo
echo "Starting build: docker build -t "cerit.io/rationai/production/wsi-service-auth:v0.0.1" -f $BASEDIR/Dockerfile ."
echo
docker build -t "cerit.io/rationai/production/wsi-service-auth:v0.0.1" -f $BASEDIR/Dockerfile .
cd -
