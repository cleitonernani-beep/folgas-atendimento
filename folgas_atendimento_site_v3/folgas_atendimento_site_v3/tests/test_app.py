from streamlit.testing.v1 import AppTest


def test_app_opens_without_streamlit_exceptions():
    at = AppTest.from_file("app.py", default_timeout=15)
    at.run()
    assert not at.exception
    assert [tab.label for tab in at.tabs] == [
        "1. Colaboradores",
        "2. Quadro ideal",
        "3. Folgas / Férias / Ajustes",
        "4. Gerar escala",
        "5. Ajuda / Regras",
    ]
