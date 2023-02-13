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

from typing import abstractmethod
from .pelorus_webhook import PelorusWebhookPlugin

class GithubWebhookHandler(PelorusWebhookPlugin):
    user_agent_str = "GitHub-Hookshot/"

    def ping_function():
        pass

    def github_push():
        pass

    handler_functions = {
            "ping": ping_function,
            "push": github_push
    }
    
    @classmethod
    def register(cls)->str:
        return GithubWebhookHandler.user_agent_str.lower()