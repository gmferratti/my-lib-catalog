import json
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

_PREFS_PATH = Path(__file__).parent.parent / ".streamlit" / "ui_prefs.json"


def _ler_tema() -> str:
    try:
        data = json.loads(_PREFS_PATH.read_text(encoding="utf-8"))
        return data.get("tema", "escuro")
    except (FileNotFoundError, json.JSONDecodeError):
        return "escuro"


def _salvar_tema(tema: str) -> None:
    _PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _PREFS_PATH.write_text(json.dumps({"tema": tema}), encoding="utf-8")


def _css_tema(dark: bool) -> str:
    if dark:
        return """
.badge-etiqueta { background: #2d1b4e; color: #ce93d8; }
.capa-placeholder { background: #2d2d2d; }
div[data-testid="column"] button[kind="secondary"] {
    background: none !important; border: none !important; box-shadow: none !important;
    text-align: left !important; font-weight: 600 !important;
    padding: 2px 0 !important; cursor: pointer !important;
    line-height: 1.4 !important; white-space: normal !important;
    color: #fafafa !important; width: 100% !important;
}
div[data-testid="column"] button[kind="secondary"]:hover {
    color: #90caf9 !important; background: none !important; box-shadow: none !important;
}
"""
    return """
.badge-etiqueta { background: #ede7f6; color: #6a1b9a; }
.capa-placeholder { background: #eceff1; }
div[data-testid="column"] button[kind="secondary"] {
    background: none !important; border: none !important; box-shadow: none !important;
    text-align: left !important; font-weight: 600 !important;
    padding: 2px 0 !important; cursor: pointer !important;
    line-height: 1.4 !important; white-space: normal !important;
    color: rgb(49,51,63) !important; width: 100% !important;
}
div[data-testid="column"] button[kind="secondary"]:hover {
    color: #1565c0 !important; background: none !important; box-shadow: none !important;
}
.stApp { background-color: #ffffff !important; }
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main { background-color: #ffffff !important; }
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div { background-color: #f0f2f6 !important; }
[data-testid="metric-container"] { background-color: #f0f2f6 !important; border: 1px solid #e6e9ef !important; }
[data-testid="stMetricValue"], [data-testid="stMetricLabel"] { color: #31333f !important; }
.stTextInput input { background-color: #ffffff !important; color: #31333f !important; }
[data-testid="stExpander"] { background-color: #f0f2f6 !important; }
"""


def _injetar_tema() -> None:
    dark = st.session_state.get("tema", "escuro") == "escuro"
    st.markdown(f"<style>{_css_tema(dark)}</style>", unsafe_allow_html=True)


def _sidebar_tema() -> None:
    if "tema" not in st.session_state:
        st.session_state["tema"] = _ler_tema()
    with st.sidebar:
        st.divider()
        claro = st.toggle(
            "☀️ Modo claro",
            value=st.session_state["tema"] == "claro",
            key="toggle_tema",
        )
        novo = "claro" if claro else "escuro"
        if novo != st.session_state["tema"]:
            st.session_state["tema"] = novo
            _salvar_tema(novo)
            st.rerun()


from catalog.organizer import (
    ConfigEstantes,
    EstanteConfig,
    PrateleiraConfig,
    carregar_config,
    organizar,
    salvar_config,
)
from catalog.series import compor_titulo, detectar_serie
from catalog.storage import carregar_todos_registros, reescrever_registros, salvar
import catalog.notas as notas

FONTE_CORES = {
    "openlibrary":    "#2e7d32",
    "googlebooks":    "#1565c0",
    "brasilapi":      "#f9a825",
    "isbndb":         "#6a1b9a",
    "nao_encontrado": "#b71c1c",
    "manual":         "#37474f",
}

FONTE_LABELS = {
    "openlibrary":    "Open Library",
    "googlebooks":    "Google Books",
    "brasilapi":      "BrasilAPI",
    "isbndb":         "ISBNdb",
    "nao_encontrado": "Não encontrado",
    "manual":         "Manual",
}

