from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
DIAS_PT = {
    0: "Segunda",
    1: "Terça",
    2: "Quarta",
    3: "Quinta",
    4: "Sexta",
    5: "Sábado",
    6: "Domingo",
}
PERIODOS = ["Manhã", "Tarde", "Noite"]
SETORES = ["Praça", "Copa", "Caixa", "Escritório", "Entrega"]


def load_csv(name: str) -> pd.DataFrame:
    path = DATA_DIR / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str).fillna("")


def save_csv(df: pd.DataFrame, name: str) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    df.to_csv(DATA_DIR / name, index=False)


def normalize_bool(value: object) -> bool:
    text = str(value).strip().lower()
    return text in {"sim", "s", "yes", "true", "1", "poderá trabalhar sim"}


def normalize_day(value: object) -> str:
    text = str(value).strip().lower()
    mapping = {
        "segunda": "Segunda",
        "segunda-feira": "Segunda",
        "terça": "Terça",
        "terca": "Terça",
        "terça-feira": "Terça",
        "terca-feira": "Terça",
        "quarta": "Quarta",
        "quarta-feira": "Quarta",
        "quinta": "Quinta",
        "quinta-feira": "Quinta",
        "sexta": "Sexta",
        "sexta-feira": "Sexta",
        "sábado": "Sábado",
        "sabado": "Sábado",
        "domingo": "Domingo",
        "não": "Não",
        "nao": "Não",
        "": "",
    }
    return mapping.get(text, str(value).strip())


def parse_date(value: object) -> date | None:
    text = str(value).strip()
    if not text:
        return None
    try:
        # A interface usa formato brasileiro (dd/mm/aaaa), mas mantemos
        # compatibilidade com datas ISO já existentes nos CSVs.
        return pd.to_datetime(text, dayfirst=True).date()
    except Exception:
        return None


def date_range(start: date, days: int = 7) -> list[date]:
    return [start + timedelta(days=i) for i in range(days)]


def is_between(current: date, start: date | None, end: date | None) -> bool:
    if start is None:
        return False
    if end is None:
        end = start
    return start <= current <= end


def employee_active(row: pd.Series, current: date, eventos: pd.DataFrame) -> bool:
    status = str(row.get("status", "Ativo")).strip().lower()
    if status and status not in {"ativo", "active"}:
        return False

    adm = parse_date(row.get("data_admissao", ""))
    dem = parse_date(row.get("data_desligamento", ""))
    if adm and current < adm:
        return False
    if dem and current > dem:
        return False

    nome = row.get("nome", "")
    if not eventos.empty:
        evs = eventos[eventos["nome"].astype(str).str.strip().str.lower() == str(nome).strip().lower()]
        for _, ev in evs.iterrows():
            tipo = str(ev.get("tipo", "")).strip().upper()
            if tipo in {"FÉRIAS", "FERIAS", "AFASTAMENTO", "ATESTADO", "DESLIGAMENTO"}:
                if is_between(current, parse_date(ev.get("data_inicio")), parse_date(ev.get("data_fim"))):
                    return False
    return True


def explicit_folga(nome: str, current: date, eventos: pd.DataFrame) -> bool:
    if eventos.empty:
        return False
    evs = eventos[eventos["nome"].astype(str).str.strip().str.lower() == str(nome).strip().lower()]
    for _, ev in evs.iterrows():
        tipo = str(ev.get("tipo", "")).strip().upper()
        start = parse_date(ev.get("data_inicio"))
        end = parse_date(ev.get("data_fim")) or start
        if tipo in {"FOLGA", "FOLGA SEMANAL", "SEM"} and is_between(current, start, end):
            return True
        if tipo in {"DOM", "DOM/SEM", "DIA/DOM/SEM"} and current.weekday() == 6 and is_between(current, start, end):
            return True
        # Folga da semana vinculada a DOM/SEM ou DIA/DOM/SEM
        dia_sem = normalize_day(ev.get("dia_folga_semana", ""))
        if tipo in {"DOM/SEM", "DIA/DOM/SEM"} and dia_sem and DIAS_PT[current.weekday()] == dia_sem:
            return True
    return False


