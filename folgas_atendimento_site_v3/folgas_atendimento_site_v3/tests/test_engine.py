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


def test_auto_fill_uses_secondary_sector_before_alerting():
    import pandas as pd

    colaboradores = pd.DataFrame([
        {
            'nome': 'Pessoa Apoio',
            'tipo': 'Fixo',
            'setor_cadastro': 'Copa',
            'setor_escala': 'Copa',
            'funcao': 'Atendente',
            'setores_secundarios': 'Praça',
            'horario_padrao': '08:00',
            'periodo_padrao': 'Manhã',
            'folga_fixa': 'Não',
            'trabalha_domingo': 'Sim',
            'status': 'Ativo',
        }
    ])
    quadro = pd.DataFrame([{'dia': 'Sábado', 'periodo': 'Manhã', 'Praça': '1', 'Copa': '0', 'Caixa': '0', 'Escritório': '0', 'Entrega': '0'}])

    schedule, summary = generate_schedule(colaboradores, quadro, pd.DataFrame(), pd.DataFrame(), date(2026, 7, 4))

    auto_rows = schedule[schedule['origem'] == 'Auto - fixo outro setor']
    assert not auto_rows.empty
    assert auto_rows.iloc[0]['setor'] == 'Praça'
    assert int(summary['faltam'].sum()) == 0


def test_missing_alert_has_reason_after_all_options():
    import pandas as pd

    colaboradores = pd.DataFrame(columns=['nome', 'tipo', 'setor_cadastro', 'setor_escala', 'funcao', 'setores_secundarios', 'horario_padrao', 'periodo_padrao', 'folga_fixa', 'trabalha_domingo', 'status'])
    quadro = pd.DataFrame([{'dia': 'Sábado', 'periodo': 'Manhã', 'Praça': '1', 'Copa': '0', 'Caixa': '0', 'Escritório': '0', 'Entrega': '0'}])

    _schedule, summary = generate_schedule(colaboradores, quadro, pd.DataFrame(), pd.DataFrame(), date(2026, 7, 4))

    row = summary.iloc[0]
    assert row['dia'] == 'Sábado'
    assert row['periodo'] == 'Manhã'
    assert row['setor'] == 'Praça'
    assert row['ideal'] == 1
    assert row['escalado'] == 0
    assert row['faltam'] == 1
    assert row['motivo_falta']
