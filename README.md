# StoryFlow

Plataforma web de leitura e autoria com conta híbrida (todo usuário é leitor e autor ao mesmo tempo), telas separadas por função e autenticação por sessão.

## Funcionalidades

- Login/cadastro com conta híbrida (leitor + autor)
- Telas separadas: `inicio`, `historias`, `biblioteca`, `escrever`, `voce`
- Middleware de autenticação protegendo endpoints privados em `/api/me/*`
- Catálogo com busca/filtros, leitura de capítulos, progresso e comentários
- Publicação de histórias e capítulos pelo mesmo usuário logado
- Biblioteca Pessoal 
- Modo confortável de Leitura
- Modo Maratona de Leitura
- Sistema de avaliação por capítulos 
- Persistência online opcional em Firebase Firestore

## Stack

- Python 3
- Flask
- HTML/CSS/JavaScript vanilla
- Firebase Admin SDK (Firestore)

## Rodando localmente

```bash
python3 -m pip install -r requirements.txt
python3 main.py
```

Acesse `http://localhost:5219`.

## Conectando ao Firebase Firestore

Quando configurado, o estado completo da aplicação é salvo e carregado do Firestore automaticamente.

### 1) Criar projeto e Firestore

1. Crie um projeto no Firebase/Google Cloud.
2. Ative o Firestore no modo nativo.
3. Gere uma Service Account com permissão para Firestore.

### 2) Configurar credenciais

 Pode usar uma das opções:

- `FIREBASE_SERVICE_ACCOUNT_PATH`: caminho para o JSON da service account
- `FIREBASE_SERVICE_ACCOUNT_JSON`: conteúdo JSON da service account em string (bom para deploy)

Variáveis opcionais:

- `FIREBASE_PROJECT_ID`: id do projeto
- `FIREBASE_COLLECTION` (padrão: `storyflow`)
- `FIREBASE_DOCUMENT` (padrão: `app_state`)
- `STORYFLOW_DEMO_SEED` (padrão: `true`) para habilitar/desabilitar dados demo automáticos

Exemplo:

```bash
export FIREBASE_SERVICE_ACCOUNT_PATH="/caminho/sa.json"
export FIREBASE_PROJECT_ID="meu-projeto"
python3 main.py
```

## Verificando conexão

Consulte:

- `GET /api/status`

O campo `persistencia` mostra se o backend ativo está em `firestore` ou `memory`.


## Padrão Criacional - Singleton

O padrão Singleton foi utilizado para garantir que uma classe possua apenas uma única instância durante toda a execução da aplicação. Isso permite centralizar o gerenciamento de recursos compartilhados, evitando múltiplas inicializações desnecessárias e melhorando a organização do sistema. 

## Padrão Comportamental - Template Method
O padrão Template Method foi utilizado para definir a estrutura geral de um algoritmo em uma classe base, permitindo que etapas específicas sejam implementadas ou sobrescritas por subclasses. Dessa forma, promove-se o reaproveitamento de código, a padronização dos processos e a flexibilidade para adaptar comportamentos sem alterar a lógica principal do algoritmo.

## Padrão Estrutural - Proxy
O padrão Proxy foi utilizado para fornecer um objeto intermediário que controla o acesso a outro objeto. Essa abordagem permite adicionar funcionalidades como controle de acesso, validação, monitoramento ou otimização de recursos sem modificar diretamente a implementação do objeto original, contribuindo para uma arquitetura mais organizada e desacoplada