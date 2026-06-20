import json
from dataclasses import asdict
from pathlib import Path

import catalog.storage.git_sync as git_sync

from ..config import ESTANTES_FILE
from .models import ConfigEstantes, EstanteConfig, PrateleiraConfig

ESTANTES_DEFAULT = ConfigEstantes(estantes=[], espessura_media_cm=2.5)


def salvar_config(config: ConfigEstantes, path: str = ESTANTES_FILE) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(asdict(config), f, ensure_ascii=False, indent=2)
    git_sync.commit_se_houver_mudancas("estantes: configuração atualizada", arquivos=[path])


def carregar_config(path: str = ESTANTES_FILE) -> ConfigEstantes:
    if not Path(path).exists():
        return ConfigEstantes(
            estantes=ESTANTES_DEFAULT.estantes[:],
            espessura_media_cm=ESTANTES_DEFAULT.espessura_media_cm,
        )
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    estantes = [
        EstanteConfig(
            nome=e["nome"],
            prateleiras=[
                PrateleiraConfig(nome=p["nome"], largura_cm=float(p["largura_cm"]))
                for p in e.get("prateleiras", [])
            ],
        )
        for e in data.get("estantes", [])
    ]
    return ConfigEstantes(
        estantes=estantes,
        espessura_media_cm=float(data.get("espessura_media_cm", 2.5)),
    )
