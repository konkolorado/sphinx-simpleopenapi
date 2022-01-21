import functools
from pathlib import Path

import yaml

from sphinx_simpleopenapi.errors import ApiSpecNotFound


# Locally cache spec to speedup processing of same spec file in multiple
# openapi directives
@functools.lru_cache()
def get_openapi_spec(path, encoding):
    if not Path(path).exists():
        raise ApiSpecNotFound(f"{path} does not exist")

    abspath = Path.cwd() / path
    with open(abspath, "rt", encoding=encoding) as stream:
        return yaml.safe_load(stream)
