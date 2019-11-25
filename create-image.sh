#!/bin/bash

DOCKER_REGISTRY=${DOCKER_REGISTRY:-"docker-fts.rep01.frauscher.intern"}
source current-version.sh

echo "Building..."
echo "  registry: ${DOCKER_REGISTRY}"
echo "  name: ${DOCKER_IMAGE_NAME}"
echo "  tag: ${DOCKER_IMAGE_TAG}"

rm -rf dist/*.whl
docker build -t "$DOCKER_REGISTRY/${DOCKER_IMAGE_NAME}:${DOCKER_IMAGE_TAG}" .
