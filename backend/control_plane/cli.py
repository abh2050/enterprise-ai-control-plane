"""The ``cp`` command line."""

import os
from typing import Annotated, NoReturn

import typer

from control_plane.settings import Settings, UnsafeBindError, assert_safe_bind, get_settings

app = typer.Typer(help="Enterprise AI Control Plane", no_args_is_help=True)
data_app = typer.Typer(help="Banking77 data import and splits (M2)", no_args_is_help=True)
users_app = typer.Typer(help="User and role management (M4)", no_args_is_help=True)
app.add_typer(data_app, name="data")
app.add_typer(users_app, name="users")


def _not_yet(milestone: str) -> NoReturn:
    typer.echo(f"Not implemented until {milestone}.", err=True)
    raise typer.Exit(code=2)


@app.command()
def serve(
    host: Annotated[str | None, typer.Option(help="Bind address")] = None,
    port: Annotated[int | None, typer.Option(help="Bind port")] = None,
    reload: Annotated[bool, typer.Option(help="Reload on code changes")] = False,
) -> None:
    """Run the API and console."""
    import uvicorn

    base = get_settings()
    bind_host = host or base.bind_host
    bind_port = port or base.bind_port
    settings = Settings(bind_host=bind_host, bind_port=bind_port)
    try:
        assert_safe_bind(settings)
    except UnsafeBindError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    # Child processes re-read the environment, so pin the checked host there too.
    os.environ["BIND_HOST"] = bind_host
    uvicorn.run(
        "control_plane.api:create_app",
        factory=True,
        host=bind_host,
        port=bind_port,
        reload=reload,
        access_log=False,  # access logs could carry query text; keep them off
    )


@app.command("seed-fixture")
def seed_fixture_cmd() -> None:
    """Load fixture users and FIXTURE apps into the configured store."""
    from control_plane.fixtures import seed_fixture
    from control_plane.settings import StoreBackend
    from control_plane.store import build_store

    settings = get_settings()
    if settings.store_backend is StoreBackend.MEMORY:
        typer.echo("Memory store seeds itself on startup; nothing to do.")
        return
    users, apps = seed_fixture(build_store(settings))
    typer.echo(f"Seeded {users} fixture users and {apps} FIXTURE apps.")


@data_app.command("fetch")
def data_fetch() -> None:
    """Download Banking77 at a pinned commit and verify hashes."""
    _not_yet("M2")


@data_app.command("split")
def data_split() -> None:
    """Create the development, training, frozen evaluation, and shadow splits."""
    _not_yet("M2")


@app.command()
def evaluate() -> None:
    """Run a config against the frozen evaluation set."""
    _not_yet("M2")


@app.command()
def preflight() -> None:
    """Verify model access, structured output, and token counting."""
    _not_yet("M3")


@app.command()
def pricecheck() -> None:
    """Refresh and version the Vertex price card."""
    _not_yet("M3")


@app.command()
def importregistry() -> None:
    """Import an organization's app list from CSV plus a column mapping."""
    _not_yet("M4")


@users_app.command("set-role")
def users_set_role() -> None:
    """Assign a role to a user."""
    _not_yet("M4")


@app.command()
def shadow() -> None:
    """Replay simulated days through the approved and candidate configs."""
    _not_yet("M5")


@app.command()
def drill() -> None:
    """Run the incident drill on simulated days 10 to 12."""
    _not_yet("M5")


@app.command()
def export() -> None:
    """Export events and results to BigQuery idempotently."""
    _not_yet("M6")


@app.command()
def report() -> None:
    """Generate docs/executive_report.md from the analytics queries."""
    _not_yet("M6")


@app.command()
def snapshot() -> None:
    """Export read-only JSON for the static snapshot console."""
    _not_yet("M7")


if __name__ == "__main__":
    app()
