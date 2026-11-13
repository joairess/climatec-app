# Climatec — agenda e atendimento

Aplicativo web para a **Climatec Climatização e Engenharia Ltda.**, de João Pessoa/PB. O cliente pede instalação, limpeza, manutenção ou contrato (PMOC) sem criar conta. A equipe confirma, remarca e acompanha o dia na área restrita.

Não há venda de equipamentos. Orçamento online, lembrete automático e pagamento ficam para uma fase seguinte. O cadastro do cliente já guarda o histórico por endereço, que é a base para lembrete de limpeza e PMOC.

## O que dá para fazer

- Pedir atendimento informando serviço, tipo de cliente (residência, empresa ou condomínio), contato, endereço, quantidade de aparelhos e um horário livre.
- Acompanhar o pedido por um código, sem mostrar telefone nem endereço. A página pública mostra só o primeiro nome, o serviço, a data e a situação.
- Na área da equipe: ver o dia e a semana, filtrar por situação, confirmar, remarcar, cancelar, marcar “a caminho” e “concluído”, e registrar um pedido que chegou por telefone ou WhatsApp.
- Reunir a mesma pessoa pelo telefone e ver, em cada endereço, os atendimentos passados e futuros.

Situações: Recebido, Confirmado, Remarcado, A caminho, Concluído e Cancelado.

A grade padrão é de segunda a sexta, 8h–18h, sábado 8h–12h, domingo fechado, faixas de 2 horas e **1 atendimento por horário**. Isso se muda em **Horários**, inclusive com dias de folga.

## Como rodar

Requisitos: Python 3.12.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Abra <http://127.0.0.1:8000/>.

| Acesso | Valor |
| --- | --- |
| Usuário da equipe | `atendimento` |
| Senha | `climatec-demo` |
| Exemplo de acompanhamento | <http://127.0.0.1:8000/acompanhar/CLM-DEMO01/> |

Os clientes, endereços e pedidos do `seed_demo` são fictícios. A senha acima é só para demonstração. Antes de publicar, crie outro usuário e não rode esse comando em produção (ele se recusa sozinho no Render).

Telefone da empresa: (83) 3221-0628. WhatsApp: (83) 98855-2060 (`https://wa.me/5583988552060`).

## Testes

```bash
pytest
```

A suíte cobre o cadastro pelo telefone, a regra de horários livres (capacidade, folga, sábado, horário que já passou) e as telas principais: pedido público, página de status, login e ações da agenda.

## Deploy no Render

O arquivo `render.yaml` descreve um web service **free** em Python:

- build: `pip install` e `collectstatic`
- start: `migrate` e gunicorn escutando em `0.0.0.0:$PORT`
- saúde: `GET /saude/` responde `{"status": "ok"}`
- `SECRET_KEY` gerada pelo Blueprint, sem segredo no repositório

No plano gratuito o disco é efêmero. O SQLite padrão serve para desenvolver, mas os dados somem quando o serviço dorme ou recebe um deploy novo. Para uso real, crie um Postgres no Render e coloque a connection string em `DATABASE_URL`. O projeto lê essa variável e usa SQLite quando ela está vazia.

Depois do primeiro deploy, abra o shell do serviço e crie o acesso da equipe:

```bash
python manage.py createsuperuser
```

Troque a senha de demonstração se alguém já tiver rodado o seed. O mesmo usuário entra em `/entrar/` e, se for equipe, também em `/admin/`.

## Privacidade

Nome, telefone e endereço são dados pessoais e só aparecem depois do login. A página do código não mostra esses dados. O formulário de pedido tem um aviso curto da LGPD, com o texto completo em `/privacidade/`.

## Estrutura

- `config/` — settings, URLs e WSGI
- `atendimento/` — modelos, grade de horários, telas e o comando `seed_demo`
- `templates/` — páginas em português
- `static/` — logo, CSS e Bootstrap 5
