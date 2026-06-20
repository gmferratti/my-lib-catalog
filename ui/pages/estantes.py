import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from catalog.organizer import (
    ConfigEstantes,
    EstanteConfig,
    PrateleiraConfig,
    carregar_config,
    organizar,
    salvar_config,
)
from catalog.storage import carregar_todos_registros, reescrever_registros
from ui.utils import ESTILOS, _carregar, _carregar_config, _injetar_tema, _session_bar, _sidebar_tema
from ui.formatting import _formatar_livro

_injetar_tema()
if st.button("← Voltar ao acervo"):
    st.switch_page("pages/acervo.py")

st.title("📚 Minha Biblioteca")

with st.sidebar:
    st.page_link("pages/acervo.py", label="📚 Acervo")
    st.page_link("pages/estantes.py", label="🗂️ Estantes")
    st.page_link("pages/leitura.py", label="📋 Lista de Leitura")
    st.page_link("pages/sobre.py", label="📖 Sobre")

livros = _carregar()


def _gerar_txt(resultados: list, sem_lugar: list[dict], estilo: str) -> str:
    linhas = [f"Organização por: {ESTILOS[estilo]}", "=" * 60, ""]
    for r in resultados:
        ocupacao = len(r.livros)
        linhas.append(f"🗄️  {r.estante} — {r.prateleira}  |  {r.label_sugerido}"
                      f"  |  {ocupacao}/{r.capacidade} livros")
        linhas.append("-" * 60)
        for livro in r.livros:
            linhas.append(f"  {_formatar_livro(livro, markdown=False)}")
        linhas.append("")
    if sem_lugar:
        linhas += [f"⚠️  {len(sem_lugar)} livros sem lugar:", "-" * 60]
        for livro in sem_lugar:
            linhas.append(f"  {_formatar_livro(livro, markdown=False)}")
    return "\n".join(linhas)


def _sync_draft() -> None:
    """Lê os valores atuais dos widgets e os grava no rascunho."""
    for i, e in enumerate(st.session_state.get("estante_draft", [])):
        e["nome"] = st.session_state.get(f"est_{i}_nome", e["nome"])
        for j, p in enumerate(e["prateleiras"]):
            p["nome"] = st.session_state.get(f"prat_{i}_{j}_nome", p["nome"])
            p["largura_cm"] = float(
                st.session_state.get(f"prat_{i}_{j}_largura", p["largura_cm"])
            )


def _clear_widget_keys() -> None:
    """Remove as chaves dos widgets de prateleira/estante para forçar reinicialização."""
    for k in [k for k in st.session_state
              if k.startswith(("est_", "prat_", "espessura_editor"))]:
        del st.session_state[k]


if "estante_draft" not in st.session_state:
    _cfg_init = carregar_config()
    st.session_state["estante_draft"] = [
        {
            "nome": e.nome,
            "prateleiras": [
                {"nome": p.nome, "largura_cm": p.largura_cm}
                for p in e.prateleiras
            ],
        }
        for e in _cfg_init.estantes
    ]
    st.session_state["espessura_draft"] = _cfg_init.espessura_media_cm

