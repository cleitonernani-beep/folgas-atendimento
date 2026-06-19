from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

from escala_engine import (
    DATA_DIR,
    generate_schedule,
    load_csv,
    save_csv,
    to_excel_bytes,
    whatsapp_text,
)

st.set_page_config(page_title="FOLGAS ATENDIMENTO — v4 visual Jones", layout="wide")

DIAS_SEMANA = ["Sábado", "Domingo", "Segunda", "Terça", "Quarta", "Quinta", "Sexta"]
TIPOS_EVENTO = ["Folga", "Férias", "Afastamento", "Ajuste Manual", "DOM", "DOM/SEM", "DIA/DOM/SEM"]

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #111814 0%, #18231d 45%, #2b2418 100%);
        color: #fffaf0;
    }
    [data-testid="stSidebar"] {
        background: #0f1713;
        border-right: 1px solid #c9a44a55;
    }
    .v4-hero {
        padding: 28px 32px;
        border-radius: 24px;
        background: linear-gradient(120deg, #0e1712, #31472f 58%, #b89238);
        border: 1px solid #e7d9aa;
        box-shadow: 0 18px 45px rgba(0, 0, 0, .38);
        margin-bottom: 18px;
    }
    .v4-hero h1 {
        color: #fffdf4;
        font-size: 2.4rem;
        margin: 0;
        letter-spacing: .04em;
    }
    .v4-hero p { color: #f7ebc6; font-size: 1.05rem; margin: 8px 0 0; }
    div[data-testid="stMetric"] {
        background: #f5ead0;
        border: 1px solid #d6b86c;
        border-radius: 18px;
        padding: 16px;
        box-shadow: 0 10px 28px rgba(0, 0, 0, .24);
    }
    div[data-testid="stMetric"] label, div[data-testid="stMetric"] [data-testid="stMetricValue"] { color: #1b241d !important; }
    .stButton button, .stDownloadButton button {
        background: linear-gradient(90deg, #d5b45b, #6fa57b) !important;
        color: #102016 !important;
        border: 0 !important;
        border-radius: 999px !important;
        font-weight: 800 !important;
        box-shadow: 0 8px 22px rgba(0, 0, 0, .28);
    }
    .stDataFrame, [data-testid="stDataEditor"] {
        border: 1px solid #d6b86c88;
        border-radius: 16px;
        overflow: hidden;
        background: #fffaf0;
    }
    div[data-testid="stTabs"] button { color: #fff8df; font-weight: 700; }
    h2, h3 { color: #f2d890 !important; }
    .v4-card {
        padding: 16px 18px;
        background: rgba(255, 250, 240, .10);
        border: 1px solid rgba(214, 184, 108, .55);
        border-radius: 18px;
        margin: 10px 0 16px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="v4-hero">
      <h1>FOLGAS ATENDIMENTO — v4 visual Jones</h1>
      <p>Escala semanal com visual escuro, bege/dourado, branco e verde suave.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


def br_date(value: object) -> str:
    if value is None or str(value).strip() == "":
        return ""
    parsed = pd.to_datetime(value, dayfirst=True, errors="coerce")
    return "" if pd.isna(parsed) else parsed.strftime("%d/%m/%Y")


def normalize_date_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    df = df.copy()
    for column in columns:
        if column in df.columns:
            df[column] = df[column].map(br_date)
    return df

st.caption("Protótipo em Python/Streamlit para gerar escala semanal de sábado a sexta, considerando folgas, férias, desligamentos, quadro ideal e extras.")

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
ajustes_display = normalize_date_columns(ajustes, ["data"])

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
    colab_columns = {
        "nome": "Colaborador",
        "tipo": "Tipo",
        "setor_cadastro": "Setor cadastro",
        "setor_escala": "Setor escala",
        "funcao": "Função",
        "horario_padrao": "Horário padrão",
        "periodo_padrao": "Período",
        "folga_fixa": "Folga fixa",
        "trabalha_domingo": "Trabalha domingo?",
        "status": "Status",
        "data_admissao": "Admissão",
        "data_desligamento": "Desligamento",
        "obs": "Observações",
    }
    edited = st.data_editor(
        colaboradores,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_order=[col for col in colab_columns if col in colaboradores.columns],
        column_config={
            key: st.column_config.TextColumn(label) for key, label in colab_columns.items() if key in colaboradores.columns
        } | {
            "tipo": st.column_config.SelectboxColumn("Tipo", options=["Fixo", "Estagiário", "Extra"]),
            "periodo_padrao": st.column_config.SelectboxColumn("Período", options=["Manhã", "Tarde", "Noite"]),
            "folga_fixa": st.column_config.SelectboxColumn("Folga fixa", options=["Não", *DIAS_SEMANA]),
            "status": st.column_config.SelectboxColumn("Status", options=["Ativo", "Inativo"]),
        },
        key="colab_editor",
    )
    if st.button("Salvar colaboradores", type="primary"):
        save_and_rerun(edited, "colaboradores.csv")

with tab2:
    st.subheader("Quadro ideal por dia, período e setor")
    st.info("Essa tabela define quantas pessoas o sistema deve tentar cobrir por setor. Quando faltar, o sistema mostra alerta e pode sugerir extras.")
    edited_quadro = st.data_editor(quadro, num_rows="dynamic", use_container_width=True, key="quadro_editor")
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
        use_container_width=True,
        hide_index=True,
        column_config={
            "tipo": st.column_config.SelectboxColumn("Tipo de evento", options=TIPOS_EVENTO),
            "nome": st.column_config.SelectboxColumn("Colaborador", options=colaborador_nomes),
            "data_inicio": st.column_config.DateColumn("Data início", format="DD/MM/YYYY"),
            "data_fim": st.column_config.DateColumn("Data fim", format="DD/MM/YYYY"),
            "dia_folga_semana": st.column_config.SelectboxColumn("Folga na semana", options=["", *DIAS_SEMANA]),
            "observacao": st.column_config.TextColumn("Observação"),
        },
        key="eventos_editor",
    )
    if st.button("Salvar eventos", type="primary"):
        save_and_rerun(normalize_date_columns(edited_eventos, ["data_inicio", "data_fim"]), "eventos.csv")

    st.divider()
    st.write("### Ajustes semanais manuais")
    edited_ajustes = st.data_editor(
        ajustes_display,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
            "nome": st.column_config.SelectboxColumn("Colaborador", options=colaborador_nomes),
            "acao": st.column_config.SelectboxColumn("Ação", options=["ESCALAR", "FOLGAR", "ALTERAR_HORARIO", "ALTERAR_SETOR", "ALTERAR_PERIODO"]),
            "setor": st.column_config.SelectboxColumn("Setor", options=["", "Praça", "Copa", "Caixa", "Escritório", "Entrega"]),
            "periodo": st.column_config.SelectboxColumn("Período", options=["", "Manhã", "Tarde", "Noite"]),
            "horario": st.column_config.TextColumn("Horário"),
            "observacao": st.column_config.TextColumn("Observação"),
        },
        key="ajustes_editor",
    )
    if st.button("Salvar ajustes semanais", type="primary"):
        save_and_rerun(normalize_date_columns(edited_ajustes, ["data"]), "ajustes_semanais.csv")

with tab4:
    st.subheader("Escala semanal gerada")
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

    st.write("### Tabela da escala")
    st.dataframe(schedule, use_container_width=True, hide_index=True)

    st.write("### Conferência do quadro ideal")
    if not summary.empty:
        def highlight_gap(row):
            if row["faltam"] > 0:
                return ["background-color: #ffd6d6"] * len(row)
            if row["sobra"] > 0:
                return ["background-color: #fff4cc"] * len(row)
            return [""] * len(row)

        st.dataframe(summary.style.apply(highlight_gap, axis=1), use_container_width=True, hide_index=True)
        faltas = summary[summary["faltam"] > 0].copy()
        if not faltas.empty:
            st.error("Alertas finais após tentativa automática de preenchimento")
            st.dataframe(
                faltas[["dia", "periodo", "setor", "ideal", "escalado", "faltam", "motivo_falta"]],
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.info("Nenhum quadro ideal encontrado.")

    st.write("### Texto pronto para WhatsApp")
    text = whatsapp_text(schedule, summary)
    st.text_area("Copie e cole no grupo", value=text, height=420)

    st.download_button("Baixar texto para WhatsApp (.txt)", data=text.encode("utf-8"), file_name="escala_whatsapp.txt", mime="text/plain")
    st.download_button("Baixar escala em CSV", data=schedule.to_csv(index=False).encode("utf-8"), file_name="escala_semanal.csv", mime="text/csv")
    st.download_button("Baixar Excel com escala e cobertura", data=to_excel_bytes(schedule, summary), file_name="escala_semanal.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

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
