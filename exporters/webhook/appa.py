import importlib
from typing import Optional
import os

from webhook.handlers.pelorus_webhook import PelorusWebhookPlugin


DEFAULT_PLUGIN_FOLDER="handlers"

plugins={}

def register_plugin(webhook_plugin: PelorusWebhookPlugin) -> bool:
    try:
        has_register = getattr(webhook_plugin, "register", None)
        if callable(has_register):
            plugins[webhook_plugin.register()] = webhook_plugin
    except NotImplementedError:
        pass

def load_plugins(plugins_path: Optional[str] = DEFAULT_PLUGIN_FOLDER) -> bool:
    for filename in os.listdir(plugins_path):
        if filename.endswith('_handler.py'):
            module = importlib.import_module(f'{plugins_path}.{filename[:-3]}')
            for name in dir(module):
                obj = getattr(module, name)
                register_plugin(obj)
                breakpoint()
                if isinstance(obj, type) and issubclass(obj, PelorusWebhookPlugin) and obj is not PelorusWebhookPlugin:
                    register_plugin(obj)

if __name__ == '__main__':
    load_plugins()
    print(plugins)