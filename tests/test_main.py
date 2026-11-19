import re

from typer.testing import CliRunner

from hexapla.main import app

from .conftest import CONFIG_NAME, PROJECT, read_config, write_config

runner = CliRunner()


def invoke(*args):
    """ Runs the CLI with a wide terminal, so rich does not wrap table cells. """
    return runner.invoke(app, [str(arg) for arg in args], env={"COLUMNS": "200"})


def row(output: str, *cells: str) -> bool:
    """ Whether a line of the output holds these cells, in this order (rich pads them with spaces and borders). """
    pattern = r".*".join(re.escape(cell) for cell in cells)
    return any(re.search(pattern, line) for line in output.splitlines())


def test_build_command(tmp_path):
    output = tmp_path / "site"
    result = invoke("build", PROJECT / CONFIG_NAME, "--output", output)
    assert result.exit_code == 0, result.output
    assert "Test Navigator" in result.output
    assert row(result.output, "claro", "Codex Claromontanus", "Greek–Latin", "3")
    assert row(result.output, "✓", "Built 1 alignment and 2 manuscripts", str(output))
    assert (output / "index.html").exists()


def test_build_reports_problems(project_dir, tmp_path):
    greek = project_dir / "claro" / "claro-greek.conllu"
    greek.write_text(greek.read_text() + "\n# sent_id = extra\n1\tx\tx\tX\t_\t_\t0\troot\t_\t_\n")
    result = invoke("build", project_dir / CONFIG_NAME, "--output", tmp_path / "site")
    assert result.exit_code == 0
    assert row(result.output, "claro", "1")  # the problems column
    assert row(result.output, "⚠", "claro", "1 sentence(s) only in Greek: extra")


def test_validate_command():
    result = invoke("validate", PROJECT / CONFIG_NAME)
    assert result.exit_code == 0, result.output
    assert "Manuscripts" in result.output and "Alignments" in result.output
    assert row(result.output, "claro-greek", "Codex Claromontanus", "Greek", "claro-greek.xml", "3")
    assert row(result.output, "claro", "Codex Claromontanus", "Greek–Latin", "3")
    assert row(result.output, "✓", "valid")


def test_validate_reports_problems(project_dir):
    links = project_dir / "claro" / "claro-links.jsonl"
    links.write_text(links.read_text() + '{"sent_id": "nowhere", "links": []}\n')
    result = invoke("validate", project_dir / CONFIG_NAME)
    assert result.exit_code == 0
    assert row(result.output, "⚠", "claro", "1 aligned sent_id(s) not in both CoNLL-U files: nowhere")
    assert row(result.output, "1 warning")


def test_config_errors_exit_with_a_message(project_dir, tmp_path):
    data = read_config(project_dir)
    data["manuscripts"]["claro-greek"]["tei"] = "gone.xml"
    write_config(project_dir, data)
    for command in (["validate"], ["build", "--output", tmp_path / "site"]):
        result = invoke(command[0], project_dir / CONFIG_NAME, *command[1:])
        assert result.exit_code == 1
        assert row(result.output, "✗", "manuscripts.claro-greek.tei", "gone.xml")
        assert "project.yaml" in result.output


def test_corpus_errors_exit_with_a_message(project_dir, tmp_path):
    greek = project_dir / "claro" / "claro-greek.xml"
    greek.write_text(greek.read_text().replace(' xml:lang="grc"', ""))
    for command in (["validate"], ["build", "--output", tmp_path / "site"]):
        result = invoke(command[0], project_dir / CONFIG_NAME, *command[1:])
        assert result.exit_code == 1
        assert row(result.output, "✗", "xml:lang")


def test_build_errors_exit_with_a_message(project_dir, tmp_path):
    (project_dir / "theme" / "variables.scss").write_text("$primary: ;")
    result = invoke("build", project_dir / CONFIG_NAME, "--output", tmp_path / "site")
    assert result.exit_code == 1 and row(result.output, "✗", "variables.scss")

    output = tmp_path / "taken"
    output.mkdir()
    (output / "keep.txt").write_text("x")
    result = invoke("build", PROJECT / CONFIG_NAME, "--output", output)
    assert result.exit_code == 1 and row(result.output, "✗", "not built by Hexapla")
