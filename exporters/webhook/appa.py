import importlib
from typing import Optional
import os

from webhook.handlers.pelorus_webhook import PelorusWebhookPlugin
from webhook.handlers.github_handler import GithubWebhookHandler


DEFAULT_PLUGIN_FOLDER="handlers"

plugins={}

def register_plugin(webhook_plugin: PelorusWebhookPlugin) -> bool:
    try:
        is_pelorus_plugin = getattr(webhook_plugin, "is_pelorus_webhook_handler", None)
        has_register = getattr(webhook_plugin, "register", None)
        if callable(is_pelorus_plugin) and callable(has_register):
            plugins[webhook_plugin.register()] = webhook_plugin
            return True
    except NotImplementedError:
        # Log info that the plugin can not be registered
        pass
    return False


def load_plugins(plugins_path: Optional[str] = DEFAULT_PLUGIN_FOLDER) -> bool:
    for filename in os.listdir(plugins_path):
        if filename.endswith('_handler.py'):
            module = importlib.import_module(f'{plugins_path}.{filename[:-3]}')
            for name in dir(module):
                obj = getattr(module, name)
                if isinstance(obj, type):
                    register_plugin(obj)

if __name__ == '__main__':
    load_plugins()
    print(plugins)