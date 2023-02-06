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

from enum import Enum

from pydantic import BaseModel, Field, validator


class PelorusDeliveryHeaders(BaseModel):
    class PelorusMetric(str, Enum):
        """
        The metric should correspond to the known exporter types.
        """

        COMMIT_TIME = "committime"
        DEPLOY_TIME = "deploytime"
        FAILURE = "failure"
        PING = "ping"

    # https://docs.pydantic.dev/usage/models/
    event_type: PelorusMetric = Field(example="committime", alias="x-pelorus-event")


class PelorusPayload(BaseModel):
    """
    Base class for the Pelorus payload model that is used across data
    recived by different webhooks.

    Attributes:
        app (str): Application name.
        timestamp (str): Timestamp of the event. This is different from the
                         time when the webhook could have been received.
    """

    # Even if we consider git project name as app, it still should be below 100
    app: str = Field(max_length=200)
    # ISO 8601 is 19 chars long, so don't expect any format can be longer then 50 chars
    timestamp: str = Field(max_length=50)


class FailurePelorusPayload(PelorusPayload):
    """
    Failure Pelorus payload model.

    Attributes:
        failure_id (str): falure identified for a given app.
        failure_event (FailureEvent): failure may have only two events
                                      created or resolved states.
    """

    class FailureEvent(str, Enum):
        """
        The failure may be one of two events. When it occurs it's created
        and when it is resolved it's closed. Both events are different
        Prometheus metrics, so we need to distinquish between them.
        """

        CREATED = "created"
        RESOLVED = "resolved"

    failure_id: str  # It's an str, because issue may be mix of str and int, e.g. Issue-1
    failure_event: FailureEvent


class DeployTimePelorusPayload(PelorusPayload):
    """
    Deploy time Pelorus payload model, represents the deployment of
    an application.

    Attributes:
        image_sha (str): The container image SHA which was used for the
                         deployment.
        namespace (str): The k8s namespace used for the deployment.
    """

    image_sha: str = Field(regex=r"^sha256:[a-f0-9]{64}$")
    # rfc1035/rfc1123: An alphanumeric string, with a maximum length of 63 characters
    namespace: str = Field(max_length=63)  #


class CommitTimePelorusPayload(DeployTimePelorusPayload):
    """
    Source code commit time Pelorus payload model, represents the time when
    the change was commited to the codebase and later used to deploy an
    application. It uses the same data as Deploy time, except it adds
    the commit hash to the metric.

    Attributes:
        commit_hash (str): Commit SHA-1 hash associated with the commit
    """

    # Commit uses same data as Deploy, except it adds
    # commit hash to the metric
    commit_hash: str = Field(min_length=7, max_length=40)

    @validator("commit_hash", check_fields=False)
    def check_git_hash_length(cls, v):
        # git hash must be 7 or 40 characters
        length = len(v)
        if length in (7, 40):
            return v
        raise ValueError(
            "Git SHA-1 hash must be either 7 (short) or 40 (long) characters long"
        )