CAPA_FONTE_CORES = {
    "openlibrary_isbn":    "#1b5e20",
    "openlibrary_cover_i": "#2e7d32",
    "openlibrary_titulo":  "#388e3c",
    "googlebooks_isbn":    "#0d47a1",
    "googlebooks_titulo":  "#1565c0",
    "duckduckgo":          "#e65100",
    "google_cse":          "#4a148c",
    "manual":              "#37474f",
}

CAPA_FONTE_LABELS = {
    "openlibrary_isbn":    "OL ISBN",
    "openlibrary_cover_i": "OL Cover ID",
    "openlibrary_titulo":  "OL Título",
    "googlebooks_isbn":    "GB ISBN",
    "googlebooks_titulo":  "GB Título",
    "duckduckgo":          "DuckDuckGo",
    "google_cse":          "Google CSE",
    "manual":              "Manual",
}

ESTILOS = {
    "autor":   "Por autor (A → Z)",
    "assunto": "Por assunto / gênero",
    "ano":     "Por ano (mais recente primeiro)",
}

_IDIOMA_NORM = {
    "pt": "Português", "por": "Português", "pt-br": "Português", "pt-BR": "Português",
    "en": "Inglês", "eng": "Inglês",
    "es": "Espanhol", "spa": "Espanhol",
    "fr": "Francês", "fra": "Francês",
    "de": "Alemão", "deu": "Alemão", "ger": "Alemão",
    "ja": "Japonês", "jpn": "Japonês",
    "cs": "Tcheco", "ces": "Tcheco", "cze": "Tcheco",
    "it": "Italiano", "ita": "Italiano",
    "ru": "Russo", "rus": "Russo",
    "zh": "Chinês", "chi": "Chinês", "zho": "Chinês",
}


def _normalizar(s: str) -> str:
    return unicodedata.normalize("NFD", s.lower()).encode("ascii", "ignore").decode("ascii")


def _estatisticas(registros: list[dict]) -> dict:
    total = len(registros)
    total_paginas = sum(
        int(r["paginas"]) for r in registros
        if str(r.get("paginas", "")).isdigit()
    )
    com_capa = sum(1 for r in registros if r.get("capa_url"))

    contagem_idioma: dict[str, int] = {}
    for r in registros:
        cod = (r.get("idioma") or "").strip()
        if not cod:
            continue
        nome = _IDIOMA_NORM.get(cod, cod)
        contagem_idioma[nome] = contagem_idioma.get(nome, 0) + 1
    idiomas = sorted(contagem_idioma.items(), key=lambda x: -x[1])

    contagem_assunto: dict[str, int] = {}
    for r in registros:
        for termo in (r.get("assuntos") or "").split(","):
            termo = termo.strip()
            if termo:
                contagem_assunto[termo] = contagem_assunto.get(termo, 0) + 1
    assuntos = sorted(contagem_assunto.items(), key=lambda x: -x[1])[:5]

    return {
        "total": total,
        "total_paginas": total_paginas,
        "com_capa": com_capa,
        "idiomas": idiomas,
        "assuntos": assuntos,
    }


def _barra(valor: int, maximo: int, largura: int = 20) -> str:
    preenchimento = round(valor / maximo * largura) if maximo else 0
    return "█" * preenchimento


@st.cache_data(ttl=60)
def _carregar() -> list[dict]:
    return carregar_todos_registros()


@st.cache_data(ttl=None)
def _carregar_config() -> ConfigEstantes:
    return carregar_config()


def _badge(fonte: str) -> str:
    cor = FONTE_CORES.get(fonte, "#78909c")
    label = FONTE_LABELS.get(fonte, fonte)
    return (
        f'<span style="background:{cor};color:white;padding:2px 8px;'
        f'border-radius:4px;font-size:0.75rem">{label}</span>'
    )


def _badge_capa(capa_fonte: str) -> str:
    if not capa_fonte or capa_fonte == "legado":
        return ""
    cor = CAPA_FONTE_CORES.get(capa_fonte, "#78909c")
    label = CAPA_FONTE_LABELS.get(capa_fonte, capa_fonte)
    return (
        f'<span style="background:{cor};color:white;padding:2px 8px;'
        f'border-radius:4px;font-size:0.75rem">{label}</span>'
    )


