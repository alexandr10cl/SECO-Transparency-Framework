"""guideline_for_task/serialize_guideline traduzem models ORM para o schema que
personalizacao.py espera. Sao so leitura contra o banco de dev (dados de seed
reais - guideline/task/processo 1, seedados por `flask seed`) - nada e criado
ou apagado, entao rodam junto do resto por padrao (sem marker de integracao).

Pulam sozinhos se o banco de dev nao estiver acessivel ou sem seed, em vez de
falhar - sao ambiente, nao regressao de codigo.
"""
import pytest

from services.scenario_personalization.serializers import guideline_for_task, serialize_guideline


@pytest.fixture()
def task_um(app):
    from index import db
    from models import Task

    task = db.session.get(Task, 1)
    if task is None:
        pytest.skip("seed de referencia ausente - rode `flask seed` no banco de dev")
    return task


def test_guideline_for_task_resolve_a_diretriz_1_1_do_seed(task_um):
    guideline = guideline_for_task(task_um)

    assert guideline is not None
    assert guideline.guidelineID == 1


def test_guideline_for_task_devolve_none_quando_task_sem_processo(app):
    from models import Task

    task_orfa = Task(task_id=-1, title="orfa", description="sem processo", summary="s")
    assert guideline_for_task(task_orfa) is None


def test_serialize_guideline_produz_o_schema_esperado(task_um):
    guideline = guideline_for_task(task_um)
    resultado = serialize_guideline(guideline)

    assert resultado["id"] == f"G{guideline.guidelineID}"
    assert resultado["titulo"] == guideline.title
    assert resultado["descricao"] == guideline.description
    assert isinstance(resultado["dimensoes"], list)
    assert isinstance(resultado["fatores_condicionantes"], list)
    assert isinstance(resultado["fatores_experiencia_desenvolvedor"], list)
    assert isinstance(resultado["criterios_sucesso"], list) and resultado["criterios_sucesso"]

    primeiro_criterio = resultado["criterios_sucesso"][0]
    assert set(primeiro_criterio.keys()) == {"titulo", "descricao", "exemplo"}