def works_only_day(nome: str, current: date, eventos: pd.DataFrame) -> bool:
    """Regra DIA/DOM/SEM: trabalha só Manhã/Tarde na data indicada, sem Noite."""
    if eventos.empty:
        return False
    evs = eventos[eventos["nome"].astype(str).str.strip().str.lower() == str(nome).strip().lower()]
    for _, ev in evs.iterrows():
        tipo = str(ev.get("tipo", "")).strip().upper()
        if tipo == "DIA/DOM/SEM" and is_between(current, parse_date(ev.get("data_inicio")), parse_date(ev.get("data_inicio"))):
            return True
    return False


def manual_actions_for_date(ajustes: pd.DataFrame, current: date) -> pd.DataFrame:
    if ajustes.empty or "data" not in ajustes.columns:
        return pd.DataFrame(columns=ajustes.columns if not ajustes.empty else [])
    parsed = ajustes["data"].map(parse_date)
    return ajustes[parsed == current].copy()


def has_manual_escalar(nome: str, current: date, ajustes: pd.DataFrame) -> bool:
    acts = manual_actions_for_date(ajustes, current)
    if acts.empty:
        return False
    mask = acts["nome"].astype(str).str.strip().str.lower() == str(nome).strip().lower()
    mask &= acts["acao"].astype(str).str.strip().str.upper() == "ESCALAR"
    return bool(mask.any())


def default_sunday_time(row: pd.Series) -> tuple[str, str]:
    nome = str(row.get("nome", "")).strip().upper()
    horario = str(row.get("horario_padrao", "")).strip()
    periodo = str(row.get("periodo_padrao", "")).strip() or "Tarde"

    if nome in {"ANA JULYA", "THIAGO"}:
        return "18:00", "Noite"
    if horario < "16:00":
        return "16:00", "Tarde"
    return horario, periodo


def default_saturday_override(row: pd.Series) -> tuple[str, str] | None:
    nome = str(row.get("nome", "")).strip().upper()
    if nome == "LOHRAN":
        return "17:00", "Noite"
    return None


def should_schedule_employee(row: pd.Series, current: date, eventos: pd.DataFrame, ajustes: pd.DataFrame, domingo_especial: bool) -> bool:
    nome = str(row.get("nome", "")).strip()
    tipo = str(row.get("tipo", "")).strip().lower()
    dia = DIAS_PT[current.weekday()]

    if not employee_active(row, current, eventos):
        return False

    # Extras entram por sugestão para fechar quadro, não como base fixa.
    if tipo == "extra":
        return False

    # Domingo: estagiários não entram e folga fixa domingo é padrão, mas pode ser forçada por ajuste manual.
    if current.weekday() == 6:
        if tipo.startswith("estagi"):
            return False
        if not normalize_bool(row.get("trabalha_domingo", "")):
            return False
        if normalize_day(row.get("folga_fixa", "")) == "Domingo" and not has_manual_escalar(nome, current, ajustes):
            return False

    if explicit_folga(nome, current, eventos) and not has_manual_escalar(nome, current, ajustes):
        return False

    folga_fixa = normalize_day(row.get("folga_fixa", ""))
    if folga_fixa and folga_fixa != "Não" and dia == folga_fixa and not has_manual_escalar(nome, current, ajustes):
        return False

    # Domingo normal não tem Manhã.
    if current.weekday() == 6 and not domingo_especial:
        return True
    return True


