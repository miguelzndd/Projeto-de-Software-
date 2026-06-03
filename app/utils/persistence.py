
from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from datetime import datetime
from threading import Lock

from app.models.autor import Autor
from app.models.leitor import Leitor
from app.models.historia import Historia
from app.models.capitulo import Capitulo
from app.models.avaliacao import Avaliacao, TipoAvaliacao
from app.models.comentario import Comentario
from app.models.notificacao import Notificacao, TipoNotificacao
from app.models.biblioteca import CategoriaBiblioteca

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except Exception:
    firebase_admin = None
    credentials = None
    firestore = None

class EstadoSerializer(ABC):
    

    def serializar(self, usuarios_db, contas_db, sessoes_db, historias_db) -> dict:
        senhas = self._coletar_senhas(contas_db)
        usuarios = self._serializar_usuarios(usuarios_db, senhas)
        historias = self._serializar_historias(historias_db)
        return self._montar_payload(contas_db, sessoes_db, usuarios, historias)

    def desserializar(self, state, usuarios_db, contas_db, sessoes_db, historias_db):
        self._limpar_bancos(usuarios_db, contas_db, sessoes_db, historias_db)
        self._restaurar_contas(state, contas_db)
        self._restaurar_sessoes(state, contas_db, sessoes_db)
        metadados = self._restaurar_usuarios(state, contas_db, usuarios_db)
        self._restaurar_historias(state, usuarios_db, historias_db)
        self._restaurar_metadados(metadados, usuarios_db, historias_db)

    def _coletar_senhas(self, contas_db):
        senhas = {}
        for conta in contas_db.values():
            senha = conta.get('senha')
            if senha:
                senhas[conta.get('leitor_id')] = senha
                senhas[conta.get('autor_id')] = senha
        return senhas

    def _montar_payload(self, contas_db, sessoes_db, usuarios, historias):
        return {
            'schema_version': 1,
            'gerado_em': datetime.now().isoformat(),
            'contas': dict(contas_db),
            'sessoes': dict(sessoes_db),
            'usuarios': usuarios,
            'historias': historias,
        }

    def _limpar_bancos(self, usuarios_db, contas_db, sessoes_db, historias_db):
        usuarios_db.clear()
        contas_db.clear()
        sessoes_db.clear()
        historias_db.clear()

    def _restaurar_contas(self, state, contas_db):
        contas = state.get('contas', {})
        if isinstance(contas, dict):
            contas_db.update(contas)

    def _restaurar_sessoes(self, state, contas_db, sessoes_db):
        sessoes = state.get('sessoes', {})
        if isinstance(sessoes, dict):
            for token, conta_id in sessoes.items():
                if conta_id in contas_db:
                    sessoes_db[token] = conta_id

    @abstractmethod
    def _serializar_usuarios(self, usuarios_db, senhas) -> dict: pass

    @abstractmethod
    def _serializar_historias(self, historias_db) -> dict: pass

    @abstractmethod
    def _restaurar_usuarios(self, state, contas_db, usuarios_db) -> dict: pass

    @abstractmethod
    def _restaurar_historias(self, state, usuarios_db, historias_db): pass

    @abstractmethod
    def _restaurar_metadados(self, metadados, usuarios_db, historias_db): pass

