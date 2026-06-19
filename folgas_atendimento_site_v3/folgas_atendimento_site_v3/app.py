from __future__ import annotations

from datetime import date, timedelta
from html import escape
import pandas as pd
import streamlit as st

from escala_engine import (
    DATA_DIR,
    build_weekly_visual_rows,
    collaborator_kind_map,
    coverage_diagnostics,
    generate_schedule,
    load_csv,
    save_csv,
    to_excel_bytes,
    whatsapp_text,
)

st.set_page_config(page_title="FOLGAS ATENDIMENTO", layout="wide")

DIAS_SEMANA = ["Sábado", "Domingo", "Segunda", "Terça", "Quarta", "Quinta", "Sexta"]
TIPOS_EVENTO = ["Folga", "Férias", "Afastamento", "Ajuste Manual", "DOM", "DOM/SEM", "DIA/DOM/SEM"]
ACOES_AJUSTE = [
    "Alterar horário",
    "Entrar mais cedo",
    "Trocar setor",
    "Adicionar extra",
    "Remover da escala",
    "Marcar folga",
    "Trabalhar no domingo",
    "Incluir no período",
    "Observação",
]
ACOES_LEGADAS = {
    "ESCALAR": "Adicionar extra",
    "FOLGAR": "Marcar folga",
    "ALTERAR_HORARIO": "Alterar horário",
    "ALTERAR_SETOR": "Trocar setor",
    "ALTERAR_PERIODO": "Incluir no período",
}
SETORES_OFICIAIS = ["Praça", "Copa", "Caixa", "Escritório", "Entrega"]
PERIODOS_OFICIAIS = ["Manhã", "Tarde", "Noite"]
HORARIOS_CONHECIDOS = ["08:30", "08:40", "10:30", "11:00", "11:30", "12:00", "14:30", "16:00", "16:30", "18:00", "18:30", "19:00", "19:30"]

