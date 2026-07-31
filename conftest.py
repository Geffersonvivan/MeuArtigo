import pytest


@pytest.fixture(autouse=True)
def _tmp_artigos(tmp_path, settings):
    """Isola a pasta física dos artigos num diretório temporário por teste."""
    settings.ARTIGOS_ROOT = tmp_path / "artigos"
