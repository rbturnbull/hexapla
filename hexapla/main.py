"""
The ``hexapla`` command::

    hexapla build project-config.yaml --output site
    hexapla validate project-config.yaml
"""
from __future__ import annotations

import time
from pathlib import Path

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__
from .build import OutputDirError, build_site
from .config import ConfigError, load_config
from .corpus import CorpusError, Project, load_project
from .theme import ThemeError

app = typer.Typer(help="Static websites for reading and exploring word-aligned manuscript texts.", no_args_is_help=True)


def show_version(value: bool):
    if value:
        typer.echo(f"hexapla {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", callback=show_version, is_eager=True,
                                 help="Show Hexapla's version and exit."),
):
    """ Static websites for reading and exploring word-aligned manuscript texts. """


def make_console() -> Console:
    # Made per command (not at import), so it writes to the stdout the command runs with.
    return Console(highlight=False)


def plural(count: int, noun: str, nouns: str | None = None) -> str:
    return f"{count:,} {noun if count == 1 else (nouns or noun + 's')}"


def relative(text: str, root: Path) -> str:
    """ Paths in messages, shown relative to the project folder. """
    return text.replace(f"{root}/", "")


def show_errors(console: Console, title: str, errors: list[str], root: Path):
    lines = "\n".join(f"[red]✗[/] {relative(error, root)}" for error in errors)
    console.print(Panel(lines, title=f"[bold red]{title}[/]", title_align="left", border_style="red", expand=False))


def load(console: Console, config_path: Path) -> Project:
    """ Loads the project, or shows what is wrong with it and exits. """
    root = config_path.expanduser().resolve().parent
    try:
        return load_project(load_config(config_path))
    except ConfigError as err:
        show_errors(console, f"Problems in {Path(err.source).name}", err.errors, root)
    except CorpusError as err:
        show_errors(console, f"Problems in the files {config_path.name} names", err.errors, root)
    raise typer.Exit(1)


def heading(console: Console, project: Project):
    console.print()
    console.rule(f"[bold]{project.config.theme.name}[/]  [dim]· Hexapla[/]", style="dim")


def table(title: str) -> Table:
    return Table(title=f"[bold]{title}[/]", title_justify="left", box=box.SIMPLE_HEAD, header_style="bold dim",
                 pad_edge=False)


def alignments_table(project: Project) -> Table:
    result = table("Alignments")
    result.add_column("Alignment", style="cyan", no_wrap=True)
    result.add_column("Title")
    result.add_column("Languages")
    result.add_column("Verses", justify="right")
    result.add_column("Links", justify="right")
    result.add_column("Probable", justify="right")
    result.add_column("Warnings", justify="right")
    for pair in project.pairs:
        stats = pair.stats()
        warnings = f"[yellow]{len(pair.problems)}[/]" if pair.problems else "[dim]—[/]"
        result.add_row(pair.id, pair.title, f"{pair.lang_a.label}–{pair.lang_b.label}", f"{stats['verses']:,}",
                       f"{stats['links']:,}", f"{stats['probable']:,}", warnings)
    return result


def manuscripts_table(project: Project) -> Table:
    result = table("Manuscripts")
    result.add_column("Manuscript", style="cyan", no_wrap=True)
    result.add_column("Name")
    result.add_column("Language")
    result.add_column("TEI file", style="dim")
    result.add_column("Sentences", justify="right")
    for witness in project.witnesses.values():
        result.add_row(witness.id, witness.name, witness.label, witness.transcription.path.name,
                       f"{len(witness.sentences):,}")
    return result


def show_problems(console: Console, project: Project) -> int:
    """ The smaller problems, which do not stop the build. Returns how many there are. """
    problems = [(pair.id, problem) for pair in project.pairs for problem in pair.problems]
    width = max((len(pair_id) for pair_id, _ in problems), default=0)
    for pair_id, problem in problems:
        console.print(f"  [yellow]⚠[/] [dim]{pair_id:<{width}}[/]  {problem}")
    if problems:
        console.print()
    return len(problems)


@app.command()
def build(
    config: Path = typer.Argument(..., help="The project's config file."),
    output: Path = typer.Option(Path("site"), "--output", "-o", help="Where to write the website."),
):
    """ Build the website for a project. """
    console = make_console()
    project = load(console, config)
    heading(console, project)
    console.print(alignments_table(project))
    show_problems(console, project)

    start = time.perf_counter()
    try:
        with console.status("Building the website…"):
            build_site(project, output)
    except (ThemeError, OutputDirError) as err:
        show_errors(console, "The website could not be built", [str(err)], config.expanduser().resolve().parent)
        raise typer.Exit(1)
    seconds = time.perf_counter() - start

    files = [path for path in output.rglob("*") if path.is_file()]
    pages = sum(1 for path in files if path.name == "index.html")
    megabytes = sum(path.stat().st_size for path in files) / 1e6
    console.print(f"[green]✓[/] Built {plural(len(project.pairs), 'alignment')} and "
                  f"{plural(len(project.witnesses), 'manuscript')} [dim]({plural(pages, 'page')}, {megabytes:,.1f} MB, "
                  f"{seconds:.1f} s)[/] → [bold]{output}[/]")


@app.command()
def validate(config: Path = typer.Argument(..., help="The project's config file.")):
    """ Check that the config and every file it names can be read, and report what would be built. """
    console = make_console()
    project = load(console, config)
    heading(console, project)
    console.print(manuscripts_table(project))
    console.print(alignments_table(project))
    warnings = show_problems(console, project)
    note = f" [dim]·[/] [yellow]{plural(warnings, 'warning')}[/]" if warnings else ""
    console.print(f"[green]✓[/] All files are valid{note}")


if __name__ == "__main__":  # pragma: no cover - run as ``python -m hexapla.main``
    app()