st.markdown(
    """
    <style>
    .stApp {
        background: #f7f6f0;
        color: #26342b;
    }
    [data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid #ded6c3;
    }
    .v4-hero {
        padding: 26px 30px;
        border-radius: 18px;
        background: linear-gradient(120deg, #ffffff 0%, #f4efe3 62%, #e7d29a 100%);
        border: 1px solid #ded6c3;
        box-shadow: 0 10px 26px rgba(31, 63, 43, .10);
        margin-bottom: 18px;
    }
    .v4-hero h1 {
        color: #1f4e3d;
        font-size: 2.35rem;
        margin: 0 0 12px;
        letter-spacing: .03em;
    }
    .v4-hero h2 {
        color: #6b5a2e !important;
        font-size: 1.25rem;
        margin: 0 0 8px;
    }
    .v4-hero p { color: #344238; font-size: 1.02rem; margin: 0; max-width: 1100px; }
    .v4-objective {
        background: #ffffff;
        border: 1px solid #ded6c3;
        border-left: 6px solid #6fa57b;
        border-radius: 14px;
        padding: 14px 18px;
        margin: 12px 0 18px;
        color: #26342b;
    }
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #ded6c3;
        border-radius: 14px;
        padding: 14px;
        box-shadow: 0 6px 18px rgba(31, 63, 43, .08);
    }
    div[data-testid="stMetric"] label, div[data-testid="stMetric"] [data-testid="stMetricValue"] { color: #1f4e3d !important; }
    .stButton button, .stDownloadButton button {
        background: #1f7a4d !important;
        color: #ffffff !important;
        border: 0 !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
    }
    .stDataFrame, [data-testid="stDataEditor"] {
        border: 1px solid #ded6c3;
        border-radius: 12px;
        overflow: hidden;
        background: #ffffff;
    }
    div[data-testid="stTabs"] button { color: #26342b; font-weight: 650; }
    h2, h3 { color: #1f4e3d !important; }
    .v4-card {
        padding: 14px 16px;
        background: #ffffff;
        border: 1px solid #ded6c3;
        border-radius: 12px;
        margin: 10px 0 16px;
        color: #26342b;
    }
    .schedule-day-card { background: #ffffff; border: 1px solid #ded6c3; border-radius: 16px; margin: 18px 0; overflow: hidden; box-shadow: 0 8px 22px rgba(31, 63, 43, .08); }
    .schedule-day-header { background: #d9b85f; color: #26342b; padding: 12px 18px; font-weight: 850; font-size: 1.08rem; letter-spacing: .03em; }
    .schedule-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0; }
    .schedule-col { border-right: 1px solid #eee3c8; min-height: 120px; padding: 12px; }
    .schedule-col:last-child { border-right: 0; }
    .schedule-col h4 { margin: 0 0 10px; color: #1f4e3d; font-size: .95rem; text-transform: uppercase; }
    .schedule-item { border: 1px solid #e6deca; border-radius: 10px; padding: 8px 9px; margin-bottom: 8px; background: #fbfaf6; }
    .schedule-item strong { color: #1f4e3d; }
    .schedule-time { font-weight: 850; color: #5f4d17; }
    .schedule-meta { color: #59645d; font-size: .86rem; }
    .schedule-tag { display: inline-block; border-radius: 999px; padding: 1px 7px; background: #d9ead3; color: #1f4e3d; font-size: .72rem; font-weight: 800; margin-left: 4px; }
    .schedule-closed { color: #8a6d19; background: #fff4cc; border: 1px dashed #d9b85f; border-radius: 10px; padding: 10px; }
    .coverage-help { background: #ffffff; border-left: 5px solid #d9b85f; padding: 12px 14px; border-radius: 12px; margin: 10px 0 16px; }
    @media print { .stSidebar, header, .stTabs [role="tablist"], .stDownloadButton, .stButton { display: none !important; } .schedule-day-card { page-break-inside: avoid; } }
    .version-note { color: #6f6f6f; font-size: .86rem; margin-top: 18px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="v4-hero">
      <h1>FOLGAS ATENDIMENTO</h1>
      <h2>Objetivo deste aplicativo</h2>
      <p>Gerar uma escala semanal de atendimento, de sábado a sexta-feira, considerando colaboradores fixos, estagiários, extras, folgas, férias, afastamentos, horários de entrada e quadro ideal por setor.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="v4-objective">
      <strong>Relatório semanal esperado:</strong> sábado com Manhã, Tarde e Noite; domingo normal com Tarde e Noite; domingo especial com Manhã, Tarde e Noite; segunda a sexta com Manhã, Tarde e Noite. O sistema usa somente o horário de entrada — sem calcular saída, jornada ou banco de horas.
    </div>
    """,
    unsafe_allow_html=True,
)


def br_date(value: object) -> str:
    if value is None or str(value).strip() == "":
        return ""
    text = str(value).strip()
    dayfirst = not (len(text) >= 10 and text[4:5] == "-" and text[7:8] == "-")
    parsed = pd.to_datetime(text, dayfirst=dayfirst, errors="coerce")
    return "" if pd.isna(parsed) else parsed.strftime("%d/%m/%Y")


def normalize_date_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    df = df.copy()
    for column in columns:
        if column in df.columns:
            df[column] = df[column].map(br_date)
    return df


def display_action(value: object) -> str:
    text = str(value).strip()
    return ACOES_LEGADAS.get(text.upper(), text)


def prepare_ajustes_display(df: pd.DataFrame) -> pd.DataFrame:
    df = normalize_date_columns(df, ["data"])
    if "acao" in df.columns:
        df["acao"] = df["acao"].map(display_action)
    return df

st.caption("Operação semanal por dia, período, setor, função, colaborador, horário de entrada, folgas, férias, afastamentos e extras.")

DATA_DIR.mkdir(exist_ok=True)

@st.cache_data(show_spinner=False)
def read_all():
    return {
        "colaboradores": load_csv("colaboradores.csv"),
        "quadro": load_csv("quadro_ideal.csv"),
        "eventos": load_csv("eventos.csv"),
        "ajustes": load_csv("ajustes_semanais.csv"),
    }

if "reload" not in st.session_state:
    st.session_state.reload = 0

# Força recarregar quando salvar dados.
cache = read_all()
colaboradores = cache["colaboradores"]
quadro = cache["quadro"]
eventos = cache["eventos"]
ajustes = cache["ajustes"]

colaborador_nomes = sorted(colaboradores.get("nome", pd.Series(dtype=str)).astype(str).str.strip().replace("", pd.NA).dropna().unique().tolist())
eventos_display = normalize_date_columns(eventos, ["data_inicio", "data_fim"])
ajustes_display = prepare_ajustes_display(ajustes)

