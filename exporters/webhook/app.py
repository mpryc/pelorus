#!/usr/bin/env python3
#
# Copyright Red Hat
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

import asyncio
import http
import json
import logging
import os
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Header, Request, Response
from fastapi.responses import PlainTextResponse
from prometheus_client import Counter, generate_latest
from prometheus_client.core import REGISTRY
from pydantic import BaseModel, ValidationError, parse_obj_as

import importlib

import pelorus
from committime import CommitMetric
from pelorus.config import load_and_log
from webhook.handlers.pelorus_webhook import PelorusWebhookPlugin
from webhook.models.github_webhook import GitHubCommit, GitHubDeliveryHeaders
from webhook.models.in_memory_metric import (
    PelorusGaugeMetricFamily,
    in_memory_commit_metrics,
)
from webhook.models.pelorus_webhook import (
    CommitTimePelorusPayload,
    PelorusDeliveryHeaders,
)

pelorus.setup_logging()

DEFAULT_PLUGIN_FOLDER="handlers"

plugins={}

webhook_received = Counter("webhook_received_total", "Number of received webhooks")
webhook_processed = Counter("webhook_processed_total", "Number of processed webhooks")

commit_hash_set = set()

# APIRouter here... ?
app = FastAPI(title="Pelorus Webhook receiver")


def register_plugin(webhook_plugin: PelorusWebhookPlugin) -> bool:
    try:
        is_pelorus_plugin = getattr(webhook_plugin, "is_pelorus_webhook_handler", None)
        has_register = getattr(webhook_plugin, "register", None)
        if callable(is_pelorus_plugin) and callable(has_register):
            plugins[webhook_plugin.register()] = webhook_plugin
            logging.info("Registered webhook plugin for user-agent: '%s'" % webhook_plugin.register())
            return True
    except NotImplementedError:
        logging.warning("Could not register plugin: %s" % str(webhook_plugin))
        pass
    return False

def load_plugins(plugins_path: Optional[str] = DEFAULT_PLUGIN_FOLDER) -> bool:
    for filename in os.listdir(plugins_path):
        if filename.endswith('_handler.py'):
            module = importlib.import_module(f'{plugins_path}.{filename[:-3]}')
            for name in dir(module):
                obj = getattr(module, name)
                if isinstance(obj, type):
                    # Do not register base class
                    if str(obj.__name__) == "PelorusWebhookPlugin":
                        continue                    
                    register_plugin(obj)

class PelorusWebhookResponse(BaseModel):
    http_response: str
    http_response_code: int

def allowed_hosts(request: Request) -> bool:
    # Raise exception if the request is not from allowed hosts
    return True

# This should be our env/secret from env
# Plus it's dependent on the service itself. e.g. github may use different secret
# https://towardsdev.com/build-a-webhook-endpoint-with-fastapi-d14bf1b1d55d
SECRET_TOKEN = None


async def get_handler(user_agent: str):
    for handler in plugins.values():
        if handler.can_handle(user_agent):
            return handler
    return None


@app.post(
    "/pelorus/webhook",
    status_code=http.HTTPStatus.ACCEPTED,
    dependencies=[Depends(allowed_hosts)],
)
async def pelorus_webhook(
    request: Request,
    response: Response,
    payload: dict,
    user_agent: str = Header(None),
    content_length: int = Header(...),
) -> PelorusWebhookResponse:

    webhook_received.inc()

    if content_length > 100000:
        raise HTTPException(
            status_code=http.HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            detail="Content length too big.",
        )

    logging.debug("User-agent: %s" % user_agent)
    webhook_handler = await get_handler(user_agent)
    if not webhook_handler:
        logging.warning("Could not find webhook handler for the user agent: %s" % user_agent)
        raise HTTPException(
            status_code=http.HTTPStatus.PRECONDITION_FAILED,
            detail="Unsupported request.",
        )

    payload_headers = None
    payload_model = None
    return



    try:
        logging.debug("User-agent: %s" % user_agent)
        webhook_handler = await get_handler(user_agent)
        breakpoint()
        payload_headers = await webhook_handler.handshake(user_agent)

        if user_agent.startswith("GitHub-Hookshot/"):
            payload_headers = parse_obj_as(GitHubDeliveryHeaders, request.headers)
        elif user_agent.startswith("Pelorus-Webhook/"):
            payload_headers = parse_obj_as(PelorusDeliveryHeaders, request.headers)
        else:
            raise HTTPException(
                status_code=http.HTTPStatus.PRECONDITION_FAILED,
                detail="Unsupported request.",
            )

    except ValidationError as ex:
        logging.error(request.headers)
        logging.error(ex)
        raise HTTPException(
            status_code=http.HTTPStatus.BAD_REQUEST,
            detail="Improper headers.",
        )

    # TODO Logic to validate the secret and payload
    # Should this be per received header type?
    #    if SECRET_TOKEN and x_secret_signature != SECRET_TOKEN:
    #        raise HTTPException...

    # Register webhook ping/pong
    if payload_headers and payload_headers.event_type == "ping":
        return PelorusWebhookResponse(
            http_response="pong", http_response_code=http.HTTPStatus.OK
        )

    # only_allow_known_event_types could be used here
    if payload_headers and payload_headers.event_type:
        try:
            payload = await request.json()
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=http.HTTPStatus.BAD_REQUEST,
                detail="Invalid payload format.",
            )

        try:
            if user_agent.startswith("GitHub-Hookshot/"):
                if payload_headers.event_type == "push":
                    payload_model = GitHubCommit(**payload)
                    metric = CommitMetric(
                        name=payload_model.repository.full_name,
                        commit_timestamp=payload_model.repository.commit_timestamp,
                        commit_hash=payload_model.commit_hash,
                    )
                    asyncio.create_task(prometheus_metric(metric))
            elif user_agent.startswith("Pelorus-Webhook/"):
                if (
                    payload_headers.event_type
                    == PelorusDeliveryHeaders.PelorusMetric.COMMIT_TIME
                ):
                    payload_model = CommitTimePelorusPayload(**payload)
                    metric = CommitMetric(
                        name=payload_model.app,
                        image_hash=payload_model.image_sha,
                        commit_hash=payload_model.commit_hash,
                        namespace=payload_model.namespace,
                        commit_timestamp=payload_model.timestamp,
                    )
                    asyncio.create_task(prometheus_metric(metric))
        except ValidationError as ex:
            logging.error(payload_headers)
            logging.error(payload)
            logging.error(ex)
            raise HTTPException(
                status_code=http.HTTPStatus.UNPROCESSABLE_ENTITY,
                detail="Invalid payload.",
            )

    return PelorusWebhookResponse(
        http_response="Webhook Received", http_response_code=http.HTTPStatus.OK
    )


class WebhookCommitCollector(pelorus.AbstractPelorusExporter):
    """
    Base class for a WebHook Commit time collector.
    """

    def collect(self) -> PelorusGaugeMetricFamily:
        yield in_memory_commit_metrics


collector = load_and_log(WebhookCommitCollector)
REGISTRY.register(collector)
print("Registered")


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    return generate_latest()


async def prometheus_metric(metric: CommitMetric):
    if metric.commit_hash not in commit_hash_set:
        in_memory_commit_metrics.add_metric(
            [metric.namespace, metric.name, metric.commit_hash, metric.image_hash],
            metric.commit_timestamp,
        )
    commit_hash_set.add(metric.commit_hash)
    # Increase the number of webhooks processed
    webhook_processed.inc()
    logging.debug("Webhook processed")

load_plugins()
