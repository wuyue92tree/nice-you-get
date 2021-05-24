import os
import json
from conf.settings import CONFIG_PATH, HOME_DIR


class Config(object):
    def __init__(self) -> None:
        super().__init__()
        self.default_config = {
            'save_path': os.path.join(HOME_DIR, 'media'),
            'insecure': 0,
            'merge': 0,
            'caption': 0
        }

    def load(self):
        if os.path.exists(CONFIG_PATH) is False:
            return self.default_config

        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.loads(f.read())

    def save(self, **kwargs):
        config = self.load()
        for k, v in kwargs.items():
            config[k] = v

        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            f.write(json.dumps(config, ensure_ascii=False, indent=4))


config = Config()