def _badge_etiqueta(etiqueta: str) -> str:
    return (
        f'<span class="badge-etiqueta" style="padding:2px 8px;'
        f'border-radius:12px;font-size:0.75rem;font-weight:500">{etiqueta}</span>'
    )


def _is_autenticado() -> bool:
    return st.session_state.get("autenticado", False)


@st.dialog("🔒 Acesso restrito", width="small")
def _dialog_login() -> None:
    st.markdown("Digite a senha para habilitar o modo edição.")
    senha = st.text_input("Senha", type="password", label_visibility="collapsed")
    if st.button("Entrar", type="primary", use_container_width=True):
        senha_correta = st.secrets.get("EDIT_PASSWORD", "")
        if senha and senha == senha_correta:
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("Senha incorreta.")


def _salvar_edicao(isbn: str, campos: dict) -> None:
    registros = carregar_todos_registros()
    for r in registros:
        if r["isbn"] == isbn:
            r.update(campos)
            break
    reescrever_registros(registros)
    st.cache_data.clear()


@st.dialog("Editar livro", width="large")
def _dialog_editar(registro: dict) -> None:
    isbn = registro["isbn"]

    capa_atual = registro.get("capa_url", "")
    if capa_atual:
        col_img, col_info = st.columns([1, 3])
        with col_img:
            st.image(capa_atual, width=120)
        with col_info:
            st.markdown(f"**ISBN:** `{isbn}`")
            st.markdown(f"**Fonte original:** {registro.get('fonte', '—')}")
            capa_fonte_label = CAPA_FONTE_LABELS.get(
                registro.get("capa_fonte", ""), registro.get("capa_fonte") or "—"
            )
            st.markdown(f"**Fonte da capa:** {capa_fonte_label}")
            st.markdown(f"**Cadastrado em:** {registro.get('data_cadastro', '—')}")
    else:
        st.markdown(f"**ISBN:** `{isbn}` &nbsp;·&nbsp; sem capa cadastrada",
                    unsafe_allow_html=True)
        capa_fonte_val = registro.get("capa_fonte", "")
        if capa_fonte_val and capa_fonte_val != "legado":
            capa_fonte_label = CAPA_FONTE_LABELS.get(capa_fonte_val, capa_fonte_val)
            st.markdown(f"**Fonte da capa:** {capa_fonte_label}")

    st.divider()

    todos_registros = carregar_todos_registros()
    todas_etiquetas = sorted({
        e.strip()
        for r in todos_registros
        for e in (r.get("etiquetas") or "").split(",")
        if e.strip()
    })
    etiquetas_atuais = [
        e.strip()
        for e in (registro.get("etiquetas") or "").split(",")
        if e.strip()
    ]

    # --- Bloco série (fora do form para reagir ao toggle) ---
    serie_atual = detectar_serie(registro.get("titulo", ""))
    is_serie = st.toggle("É parte de uma série", value=serie_atual is not None)

    serie_nome = serie_atual["serie"] if serie_atual else ""
    volume_num = serie_atual["volume"] if serie_atual else 1
    sub_texto = serie_atual["subtitulo"] if serie_atual else ""

    if is_serie:
        cs1, cs2, cs3 = st.columns([2, 1, 3])
        serie_nome = cs1.text_input("Série", value=serie_nome)
        volume_num = cs2.number_input("Vol. nº", min_value=1, value=volume_num, step=1)
        sub_texto = cs3.text_input("Subtítulo", value=sub_texto,
                                   help="Deixe vazio se o volume não tem subtítulo")

    titulo_composto = compor_titulo(serie_nome, int(volume_num), sub_texto) if is_serie else ""

    with st.form("form_edicao", border=False):
        titulo = st.text_input(
            "Título",
            value=titulo_composto if is_serie else registro.get("titulo", ""),
            disabled=is_serie,
            help="Preenchido automaticamente pela seção de série acima" if is_serie else "",
        )
        autores = st.text_input("Autores", value=registro.get("autores", ""),
                                help="Separe múltiplos autores por vírgula")

        c1, c2, c3 = st.columns(3)
        with c1:
            editora = st.text_input("Editora", value=registro.get("editora", ""))
        with c2:
            ano = st.text_input("Ano", value=registro.get("ano", ""))
        with c3:
            paginas = st.text_input("Páginas", value=str(registro.get("paginas", "")))

        c4, c5 = st.columns([1, 3])
        with c4:
            idioma = st.text_input("Idioma", value=registro.get("idioma", ""),
                                   help="ISO 639-1 — pt, en, es …")
        with c5:
            assuntos = st.text_input("Assuntos", value=registro.get("assuntos", ""),
                                     help="Separe por vírgula")

        etiquetas_sel = st.multiselect(
            "Etiquetas",
            options=sorted(set(todas_etiquetas) | set(etiquetas_atuais)),
            default=etiquetas_atuais,
            accept_new_options=True,
            help="Sua curadoria pessoal — selecione existentes ou digite novas",
        )

        st.markdown("**URL da capa**")
        capa_url = st.text_input("URL da capa", value=capa_atual,
                                 label_visibility="collapsed",
                                 placeholder="https://...")

        st.markdown("**Fonte**")
        opcoes_fonte = list(FONTE_LABELS.keys())
        fonte_atual = registro.get("fonte", "manual")
        fonte_idx = opcoes_fonte.index(fonte_atual) if fonte_atual in opcoes_fonte else opcoes_fonte.index("manual")
        fonte = st.selectbox("Fonte", options=opcoes_fonte, index=fonte_idx,
                             format_func=lambda k: FONTE_LABELS[k],
                             label_visibility="collapsed")

        submitted = st.form_submit_button("💾 Salvar alterações", type="primary",
                                          use_container_width=True)

    if submitted:
        titulo_final = titulo_composto if is_serie else titulo.strip()
        _salvar_edicao(isbn, {
            "titulo": titulo_final, "autores": autores.strip(),
            "editora": editora.strip(), "ano": ano.strip(),
            "paginas": paginas.strip(), "idioma": idioma.strip(),
            "assuntos": assuntos.strip(), "capa_url": capa_url.strip(),
            "fonte": fonte,
            "etiquetas": ", ".join(etiquetas_sel),
        })
        st.toast("Registro atualizado!", icon="✅")
        st.rerun()


