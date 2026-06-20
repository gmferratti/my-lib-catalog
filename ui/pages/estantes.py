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
from ui.utils import ESTILOS, _carregar, _carregar_config

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
            titulo = livro.get("titulo") or "(sem título)"
            autores = livro.get("autores") or "(sem autor)"
            ano = livro.get("ano") or "—"
            linhas.append(f"  {autores} — {titulo} ({ano})")
        linhas.append("")
    if sem_lugar:
        linhas += [f"⚠️  {len(sem_lugar)} livros sem lugar:", "-" * 60]
        for livro in sem_lugar:
            titulo = livro.get("titulo") or livro.get("isbn", "—")
            linhas.append(f"  {titulo}")
    return "\n".join(linhas)


with st.expander("⚙️ Configurar estantes", expanded=not bool(_carregar_config().estantes)):
    cfg_atual = _carregar_config()

    with st.form("form_config_estantes"):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            num_estantes = st.number_input(
                "Número de estantes", min_value=1, max_value=20,
                value=max(1, len(cfg_atual.estantes)),
                step=1,
            )
        with c2:
            prat_por_estante = st.number_input(
                "Prateleiras por estante", min_value=1, max_value=30,
                value=max(1, len(cfg_atual.estantes[0].prateleiras)
                          if cfg_atual.estantes else 4),
                step=1,
            )
        with c3:
            largura_cm = st.number_input(
                "Largura de cada prateleira (cm)", min_value=10.0, max_value=300.0,
                value=float(cfg_atual.estantes[0].prateleiras[0].largura_cm
                            if cfg_atual.estantes and cfg_atual.estantes[0].prateleiras
                            else 80.0),
                step=5.0,
            )
        with c4:
            espessura_cm = st.number_input(
                "Espessura média dos livros (cm)", min_value=0.5, max_value=10.0,
                value=float(cfg_atual.espessura_media_cm),
                step=0.5,
                help="Espessura média da lombada. Padrão: 2,5 cm.",
            )

        cap_prat = max(1, int(largura_cm / espessura_cm))
        cap_total_prev = int(num_estantes) * int(prat_por_estante) * cap_prat
        num_prat_total = int(num_estantes) * int(prat_por_estante)
        st.caption(
            f"Capacidade estimada: **{cap_prat} livros/prateleira** · "
            f"**{num_prat_total} prateleiras** · "
            f"**{cap_total_prev} livros no total**"
        )

        salvar = st.form_submit_button("💾 Salvar configuração", type="primary")

    if salvar:
        letras = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        nova_cfg = ConfigEstantes(
            espessura_media_cm=float(espessura_cm),
            estantes=[
                EstanteConfig(
                    nome=f"Estante {i + 1}",
                    prateleiras=[
                        PrateleiraConfig(
                            nome=letras[j % 26] if j < 26 else f"{letras[(j // 26) - 1]}{letras[j % 26]}",
                            largura_cm=float(largura_cm),
                        )
                        for j in range(int(prat_por_estante))
                    ],
                )
                for i in range(int(num_estantes))
            ],
        )
        salvar_config(nova_cfg)
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
                titulo = livro.get("titulo") or "(sem título)"
                autores = livro.get("autores") or "(sem autor)"
                ano = f" ({livro['ano']})" if livro.get("ano") else ""
                st.markdown(f"- {autores} — **{titulo}**{ano}")

if sem_lugar:
    st.subheader("📦 Livros sem lugar")
    for livro in sem_lugar:
        titulo = livro.get("titulo") or livro.get("isbn", "—")
        autores = livro.get("autores", "")
        st.markdown(f"- {autores} — **{titulo}**" if autores else f"- **{titulo}**")
