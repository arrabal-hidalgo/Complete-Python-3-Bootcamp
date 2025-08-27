import json
import os
import re
from importlib import resources
from typing import Any, Dict


class SettingGlobal:
    _config: Dict[str, Dict[str, Any]] = {}
    default_config_dir: str = "segittur_commons.config"
    default_config_file: str
    config_file_var_env: str

    @classmethod
    def __open_config(cls) -> str:
        if config := os.getenv(cls.config_file_var_env):
            with open(config, "r") as f:
                config_str = f.read()
        else:
            with (
                resources.files(cls.default_config_dir)
                .joinpath(cls.default_config_file)
                .open("r") as f
            ):
                config_str = f.read()
        return config_str

    @classmethod
    def _load_config(cls) -> Dict[str, Any]:
        if cls._config is None or cls._config == {}:
            config_str = cls.__open_config()

            def replace_env_var(match):
                var_name = match.group(1)
                return os.getenv(var_name, "")

            config_str = re.sub(r"\$\{(\w+)\}", replace_env_var, config_str)
            cls._config = json.loads(config_str)

        return cls._config