@st.dialog("➕ Adicionar livro por ISBN", width="large")
def _dialog_adicionar() -> None:
    preview = st.session_state.get("_isbn_add_preview")

    if preview is None:
        st.markdown("Digite o ISBN do livro. Os metadados serão buscados automaticamente nas APIs.")
        isbn_input = st.text_input(
            "ISBN",
            placeholder="9788535914849",
            help="10 ou 13 dígitos — hífens e espaços são ignorados",
            key="_isbn_add_input",
        )
        if st.button("🔍 Buscar metadados", type="primary", use_container_width=True):
            isbn_norm = "".join(c for c in (isbn_input or "") if c.isdigit())
            if len(isbn_norm) not in (10, 13):
                st.error("ISBN inválido — deve ter 10 ou 13 dígitos.")
                st.stop()
            registros = carregar_todos_registros()
            if any(r["isbn"] == isbn_norm for r in registros):
                st.warning(f"ISBN `{isbn_norm}` já está no acervo.")
                st.stop()
            with st.spinner("Buscando nas APIs…"):
                from catalog.metadata.api import buscar_metadados
                dados = buscar_metadados(isbn_norm)
            st.session_state["_isbn_add_preview"] = dados
            st.rerun()
        return

    fonte = preview.get("fonte", "")
    if fonte == "nao_encontrado":
        st.warning("⚠️ ISBN não encontrado nas APIs. Você pode salvar e editar os dados manualmente depois.")
    else:
        st.success(f"✅ Metadados encontrados via **{FONTE_LABELS.get(fonte, fonte)}**")

    col_capa, col_info = st.columns([1, 3])
    with col_capa:
        capa_url = preview.get("capa_url", "")
        if capa_url:
            st.image(capa_url, width=120)
        else:
            st.markdown(
                '<div style="height:160px;background:#eceff1;display:flex;align-items:center;'
                'justify-content:center;font-size:2.5rem;border-radius:8px">📖</div>',
                unsafe_allow_html=True,
            )
    with col_info:
        st.markdown(f"**{preview.get('titulo') or '(sem título)'}**")
        if preview.get("autores"):
            st.markdown(preview["autores"])
        partes = [p for p in [preview.get("ano"), preview.get("editora")] if p]
        if partes:
            st.caption(" · ".join(partes))
        if preview.get("assuntos"):
            st.caption(f"📌 {preview['assuntos']}")
        st.caption(f"ISBN: `{preview['isbn']}`")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Confirmar e salvar", type="primary", use_container_width=True):
            salvar(preview)
            st.cache_data.clear()
            del st.session_state["_isbn_add_preview"]
            st.toast("Livro adicionado ao acervo!", icon="✅")
            st.rerun()
    with col2:
        if st.button("↩️ Buscar outro ISBN", use_container_width=True):
            del st.session_state["_isbn_add_preview"]
            st.rerun()


