# Prompt para continuar este projeto no Codex

Você é um agente de programação. Continue o projeto `FOLGAS ATENDIMENTO`, um sistema em Python/Streamlit para gerar escalas de atendimento de restaurante.

## Objetivo

Transformar o protótipo em um sistema interno simples, com cadastro de colaboradores, folgas, férias, quadro ideal, extras e geração semanal de escala de sábado a sexta. A saída principal deve ser um texto/tabela diária para WhatsApp, além de exportação em Excel/CSV.

## Regras de negócio já definidas

- Semana operacional: sábado até sexta.
- Setores oficiais: Praça, Copa, Caixa, Escritório e Entrega.
- Períodos: Manhã, Tarde e Noite.
- Considerar somente horário de entrada; não calcular saída nem banco de horas.
- Domingo normal abre às 16h e não tem Manhã.
- Domingo especial abre às 11h e ativa Manhã.
- Domingo sempre tem Tarde e Noite.
- Quem entra às 16h no domingo cobre a noite toda.
- A gestão define manualmente quem entra às 16h, 18h ou outro horário no domingo.
- Folga fixa é padrão, mas pode ser alterada manualmente pela gestão.
- `DIA/DOM/SEM`: a pessoa trabalha só Manhã/Tarde, não trabalha Noite, folga domingo e tem mais uma folga na semana.
- Estagiários trabalham 5 horas por dia e têm domingo fixo de folga.
- Lohran tem exceção no sábado: entra 17h para ajudar a Copa.
- Ana Julya e Thiago têm regra de Escritório durante a semana, mas aparecem na operação de Copa/Praça conforme escala.
- Daia - Extra e Hemerson - Extra representam Daiana/Hemerson quando atuam como extras de Manhã.
- Extras devem ser distribuídos por rodízio equilibrado.
- A gestão pode ajustar manualmente qualquer escala antes de enviar.

## Arquivos principais

- `app.py`: interface Streamlit.
- `escala_engine.py`: lógica de geração, eventos, cobertura e output.
- `data/colaboradores.csv`: base inicial de colaboradores.
- `data/quadro_ideal.csv`: quadro ideal oficial.
- `data/eventos.csv`: férias, folgas e ausências.
- `data/ajustes_semanais.csv`: ajustes manuais da semana.

## Próximas melhorias sugeridas

1. Criar tela para salvar escala gerada como histórico mensal.
2. Criar tela específica para montar folgas de domingo por mês.
3. Criar controle de rodízio de domingo às 16h/18h.
4. Criar botão para gerar imagem diária da escala.
5. Migrar persistência de CSV para SQLite.
6. Criar autenticação simples por senha.
7. Melhorar visual do texto do WhatsApp para ficar idêntico ao modelo usado pela equipe.
8. Criar testes unitários para as regras `DOM/SEM`, `DIA/DOM/SEM`, férias, estagiários e extras.