def generate_base_schedule(
    colaboradores: pd.DataFrame,
    eventos: pd.DataFrame,
    ajustes: pd.DataFrame,
    start: date,
    domingo_especial: bool = False,
) -> pd.DataFrame:
    rows: list[dict] = []
    for current in date_range(start, 7):
        dia = DIAS_PT[current.weekday()]
        for _, emp in colaboradores.iterrows():
            if not should_schedule_employee(emp, current, eventos, ajustes, domingo_especial):
                continue
            nome = str(emp.get("nome", "")).strip()
            horario = str(emp.get("horario_padrao", "")).strip()
            periodo = str(emp.get("periodo_padrao", "")).strip() or "Tarde"
            setor = str(emp.get("setor_escala", emp.get("setor_cadastro", ""))).strip()
            funcao = str(emp.get("funcao", "")).strip()

            sat_override = default_saturday_override(emp) if current.weekday() == 5 else None
            if sat_override:
                horario, periodo = sat_override
            if current.weekday() == 6:
                horario, periodo = default_sunday_time(emp)
                if not domingo_especial and periodo == "Manhã":
                    periodo = "Tarde"
                    horario = "16:00"

            # DIA/DOM/SEM na data do DIA: não trabalha à noite.
            if works_only_day(nome, current, eventos) and periodo == "Noite":
                continue

            rows.append(
                {
                    "data": current.isoformat(),
                    "dia": dia,
                    "periodo": periodo,
                    "setor": setor,
                    "funcao": funcao,
                    "nome": nome,
                    "horario": horario,
                    "origem": "Base",
                    "observacao": str(emp.get("obs", "")).strip(),
                }
            )
    schedule = pd.DataFrame(rows)
    if schedule.empty:
        return pd.DataFrame(columns=["data", "dia", "periodo", "setor", "funcao", "nome", "horario", "origem", "observacao"])
    schedule = apply_manual_adjustments(schedule, colaboradores, ajustes)
    return schedule.sort_values(["data", "periodo", "setor", "horario", "nome"]).reset_index(drop=True)


def apply_manual_adjustments(schedule: pd.DataFrame, colaboradores: pd.DataFrame, ajustes: pd.DataFrame) -> pd.DataFrame:
    if ajustes.empty:
        return schedule
    schedule = schedule.copy()
    for _, act in ajustes.iterrows():
        current_date = parse_date(act.get("data", ""))
        current = current_date.isoformat() if current_date else str(act.get("data", "")).strip()
        nome = str(act.get("nome", "")).strip()
        acao = str(act.get("acao", "")).strip().upper()
        if not current or not nome or not acao:
            continue
        mask = (schedule["data"].astype(str) == current) & (schedule["nome"].astype(str).str.strip().str.lower() == nome.lower())
        if acao == "FOLGAR":
            schedule = schedule.loc[~mask].copy()
        elif acao in {"ALTERAR_HORARIO", "ALTERAR_SETOR", "ALTERAR_PERIODO"}:
            if mask.any():
                if str(act.get("setor", "")).strip():
                    schedule.loc[mask, "setor"] = str(act.get("setor", "")).strip()
                if str(act.get("periodo", "")).strip():
                    schedule.loc[mask, "periodo"] = str(act.get("periodo", "")).strip()
                if str(act.get("horario", "")).strip():
                    schedule.loc[mask, "horario"] = str(act.get("horario", "")).strip()
                if str(act.get("observacao", "")).strip():
                    schedule.loc[mask, "observacao"] = str(act.get("observacao", "")).strip()
        elif acao == "ESCALAR":
            emp = colaboradores[colaboradores["nome"].astype(str).str.strip().str.lower() == nome.lower()]
            funcao = ""
            if not emp.empty:
                funcao = str(emp.iloc[0].get("funcao", "")).strip()
            new_row = {
                "data": current,
                "dia": DIAS_PT[pd.to_datetime(current).weekday()],
                "periodo": str(act.get("periodo", "")).strip() or "Tarde",
                "setor": str(act.get("setor", "")).strip() or (str(emp.iloc[0].get("setor_escala", "")).strip() if not emp.empty else ""),
                "funcao": funcao,
                "nome": nome,
                "horario": str(act.get("horario", "")).strip() or (str(emp.iloc[0].get("horario_padrao", "")).strip() if not emp.empty else ""),
                "origem": "Manual",
                "observacao": str(act.get("observacao", "")).strip(),
            }
            # Evita duplicar se já houver linha idêntica de ajuste manual.
            duplicate = (
                (schedule["data"].astype(str) == new_row["data"])
                & (schedule["nome"].astype(str).str.lower() == new_row["nome"].lower())
                & (schedule["periodo"].astype(str) == new_row["periodo"])
            )
            if not duplicate.any():
                schedule = pd.concat([schedule, pd.DataFrame([new_row])], ignore_index=True)
    return schedule


