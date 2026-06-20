from ui.formatting import _formatar_livro


def _livro(**kwargs):
    base = {"titulo": "", "autores": "", "ano": "", "isbn": "0000000000"}
    base.update(kwargs)
    return base


# ── markdown=True (padrão) ────────────────────────────────────────────────────

def test_titulo_autor_ano():
    livro = _livro(titulo="Kubernetes", autores="Kevin Welter", ano="2022")
    assert _formatar_livro(livro) == "**Kubernetes** — Kevin Welter (2022)"


def test_sem_autor():
    livro = _livro(titulo="Quadribol através dos séculos", ano="2001")
    assert _formatar_livro(livro) == "**Quadribol através dos séculos** (2001)"


def test_sem_ano():
    livro = _livro(titulo="Kubernetes", autores="Kevin Welter")
    assert _formatar_livro(livro) == "**Kubernetes** — Kevin Welter"


def test_sem_titulo():
    livro = _livro(autores="Autor Desconhecido", ano="2020")
    assert _formatar_livro(livro) == "**(sem título)** — Autor Desconhecido (2020)"


def test_apenas_titulo_sem_autor_sem_ano():
    livro = _livro(titulo="Apenas Título")
    assert _formatar_livro(livro) == "**Apenas Título**"


def test_titulo_e_autor_sem_ano():
    livro = _livro(titulo="Social Psychology of Organizing", autores="Karl E Weick")
    assert _formatar_livro(livro) == "**Social Psychology of Organizing** — Karl E Weick"


# ── markdown=False ────────────────────────────────────────────────────────────

def test_plain_text_com_autor():
    livro = _livro(titulo="Kubernetes", autores="Kevin Welter", ano="2022")
    assert _formatar_livro(livro, markdown=False) == "Kubernetes — Kevin Welter (2022)"


def test_plain_text_sem_autor():
    livro = _livro(titulo="Quadribol através dos séculos", ano="2001")
    assert _formatar_livro(livro, markdown=False) == "Quadribol através dos séculos (2001)"


# ── ano inválido / None literal ───────────────────────────────────────────────

def test_ano_none_literal_omitido():
    livro = _livro(titulo="Algo", autores="Alguém", ano="None")
    assert _formatar_livro(livro) == "**Algo** — Alguém"


def test_ano_none_python_omitido():
    livro = _livro(titulo="Algo", autores="Alguém", ano=None)
    assert _formatar_livro(livro) == "**Algo** — Alguém"


def test_ano_none_sem_autor():
    livro = _livro(titulo="A startup enxuta", ano="None")
    assert _formatar_livro(livro) == "**A startup enxuta**"