with st.expander("⚙️ Configurar estantes", expanded=not bool(st.session_state["estante_draft"])):
    st.number_input(
        "Espessura média dos livros (cm)", min_value=0.5, max_value=10.0,
        value=float(st.session_state.get("espessura_draft", 2.5)),
        step=0.5, key="espessura_editor",
        help="Usada para estimar quantos livros cabem em cada prateleira.",
    )

    for i, estante in enumerate(st.session_state["estante_draft"]):
        st.markdown(f"---\n**🗄️ Estante {i + 1}**")
        st.text_input(
            "Nome da estante", value=estante["nome"],
            key=f"est_{i}_nome", label_visibility="collapsed",
            placeholder="Nome da estante",
        )

        for j, prat in enumerate(estante["prateleiras"]):
            c1, c2, c3 = st.columns([2, 4, 1])
            c1.text_input(
                "Nome", value=prat["nome"],
                key=f"prat_{i}_{j}_nome", label_visibility="collapsed",
                placeholder="Nome",
            )
            c2.number_input(
                "Largura (cm)", min_value=10.0, max_value=500.0, step=5.0,
                value=float(prat["largura_cm"]),
                key=f"prat_{i}_{j}_largura", label_visibility="collapsed",
            )
            if c3.button("🗑️", key=f"del_prat_{i}_{j}", help="Remover prateleira"):
                _sync_draft()
                estante["prateleiras"].pop(j)
                _clear_widget_keys()
                st.rerun()

        col_add_p, col_del_e = st.columns([3, 2])
        if col_add_p.button("+ Prateleira", key=f"add_prat_{i}"):
            _sync_draft()
            letras = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            n = len(estante["prateleiras"])
            nome_prat = (
                letras[n % 26] if n < 26
                else f"{letras[(n // 26) - 1]}{letras[n % 26]}"
            )
            estante["prateleiras"].append({"nome": nome_prat, "largura_cm": 80.0})
            _clear_widget_keys()
            st.rerun()
        if col_del_e.button("🗑️ Remover estante", key=f"del_est_{i}", type="secondary"):
            _sync_draft()
            st.session_state["estante_draft"].pop(i)
            _clear_widget_keys()
            st.rerun()

        espessura_val = float(st.session_state.get("espessura_editor", 2.5))
        cap_est = sum(
            max(1, int(
                float(st.session_state.get(f"prat_{i}_{j}_largura", p["largura_cm"]))
                / espessura_val
            ))
            for j, p in enumerate(estante["prateleiras"])
        )
        st.caption(
            f"Capacidade estimada: **{cap_est} livros** "
            f"({len(estante['prateleiras'])} prateleiras)"
        )

    st.divider()
    col_add_e, col_add_p, col_save = st.columns([1, 1, 1])
    if col_add_e.button("+ Estante", key="add_estante"):
        _sync_draft()
        n = len(st.session_state["estante_draft"])
        st.session_state["estante_draft"].append({
            "nome": f"Estante {n + 1}",
            "prateleiras": [{"nome": "A", "largura_cm": 80.0}],
        })
        _clear_widget_keys()
        st.rerun()

    if col_add_p.button("+ Prateleira avulsa", key="add_prat_avulsa",
                        help="Prateleira sem estante — p. ex. fixada na parede"):
        _sync_draft()
        n_avulsas = sum(
            1 for e in st.session_state["estante_draft"]
            if e["nome"].startswith("Prateleira ")
        )
        st.session_state["estante_draft"].append({
            "nome": f"Prateleira {n_avulsas + 1}",
            "prateleiras": [{"nome": "A", "largura_cm": 80.0}],
        })
        _clear_widget_keys()
        st.rerun()

    if col_save.button("💾 Salvar configuração", type="primary", key="salvar_estantes"):
        _sync_draft()
        nova_cfg = ConfigEstantes(
            espessura_media_cm=float(st.session_state.get("espessura_editor", 2.5)),
            estantes=[
                EstanteConfig(
                    nome=e["nome"],
                    prateleiras=[
                        PrateleiraConfig(
                            nome=p["nome"],
                            largura_cm=float(p["largura_cm"]),
                        )
                        for p in e["prateleiras"]
                    ],
                )
                for e in st.session_state["estante_draft"]
            ],
        )
        salvar_config(nova_cfg)
        del st.session_state["estante_draft"]
        _clear_widget_keys()
        st.cache_data.clear()
        st.toast("Configuração salva!", icon="✅")
        st.rerun()

cfg = _carregar_config()
if not cfg.estantes:
    st.info("Configure as suas estantes acima para gerar uma sugestão de organização.")
    st.stop()

