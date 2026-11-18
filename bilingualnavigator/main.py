import re
from pathlib import Path
from typing import Union
import ssl, certifi
import urllib.request
import typer
import yaml
from rich.progress import Progress

from .bible import read_verse_ref
from .tei import read_tei, extract_text, find_elements
from .build import build_website, WEBSITE_DIR
from .dataset import DATASETS_DIR, DatasetError, find_manifests, load_dataset, load_datasets

DATA_DIR = Path("data")
MANUSCRIPT_DATA_PATH = DATA_DIR / "bilingual-mss.yaml"

app = typer.Typer()

class DownloadError(Exception):
    pass


def download_file(url:str, local_path:Path, chunk_size:int=16 * 1024, context=None):
    """ adapted from https://stackoverflow.com/a/1517728 """
    local_path = Path(local_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)

    with urllib.request.urlopen(url, context=context) as response, open(local_path, 'wb') as f, Progress() as progress:
        task = progress.add_task("[red]Downloading", total=response.length)
        while True:
            chunk = response.read(chunk_size)
            progress.update(task, advance=chunk_size)
            if not chunk:
                break
            f.write(chunk)
        
    return local_path


def cached_download(url: str, local_path: Union[str, Path], force: bool = False) -> None:
    """
    Downloads a file if a local file does not already exist.

    Args:
        url (str): The url of the file to download.
        local_path (str, Path): The local path of where the file should be.
            If this file isn't there or the file size is zero then this function downloads it to this location.
        force (bool): Whether or not the file should be forced to download again even if present in the local path.
            Default False.

    Raises:
        DownloadError: Raises an exception if it cannot download the file.
        IOError: Raises an exception if the file does not exist or is empty after downloading.
    """
    local_path = Path(local_path)
    if (not local_path.exists() or local_path.stat().st_size == 0) or force:
        try:
            print(f"Downloading {url} to {local_path}")
            download_file(url, local_path)
        except Exception:
            try:
                download_file(url, local_path, context=ssl.create_default_context(cafile=certifi.where()))
            except Exception as err:                    
                raise DownloadError(f"Error downloading {url} to {local_path}:\n{err}")

    if not local_path.exists() or local_path.stat().st_size == 0:
        raise IOError(f"Error reading {local_path}")
    

@app.command()
def download():
    manuscript_data = yaml.safe_load(MANUSCRIPT_DATA_PATH.read_text(encoding="utf-8"))
    for ms_id, ms_data in manuscript_data.items():
        manuscript_dir = DATA_DIR / ms_id
        for language, transcriptions in ms_data['transcriptions'].items():
            language_dir = manuscript_dir / language
            if not transcriptions:
                print(f"No transcriptions for {ms_id} in {language}")
                continue
            for transcription_url in transcriptions:
                filename = transcription_url.split("/")[-1]
                local_path = language_dir / filename
                try:
                    cached_download(transcription_url, local_path)
                except Exception as err:
                    print(f"Error downloading {transcription_url} to {local_path}:\n{err}")


def extract_verse(tei_path:Path) -> dict[str, dict[str, str | None]]:
    """
    Extracts the text of each verse from a TEI XML file and returns a dictionary mapping verse IDs to their text.

    Args:
        tei_path (Path): The path to the TEI XML file.
    Returns:
        dict[str, dict[str, str | None]]: A dictionary mapping verse IDs to their text and language.
    """
    data = read_tei(tei_path)
    verses = dict()
    for verse in find_elements(data, ".//ab"):
        verse_id = verse.attrib.get("n")
        if not verse_id:
            continue

        try:
            verse_id, verbose_verse_ref = read_verse_ref(verse_id)
        except Exception as err:
            print(f"Error interpreting verse reference {verse_id} in {tei_path}: {err}")
            continue
        verse_text = extract_text(verse).replace("\n", " ").strip()
        verse_text = re.sub(r"\s+", " ", verse_text)
        verses[verse_id] = {
            "text": verse_text,
            "verse": verbose_verse_ref,
        }
    return verses

