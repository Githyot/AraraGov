# Fontes que só respondem a IPs do Brasil

Os servidores do GitHub Actions ficam nos EUA. Alguns portais públicos não aceitam
conexões de fora do país: nas sondagens, as assembleias de PE, RS, ES e DF, o TCE-PR e
a Receita (dados abertos do CNPJ) esgotaram o tempo ou recusaram a conexão a partir do
GitHub. São dados públicos, que qualquer pessoa no Brasil acessa pelo navegador; o
problema é só a origem da conexão.

## Como o coletor lida com isso

O cliente HTTP (`araragov/http.py`) aceita uma **saída com IP brasileiro**, um proxy
HTTP ou SOCKS5 configurado em `ARARAGOV_PROXY_BR`:

1. Cada servidor é tentado primeiro pela conexão normal.
2. Se a conexão falha, esgota o tempo ou o servidor responde **403** ou **451**, o
   coletor repete o pedido pela saída brasileira e, dali em diante, usa essa saída para
   aquele servidor até o fim da execução.
3. Os servidores que já se sabe que bloqueiam (`HOSTS_SO_BRASIL` em `araragov/config.py`,
   mais os de `ARARAGOV_PROXY_HOSTS`) vão direto pela saída brasileira.
4. Sem `ARARAGOV_PROXY_BR`, nada muda.

### O que fica de fora, de propósito

- **Limite de pedidos (HTTP 429)**, como o da Caixa (SINAPI): o servidor está dizendo
  "devagar", não "você é de fora". Trocar de IP para continuar pedindo é burlar o
  limite e pode fazer o órgão bloquear o coletor de vez. Nesses casos o coletor espera
  e tenta de novo, ou a coleta é feita no computador do mantenedor
  (`araragov coleta-local`).
- **Páginas proibidas pelo robots.txt** (remuneração de assessores na Câmara, API da
  Alep, DOCIGP da Alerj): o bloqueio ali não é geográfico, é uma regra do site. O
  coletor não as acessa, com ou sem IP brasileiro.

## Configurar no GitHub (opção A: proxy brasileiro)

1. Contrate um proxy ou VPN com saída no Brasil que ofereça acesso por **HTTP ou
   SOCKS5 com usuário e senha** (muitos provedores de VPN e de proxy residencial
   oferecem; procure "proxy SOCKS5 Brasil"). Uma VPN só com aplicativo, sem proxy, não
   serve para o GitHub Actions.
2. No repositório: *Settings → Secrets and variables → Actions → New repository secret*.
   - Nome: `ARARAGOV_PROXY_BR`
   - Valor: `socks5h://usuario:senha@host:porta` (ou `http://usuario:senha@host:porta`)
3. Opcional: o secret `ARARAGOV_PROXY_HOSTS` com outros servidores que devem ir direto
   pelo Brasil, separados por vírgula.

O workflow de coleta repassa esses secrets aos coletores. A senha nunca aparece no log:
o log mostra só o host e a porta do proxy.

Para testar no seu computador:

```sh
ARARAGOV_PROXY_BR='socks5h://usuario:senha@host:porta' python -m araragov ...
```

## Opção B: rodar no seu computador como runner do GitHub

Um *self-hosted runner* (pasta `~/actions-runner`) roda os jobs no seu PC, com o seu IP
brasileiro, sem proxy. Cuidados:

- O PC precisa estar ligado no horário da coleta (segunda, 06:00 UTC).
- **Repositório público:** um pull request de terceiros pode alterar o workflow e rodar
  código no runner, ou seja, no seu computador. Se usar esta opção, deixe em
  *Settings → Actions → General* a aprovação obrigatória para workflows de quem não é
  colaborador, e use o runner só em jobs de `schedule` e `workflow_dispatch`, nunca em
  `pull_request`.

Por isso a opção A é a recomendada para a coleta semanal automática.