with st.sidebar:
    st.header("Geração")
    today = date.today()
    next_saturday = today + timedelta((5 - today.weekday()) % 7)
    start_date = st.date_input("Sábado inicial da semana", value=next_saturday)
    if start_date.weekday() != 5:
        st.warning("A semana operacional deve iniciar no sábado. Você pode continuar, mas o ideal é escolher um sábado.")
    domingo_tipo = st.radio("Tipo de domingo", ["Normal — abre 16h", "Especial — abre 11h"], index=0)
    domingo_especial = domingo_tipo.startswith("Especial")
    sugerir_extras = st.checkbox("Sugerir extras automaticamente para fechar quadro", value=True)
    st.markdown('<div class="version-note">Versão: v4.1 correção de estabilidade</div>', unsafe_allow_html=True)



def render_schedule_cards(schedule: pd.DataFrame, start: date, colaboradores: pd.DataFrame, eventos: pd.DataFrame, domingo_especial: bool) -> None:
    visual_rows = build_weekly_visual_rows(schedule, start, colaboradores, eventos, domingo_especial=domingo_especial)
    for _, day_row in visual_rows.iterrows():
        day_title = escape(str(day_row["Dia"]))
        columns_html = []
        for col in ["Meio Dia / Manhã", "Tarde", "Noite", "Folgas"]:
            raw = str(day_row.get(col, "") or "")
            if raw == "FECHADO":
                body = '<div class="schedule-closed">Fechado neste período</div>'
            elif col == "Folgas":
                names = [escape(item) for item in raw.split("\n") if item.strip()]
                body = "".join(f'<div class="schedule-item"><strong>{name}</strong></div>' for name in names) or '<div class="schedule-meta">Sem folgas identificadas</div>'
            else:
                items = []
                for line in [item for item in raw.split("\n") if item.strip()]:
                    setor, horario, resto = (line.split(" | ", 2) + ["", ""])[:3]
                    tags = []
                    if "[EXTRA" in resto:
                        tags.append("EXTRA")
                    if "ESTAGIÁRIO" in resto:
                        tags.append("ESTAGIÁRIO")
                    nome_funcao = resto.split(" [", 1)[0]
                    tag_html = "".join(f'<span class="schedule-tag">{escape(tag)}</span>' for tag in tags)
                    items.append(
                        '<div class="schedule-item">'
                        f'<div><strong>{escape(nome_funcao)}</strong>{tag_html}</div>'
                        f'<div><span class="schedule-time">{escape(horario)}</span> · {escape(setor)}</div>'
                        '</div>'
                    )
                body = "".join(items) or '<div class="schedule-meta">Sem pessoas escaladas</div>'
            columns_html.append(f'<div class="schedule-col"><h4>{escape(col)}</h4>{body}</div>')
        st.markdown(
            f'<div class="schedule-day-card"><div class="schedule-day-header">{day_title}</div><div class="schedule-grid">{"".join(columns_html)}</div></div>',
            unsafe_allow_html=True,
        )

def save_and_rerun(df: pd.DataFrame, filename: str):
    save_csv(df, filename)
    st.cache_data.clear()
    st.success(f"{filename} salvo.")
    st.rerun()


tab1, tab2, tab3, tab4, tab5 = st.tabs(["1. Colaboradores", "2. Quadro ideal", "3. Folgas / Férias / Ajustes", "4. Gerar escala", "5. Ajuda / Regras"])

with tab1:
    st.subheader("Cadastro de colaboradores, estagiários e extras")
    st.info("Edite os dados e clique em salvar. Extras externos entram por sugestão automática; colaboradores fixos entram na base conforme folgas e ajustes.")
    st.markdown('<div class="v4-card">Planilha editável: inclua, remova ou ajuste colaboradores diretamente na grade.</div>', unsafe_allow_html=True)
    edited = st.data_editor(
        colaboradores,
        num_rows="dynamic",
        width="stretch",
        hide_index=True,
        key="colab_editor",
    )
    if st.button("Salvar colaboradores", type="primary"):
        save_and_rerun(edited, "colaboradores.csv")

