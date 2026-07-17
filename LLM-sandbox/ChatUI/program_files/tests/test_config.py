from pathlib import Path

from program_files.utils.config import load_settings


def _write(path: Path, frontmatter: str, body: str = "# doc\n") -> None:
    path.write_text(f"---\n{frontmatter}\n---\n\n{body}", encoding="utf-8")


def test_load_settings_merges_settings_and_models(tmp_path: Path) -> None:
    config_dir = tmp_path / "ChatUI" / "config"
    config_dir.mkdir(parents=True)
    _write(config_dir / "settings.md", "similarity_threshold: 0.7\ntop_k: 8\n")
    _write(
        config_dir / "models.md",
        "chat_model: llama3.2:3b\ncoding_model: qwen2.5-coder:7b\nembed_model: nomic-embed-text\n",
    )

    settings = load_settings(config_dir)

    assert settings.similarity_threshold == 0.7
    assert settings.top_k == 8
    assert settings.chat_model == "llama3.2:3b"
    # untouched keys fall back to defaults
    assert settings.chunk_size == 800
    assert settings.web_search_results == 3


def test_load_settings_defaults_vault_path_from_config_dir(tmp_path: Path) -> None:
    config_dir = tmp_path / "ChatUI" / "config"
    config_dir.mkdir(parents=True)

    settings = load_settings(config_dir)

    assert settings.vault_path == tmp_path / "Knowledge"


def test_load_settings_honors_explicit_vault_path(tmp_path: Path) -> None:
    config_dir = tmp_path / "ChatUI" / "config"
    config_dir.mkdir(parents=True)
    custom_vault = tmp_path / "elsewhere"
    _write(config_dir / "settings.md", f"vault_path: {custom_vault}\n")

    settings = load_settings(config_dir)

    assert settings.vault_path == custom_vault


def test_load_settings_tolerates_missing_config_files(tmp_path: Path) -> None:
    config_dir = tmp_path / "ChatUI" / "config"
    config_dir.mkdir(parents=True)

    settings = load_settings(config_dir)

    assert settings.chat_model == "llama3.1:8b"
    assert settings.top_k == 5
