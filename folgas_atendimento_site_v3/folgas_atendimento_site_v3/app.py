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

st.set_page_config(page_title="FOLGAS ATENDIMENTO", layout="wide")

st.title("FOLGAS ATENDIMENTO")
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
    edited = st.data_editor(colaboradores, num_rows="dynamic", use_container_width=True, key="colab_editor")
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
    edited_eventos = st.data_editor(eventos, num_rows="dynamic", use_container_width=True, key="eventos_editor")
    if st.button("Salvar eventos", type="primary"):
        save_and_rerun(edited_eventos, "eventos.csv")

    st.divider()
    st.write("### Ajustes semanais manuais")
    edited_ajustes = st.data_editor(ajustes, num_rows="dynamic", use_container_width=True, key="ajustes_editor")
    if st.button("Salvar ajustes semanais", type="primary"):
        save_and_rerun(edited_ajustes, "ajustes_semanais.csv")

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
