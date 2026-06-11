import json
import os

import click
from flask.cli import with_appcontext

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


def _load_seed_data():
    path = os.path.join(os.path.dirname(__file__), "seed_data.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _seed_simple_table(model, rows, id_col, columns):
    """Insert rows into a simple (non-association) table, skipping existing."""
    for row in rows:
        if db.session.get(model, row[id_col]):
            continue
        obj = model(**{col: row[col] for col in columns})
        db.session.add(obj)


def _seed_association(table, rows):
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
    data = _load_seed_data()

    click.echo("Seeding seco_dimension...")
    _seed_simple_table(
        SECO_dimension, data["seco_dimension"],
        "seco_dimension_id", ["seco_dimension_id", "name"]
    )

    click.echo("Seeding seco_process...")
    _seed_simple_table(
        SECO_process, data["seco_process"],
        "seco_process_id", ["seco_process_id", "description"]
    )

    click.echo("Seeding guideline...")
    _seed_simple_table(
        Guideline, data["guideline"],
        "guidelineID", ["guidelineID", "title", "description", "notes"]
    )

    click.echo("Seeding conditioning_factor_transp...")
    _seed_simple_table(
        Conditioning_factor_transp, data["conditioning_factor_transp"],
        "conditioning_factor_transp_id",
        ["conditioning_factor_transp_id", "description"]
    )

    click.echo("Seeding dx_factor...")
    _seed_simple_table(
        DX_factor, data["dx_factor"],
        "dx_factor_id", ["dx_factor_id", "description"]
    )

    click.echo("Seeding key_success_criterion...")
    _seed_simple_table(
        Key_success_criterion, data["key_success_criterion"],
        "key_success_criterion_id",
        ["key_success_criterion_id", "title", "description", "guideline_id"]
    )

    click.echo("Seeding example...")
    _seed_simple_table(
        Example, data["example"],
        "example_id",
        ["example_id", "description", "key_success_criterion_id"]
    )

    click.echo("Seeding task...")
    _seed_simple_table(
        Task, data["task"],
        "task_id", ["task_id", "title", "description", "summary"]
    )

    click.echo("Seeding question...")
    _seed_simple_table(
        Question, data["question"],
        "question_id",
        ["question_id", "question", "key_success_criterion_id"]
    )

    db.session.flush()

    click.echo("Seeding association tables...")
    _seed_association(guideline_conditioning_factor, data["guideline_conditioning_factor"])
    _seed_association(guideline_dx_factor, data["guideline_dx_factor"])
    _seed_association(guideline_seco_process, data["guideline_seco_process"])
    _seed_association(guideline_seco_dimension, data["guideline_seco_dimension"])
    _seed_association(process_task, data["process_task"])
    _seed_association(task_seco_type, data["task_seco_type"])

    db.session.commit()
    click.echo("Seed complete!")


def register_commands(app):
    app.cli.add_command(seed_command)
