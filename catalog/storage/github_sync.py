"""
Sync de dados com GitHub via REST API.

Usado quando GITHUB_TOKEN e GITHUB_REPO estão configurados (Streamlit Cloud).
Cada sessão cria um branch data/YYYY-MM-DD e commits atômicos multi-arquivo
via Git Data API. "Finalizar sessão" abre uma PR via API.

Variáveis de ambiente:
  GITHUB_TOKEN  — Personal Access Token com scope 'repo'
  GITHUB_REPO   — "owner/nome-do-repo" (ex.: "ferratti/my-lib-catalog")
  GITHUB_BRANCH — branch base (padrão: "main")
"""
import base64
import os
from datetime import date
from pathlib import Path

import requests

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_sessao_branch: str | None = None


def disponivel() -> bool:
    return bool(os.environ.get("GITHUB_TOKEN") and os.environ.get("GITHUB_REPO"))


def _token() -> str:
    return os.environ.get("GITHUB_TOKEN", "")


def _repo() -> str:
    return os.environ.get("GITHUB_REPO", "")


def _base_branch() -> str:
    return os.environ.get("GITHUB_BRANCH", "main")


def _headers() -> dict:
    return {
        "Authorization": f"token {_token()}",
        "Accept": "application/vnd.github.v3+json",
    }


def _get_branch_sha(branch: str) -> str | None:
    r = requests.get(
        f"https://api.github.com/repos/{_repo()}/git/ref/heads/{branch}",
        headers=_headers(),
        timeout=10,
    )
    if r.status_code == 200:
        return r.json()["object"]["sha"]
    return None


def garantir_branch_sessao() -> str:
    global _sessao_branch
    if _sessao_branch:
        return _sessao_branch

    hoje = date.today().isoformat()
    nome = f"data/{hoje}"

    if _get_branch_sha(nome):
        _sessao_branch = nome
        return nome

    base_sha = _get_branch_sha(_base_branch())
    if not base_sha:
        raise RuntimeError(f"Branch base '{_base_branch()}' não encontrado no GitHub")

    r = requests.post(
        f"https://api.github.com/repos/{_repo()}/git/refs",
        headers=_headers(),
        json={"ref": f"refs/heads/{nome}", "sha": base_sha},
        timeout=10,
    )
    if r.status_code not in (201, 422):  # 422 = branch já existe (race condition)
        raise RuntimeError(f"Erro ao criar branch {nome}: HTTP {r.status_code}")

    _sessao_branch = nome
    return nome


def branch_sessao() -> str | None:
    return _sessao_branch


def commit_arquivos(paths: list, mensagem: str) -> bool:
    """Commit atômico de múltiplos arquivos via Git Data API."""
    if not _sessao_branch:
        return False

    branch_sha = _get_branch_sha(_sessao_branch)
    if not branch_sha:
        return False

    r = requests.get(
        f"https://api.github.com/repos/{_repo()}/git/commits/{branch_sha}",
        headers=_headers(),
        timeout=10,
    )
    if r.status_code != 200:
        return False
    tree_sha = r.json()["tree"]["sha"]

    blobs = []
    for path in paths:
        p = Path(path)
        if not p.exists():
            continue
        content = p.read_bytes()
        rb = requests.post(
            f"https://api.github.com/repos/{_repo()}/git/blobs",
            headers=_headers(),
            json={"content": base64.b64encode(content).decode(), "encoding": "base64"},
            timeout=15,
        )
        if rb.status_code != 201:
            continue
        try:
            rel = str(p.resolve().relative_to(_REPO_ROOT))
        except ValueError:
            continue
        blobs.append({"path": rel, "mode": "100644", "type": "blob", "sha": rb.json()["sha"]})

    if not blobs:
        return False

    rt = requests.post(
        f"https://api.github.com/repos/{_repo()}/git/trees",
        headers=_headers(),
        json={"base_tree": tree_sha, "tree": blobs},
        timeout=15,
    )
    if rt.status_code != 201:
        return False

    rc = requests.post(
        f"https://api.github.com/repos/{_repo()}/git/commits",
        headers=_headers(),
        json={
            "message": mensagem,
            "tree": rt.json()["sha"],
            "parents": [branch_sha],
        },
        timeout=15,
    )
    if rc.status_code != 201:
        return False

    rr = requests.patch(
        f"https://api.github.com/repos/{_repo()}/git/refs/heads/{_sessao_branch}",
        headers=_headers(),
        json={"sha": rc.json()["sha"]},
        timeout=10,
    )
    return rr.status_code == 200


def contar_commits_sessao() -> int:
    if not _sessao_branch:
        return 0
    r = requests.get(
        f"https://api.github.com/repos/{_repo()}/compare/{_base_branch()}...{_sessao_branch}",
        headers=_headers(),
        timeout=10,
    )
    if r.status_code == 200:
        return r.json().get("ahead_by", 0)
    return 0


def finalizar_sessao() -> str:
    n = contar_commits_sessao()
    if n == 0:
        raise ValueError("Nenhuma alteração para enviar.")

    hoje = date.today().isoformat()
    sufixo = "ões" if n > 1 else "ão"
    titulo = f"data: sessão {hoje} – {n} alteraç{sufixo}"
    corpo = (
        f"Sessão de {hoje}: {n} alteraç{sufixo} nos dados da biblioteca.\n\n"
        f"> Use **Squash and merge** para manter o histórico limpo."
    )

    owner = _repo().split("/")[0]
    existing = requests.get(
        f"https://api.github.com/repos/{_repo()}/pulls",
        headers=_headers(),
        params={"head": f"{owner}:{_sessao_branch}", "state": "open"},
        timeout=10,
    )
    if existing.status_code == 200 and existing.json():
        return existing.json()[0]["html_url"]

    r = requests.post(
        f"https://api.github.com/repos/{_repo()}/pulls",
        headers=_headers(),
        json={"title": titulo, "head": _sessao_branch, "base": _base_branch(), "body": corpo},
        timeout=15,
    )
    if r.status_code == 201:
        return r.json()["html_url"]
    raise RuntimeError(
        f"Erro ao criar PR: HTTP {r.status_code} — {r.json().get('message', '')}"
    )
