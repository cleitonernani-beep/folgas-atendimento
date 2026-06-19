from datetime import date
from escala_engine import load_csv, generate_schedule


def test_generate_schedule_runs():
    colaboradores = load_csv('colaboradores.csv')
    quadro = load_csv('quadro_ideal.csv')
    eventos = load_csv('eventos.csv')
    ajustes = load_csv('ajustes_semanais.csv')
    schedule, summary = generate_schedule(colaboradores, quadro, eventos, ajustes, date(2026, 7, 4))
    assert not schedule.empty
    assert not summary.empty
    assert 'nome' in schedule.columns
    assert 'faltam' in summary.columns


def test_visual_excel_export_has_required_sheets():
    from io import BytesIO
    from openpyxl import load_workbook
    from escala_engine import to_excel_bytes

    colaboradores = load_csv('colaboradores.csv')
    quadro = load_csv('quadro_ideal.csv')
    eventos = load_csv('eventos.csv')
    ajustes = load_csv('ajustes_semanais.csv')
    start = date(2026, 7, 4)
    schedule, summary = generate_schedule(colaboradores, quadro, eventos, ajustes, start)

    payload = to_excel_bytes(schedule, summary, colaboradores=colaboradores, eventos=eventos, start=start)
    workbook = load_workbook(BytesIO(payload))

    assert workbook.sheetnames == ['Escala Semanal Visual', 'Escala por Colaborador', 'Escala por Dia', 'Cobertura']
    assert [cell.value for cell in workbook['Escala Semanal Visual'][1]] == ['Dia', 'Meio Dia / Manhã', 'Tarde', 'Noite', 'Folgas']
    assert workbook['Escala por Colaborador'].freeze_panes == 'A2'
    assert [cell.value for cell in workbook['Cobertura'][1]] == ['Dia', 'Período', 'Setor', 'Ideal', 'Escalado', 'Diferença', 'Status']
    assert workbook['Escala por Dia'].max_row > 1
