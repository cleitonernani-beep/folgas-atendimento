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