with tab2:
    st.subheader("Quadro ideal por dia, período e setor")
    st.info("Essa tabela define quantas pessoas o sistema deve tentar cobrir por setor. Quando faltar, o sistema mostra alerta e pode sugerir extras.")
    edited_quadro = st.data_editor(quadro, num_rows="dynamic", width="stretch", key="quadro_editor")
    if st.button("Salvar quadro ideal", type="primary"):
        save_and_rerun(edited_quadro, "quadro_ideal.csv")

with tab3:
    st.subheader("Eventos: férias, afastamentos, folgas e exceções")
    st.markdown("""
Use **Eventos** para ausências e regras mensais. Exemplos de tipo: `FÉRIAS`, `AFASTAMENTO`, `FOLGA`, `DOM`, `DOM/SEM`, `DIA/DOM/SEM`.

Use **Ajustes semanais** para decisões manuais da gestão. Exemplos de ação: `ESCALAR`, `FOLGAR`, `ALTERAR_HORARIO`, `ALTERAR_SETOR`, `ALTERAR_PERIODO`.
""")
    st.write("### Eventos")
    edited_eventos = st.data_editor(
        eventos_display,
        num_rows="dynamic",
        width="stretch",
        hide_index=True,
        key="eventos_editor",
    )
    if st.button("Salvar eventos", type="primary"):
        save_and_rerun(normalize_date_columns(edited_eventos, ["data_inicio", "data_fim"]), "eventos.csv")

    st.divider()
    st.write("### Ajustes semanais manuais")
    with st.expander("Ações disponíveis", expanded=True):
        st.table(pd.DataFrame([
            {"Ação": "Alterar horário", "Quando usar": "Muda o horário de entrada do colaborador naquele dia."},
            {"Ação": "Entrar mais cedo", "Quando usar": "Antecipa o colaborador para um horário definido manualmente."},
            {"Ação": "Trocar setor", "Quando usar": "Muda o setor do colaborador naquele dia/período."},
            {"Ação": "Adicionar extra", "Quando usar": "Inclui um extra manualmente no dia/período/setor."},
            {"Ação": "Remover da escala", "Quando usar": "Retira o colaborador daquele dia/período."},
            {"Ação": "Marcar folga", "Quando usar": "Marca folga manual naquele dia."},
            {"Ação": "Trabalhar no domingo", "Quando usar": "Permite escalar manualmente alguém que normalmente folga domingo."},
            {"Ação": "Incluir no período", "Quando usar": "Força a inclusão do colaborador em um período específico."},
            {"Ação": "Observação", "Quando usar": "Registra uma informação sem alterar automaticamente a escala."},
        ]))

    edited_ajustes = st.data_editor(
        ajustes_display,
        num_rows="dynamic",
        width="stretch",
        hide_index=True,
        column_config={
            "data": st.column_config.TextColumn("Data (dd/mm/aaaa)"),
            "nome": st.column_config.SelectboxColumn("Nome", options=colaborador_nomes, required=False),
            "acao": st.column_config.SelectboxColumn("Ação", options=ACOES_AJUSTE, required=False),
            "setor": st.column_config.SelectboxColumn("Setor", options=["", *SETORES_OFICIAIS], required=False),
            "periodo": st.column_config.SelectboxColumn("Período", options=["", *PERIODOS_OFICIAIS], required=False),
            "horario": st.column_config.SelectboxColumn("Horário", options=["", *HORARIOS_CONHECIDOS], required=False),
            "observacao": st.column_config.TextColumn("Observação"),
        },
        key="ajustes_editor",
    )
    if st.button("Salvar ajustes semanais", type="primary"):
        save_and_rerun(normalize_date_columns(edited_ajustes, ["data"]), "ajustes_semanais.csv")

