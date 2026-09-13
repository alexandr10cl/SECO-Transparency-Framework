"""Fixtures compartilhadas. So os testes que precisam do banco (serializers,
integracao) usam a fixture `app` - estruturacao e validacao nao tocam o Flask
nem o banco, entao rodam sem nenhuma fixture.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

# Import em nivel de modulo, de proposito: precisa ser a PRIMEIRA coisa a tocar
# em `models`/`services`, porque `index.py` e quem resolve a ordem certa da
# cadeia circular (index -> views -> functions -> models -> index...). Um
# teste que importe `services.scenario_personalization.*` (que puxa `models`)
# antes de `index` ja ter rodado cai num ImportError de import parcial.
from index import app as _flask_app  # noqa: E402


@pytest.fixture()
def app():
    """App context ja empurrado - da pra usar `Model.query` direto no teste."""
    with _flask_app.app_context():
        yield _flask_app
