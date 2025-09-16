
-----

# Simulador de Rede P2P Estilo BitTorrent

Este projeto é uma simulação de uma rede de compartilhamento de arquivos peer-to-peer (P2P) inspirada no protocolo BitTorrent. A aplicação é desenvolvida em Python e demonstra os conceitos fundamentais de rastreadores (trackers), semeadores (seeders) e peers (pares) que colaboram para distribuir um arquivo de forma eficiente.

## Aplicação Proposta

O sistema simula a distribuição de um arquivo grande (por exemplo, uma imagem `.iso` de 500MB) entre múltiplos clientes (pares). Ele é composto por três componentes principais:

1.  **Rastreador (`rastreador.py`):** Um servidor central que não armazena o arquivo, mas coordena a comunicação entre os pares. Ele mantém um registro de quais pares estão na rede e quais pedaços do arquivo cada par possui.
2.  **Par (`par.py`):** O cliente da rede P2P. Cada par pode atuar como:
      * **Semeador (Seeder):** Um par que possui o arquivo completo (100%) e apenas o envia para outros.
      * **Leecher:** Um par que está baixando o arquivo. Ele baixa os pedaços que não tem e, ao mesmo tempo, envia os pedaços que já possui para outros leechers, otimizando a velocidade de download de toda a rede.
3.  **Criador de Arquivo (`criar_arquivo.py`):** Um script utilitário para gerar um arquivo grande de teste, que será usado pelo semeador inicial.

O objetivo é demonstrar como a colaboração entre os pares permite uma distribuição de arquivos mais rápida e escalável do que um modelo cliente-servidor tradicional, onde um único servidor atenderia a todas as solicitações.

## Arquitetura e Topologia

A aplicação utiliza uma **topologia de rede híbrida**:

1.  **Modelo Cliente-Servidor (Centralizado):** A comunicação entre os pares e o Rastreador segue este modelo. Os pares se registram no Rastreador e solicitam a lista de outros pares. Esta comunicação é feita usando o protocolo **XML-RPC**, que permite a chamada de procedimentos remotos de forma simples.

2.  **Modelo Peer-to-Peer (Distribuído):** A transferência real dos pedaços do arquivo ocorre diretamente entre os pares, sem intermediários. Esta comunicação é realizada através de **Sockets TCP**, garantindo uma transferência de dados confiável.

Essa combinação cria uma "nuvem" ou "enxame" (swarm) de pares que trocam dados entre si, sendo apenas coordenados pelo Rastreador.

### Fluxo de Operação:

1.  Um semeador inicial (que já tem o arquivo) se conecta ao Rastreador e informa que possui todos os pedaços.
2.  Novos pares (leechers) se conectam ao Rastreador para obter a lista de outros pares na rede.
3.  O leecher analisa quais pedaços estão disponíveis e em quais pares, e começa a solicitar os pedaços mais raros primeiro ("Rarest First") para garantir uma boa distribuição.
4.  À medida que um leecher baixa pedaços, ele informa periodicamente ao Rastreador seu novo progresso.
5.  Simultaneamente, o leecher também atende a solicitações de outros pares, enviando os pedaços que já possui.
6.  Quando um leecher conclui o download de todos os pedaços, ele se torna um semeador, continuando a compartilhar o arquivo com o restante da rede.

## Ferramentas Utilizadas

  * **Linguagem:** Python 3
  * **Bibliotecas Padrão:**
      * `xmlrpc` (`client` e `server`): Para a comunicação RPC entre os Pares e o Rastreador.
      * `socket`: Para a transferência de dados P2P direta via TCP.
      * `threading` e `concurrent.futures.ThreadPoolExecutor`: Para gerenciar múltiplas conexões e downloads/uploads simultâneos de forma eficiente, sem que uma tarefa bloqueie as outras.
      * `os` e `sys`: Para manipulação de arquivos e leitura de argumentos da linha de comando.

## Passos da Implementação (Tutorial)

Siga os passos abaixo para executar a simulação em sua máquina local.

### Passo 1: Preparar os Arquivos

Salve os três códigos-fonte fornecidos em uma mesma pasta com os seguintes nomes:

1.  `rastreador.py` (O servidor Rastreador)
2.  `par.py` (O cliente P2P)
3.  `criar_arquivo.py` (O utilitário para criar o arquivo de teste)