with tab4:
    st.subheader("Escala Semanal")
    st.caption("Selecione a semana na lateral e use os botões abaixo para gerar, imprimir ou baixar os relatórios.")
    action_cols = st.columns([1, 1, 4])
    with action_cols[0]:
        st.button("Gerar Sugestão", type="primary")
    with action_cols[1]:
        st.button("Imprimir", help="Use Ctrl+P / Cmd+P para imprimir os cards da escala.")
    schedule, summary = generate_schedule(
        colaboradores=colaboradores,
        ideal=quadro,
        eventos=eventos,
        ajustes=ajustes,
        start=start_date,
        domingo_especial=domingo_especial,
        sugerir_extras=sugerir_extras,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Pessoas/linhas na escala", len(schedule))
    with c2:
        st.metric("Alertas de falta", int(summary["faltam"].sum()) if not summary.empty else 0)
    with c3:
        st.metric("Sugestões de extras", int((schedule["origem"] == "Sugestão extra").sum()) if not schedule.empty and "origem" in schedule else 0)

    st.write("### Relatório semanal visual")
    render_schedule_cards(schedule, start_date, colaboradores, eventos, domingo_especial)

    with st.expander("Tabela técnica da escala", expanded=False):
        st.dataframe(schedule, width="stretch", hide_index=True)

    st.write("### Conferência do quadro ideal")
    if not summary.empty:
        def highlight_gap(row):
            if row["faltam"] > 0:
                return ["background-color: #ffd6d6"] * len(row)
            if row["sobra"] > 0:
                return ["background-color: #fff4cc"] * len(row)
            return [""] * len(row)
        st.dataframe(summary.style.apply(highlight_gap, axis=1), width="stretch", hide_index=True)
    else:
        st.info("Nenhum quadro ideal encontrado.")

    st.write("### Diagnóstico de cobertura")
    diagnostico = coverage_diagnostics(summary, colaboradores, schedule, eventos, start_date)
    if not diagnostico.empty:
        st.markdown('<div class="coverage-help">Use esta área para entender se a falta é de cadastro, disponibilidade, extra ou excesso no quadro ideal.</div>', unsafe_allow_html=True)
        st.dataframe(diagnostico, width="stretch", hide_index=True)
    else:
        st.info("Não há dados suficientes para diagnóstico de cobertura.")

    st.write("### Texto pronto para WhatsApp")
    text = whatsapp_text(schedule, summary, colaboradores=colaboradores, eventos=eventos, start=start_date)
    st.text_area("Copie e cole no grupo", value=text, height=420)

    st.download_button("Baixar texto para WhatsApp (.txt)", data=text.encode("utf-8"), file_name="escala_whatsapp.txt", mime="text/plain")
    st.download_button("Baixar escala em CSV", data=schedule.to_csv(index=False).encode("utf-8"), file_name="escala_semanal.csv", mime="text/csv")
    excel_filename = f"escala_atendimento_{start_date:%Y-%m-%d}.xlsx"
    st.download_button(
        "Baixar Excel visual (.xlsx)",
        data=to_excel_bytes(schedule, summary, colaboradores=colaboradores, eventos=eventos, start=start_date, domingo_especial=domingo_especial),
        file_name=excel_filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

with tab5:
    st.subheader("Regras implementadas nesta versão")
    st.markdown("""
- A semana operacional é de **sábado até sexta**.
- O sistema considera **somente horário de entrada**, sem calcular saída ou banco de horas.
- Setores oficiais: **Praça, Copa, Caixa, Escritório e Entrega**.
- Domingo normal abre às **16h** e não usa Manhã; domingo especial pode abrir às **11h**.
- Estagiários têm domingo fixo de folga.
- Folga fixa é padrão, mas pode ser alterada manualmente em **Ajustes semanais**.
- `DIA/DOM/SEM`: trabalha só o dia, folga domingo e ganha mais uma folga na semana.
- Extras são sugeridos por déficit no quadro ideal, com rodízio simples pelo menor número de escalações.
- Colaboradores que podem antecipar horário não são alterados automaticamente; a gestão define manualmente.
- Daia - Extra e Hemerson - Extra aparecem como extras separados no output, conforme solicitado.
""")
    st.write("### O que ainda deve ser ajustado pelo uso real")
    st.markdown("""
1. Ajustar manualmente entradas específicas de domingo às 16h ou 18h.
2. Revisar se o Guilherme ficará como cadastro Entrega e escala Praça, ou se deve mudar para Entrega também na escala.
3. Confirmar se Lohran fica 11h ou 11h30 durante a semana; nesta versão usei 11h por ser a informação mais recente.
4. Alimentar férias, afastamentos, admissões e desligamentos mês a mês.
5. Apagar os exemplos já preenchidos em Eventos/Ajustes antes de usar oficialmente.
""")