def covered_periods(row: pd.Series) -> list[str]:
    """
    Calcula presença operacional por período sem usar horário de saída.

    Decisão do protótipo:
    - Entrada de Manhã conta para Manhã e Tarde.
    - Entrada de Tarde conta para Tarde e Noite.
    - Entrada de Noite conta para Noite.
    - Extras sugeridos de Manhã contam só Manhã, pois normalmente são apoio pontual.
    """
    periodo = str(row.get("periodo", "")).strip()
    origem = str(row.get("origem", "")).strip()
    if origem == "Sugestão extra" and periodo == "Manhã":
        return ["Manhã"]
    if periodo == "Manhã":
        return ["Manhã", "Tarde"]
    if periodo == "Tarde":
        return ["Tarde", "Noite"]
    if periodo == "Noite":
        return ["Noite"]
    return [periodo] if periodo else []


def coverage_frame(schedule: pd.DataFrame) -> pd.DataFrame:
    if schedule.empty:
        return pd.DataFrame(columns=["dia", "periodo", "setor", "nome"])
    rows = []
    for _, row in schedule.iterrows():
        for per in covered_periods(row):
            rows.append({
                "data": row.get("data", ""),
                "dia": row.get("dia", ""),
                "periodo": per,
                "setor": row.get("setor", ""),
                "nome": row.get("nome", ""),
            })
    return pd.DataFrame(rows)


def coverage_summary(schedule: pd.DataFrame, ideal: pd.DataFrame) -> pd.DataFrame:
    if ideal.empty:
        return pd.DataFrame()
    ideal = ideal.copy()
    ideal["dia"] = ideal["dia"].map(normalize_day)
    coverage = coverage_frame(schedule)
    rows = []
    for _, ir in ideal.iterrows():
        dia = ir.get("dia", "")
        periodo = ir.get("periodo", "")
        for setor in SETORES:
            try:
                needed = int(float(str(ir.get(setor, 0)).replace(",", ".") or 0))
            except Exception:
                needed = 0
            if needed <= 0:
                continue
            if coverage.empty:
                actual = 0
            else:
                actual = int(((coverage["dia"] == dia) & (coverage["periodo"] == periodo) & (coverage["setor"] == setor)).sum())
            rows.append({"dia": dia, "periodo": periodo, "setor": setor, "ideal": needed, "escalado": actual, "faltam": max(needed - actual, 0), "sobra": max(actual - needed, 0)})
    return pd.DataFrame(rows)