class FirestoreSerializer(EstadoSerializer):

    def _serializar_usuarios(self, usuarios_db, senhas):
        resultado = {}
        for usuario_id, usuario in usuarios_db.items():
            dados = {
                'id': usuario_id,
                'tipo': usuario.__class__.__name__,
                'nome': usuario.nome,
                'email': usuario.email,
                'senha': senhas.get(usuario_id),
                'data_criacao': _iso(getattr(usuario, 'data_criacao', None)),
                'notificacoes': [
                    {
                        'id': n.id, 'titulo': n.titulo, 'mensagem': n.obter_mensagem(),
                        'tipo': n.tipo.value, 'lida': n.lida, 'data_criacao': _iso(n.data_criacao),
                    }
                    for n in usuario.obter_notificacoes()
                ],
            }
            if isinstance(usuario, Leitor):
                dados['progresso_leitura'] = dict(usuario.progresso_leitura)
                dados['sessoes_leitura'] = dict(usuario.sessoes_leitura)
                dados['biblioteca'] = {
                    cat.value: [h.id for h in usuario.biblioteca.obter_historias_por_categoria(cat)]
                    for cat in CategoriaBiblioteca
                }
            elif isinstance(usuario, Autor):
                dados['obras'] = [h.id for h in usuario.obter_obras()]
            resultado[usuario_id] = dados
        return resultado

    def _serializar_historias(self, historias_db):
        resultado = {}
        for historia_id, historia in historias_db.items():
            resultado[historia_id] = {
                'id': historia.id, 'titulo': historia.titulo, 'sinopse': historia.sinopse,
                'genero': historia.genero, 'capa': historia.capa, 'status': historia.status,
                'autor_id': historia.autor.id_usuario if historia.autor else None,
                'leitor_ids': [l.id_usuario for l in historia.leitores],
                'data_criacao': _iso(historia.data_criacao),
                'data_atualizacao': _iso(historia.data_atualizacao),
                'avaliacoes': [
                    {'id': av.id, 'usuario_id': av.usuario.id_usuario if av.usuario else None,
                     'nota': av.nota, 'tipo': av.tipo.value, 'conteudo_id': av.conteudo_id,
                     'data_criacao': _iso(av.data_criacao)}
                    for av in historia.avaliacoes
                ],
                'capitulos': [
                    {
                        'id': cap.id, 'titulo': cap.titulo, 'conteudo': cap.conteudo,
                        'ordem': cap.ordem, 'visualizacoes': cap.visualizacoes,
                        'data_criacao': _iso(cap.data_criacao), 'data_atualizacao': _iso(cap.data_atualizacao),
                        'destaques': dict(cap.destaques),
                        'avaliacoes': [
                            {'id': av.id, 'usuario_id': av.usuario.id_usuario if av.usuario else None,
                             'nota': av.nota, 'tipo': av.tipo.value, 'conteudo_id': av.conteudo_id,
                             'data_criacao': _iso(av.data_criacao)}
                            for av in cap.avaliacoes
                        ],
                        'comentarios': [
                            {'id': c.id, 'usuario_id': c.usuario.id_usuario if c.usuario else None,
                             'conteudo': c.obter_conteudo(), 'capitulo_id': c.capitulo_id,
                             'posicao_texto': c.posicao_texto, 'curtidas': c.curtidas,
                             'data_criacao': _iso(c.data_criacao)}
                            for c in cap.comentarios
                        ],
                    }
                    for cap in historia.capitulos
                ],
            }
        return resultado

    def _restaurar_usuarios(self, state, contas_db, usuarios_db):
        senha_por_usuario = {}
        for conta in contas_db.values():
            senha = conta.get('senha')
            if senha:
                senha_por_usuario[conta.get('leitor_id')] = senha
                senha_por_usuario[conta.get('autor_id')] = senha

        metadados = {}
        origem = state.get('usuarios', {})
        for usuario_id, dados in (origem.items() if isinstance(origem, dict) else []):
            if not isinstance(dados, dict):
                continue
            tipo = dados.get('tipo')
            senha = dados.get('senha') or senha_por_usuario.get(usuario_id) or '__restored__'
            if tipo == 'Leitor':
                usuario = Leitor(usuario_id, dados.get('nome', 'Usuário'), dados.get('email', ''), senha)
            elif tipo == 'Autor':
                usuario = Autor(usuario_id, dados.get('nome', 'Usuário'), dados.get('email', ''), senha)
            else:
                continue
            usuario.data_criacao = _parse_iso(dados.get('data_criacao'), usuario.data_criacao)
            usuarios_db[usuario_id] = usuario
            metadados[usuario_id] = dados
        return metadados

    def _restaurar_historias(self, state, usuarios_db, historias_db):
        origem = state.get('historias', {})
        historias_items = list(origem.items()) if isinstance(origem, dict) else []

        for historia_id, dados in historias_items:
            if not isinstance(dados, dict):
                continue
            historia = Historia(
                titulo=dados.get('titulo', 'Sem título'),
                sinopse=dados.get('sinopse', ''),
                genero=dados.get('genero', ''),
                capa=dados.get('capa'),
            )
            historia.id = historia_id
            historia.status = dados.get('status', 'em_escrita')
            historia.data_criacao = _parse_iso(dados.get('data_criacao'), historia.data_criacao)
            historia.data_atualizacao = _parse_iso(dados.get('data_atualizacao'), historia.data_atualizacao)
            historias_db[historia_id] = historia

        for historia_id, dados in historias_items:
            historia = historias_db.get(historia_id)
            if not historia or not isinstance(dados, dict):
                continue

            autor = usuarios_db.get(dados.get('autor_id'))
            if isinstance(autor, Autor):
                historia.vincular_autor(autor)
                if historia not in autor._obras:
                    autor._obras.append(historia)

            historia.leitores = [
                u for uid in dados.get('leitor_ids', [])
                for u in [usuarios_db.get(uid)] if isinstance(u, Leitor)
            ]

            capitulos = dados.get('capitulos', [])
            if isinstance(capitulos, list):
                for cap_data in sorted(capitulos, key=lambda c: c.get('ordem', 0) if isinstance(c, dict) else 0):
                    if not isinstance(cap_data, dict):
                        continue
                    capitulo = Capitulo(
                        titulo=cap_data.get('titulo', 'Capítulo'),
                        conteudo=cap_data.get('conteudo', ''),
                        ordem=cap_data.get('ordem', len(historia.capitulos) + 1),
                    )
                    capitulo.id = cap_data.get('id', capitulo.id)
                    capitulo.visualizacoes = int(cap_data.get('visualizacoes', 0))
                    capitulo.data_criacao = _parse_iso(cap_data.get('data_criacao'), capitulo.data_criacao)
                    capitulo.data_atualizacao = _parse_iso(cap_data.get('data_atualizacao'), capitulo.data_atualizacao)
                    destaques = cap_data.get('destaques', {})
                    if isinstance(destaques, dict):
                        capitulo.destaques.update(destaques)

                    for c_data in cap_data.get('comentarios', []):
                        if not isinstance(c_data, dict):
                            continue
                        usuario = usuarios_db.get(c_data.get('usuario_id'))
                        if not isinstance(usuario, Leitor):
                            continue
                        comentario = Comentario(
                            id=c_data.get('id', ''), usuario=usuario,
                            conteudo=c_data.get('conteudo', ''), capitulo_id=capitulo.id,
                            posicao_texto=c_data.get('posicao_texto'),
                        )
                        comentario.curtidas = int(c_data.get('curtidas', 0))
                        comentario.data_criacao = _parse_iso(c_data.get('data_criacao'), comentario.data_criacao)
                        capitulo.adicionar_comentario(comentario)
                        usuario._comentarios.append(comentario)

                    for av_data in cap_data.get('avaliacoes', []):
                        if not isinstance(av_data, dict):
                            continue
                        usuario = usuarios_db.get(av_data.get('usuario_id'))
                        if not isinstance(usuario, Leitor):
                            continue
                        try:
                            avaliacao = Avaliacao(
                                id=av_data.get('id', ''), usuario=usuario,
                                nota=int(av_data.get('nota', 1)),
                                tipo=_parse_tipo_avaliacao(av_data.get('tipo')),
                                conteudo_id=av_data.get('conteudo_id'),
                            )
                        except ValueError:
                            continue
                        avaliacao.data_criacao = _parse_iso(av_data.get('data_criacao'), avaliacao.data_criacao)
                        capitulo.adicionar_avaliacao(avaliacao)
                        usuario._avaliacoes.append(avaliacao)

                    historia.adicionar_capitulo(capitulo)

            for av_data in dados.get('avaliacoes', []):
                if not isinstance(av_data, dict):
                    continue
                usuario = usuarios_db.get(av_data.get('usuario_id'))
                if not isinstance(usuario, Leitor):
                    continue
                try:
                    avaliacao = Avaliacao(
                        id=av_data.get('id', ''), usuario=usuario,
                        nota=int(av_data.get('nota', 1)),
                        tipo=_parse_tipo_avaliacao(av_data.get('tipo')),
                        conteudo_id=av_data.get('conteudo_id'),
                    )
                except ValueError:
                    continue
                avaliacao.data_criacao = _parse_iso(av_data.get('data_criacao'), avaliacao.data_criacao)
                historia.adicionar_avaliacao(avaliacao)
                usuario._avaliacoes.append(avaliacao)

            historia.data_atualizacao = _parse_iso(dados.get('data_atualizacao'), historia.data_atualizacao)

    def _restaurar_metadados(self, metadados, usuarios_db, historias_db):
        for usuario_id, dados in metadados.items():
            usuario = usuarios_db.get(usuario_id)
            if not usuario or not isinstance(dados, dict):
                continue

            if isinstance(usuario, Leitor):
                progresso = dados.get('progresso_leitura', {})
                if isinstance(progresso, dict):
                    usuario.progresso_leitura = progresso
                sessoes = dados.get('sessoes_leitura', {})
                if isinstance(sessoes, dict):
                    usuario.sessoes_leitura = sessoes
                biblioteca = dados.get('biblioteca', {})
                if isinstance(biblioteca, dict):
                    for cat_nome, hist_ids in biblioteca.items():
                        categoria = _parse_categoria(cat_nome)
                        if not categoria or not isinstance(hist_ids, list):
                            continue
                        for historia_id in hist_ids:
                            historia = historias_db.get(historia_id)
                            if historia:
                                usuario.biblioteca.definir_categoria(historia, categoria)

            if isinstance(usuario, Autor):
                usuario.atualizar_metricas()

            notificacoes = dados.get('notificacoes', [])
            if isinstance(notificacoes, list):
                for notif_data in notificacoes:
                    if not isinstance(notif_data, dict):
                        continue
                    notificacao = Notificacao(
                        id=notif_data.get('id', ''), usuario=usuario,
                        mensagem=notif_data.get('mensagem', ''),
                        tipo=_parse_tipo_notificacao(notif_data.get('tipo')),
                        titulo=notif_data.get('titulo', ''),
                    )
                    notificacao.lida = bool(notif_data.get('lida', False))
                    notificacao.data_criacao = _parse_iso(notif_data.get('data_criacao'), notificacao.data_criacao)
                    usuario.adicionar_notificacao(notificacao)

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

    def __init__(self):
        if self._inicializado:
            return
        self._inicializado = True
        self._client = None
        self._firebase_inicializado = False
        self._write_lock = Lock()
        self._serializer = FirestoreSerializer()
        self._status = {
            'backend': 'memory',
            'ativo': False,
            'motivo': 'Firebase não inicializado',
            'project_id': None,
        }

    def status(self) -> dict:
        self._garantir_cliente()
        return dict(self._status)

    def carregar(self, usuarios_db, contas_db, sessoes_db, historias_db) -> bool:
        client = self._garantir_cliente()
        if client is None:
            return False
        try:
            snapshot = client.collection(_collection_name()).document(_document_name()).get()
            if not snapshot.exists:
                return False
            payload = snapshot.to_dict() or {}
            state = payload.get('state') if isinstance(payload.get('state'), dict) else payload
            if not isinstance(state, dict):
                return False
            self._serializer.desserializar(state, usuarios_db, contas_db, sessoes_db, historias_db)
            return True
        except Exception as exc:
            self._status.update({'backend': 'memory', 'ativo': False, 'motivo': f'Falha ao carregar estado: {exc}'})
            return False

    def salvar(self, usuarios_db, contas_db, sessoes_db, historias_db) -> bool:
        client = self._garantir_cliente()
        if client is None:
            return False
        state = self._serializer.serializar(usuarios_db, contas_db, sessoes_db, historias_db)
        try:
            with self._write_lock:
                client.collection(_collection_name()).document(_document_name()).set(
                    {'state': state, 'updated_at': datetime.now().isoformat()},
                    merge=True,
                )
            return True
        except Exception as exc:
            self._status.update({'backend': 'memory', 'ativo': False, 'motivo': f'Falha ao salvar estado: {exc}'})
            return False

    def _garantir_cliente(self):
        if self._firebase_inicializado:
            return self._client
        self._firebase_inicializado = True

        if firebase_admin is None or credentials is None or firestore is None:
            self._status = {'backend': 'memory', 'ativo': False, 'motivo': 'Dependência firebase-admin não instalada', 'project_id': None}
            return None

        cred_json = os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON', '').strip()
        cred_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH', '').strip() or os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '').strip()
        project_id = os.getenv('FIREBASE_PROJECT_ID', '').strip() or None

        try:
            if not firebase_admin._apps:
                cred = None
                if cred_json:
                    cred = credentials.Certificate(json.loads(cred_json))
                elif cred_path:
                    cred = credentials.Certificate(cred_path)
                options = {'projectId': project_id} if project_id else None
                if cred:
                    firebase_admin.initialize_app(cred, options=options)
                else:
                    firebase_admin.initialize_app(options=options)
            self._client = firestore.client()
            self._status = {'backend': 'firestore', 'ativo': True, 'motivo': 'Conectado', 'project_id': project_id}
        except Exception as exc:
            self._client = None
            self._status = {'backend': 'memory', 'ativo': False, 'motivo': f'Falha ao iniciar Firebase: {exc}', 'project_id': project_id}

        return self._client

