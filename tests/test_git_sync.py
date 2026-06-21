from datetime import date
from unittest.mock import call, patch
import subprocess

import pytest

import catalog.storage.git_sync as git_sync


@pytest.fixture(autouse=True)
def mock_git_sync():
    """Override do fixture global — aqui testamos o git_sync real."""
    yield


class TestBranchAtual:
    def test_retorna_nome_do_branch(self):
        with patch.object(git_sync, "_git_output", return_value="main"):
            assert git_sync.branch_atual() == "main"


class TestGarantirBranchSessao:
    def test_ja_em_branch_sessao_retorna_sem_criar(self):
        with patch.object(git_sync, "_git_output", return_value="data/2026-06-20"), \
             patch.object(git_sync, "_git") as mock_git:
            result = git_sync.garantir_branch_sessao()
        assert result == "data/2026-06-20"
        mock_git.assert_not_called()

    def test_em_main_cria_branch_do_dia(self):
        esperado = f"data/{date.today().isoformat()}"
        with patch.object(git_sync, "_git_output", return_value="main"), \
             patch.object(git_sync, "_git") as mock_git:
            result = git_sync.garantir_branch_sessao()
        assert result == esperado
        mock_git.assert_called_once_with("checkout", "-b", esperado)

    def test_branch_ja_existe_faz_checkout(self):
        esperado = f"data/{date.today().isoformat()}"
        with patch.object(git_sync, "_git_output", return_value="main"), \
             patch.object(git_sync, "_git", side_effect=[
                 subprocess.CalledProcessError(128, "git"),
                 None,
             ]) as mock_git:
            result = git_sync.garantir_branch_sessao()
        assert result == esperado
        assert mock_git.call_args_list == [
            call("checkout", "-b", esperado),
            call("checkout", esperado),
        ]


class TestCommitSeHouverMudancas:
    def test_sem_mudancas_retorna_false(self):
        with patch.object(git_sync, "_git"), \
             patch.object(git_sync, "_tem_mudancas_staged", return_value=False):
            result = git_sync.commit_se_houver_mudancas("edit: Livro")
        assert result is False

    def test_com_mudancas_commita_e_retorna_true(self):
        with patch.object(git_sync, "_git") as mock_git, \
             patch.object(git_sync, "_tem_mudancas_staged", return_value=True):
            result = git_sync.commit_se_houver_mudancas("edit: Livro Teste")
        assert result is True
        mock_git.assert_any_call("commit", "-m", "edit: Livro Teste")

    def test_sempre_faz_git_add_data(self):
        with patch.object(git_sync, "_git") as mock_git, \
             patch.object(git_sync, "_tem_mudancas_staged", return_value=False):
            git_sync.commit_se_houver_mudancas("qualquer")
        mock_git.assert_called_once_with("add", "data/")


class TestContarCommitsSessao:
    def test_retorna_inteiro(self):
        with patch.object(git_sync, "_git_output", return_value="3"):
            assert git_sync.contar_commits_sessao() == 3

    def test_sem_commits_retorna_zero(self):
        with patch.object(git_sync, "_git_output", return_value="0"):
            assert git_sync.contar_commits_sessao() == 0

    def test_erro_git_retorna_zero(self):
        with patch.object(git_sync, "_git_output",
                          side_effect=subprocess.CalledProcessError(1, "git")):
            assert git_sync.contar_commits_sessao() == 0


class TestFinalizarSessao:
    def test_sem_commits_levanta_value_error(self):
        with patch.object(git_sync, "contar_commits_sessao", return_value=0):
            with pytest.raises(ValueError, match="Nenhuma alteração"):
                git_sync.finalizar_sessao()

    def test_squash_e_pr_retorna_url(self):
        url_esperada = "https://github.com/user/repo/pull/42"
        with patch.object(git_sync, "contar_commits_sessao", return_value=2), \
             patch.object(git_sync, "branch_atual", return_value="data/2026-06-20"), \
             patch.object(git_sync, "_git") as mock_git, \
             patch.object(git_sync, "_gh", return_value=url_esperada):
            url = git_sync.finalizar_sessao()
        assert url == url_esperada
        mock_git.assert_any_call("reset", "--soft", "main")
        mock_git.assert_any_call("push", "-u", "origin", "data/2026-06-20")

    def test_mensagem_singular(self):
        with patch.object(git_sync, "contar_commits_sessao", return_value=1), \
             patch.object(git_sync, "branch_atual", return_value="data/2026-06-20"), \
             patch.object(git_sync, "_git"), \
             patch.object(git_sync, "_gh", return_value="https://example.com") as mock_gh:
            git_sync.finalizar_sessao()
        titulo = mock_gh.call_args.args[3]
        assert "1 alteração" in titulo

    def test_mensagem_plural(self):
        with patch.object(git_sync, "contar_commits_sessao", return_value=5), \
             patch.object(git_sync, "branch_atual", return_value="data/2026-06-20"), \
             patch.object(git_sync, "_git"), \
             patch.object(git_sync, "_gh", return_value="https://example.com") as mock_gh:
            git_sync.finalizar_sessao()
        titulo = mock_gh.call_args.args[3]
        assert "5 alterações" in titulo

    def test_gh_nao_instalado_levanta_runtime_error(self):
        with patch.object(git_sync, "contar_commits_sessao", return_value=1), \
             patch.object(git_sync, "branch_atual", return_value="data/2026-06-20"), \
             patch.object(git_sync, "_git"), \
             patch.object(git_sync, "_gh",
                          side_effect=RuntimeError("gh CLI não encontrado")):
            with pytest.raises(RuntimeError, match="gh CLI"):
                git_sync.finalizar_sessao()


import logging


class TestLogging:
    def test_commit_loga_info_mensagem(self, caplog):
        with patch.object(git_sync, "_git"), \
             patch.object(git_sync, "_tem_mudancas_staged", return_value=True), \
             caplog.at_level(logging.INFO, logger="catalog.storage.git_sync"):
            git_sync.commit_se_houver_mudancas("edit: Livro Teste")
        assert any("commit: edit: Livro Teste" in r.message for r in caplog.records)

    def test_sem_mudancas_loga_debug(self, caplog):
        with patch.object(git_sync, "_git"), \
             patch.object(git_sync, "_tem_mudancas_staged", return_value=False), \
             caplog.at_level(logging.DEBUG, logger="catalog.storage.git_sync"):
            git_sync.commit_se_houver_mudancas("edit: Livro Teste")
        assert any("nenhuma mudança" in r.message for r in caplog.records)
