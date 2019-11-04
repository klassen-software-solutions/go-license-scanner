#!/bin/bash

DOCKER_IMAGE_NAME="$(basename $(pwd))"
DOCKER_IMAGE_TAG=${CI_PIPELINE_ID:-"999999"}
