#!/bin/bash
if [[ "$(docker manifest inspect $1 2> /dev/null)" == "" ]]; then
  exit 0
else
  echo "$1 already exists"
  exit 1
fi