class PersistenceManagerProxy:
    

    def __init__(self):
        self._manager = PersistenceManager.get_instance()

    def status(self) -> dict:
        return self._manager.status()

    def carregar(self, usuarios_db, contas_db, sessoes_db, historias_db) -> bool:
        if not isinstance(usuarios_db, dict) or not isinstance(historias_db, dict):
            return False
        return self._manager.carregar(usuarios_db, contas_db, sessoes_db, historias_db)

    def salvar(self, usuarios_db, contas_db, sessoes_db, historias_db) -> bool:
        if not isinstance(usuarios_db, dict) or not isinstance(historias_db, dict):
            return False
        return self._manager.salvar(usuarios_db, contas_db, sessoes_db, historias_db)

_proxy = PersistenceManagerProxy()

def obter_status_persistencia() -> dict:
    return _proxy.status()

def carregar_estado(usuarios_db, contas_db, sessoes_db, historias_db) -> bool:
    return _proxy.carregar(usuarios_db, contas_db, sessoes_db, historias_db)

def salvar_estado(usuarios_db, contas_db, sessoes_db, historias_db) -> bool:
    return _proxy.salvar(usuarios_db, contas_db, sessoes_db, historias_db)

def _collection_name() -> str:
    return os.getenv('FIREBASE_COLLECTION', 'storyflow')