st.divider()
col_estilo, col_btn = st.columns([3, 1])
with col_estilo:
    estilo = st.selectbox(
        "Estilo de organização",
        options=list(ESTILOS.keys()),
        format_func=lambda k: ESTILOS[k],
        label_visibility="collapsed",
    )
with col_btn:
    gerar = st.button("🗂️ Gerar sugestão", type="primary", use_container_width=True)

if "organizer_resultado" not in st.session_state or gerar:
    if livros:
        res, sem_lugar = organizar(livros, cfg, estilo)
        st.session_state["organizer_resultado"] = res
        st.session_state["organizer_sem_lugar"] = sem_lugar
        st.session_state["organizer_estilo"] = estilo
    else:
        st.warning("Nenhum livro no acervo para organizar.")
        st.stop()

resultado: list = st.session_state.get("organizer_resultado", [])
sem_lugar: list = st.session_state.get("organizer_sem_lugar", [])
estilo_usado: str = st.session_state.get("organizer_estilo", estilo)

if not resultado:
    st.stop()

total_livros = len(livros)
total_prat = len(resultado)
cap_total = sum(r.capacidade for r in resultado)
distribuidos = sum(len(r.livros) for r in resultado)
ocupacao_pct = round(distribuidos / cap_total * 100) if cap_total else 0

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Livros no acervo", total_livros)
m2.metric("Prateleiras", total_prat)
m3.metric("Capacidade total", cap_total)
m4.metric("Distribuídos", distribuidos)
m5.metric("Ocupação", f"{ocupacao_pct}%")

if sem_lugar:
    prat_extras = -(-len(sem_lugar) // (cap_total // total_prat)) if total_prat else "?"
    st.warning(
        f"⚠️ **{len(sem_lugar)} livros não cabem** nas prateleiras configuradas. "
        f"Considere adicionar ~{prat_extras} prateleira(s) ou aumentar a largura."
    )

st.divider()

txt = _gerar_txt(resultado, sem_lugar, estilo_usado)
col_dl, col_ap = st.columns([2, 3])
with col_dl:
    st.download_button(
        "📥 Baixar sugestão (.txt)",
        data=txt.encode("utf-8"),
        file_name=f"organizacao_{estilo_usado}.txt",
        mime="text/plain",
    )
with col_ap:
    if st.button("✅ Aplicar esta sugestão como posição real", type="primary",
                 use_container_width=True):
        todos = carregar_todos_registros()
        mapa: dict[str, tuple[str, str]] = {}
        for prat in resultado:
            for livro in prat.livros:
                mapa[livro["isbn"]] = (prat.estante, prat.prateleira)
        for r in todos:
            estante_val, prat_val = mapa.get(r["isbn"], ("", ""))
            r["estante"] = estante_val
            r["prateleira"] = prat_val
        reescrever_registros(todos)
        st.cache_data.clear()
        st.toast("Posições aplicadas ao acervo!", icon="✅")
        st.rerun()

estante_atual = None
for r in resultado:
    if r.estante != estante_atual:
        estante_atual = r.estante
        st.subheader(f"🗄️ {r.estante}")

    ocupacao = len(r.livros)
    pct = ocupacao / r.capacidade if r.capacidade else 0
    header = (
        f"**{r.prateleira}** &nbsp;·&nbsp; "
        f"*{r.label_sugerido}* &nbsp;·&nbsp; "
        f"{ocupacao}/{r.capacidade} livros"
    )
    with st.expander(header, expanded=False):
        st.progress(pct)
        if not r.livros:
            st.caption("(vazia)")
        else:
            for livro in r.livros:
                st.markdown(f"- {_formatar_livro(livro)}")

if sem_lugar:
    st.subheader("📦 Livros sem lugar")
    for livro in sem_lugar:
        st.markdown(f"- {_formatar_livro(livro)}")

_session_bar()
_sidebar_tema()