@st.dialog("📝 Editar anotações", width="large")
def _dialog_notas(isbn: str, nota_atual: dict | None) -> None:
    key = f"notas_links_{isbn}"
    if key not in st.session_state:
        st.session_state[key] = [dict(l) for l in (nota_atual or {}).get("links", [])]

    anotacao = st.text_area(
        "Anotação",
        value=(nota_atual or {}).get("anotacao", ""),
        height=200,
        key=f"{key}_anotacao",
        placeholder="Escreva sua resenha ou anotações sobre o livro...",
    )

    st.markdown("**Links externos**")
    indices_remover = []
    for i, link in enumerate(st.session_state[key]):
        c1, c2, c3 = st.columns([3, 2, 1])
        link["url"] = c1.text_input(
            "URL",
            value=link.get("url", ""),
            key=f"{key}_url_{i}",
            label_visibility="collapsed",
            placeholder="https://...",
        )
        link["rotulo"] = c2.text_input(
            "Rótulo",
            value=link.get("rotulo", ""),
            key=f"{key}_rot_{i}",
            label_visibility="collapsed",
            placeholder="Rótulo (opcional)",
        )
        if c3.button("✕", key=f"{key}_rm_{i}"):
            indices_remover.append(i)

    for i in reversed(indices_remover):
        st.session_state[key].pop(i)
        st.rerun()

    if st.button("＋ Adicionar link"):
        st.session_state[key].append({"url": "", "rotulo": ""})
        st.rerun()

    st.divider()
    if st.button("💾 Salvar", type="primary", use_container_width=True):
        links_validos = [
            l for l in st.session_state[key] if l.get("url", "").strip()
        ]
        notas.salvar(isbn, anotacao, links_validos)
        del st.session_state[key]
        st.rerun()


def _session_bar() -> None:
    import catalog.storage.git_sync as git_sync
    import catalog.storage.github_sync as github_sync

    # Modo GitHub API: garante que o branch de sessão existe.
    # Se falhar, mostra o erro real — "recarregar" não ajudaria.
    if github_sync.disponivel() and not github_sync.branch_sessao():
        try:
            git_sync.garantir_branch_sessao()
        except Exception as e:
            with st.sidebar:
                st.divider()
                st.caption(f"⚠️ GitHub sync: {e}")
            return

    try:
        branch = git_sync.branch_atual()
        n = git_sync.contar_commits_sessao()
    except Exception:
        return  # Falha silenciosa — não poluir sidebar

    # Só exibe o painel quando há um branch de sessão ativo.
    # Em dev local sem GitHub token e sem branch data/, não exibe nada.
    if not branch.startswith("data/"):
        return

    with st.sidebar:
        st.divider()
        st.caption(f"🌿 `{branch}`")
        if n == 0:
            st.caption("Sem alterações pendentes.")
        else:
            label = f"{n} alteraç{'ões' if n > 1 else 'ão'} pendente{'s' if n > 1 else ''}"
            st.caption(label)

        if st.button(
            "Finalizar sessão → PR",
            disabled=(n == 0),
            key="btn_finalizar_sessao",
        ):
            try:
                url = git_sync.finalizar_sessao()
                st.success("PR criada com sucesso!")
                st.link_button("Abrir PR →", url)
            except ValueError as e:
                st.warning(str(e))
            except RuntimeError as e:
                st.error(str(e))
