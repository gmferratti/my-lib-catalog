import subprocess
from datetime import date
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _git(*args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )


def _git_output(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _gh(*args: str) -> str:
    try:
        result = subprocess.run(
            ["gh", *args],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except FileNotFoundError:
        raise RuntimeError(
            "gh CLI não encontrado. Instale em: https://cli.github.com/"
        )


def _tem_mudancas_staged() -> bool:
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=_REPO_ROOT,
    )
    return result.returncode != 0


def branch_atual() -> str:
    from catalog.storage import github_sync
    if github_sync.disponivel():
        b = github_sync.branch_sessao()
        if b:
            return b
    try:
        return _git_output("rev-parse", "--abbrev-ref", "HEAD")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "HEAD"


def garantir_branch_sessao() -> str:
    from catalog.storage import github_sync
    if github_sync.disponivel():
        return github_sync.garantir_branch_sessao()
    # git CLI local
    branch = branch_atual()
    if branch.startswith("data/"):
        return branch
    nome = f"data/{date.today().isoformat()}"
    try:
        _git("checkout", "-b", nome)
    except subprocess.CalledProcessError:
        try:
            _git("checkout", nome)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            raise RuntimeError(f"Não foi possível criar/acessar o branch {nome}: {e}") from e
    return nome


def commit_se_houver_mudancas(mensagem: str, arquivos=None) -> bool:
    from catalog.storage import github_sync
    if github_sync.disponivel():
        if not arquivos:
            return False
        return github_sync.commit_arquivos(list(arquivos), mensagem)
    # git CLI local — pode falhar em ambientes sem git configurado (ex: Streamlit Cloud sem token)
    try:
        _git("add", "data/")
        if not _tem_mudancas_staged():
            return False
        _git("commit", "-m", mensagem)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def contar_commits_sessao() -> int:
    from catalog.storage import github_sync
    if github_sync.disponivel():
        return github_sync.contar_commits_sessao()
    try:
        return int(_git_output("rev-list", "main..HEAD", "--count"))
    except (subprocess.CalledProcessError, ValueError):
        return 0


def finalizar_sessao() -> str:
    from catalog.storage import github_sync
    if github_sync.disponivel():
        return github_sync.finalizar_sessao()
    # git CLI local
    n = contar_commits_sessao()
    if n == 0:
        raise ValueError("Nenhuma alteração para enviar.")
    hoje = date.today().isoformat()
    sufixo = "ões" if n > 1 else "ão"
    mensagem = f"data: sessão {hoje} – {n} alteraç{sufixo}"
    branch = branch_atual()
    try:
        _git("reset", "--soft", "main")
        _git("commit", "-m", mensagem)
        _git("push", "-u", "origin", branch)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        raise RuntimeError(f"Erro ao finalizar sessão via git CLI: {e}") from e
    return _gh(
        "pr", "create",
        "--title", mensagem,
        "--body", f"Sessão de {hoje}: {n} alteraç{sufixo} nos dados da biblioteca.",
        "--head", branch,
        "--base", "main",
    )
