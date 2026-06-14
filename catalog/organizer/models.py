from dataclasses import dataclass, field


@dataclass
class PrateleiraConfig:
    nome: str          # "A", "B", "C" …
    largura_cm: float  # ex: 80.0


@dataclass
class EstanteConfig:
    nome: str
    prateleiras: list[PrateleiraConfig]


@dataclass
class ConfigEstantes:
    estantes: list[EstanteConfig] = field(default_factory=list)
    espessura_media_cm: float = 2.5


@dataclass
class PrateleiraResultado:
    estante: str
    prateleira: str
    capacidade: int
    livros: list[dict]
    label_sugerido: str
