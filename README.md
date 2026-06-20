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


# Padrões de Projeto Utilizados

Durante o desenvolvimento do sistema foram aplicados padrões de projeto com o objetivo de melhorar a organização, manutenção e confiabilidade da aplicação.

---

## Singleton

### Localização

Classe `PersistenceManager`

### Implementação

```python
class PersistenceManager:

    _instance: PersistenceManager | None = None
    _lock: Lock = Lock()

    def __new__(cls) -> PersistenceManager:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._inicializado = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> PersistenceManager:
        return cls()
```

### Objetivo

O padrão Singleton foi utilizado para garantir que exista apenas uma instância responsável pelo gerenciamento da persistência dos dados da aplicação.

### Benefícios

* Evita múltiplas conexões desnecessárias com o banco de dados.
* Centraliza o gerenciamento da persistência.
* Garante consistência durante operações de leitura e escrita.

---

## Template Method

### Localização

Classe abstrata `EstadoSerializer`

### Implementação

```python
class EstadoSerializer(ABC):

    def serializar(self, usuarios_db, contas_db, sessoes_db, historias_db) -> dict:
        senhas = self._coletar_senhas(contas_db)
        usuarios = self._serializar_usuarios(usuarios_db, senhas)
        historias = self._serializar_historias(historias_db)
        return self._montar_payload(contas_db, sessoes_db, usuarios, historias)
```

Métodos implementados pelas subclasses:

```python
@abstractmethod
def _serializar_usuarios(self, usuarios_db, senhas) -> dict: pass

@abstractmethod
def _serializar_historias(self, historias_db) -> dict: pass

@abstractmethod
def _restaurar_usuarios(self, state, contas_db, usuarios_db) -> dict: pass

@abstractmethod
def _restaurar_historias(self, state, usuarios_db, historias_db): pass
```

Subclasse responsável pela implementação concreta:

```python
class FirestoreSerializer(EstadoSerializer):
```

### Objetivo

O padrão Template Method foi utilizado para definir o fluxo geral de serialização e desserialização dos dados, permitindo que subclasses implementem detalhes específicos do processo.

### Benefícios

* Padroniza o processo de persistência.
* Facilita futuras extensões para outros bancos de dados.
* Evita duplicação de código.

---

## Proxy

### Localização

Classe `PersistenceManagerProxy`

### Implementação

```python
class PersistenceManagerProxy:

    def __init__(self):
        self._manager = PersistenceManager.get_instance()

    def carregar(self, usuarios_db, contas_db, sessoes_db, historias_db) -> bool:
        if not isinstance(usuarios_db, dict) or not isinstance(historias_db, dict):
            return False
        return self._manager.carregar(
            usuarios_db,
            contas_db,
            sessoes_db,
            historias_db
        )

    def salvar(self, usuarios_db, contas_db, sessoes_db, historias_db) -> bool:
        if not isinstance(usuarios_db, dict) or not isinstance(historias_db, dict):
            return False
        return self._manager.salvar(
            usuarios_db,
            contas_db,
            sessoes_db,
            historias_db
        )
```

### Objetivo

O padrão Proxy foi utilizado para atuar como intermediário entre a aplicação e o gerenciador de persistência, realizando validações antes de permitir o acesso às operações de leitura e gravação.

### Benefícios

* Adiciona uma camada de segurança.
* Impede operações com dados inválidos.
* Controla o acesso ao objeto principal sem modificar sua implementação.


## Relatório Final: Feedback dos Usuários

Para validar a aplicação, foram realizados testes com diferentes usuários, que utilizaram a plataforma e compartilharam suas impressões sobre a experiência de uso.

### Larissa

A participante avaliou a plataforma de forma positiva, destacando a organização da interface e a limpeza visual do sistema. Segundo seu relato, a disposição dos elementos contribui para uma navegação agradável e facilita a utilização da plataforma.

**Contato:** +55 82 9386-9784

### Luis

O participante avaliou positivamente a plataforma, destacando a facilidade para localizar obras e navegar pelo catálogo. Também ressaltou a eficiência do sistema de busca, especialmente a possibilidade de utilizar filtros para encontrar conteúdos específicos. De modo geral, considerou a aplicação bem desenvolvida e apresentou uma avaliação bastante favorável da experiência de uso.

**Contato:** +55 82 9147-5856