### Passo 2: Criar o Arquivo de Teste

Antes de iniciar a rede, precisamos do arquivo que será compartilhado. Execute o script `criar_arquivo.py` para gerar um arquivo de 500 MB.

Abra um terminal e execute:

```bash
python criar_arquivo.py
```

Isso criará um arquivo chamado `ubuntu-teste.iso` na pasta. Este arquivo será usado pelo primeiro semeador.

### Passo 3: Iniciar o Rastreador (Tracker)

O Rastreador deve ser o primeiro componente a ser executado. Ele ficará aguardando a conexão dos pares.

Em um **novo terminal**, execute:

```bash
python rastreador.py
```

Você verá uma interface de texto que mostrará o status do servidor e, futuramente, a lista de pares conectados.

### Passo 4: Iniciar o Semeador Inicial (Seeder)

Agora, vamos iniciar o primeiro par, que já possui o arquivo completo e atuará como a fonte inicial.

Abra um **terceiro terminal** e execute o comando abaixo. Os argumentos são: `host`, `porta` e `eh_semeador`.

```bash
python par.py localhost 9000 true
```

  * `localhost`: O endereço do par.
  * `9000`: A porta em que este par irá escutar por conexões de outros pares.
  * `true`: Indica que este par é um semeador inicial.

O semeador se registrará no Rastreador. Se você olhar o terminal do Rastreador, verá o par `localhost:9000` conectado com 100% do arquivo.

### Passo 5: Iniciar os Leechers (Clientes)

Finalmente, vamos iniciar vários clientes que começarão a baixar o arquivo. Cada um deve rodar em seu próprio terminal e usar uma porta diferente.

Abra um **novo terminal para cada leecher**:

  * **Leecher 1 (Terminal 4):**

    ```bash
    python par.py localhost 9001 false
    ```

  * **Leecher 2 (Terminal 5):**

    ```bash
    python par.py localhost 9002 false
    ```

  * **Leecher 3 (Terminal 6):**

    ```bash
    python par.py localhost 9003 false
    ```

  * ... e assim por diante.

## Resultados Obtidos

Ao seguir os passos acima, você observará o seguinte comportamento:

  * **No terminal do Rastreador:** A lista de pares ativos será exibida e atualizada em tempo real, mostrando o ID de cada par (`host:porta`) e uma barra de progresso visual que indica a porcentagem do arquivo que cada um possui.

    ```
    ╭─────────────────────────────────────────────────────────╮
    │                      🔗 RASTREADOR P2P                  │
    ├─────────────────────────────────────────────────────────┤
    │ ⏱️  Tempo ativo: 0:00:45                              │
    │ 👥 Pares conectados: 4                                  │
    ├─────────────────────────────────────────────────────────┤
    │                       PARES ATIVOS                      │
    ├─────────────────────────────────────────────────────────┤
    │  1. localhost:9000      [████████████████████] 500   │
    │  2. localhost:9001      [█████████░░░░░░░░░░] 250   │
    │  3. localhost:9002      [█████░░░░░░░░░░░░░░] 120   │
    │  4. localhost:9003      [██████░░░░░░░░░░░░░] 155   │
    ╰─────────────────────────────────────────────────────────╯
    ```

  * **Nos terminais dos Leechers:** Cada leecher exibirá seu progresso de download, mostrando quantos pedaços já baixou do total e a porcentagem correspondente. Ele também registrará de quais pares está baixando cada pedaço.

    ```
    Progresso localhost:9001: 250/500 (50.0%)
    Iniciando 15 downloads simultâneos
      Pedaço 10 de localhost:9000
      Pedaço 45 de localhost:9002
      Pedaço 123 de localhost:9003
      ...
    ```

  * **Conclusão do Download:** Quando um leecher terminar de baixar o arquivo, ele exibirá a mensagem `DOWNLOAD COMPLETO!` e automaticamente passará a atuar como um novo semeador, ajudando outros pares a completarem seus downloads.

  * **Arquivos Finais:** Ao final do processo, cada leecher terá criado uma cópia local do arquivo original (ex: `localhost_9001_ubuntu-teste.iso`). Você pode verificar a integridade comparando o tamanho desses arquivos com o `ubuntu-teste.iso` original.