def _document_name() -> str:
    return os.getenv('FIREBASE_DOCUMENT', 'app_state')

def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if isinstance(dt, datetime) else None

def _parse_iso(value, fallback=None) -> datetime:
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass
    return fallback or datetime.now()

def _parse_categoria(nome):
    if not isinstance(nome, str):
        return None
    mapa = {
        'favoritos': CategoriaBiblioteca.FAVORITOS,
        'lendo': CategoriaBiblioteca.LENDO,
        'concluidos': CategoriaBiblioteca.CONCLUIDOS,
        'concluídos': CategoriaBiblioteca.CONCLUIDOS,
        'pausados': CategoriaBiblioteca.PAUSADOS,
    }
    return mapa.get(nome.strip().casefold())

def _parse_tipo_avaliacao(valor):
    if valor == TipoAvaliacao.CAPITULO.value:
        return TipoAvaliacao.CAPITULO
    return TipoAvaliacao.HISTORIA

def _parse_tipo_notificacao(valor):
    try:
        return TipoNotificacao(valor)
    except Exception:
        return TipoNotificacao.RECOMENDACAO

def _serializar_state(usuarios_db, contas_db, sessoes_db, historias_db):
    return FirestoreSerializer().serializar(usuarios_db, contas_db, sessoes_db, historias_db)

def _desserializar_state(state, usuarios_db, contas_db, sessoes_db, historias_db):
    FirestoreSerializer().desserializar(state, usuarios_db, contas_db, sessoes_db, historias_db)