def suggest_extras(
    schedule: pd.DataFrame,
    colaboradores: pd.DataFrame,
    ideal: pd.DataFrame,
    start: date,
    domingo_especial: bool = False,
) -> pd.DataFrame:
    """Adiciona sugestões de extras para cobrir faltas, respeitando setor e rodízio simples."""
    schedule = schedule.copy()
    extras = colaboradores[colaboradores["tipo"].astype(str).str.strip().str.lower() == "extra"].copy()
    if extras.empty:
        return schedule

    extra_count = {str(n).strip(): 0 for n in extras["nome"].astype(str)}
    # Conta extras já manuais/base se houver
    if not schedule.empty:
        for nome in extra_count:
            extra_count[nome] += int((schedule["nome"].astype(str).str.strip().str.lower() == nome.lower()).sum())

    summary = coverage_summary(schedule, ideal)
    additions = []
    for _, gap in summary[summary["faltam"] > 0].iterrows():
        dia = str(gap["dia"])
        periodo = str(gap["periodo"])
        setor = str(gap["setor"])
        current_dates = [d for d in date_range(start) if DIAS_PT[d.weekday()] == dia]
        if not current_dates:
            continue
        current = current_dates[0]
        if dia == "Domingo" and periodo == "Manhã" and not domingo_especial:
            continue
        needed = int(gap["faltam"])
        candidates = extras[extras["setor_escala"].astype(str).str.strip().str.lower() == setor.lower()].copy()
        # Extra só é sugerido automaticamente no período padrão dele.
        # Ex.: Lairton/Bruno/Denner/Anderson/Rafael Lisbinski entram no período Noite;
        # Daia - Extra e Hemerson - Extra entram no período Manhã.
        if "periodo_padrao" in candidates.columns:
            period_mask = candidates["periodo_padrao"].astype(str).str.strip().str.lower() == periodo.lower()
            candidates = candidates[period_mask].copy()
        if candidates.empty:
            continue
        # Evita colocar o mesmo extra duas vezes no mesmo dia.
        scheduled_names_today = set(schedule[schedule["data"] == current.isoformat()]["nome"].astype(str).str.strip().str.lower())
        for _ in range(needed):
            available = []
            for _, ex in candidates.iterrows():
                name = str(ex["nome"]).strip()
                if name.lower() in scheduled_names_today:
                    continue
                folga = normalize_day(ex.get("folga_fixa", ""))
                if folga and folga != "Não" and folga == dia:
                    continue
                available.append(ex)
            if not available:
                break
            available_df = pd.DataFrame(available)
            available_df["_count"] = available_df["nome"].astype(str).map(lambda n: extra_count.get(n.strip(), 0))
            chosen = available_df.sort_values(["_count", "nome"]).iloc[0]
            name = str(chosen["nome"]).strip()
            extra_count[name] = extra_count.get(name, 0) + 1
            scheduled_names_today.add(name.lower())
            additions.append({
                "data": current.isoformat(),
                "dia": dia,
                "periodo": periodo,
                "setor": setor,
                "funcao": str(chosen.get("funcao", "Extra")).strip(),
                "nome": name,
                "horario": str(chosen.get("horario_padrao", "")).strip(),
                "origem": "Sugestão extra",
                "observacao": "Sugerido automaticamente para fechar quadro ideal.",
            })
            schedule = pd.concat([schedule, pd.DataFrame([additions[-1]])], ignore_index=True)
    return schedule.sort_values(["data", "periodo", "setor", "horario", "nome"]).reset_index(drop=True)


