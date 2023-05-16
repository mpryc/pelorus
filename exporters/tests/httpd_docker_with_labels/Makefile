VERSION ?= latest
IMAGE_TAG_BASE ?= quay.io/pelorus/httpd-sample-app

# Image URL to use all building/pushing image targets
IMG ?= $(IMAGE_TAG_BASE):$(VERSION)

LAST_COMMIT_DATE_TIME := $(shell git log -1 --format='%ad' --date='format:%a %b %d %H:%M:%S %Y %z')
LAST_COMMIT_SHA := $(shell git rev-parse HEAD)

.PHONY: all
all: podman-build

.PHONY: podman-build
podman-build:
	podman build \
	    --build-arg LAST_COMMIT_DATE_TIME="$(LAST_COMMIT_DATE_TIME)" \
	    --build-arg LAST_COMMIT_SHA="$(LAST_COMMIT_SHA)" \
	    -t ${IMG} .

.PHONY: podman-push
podman-push:
	podman push ${IMG}
