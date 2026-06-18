# FOLGAS ATENDIMENTO

Protótipo funcional em Python/Streamlit para gerar escala semanal de atendimento de sábado a sexta.


## Abrir no Windows do jeito mais fácil

1. Extraia o ZIP.
2. Abra a pasta `folgas_atendimento_site`.
3. Dê dois cliques em `ABRIR_SISTEMA_WINDOWS.bat`.

Não abra o `app.py` com dois cliques, porque ele abre uma janela preta e fecha. O app precisa ser iniciado pelo Streamlit.

## O que este sistema já faz

- Cadastro de colaboradores fixos, estagiários e extras.
- Cadastro de quadro ideal por dia, período e setor.
- Cadastro de férias, afastamentos, folgas e exceções.
- Cadastro de ajustes semanais manuais.
- Geração de escala semanal.
- Conferência de cobertura por Praça, Copa, Caixa, Escritório e Entrega.
- Sugestão de extras por rodízio simples.
- Texto pronto para WhatsApp.
- Exportação para CSV e Excel.

## Como rodar no computador

1. Extraia a pasta do projeto.
2. Abra o terminal dentro da pasta `folgas_atendimento_site`.
3. Instale as dependências:

```bash
pip install -r requirements.txt
```

4. Rode o site:

```bash
streamlit run app.py
```

5. O navegador abrirá o sistema.

## Como usar

### 1. Colaboradores
Edite colaboradores fixos, estagiários e extras.

Campos importantes:

- `tipo`: Fixo, Estagiário ou Extra.
- `setor_cadastro`: setor principal administrativo.
- `setor_escala`: setor em que a pessoa aparece no output da escala.
- `horario_padrao`: horário de entrada.
- `periodo_padrao`: Manhã, Tarde ou Noite.
- `folga_fixa`: dia de folga padrão.
- `trabalha_domingo`: Sim/Não.
- `pode_trabalhar_domingo_se_necessario`: permite exceção manual para quem tem folga fixa domingo.
- `pode_antecipar`: campo de controle; o sistema não antecipa sozinho.
- `pode_atuar_extra`: para casos como Daiana/Hemerson.

### 2. Quadro ideal
Define quantas pessoas são necessárias por dia, período e setor.

### 3. Eventos
Use para ausências e regras mensais.

Tipos aceitos:

- `FÉRIAS`
- `AFASTAMENTO`
- `FOLGA`
- `DOM`
- `DOM/SEM`
- `DIA/DOM/SEM`

### 4. Ajustes semanais
Use quando a gestão decidir manualmente.

Ações aceitas:

- `ESCALAR`
- `FOLGAR`
- `ALTERAR_HORARIO`
- `ALTERAR_SETOR`
- `ALTERAR_PERIODO`

Exemplo:

```csv
2026-07-05,THIAGO,ESCALAR,Copa,Tarde,16:00,"Escalar Tiago domingo às 16h"
```

## Decisões tomadas no protótipo

- A semana começa no sábado.
- O sistema considera somente horário de entrada.
- Não calcula horário de saída nem banco de horas.
- Domingo normal abre às 16h.
- Domingo especial abre às 11h.
- Estagiários não trabalham domingo.
- Folga fixa é padrão, mas pode ser alterada manualmente.
- Extras externos entram principalmente no período Noite.
- Daia - Extra e Hemerson - Extra aparecem separados quando atuam como extras.
- A cobertura considera:
  - entrada de Manhã cobre Manhã e Tarde;
  - entrada de Tarde cobre Tarde e Noite;
  - entrada de Noite cobre Noite;
  - extra sugerido de Manhã cobre apenas Manhã.

## Próximos ajustes recomendados

- Revisar manualmente quem entra às 16h ou 18h no domingo.
- Completar extras de Entrega, Caixa e Escritório se existirem.
- Trocar exemplos em `eventos.csv` e `ajustes_semanais.csv` pelos dados reais do mês.
- Evoluir o armazenamento de CSV para banco SQLite quando o uso estiver validado.