def generate_schedule(
    colaboradores: pd.DataFrame,
    ideal: pd.DataFrame,
    eventos: pd.DataFrame,
    ajustes: pd.DataFrame,
    start: date,
    domingo_especial: bool = False,
    sugerir_extras: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    base = generate_base_schedule(colaboradores, eventos, ajustes, start, domingo_especial=domingo_especial)
    if sugerir_extras:
        base = suggest_extras(base, colaboradores, ideal, start, domingo_especial=domingo_especial)
    summary = coverage_summary(base, ideal)
    return base, summary


def whatsapp_text(schedule: pd.DataFrame, summary: pd.DataFrame | None = None) -> str:
    if schedule.empty:
        return "Nenhuma escala gerada."
    lines: list[str] = []
    for current, day_df in schedule.groupby("data", sort=True):
        dt = pd.to_datetime(current).date()
        dia = DIAS_PT[dt.weekday()].upper()
        lines.append(f"*{dia} — {dt.strftime('%d/%m/%Y')}*")
        for periodo in PERIODOS:
            per_df = day_df[day_df["periodo"] == periodo]
            if per_df.empty:
                continue
            lines.append(f"\n*{periodo.upper()}*")
            for setor, setor_df in per_df.groupby("setor", sort=False):
                for _, row in setor_df.sort_values(["horario", "nome"]).iterrows():
                    horario = str(row.get("horario", "")).strip()
                    nome = str(row.get("nome", "")).strip()
                    funcao = str(row.get("funcao", "")).strip()
                    origem = str(row.get("origem", "")).strip()
                    extra_tag = " (extra)" if origem == "Sugestão extra" else ""
                    funcao_txt = f" — {funcao}" if funcao and funcao.lower() not in {setor.lower(), "garçom"} else ""
                    lines.append(f"{setor}{funcao_txt} — {horario} — {nome}{extra_tag}")
        if summary is not None and not summary.empty:
            day_summary = summary[(summary["dia"].str.upper() == dia) & (summary["faltam"] > 0)]
            if not day_summary.empty:
                lines.append("\n*ALERTAS DE COBERTURA:*")
                for _, s in day_summary.iterrows():
                    lines.append(f"Faltam {int(s['faltam'])} em {s['setor']} / {s['periodo']}")
        lines.append("\n")
    return "\n".join(lines).strip()


def build_excel_sheets(schedule: pd.DataFrame, summary: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dias_semana = ["Sábado", "Domingo", "Segunda", "Terça", "Quarta", "Quinta", "Sexta"]

    if schedule.empty:
        por_colaborador = pd.DataFrame(columns=["Colaborador", *dias_semana])
        por_dia = pd.DataFrame(columns=["Dia", "Data", "Período", "Setor", "Horário", "Colaborador", "Função"])
    else:
        rows_colaborador = []
        for nome, emp_df in schedule.groupby("nome", sort=True):
            row = {"Colaborador": nome}
            for dia in dias_semana:
                dia_df = emp_df[emp_df["dia"] == dia].sort_values(["horario", "setor", "funcao"])
                if dia_df.empty:
                    row[dia] = "FOLGA"
                else:
                    partes = []
                    for _, item in dia_df.iterrows():
                        partes.append(
                            " | ".join(
                                str(item.get(col, "")).strip()
                                for col in ["horario", "setor", "funcao"]
                                if str(item.get(col, "")).strip()
                            )
                        )
                    row[dia] = "\n".join(partes)
            rows_colaborador.append(row)
        por_colaborador = pd.DataFrame(rows_colaborador, columns=["Colaborador", *dias_semana])

        por_dia = schedule.copy()
        por_dia["Data"] = por_dia["data"].map(lambda value: pd.to_datetime(value).strftime("%d/%m/%Y") if str(value).strip() else "")
        por_dia = por_dia.rename(
            columns={
                "dia": "Dia",
                "periodo": "Período",
                "setor": "Setor",
                "horario": "Horário",
                "nome": "Colaborador",
                "funcao": "Função",
            }
        )[["Dia", "Data", "Período", "Setor", "Horário", "Colaborador", "Função"]]
        por_dia = por_dia.sort_values(["Data", "Período", "Setor", "Horário", "Colaborador"])

    cobertura = summary.copy() if summary is not None else pd.DataFrame()
    if not cobertura.empty:
        cobertura["diferença"] = cobertura["escalado"].astype(int) - cobertura["ideal"].astype(int)
        cobertura["status"] = cobertura["diferença"].map(lambda diff: "OK" if diff == 0 else ("FALTA" if diff < 0 else "SOBRA"))
        cobertura = cobertura.rename(columns={"dia": "Dia", "periodo": "Período", "setor": "Setor", "ideal": "Ideal", "escalado": "Escalado", "diferença": "Diferença", "status": "Status"})
        cobertura = cobertura[["Dia", "Período", "Setor", "Ideal", "Escalado", "Diferença", "Status"]]
    else:
        cobertura = pd.DataFrame(columns=["Dia", "Período", "Setor", "Ideal", "Escalado", "Diferença", "Status"])

    return por_colaborador, por_dia, cobertura


def to_excel_bytes(schedule: pd.DataFrame, summary: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    por_colaborador, por_dia, cobertura = build_excel_sheets(schedule, summary)
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        por_colaborador.to_excel(writer, index=False, sheet_name="Escala por Colaborador")
        por_dia.to_excel(writer, index=False, sheet_name="Escala por Dia")
        cobertura.to_excel(writer, index=False, sheet_name="Cobertura")

        for sheet in writer.book.worksheets:
            sheet.freeze_panes = "A2"
            for column_cells in sheet.columns:
                max_len = max(len(str(cell.value or "")) for cell in column_cells)
                sheet.column_dimensions[column_cells[0].column_letter].width = min(max(max_len + 2, 14), 42)
                for cell in column_cells:
                    cell.alignment = cell.alignment.copy(wrap_text=True, vertical="top")
    return output.getvalue()