### Gustavo Avelino

O participante avaliou positivamente a plataforma, destacando a fluidez da navegação e o bom desempenho do sistema durante os testes. Segundo seu relato, a aplicação apresentou funcionamento adequado, sem problemas aparentes, transmitindo uma experiência de uso satisfatória.

**Contato:** +55 82 8188-8877

### Jaciara

A participante acessou a plataforma e confirmou o funcionamento correto das funcionalidades testadas. Durante a avaliação, relatou que o sistema estava operando normalmente e expressou satisfação com a experiência de uso, classificando a plataforma de forma bastante positiva. Ao final dos testes, atribuiu nota **10/10** ao projeto.

**Contato:** +55 82 9364-7583

### Ronaldy Lacerda

Relatou que a plataforma apresentou bom desempenho, sem travamentos durante a navegação. Também destacou positivamente o modo de leitura, que ajusta automaticamente a tonalidade da tela para uma coloração mais amarelada, proporcionando maior conforto visual ao usuário.

**Contato:** +55 82 9140-6271

### Anna Luiza

Avaliou a plataforma voltada para livros e demonstrou uma reação positiva ao conceito apresentado. Após navegar pelo sistema, afirmou que gostou da proposta e da experiência oferecida.

**Contato:** +55 82 9139-5362

### Gustavo Henrique

Testou a aplicação e classificou o resultado como muito bom, demonstrando surpresa ao descobrir que o sistema havia sido desenvolvido pelo próprio autor do projeto.

**Contato:** +55 82 9344-9589

### Gustavo Terto

Também utilizou a plataforma e considerou a ideia interessante, avaliando positivamente a proposta do sistema.

**Contato:** +55 82 8729-6103

### Gledsa

Acessou a aplicação, realizou testes nas funcionalidades disponíveis e relatou ter gostado da plataforma.

**Contato:** +55 82 9352-9365

### Raiane

Analisou as funcionalidades implementadas, como autenticação, perfil de usuário, avaliações, listas personalizadas, interação social, sistema de progresso e mecanismos de busca. Após a análise, parabenizou o desenvolvimento e informou que as funcionalidades apresentadas estavam funcionando corretamente.

**Contato:** +55 82 9410-6027

### Yasmim

A participante realizou um primeiro contato com a plataforma e compartilhou algumas observações iniciais sobre a experiência de uso.

Inicialmente, destacou que explorou a aplicação apenas por um curto período de tempo, ressaltando que ainda não conheceu todas as funcionalidades disponíveis.

Em relação à leitura das obras, observou que alguns capítulos apresentavam trechos que ocupavam apenas parte da página, continuando na página seguinte mesmo havendo espaço disponível. A participante considerou que essa questão pode estar relacionada à formatação realizada pelos próprios escritores, e não necessariamente ao layout da plataforma.

Também percebeu que o catálogo ainda possui uma quantidade reduzida de livros, mas avaliou positivamente a organização por categorias, destacando que esse recurso facilita a navegação e a busca por conteúdos de interesse.

Outro ponto elogiado foi a possibilidade de personalização da leitura, permitindo alterar cores, fontes e tamanho dos textos. Durante os testes, porém, relatou dificuldade para retornar à página em que estava lendo após realizar essas alterações, sendo direcionada ao início da obra. A própria participante destacou que essa impressão pode ter sido influenciada pela pouca familiaridade com a plataforma naquele momento.

Por fim, demonstrou satisfação com o sistema de acompanhamento de progresso da leitura, especialmente pela exibição da porcentagem concluída. Também considerou interessante a proposta de permitir que um mesmo usuário atue tanto como leitor quanto como escritor dentro da plataforma.

De modo geral, a participante apresentou uma avaliação positiva da aplicação, destacando principalmente as opções de personalização, a organização por categorias, o acompanhamento do progresso de leitura e a proposta colaborativa da plataforma.

**contato:** 55 82 9976-6322

### Considerações Gerais

De forma geral, os usuários demonstraram boa aceitação da plataforma, destacando principalmente a proposta do sistema, a organização das funcionalidades, a facilidade de navegação e o funcionamento adequado da aplicação durante os testes realizados. Os feedbacks recebidos indicam uma experiência de uso positiva e reforçam a qualidade das funcionalidades desenvolvidas.
