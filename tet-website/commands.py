import json
import os

import click
from flask.cli import with_appcontext


def _load_seed_data():
    path = os.path.join(os.path.dirname(__file__), "seed_data.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _seed_simple_table(db, model, rows, id_col, columns):
    """Insert rows into a simple (non-association) table, skipping existing."""
    for row in rows:
        if db.session.get(model, row[id_col]):
            continue
        obj = model(**{col: row[col] for col in columns})
        db.session.add(obj)


def _seed_association(db, table, rows):
    """Insert rows into an association table, skipping duplicates.

    Uses INSERT IGNORE (MySQL) to avoid per-row roundtrips.
    """
    if not rows:
        return
    stmt = table.insert().prefix_with("IGNORE")
    db.session.execute(stmt, rows)


@click.command("seed")
@with_appcontext
def seed_command():
    """Populate the database with reference data (guidelines, processes, etc.)."""
    # Imports are local so this module has no import-time coupling with the
    # app (index.py imports us while it is still initializing).
    from index import db
    from models import (
        SECO_dimension,
        SECO_process,
        Guideline,
        Conditioning_factor_transp,
        DX_factor,
        Key_success_criterion,
        Example,
        Task,
        Question,
    )
    from models.guideline import (
        guideline_conditioning_factor,
        guideline_dx_factor,
        guideline_seco_process,
        guideline_seco_dimension,
        process_task,
    )
    from models.task import task_seco_type

    data = _load_seed_data()

    click.echo("Seeding seco_dimension...")
    _seed_simple_table(
        db, SECO_dimension, data["seco_dimension"],
        "seco_dimension_id", ["seco_dimension_id", "name"]
    )

    click.echo("Seeding seco_process...")
    _seed_simple_table(
        db, SECO_process, data["seco_process"],
        "seco_process_id", ["seco_process_id", "description"]
    )

    click.echo("Seeding guideline...")
    _seed_simple_table(
        db, Guideline, data["guideline"],
        "guidelineID", ["guidelineID", "title", "description", "notes"]
    )

    click.echo("Seeding conditioning_factor_transp...")
    _seed_simple_table(
        db, Conditioning_factor_transp, data["conditioning_factor_transp"],
        "conditioning_factor_transp_id",
        ["conditioning_factor_transp_id", "description"]
    )

    click.echo("Seeding dx_factor...")
    _seed_simple_table(
        db, DX_factor, data["dx_factor"],
        "dx_factor_id", ["dx_factor_id", "description"]
    )

    click.echo("Seeding key_success_criterion...")
    _seed_simple_table(
        db, Key_success_criterion, data["key_success_criterion"],
        "key_success_criterion_id",
        ["key_success_criterion_id", "title", "description", "guideline_id"]
    )

    click.echo("Seeding example...")
    _seed_simple_table(
        db, Example, data["example"],
        "example_id",
        ["example_id", "description", "key_success_criterion_id"]
    )

    click.echo("Seeding task...")
    _seed_simple_table(
        db, Task, data["task"],
        "task_id", ["task_id", "title", "description", "summary"]
    )

    click.echo("Seeding question...")
    _seed_simple_table(
        db, Question, data["question"],
        "question_id",
        ["question_id", "question", "key_success_criterion_id"]
    )

    db.session.flush()

    click.echo("Seeding association tables...")
    _seed_association(db, guideline_conditioning_factor, data["guideline_conditioning_factor"])
    _seed_association(db, guideline_dx_factor, data["guideline_dx_factor"])
    _seed_association(db, guideline_seco_process, data["guideline_seco_process"])
    _seed_association(db, guideline_seco_dimension, data["guideline_seco_dimension"])
    _seed_association(db, process_task, data["process_task"])
    _seed_association(db, task_seco_type, data["task_seco_type"])

    db.session.commit()
    click.echo("Seed complete!")


@click.command("ai-analyze")
@click.option("--evaluation-id", type=int, required=True, help="Avaliacao a analisar.")
@click.option("--model", default=None, help="Modelo a usar (padrao: AI_MODEL do .env).")
@click.option(
    "--dry-run", is_flag=True,
    help="Monta e imprime o contexto sem chamar a API — para iterar no prompt de graca.",
)
@with_appcontext
def ai_analyze_command(evaluation_id, model, dry_run):
    """Roda a camada analitica de IA numa avaliacao, pelo terminal.

    O botao do dashboard e o caminho normal. Esta CLI existe para o que a tela nao faz
    bem: iterar no prompt sem gastar chamada (--dry-run) e comparar modelos em lote.
    """
    from services.ai import pipeline
    from services.ai.context_builder import EvaluationNotAnalyzable

    try:
        if dry_run:
            result = pipeline.build_dry_run(evaluation_id)
            click.echo(result["prompt"])
            click.echo("")
            click.echo("--dry-run: nenhuma chamada a API foi feita.")
            click.echo(
                f"{result['participants']} participantes · "
                f"{result['evidence_catalog_size']} evidencias · "
                f"{result['framework_scope_size']} KSCs no escopo"
            )
            click.echo(f"Catalogo por tipo: {result['catalog_by_type']}")
            return

        click.echo(f"Analisando a avaliacao {evaluation_id}...")
        payload = pipeline.run_sync(evaluation_id, model=model)
    except EvaluationNotAnalyzable as exc:
        raise click.ClickException(str(exc))

    click.echo("")
    click.echo(f"Modelo: {payload['model']} · {payload['stats']['ai_duration_s']}s · "
               f"{payload['stats']['tokens_total']} tokens")
    click.echo("-" * 72)
    for finding in payload["findings"]:
        m = finding["metrics"]
        click.echo(f"{finding['code']}  {finding['title']}")
        click.echo(f"       KSC G{finding['ksc']['guideline_id']}/{finding['ksc']['id']} "
                   f"{finding['ksc']['title']}")
        click.echo(f"       {m['affected_participants']} participantes · recorrencia "
                   f"{m['recurrence']} · confianca {m['confidence_band']} · "
                   f"{m['evidence_count']} evidencias")
    click.echo("-" * 72)
    for action in payload["actions"]:
        click.echo(f"{action['code']}  [{action['priority_band']} {action['priority_score']}] "
                   f"{action['title']}")
        click.echo(f"       resolve {', '.join(action['resolves'])} · "
                   f"onde: {', '.join(action['where'])}")
    click.echo("-" * 72)


def register_commands(app):
    app.cli.add_command(seed_command)
    app.cli.add_command(ai_analyze_command)