@app.command()
def extract(max_verses:int|None = None):
    """ 
    For each transcription TEI file, extract the text from the text for each verse and save as YAML file.
    """
    for manuscript_dir in DATA_DIR.iterdir():
        if not manuscript_dir.is_dir():
            continue
    
        manuscript_verses = dict()
        for language_dir in manuscript_dir.iterdir():
            if not language_dir.is_dir():
                continue
            
            language = language_dir.name
            manuscript_verses[language] = dict()
            for transcription in language_dir.iterdir():
                if transcription.suffix != ".xml":
                    continue
                # print(f"Extracting {transcription}...")
                verses = extract_verse(transcription)
                manuscript_verses[language].update(verses)

        # Get intersection of verse IDs across all languages, and filter to these if max_verses is set.
        verse_id_sets = [set(verses.keys()) for verses in manuscript_verses.values()]
        common_verse_ids = set.intersection(*verse_id_sets) if verse_id_sets else set()
        verse_ids = sorted(common_verse_ids)
        if max_verses is not None:
            verse_ids = verse_ids[:max_verses]

        for language, language_verses in manuscript_verses.items():
            verses_in_language = {}
            for verse_id in verse_ids:
                verses_in_language[verse_id] = language_verses[verse_id]
            language_path = manuscript_dir / f"{language}.yaml"
            print(f"Saving {language_path}...")
            language_path.write_text(yaml.dump(verses_in_language, allow_unicode=True), encoding="utf-8")


@app.command()
def build(
    datasets_dir: Path = typer.Option(DATASETS_DIR, help="Folder with one sub-folder (and dataset.yaml) per dataset."),
    website_dir: Path = typer.Option(WEBSITE_DIR, help="Where to write the website."),
    only: list[str] = typer.Option(None, "--only", help="Build only these datasets (folder names). Repeatable."),
):
    """
    Build the website from every dataset in DATASETS_DIR (see datasets/README.md).
    """
    datasets = load_datasets(datasets_dir)
    selected = [dataset for dataset in datasets if not only or dataset.path.parent.name in only]
    if not selected:
        print(f"No datasets to build in {datasets_dir}")
        raise typer.Exit(1)
    for dataset in selected:
        print(f"Building {dataset.id}: {dataset.title} ({len(dataset.verses)} verses)")
        for problem in dataset.problems:
            print(f"    ! {problem}")
    # The sidebar and home page always list every dataset, even when only some are rebuilt.
    # Only remove stale pages when every manifest loaded, so a broken dataset keeps its last good build.
    clean = not only and len(datasets) == len(find_manifests(datasets_dir))
    build_website(datasets, website_dir, build_ids={dataset.id for dataset in selected}, clean=clean)
    print(f"Website written to {website_dir}")


@app.command()
def validate(
    datasets_dir: Path = typer.Option(DATASETS_DIR, help="Folder with one sub-folder (and dataset.yaml) per dataset."),
    only: list[str] = typer.Option(None, "--only", help="Check only these datasets (folder names). Repeatable."),
):
    """
    Check that each dataset's manifest, CoNLL-U and alignment files load, and report what would be built.
    """
    manifests = [m for m in find_manifests(datasets_dir) if not only or m.parent.name in only]
    if not manifests:
        print(f"No datasets found in {datasets_dir}")
        raise typer.Exit(1)
    failed = False
    for manifest in manifests:
        try:
            dataset = load_dataset(manifest)
        except (DatasetError, ValueError, OSError) as err:
            failed = True
            print(f"✗ {manifest.parent.name}: {err}")
            continue
        stats = ", ".join(f"{key}={value}" for key, value in dataset.stats().items())
        print(f"✓ {dataset.id}: {dataset.title} [{dataset.category}] {stats}")
        for problem in dataset.problems:
            print(f"    ! {problem}")
    if failed:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
