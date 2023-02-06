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

import threading
from typing import Optional, Sequence

from prometheus_client.core import GaugeMetricFamily


class PelorusGaugeMetricFamily(GaugeMetricFamily):
    """
    Wrapper around GaugeMetricFamily class which allows to async
    access to it's data when used by different webhook endpoints.
    """

    def __init__(
        self,
        name: str,
        documentation: str,
        value: Optional[float] = None,
        labels: Optional[Sequence[str]] = None,
        unit: str = "",
    ):
        super().__init__(name, documentation, value, labels, unit)
        self.lock = threading.Lock()

    def add_metric(self, *args, **kwargs):
        with self.lock:
            super().add_metric(*args, **kwargs)

    def __iter__(self, *args, **kwargs):
        with self.lock:
            for item in super().__iter__(*args, **kwargs):
                yield item


in_memory_commit_metrics = PelorusGaugeMetricFamily(
    "commit_timestamp",
    "Commit timestamp",
    labels=["namespace", "app", "commit", "image_sha"],
)

in_memory_deploy_timestamp_metric = PelorusGaugeMetricFamily(
    "deploy_timestamp",
    "Deployment timestamp",
    labels=["namespace", "app", "image_sha"],
)

in_memory_failure_creation_metric = PelorusGaugeMetricFamily(
    "failure_creation_timestamp",
    "Failure Creation Timestamp",
    labels=["app", "issue_number"],
)
in_memory_failure_resolution_metric = PelorusGaugeMetricFamily(
    "failure_resolution_timestamp",
    "Failure Resolution Timestamp",
    labels=["app", "issue_number"],
)
