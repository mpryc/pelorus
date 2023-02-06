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

from typing import Optional

from pydantic import BaseModel, Field, validator


# https://docs.github.com/developers/webhooks-and-events/webhooks/webhook-events-and-payloads#delivery-headers
class GitHubDeliveryHeaders(BaseModel):
    # https://docs.pydantic.dev/usage/models/
    # We need to have alias all lowercase
    event_type: str = Field(example="push", alias="x-github-event", max_length=20)
    event_id: str = Field(
        example="72d3162e-cc78-11e3-81ab-4c9367dc0958",
        alias="x-github-delivery",
        max_length=50,
    )
    # Those fields are missing when Secret is not provided
    secret_signature: Optional[str] = Field(
        default=None,
        example="sha1=7d38cdd689735b008b3c702edd92eea23791c5f6",
        alias="x-hub-signature",
    )
    secret_signature_256: Optional[str] = Field(
        default=None,
        example="sha256=d57c68ca6f92289e6987922ff26938930f6e66a2d161ef06abdf1859230aa23c",
        alias="x-hub-signature-256",
    )

    @validator("secret_signature")
    def only_allow_known_event_types(cls, v):
        # check if event_type is interestng for pelorus
        # raise error if not proper type
        return v


class GitHubCommit(BaseModel):
    # Define the request body model
    ref: str
    commit_hash: str = Field(alias="after")

    class GitHubRepository(BaseModel):
        id: int
        full_name: str
        fork: bool
        repo_url: str = Field(alias="url")
        commit_timestamp: int = Field(alias="pushed_at")

    class CommitPusher(BaseModel):
        name: str
        email: str

    repository: GitHubRepository
    pusher: CommitPusher
