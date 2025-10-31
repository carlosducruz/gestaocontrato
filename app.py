import logging
import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

import os

app = Flask(__name__)
logger.info("Aplicação iniciada")
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://appuser:apppass123@172.24.167.206:5432/appdb')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Handler global para erros não tratados
@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Erro não tratado: {e}", exc_info=True)
    return "Ocorreu um erro interno.", 500

# Configuração do upload de arquivos
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max
ALLOWED_DOCUMENT_EXTENSIONS = {'pdf', 'doc', 'docx'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov'}

# Criar pasta de uploads se não existir
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'documentos'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'videos'), exist_ok=True)

def allowed_document_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_DOCUMENT_EXTENSIONS

def allowed_video_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS

def save_uploaded_file(file, file_type):
    if file and file.filename:
        if file_type == 'documento' and allowed_document_file(file.filename):
            folder = 'documentos'
        elif file_type == 'video' and allowed_video_file(file.filename):
            folder = 'videos'
        else:
            return None
        
        # Gerar nome único para o arquivo
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = secure_filename(timestamp + file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], folder, filename)
        
        file.save(filepath)
        return filename
    
    return None

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Modelos -------------------------------------------------------------------------------------------------------
# Modelo Ferias
class Ferias(db.Model):
    __tablename__ = 'ferias'
    id = db.Column(db.Integer, primary_key=True)
    funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionarios.id'), nullable=False)
    data_inicio = db.Column(db.Date, nullable=False)
    data_fim = db.Column(db.Date, nullable=False)
    dias = db.Column(db.Integer, nullable=False)
    abono = db.Column(db.Boolean, default=False)
    observacao = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    funcionario = db.relationship('Funcionario', backref='ferias', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'funcionario_id': self.funcionario_id,
            'data_inicio': self.data_inicio.strftime('%d/%m/%Y'),
            'data_inicio_iso': self.data_inicio.strftime('%Y-%m-%d'),
            'data_fim': self.data_fim.strftime('%d/%m/%Y'),
            'data_fim_iso': self.data_fim.strftime('%Y-%m-%d'),
            'dias': self.dias,
            'abono': self.abono,
            'observacao': self.observacao
        }


class Sac(db.Model):
    __tablename__ = 'sac'
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    endereco_id = db.Column(db.Integer, db.ForeignKey('enderecos.id'), nullable=True)
    data_ocorrencia = db.Column(db.Date, nullable=False)
    hora_ocorrencia = db.Column(db.Time, nullable=False)
    tipo_contato = db.Column(db.String(50), nullable=False)  # Telefone, Email, Presencial, WhatsApp
    canal_entrada = db.Column(db.String(50), nullable=False)  # Site, Telefone, Email, App, Rede Social
    assunto = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    categoria = db.Column(db.String(100), nullable=False)  # Reclamação, Elogio, Sugestão, Dúvida, Solicitação
    prioridade = db.Column(db.String(20), nullable=False)  # Baixa, Média, Alta, Urgente
    status = db.Column(db.String(50), nullable=False, default='Aberto')  # Aberto, Em Andamento, Resolvido, Fechado
    responsavel = db.Column(db.String(200), nullable=True)
    solucao = db.Column(db.Text, nullable=True)
    data_resolucao = db.Column(db.Date, nullable=True)
    hora_resolucao = db.Column(db.Time, nullable=True)
    satisfacao = db.Column(db.String(20), nullable=True)  # Muito Insatisfeito, Insatisfeito, Neutro, Satisfeito, Muito Satisfeito
    feedback = db.Column(db.Text, nullable=True)
    arquivo_anexo = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    cliente = db.relationship('Cliente', backref='sac_ocorrencias')
    endereco = db.relationship('Endereco', backref='sac_ocorrencias')
    
    def to_dict(self):
        return {
            'id': self.id,
            'cliente_id': self.cliente_id,
            'cliente_nome': self.cliente.nome if self.cliente else 'N/A',
            'endereco_id': self.endereco_id,
            'endereco_descricao': f"{self.endereco.logradouro}, {self.endereco.numero} - {self.endereco.bairro}" if self.endereco else 'Não especificado',
            'data_ocorrencia': self.data_ocorrencia.strftime('%d/%m/%Y'),
            'data_ocorrencia_iso': self.data_ocorrencia.strftime('%Y-%m-%d'),
            'hora_ocorrencia': self.hora_ocorrencia.strftime('%H:%M'),
            'tipo_contato': self.tipo_contato,
            'canal_entrada': self.canal_entrada,
            'assunto': self.assunto,
            'descricao': self.descricao,
            'categoria': self.categoria,
            'prioridade': self.prioridade,
            'status': self.status,
            'responsavel': self.responsavel,
            'solucao': self.solucao,
            'data_resolucao': self.data_resolucao.strftime('%d/%m/%Y') if self.data_resolucao else None,
            'data_resolucao_iso': self.data_resolucao.strftime('%Y-%m-%d') if self.data_resolucao else None,
            'hora_resolucao': self.hora_resolucao.strftime('%H:%M') if self.hora_resolucao else None,
            'satisfacao': self.satisfacao,
            'feedback': self.feedback,
            'arquivo_anexo': self.arquivo_anexo,
            'created_at': self.created_at.strftime('%d/%m/%Y %H:%M'),
            'tempo_resolucao': self.calcular_tempo_resolucao(),
            'dias_aberto': self.calcular_dias_aberto()
        }
    
    def calcular_tempo_resolucao(self):
        if self.data_resolucao and self.status in ['Resolvido', 'Fechado']:
            inicio = datetime.combine(self.data_ocorrencia, self.hora_ocorrencia)
            fim = datetime.combine(self.data_resolucao, self.hora_resolucao) if self.hora_resolucao else datetime.combine(self.data_resolucao, datetime.min.time())
            diferenca = fim - inicio
            return f"{diferenca.days}d {diferenca.seconds//3600}h"
        return None
    
    def calcular_dias_aberto(self):
        if self.status in ['Aberto', 'Em Andamento']:
            inicio = datetime.combine(self.data_ocorrencia, self.hora_ocorrencia)
            fim = datetime.now()
            diferenca = fim - inicio
            return diferenca.days
        return 0
    

class Fornecedor(db.Model):
    __tablename__ = 'fornecedores'
    id = db.Column(db.Integer, primary_key=True)
    nome_empresa = db.Column(db.String(200), nullable=False)
    cnpj = db.Column(db.String(18), unique=True, nullable=False)
    pronta_resposta = db.Column(db.Boolean, default=False)
    valor_hora_homem = db.Column(db.Numeric(10, 2), nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
   
    def to_dict(self):
        # Calcular estatísticas do mês atual
        from datetime import datetime
        mes_atual = datetime.now().month
        ano_atual = datetime.now().year
        
        atendimentos_mes = AtendimentoProntaResposta.query.filter(
            AtendimentoProntaResposta.fornecedor_id == self.id,
            db.extract('month', AtendimentoProntaResposta.data_atendimento) == mes_atual,
            db.extract('year', AtendimentoProntaResposta.data_atendimento) == ano_atual
        ).all()
        
        quantidade_atendimentos_mes = len(atendimentos_mes)
        valor_total_mes = sum(float(a.valor_total) for a in atendimentos_mes)
        
        return {
            'id': self.id,
            'nome_empresa': self.nome_empresa,
            'cnpj': self.cnpj,
            'pronta_resposta': self.pronta_resposta,
            'valor_hora_homem': float(self.valor_hora_homem),
            'ativo': self.ativo,
            'quantidade_atendimentos_mes': quantidade_atendimentos_mes,
            'valor_total_mes': valor_total_mes
        }

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Funcionario(db.Model):
    __tablename__ = 'funcionarios'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    re = db.Column(db.String(50), unique=True, nullable=False)
    cargo = db.Column(db.String(100), nullable=False)
    data_admissao = db.Column(db.Date, nullable=False)
    data_demissao = db.Column(db.Date, nullable=True)
    motivo_demissao = db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True)
    salario_atual = db.Column(db.Numeric(10, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamento com evolução salarial
    evolucoes = db.relationship('EvolucaoSalarial', backref='funcionario', lazy=True, cascade='all, delete-orphan')
    faltas = db.relationship('Falta', backref='funcionario', lazy=True, cascade='all, delete-orphan')
    folgas_trabalhadas = db.relationship('FolgaTrabalhada', foreign_keys='FolgaTrabalhada.funcionario_id', backref='funcionario', lazy=True, cascade='all, delete-orphan')
    ocorrencias = db.relationship('OcorrenciaDisciplinar', backref='funcionario', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        tempo_empresa = self.calcular_tempo_empresa()
        return {
            'id': self.id,
            'nome': self.nome,
            're': self.re,
            'cargo': self.cargo,
            'data_admissao': self.data_admissao.strftime('%d/%m/%Y') if self.data_admissao else None,
            'data_demissao': self.data_demissao.strftime('%d/%m/%Y') if self.data_demissao else None,
            'motivo_demissao': self.motivo_demissao,
            'ativo': self.ativo,
            'salario_atual': float(self.salario_atual),
            'tempo_empresa': tempo_empresa
        }
    
    def calcular_tempo_empresa(self):
        data_fim = self.data_demissao if self.data_demissao else datetime.now().date()
        delta = data_fim - self.data_admissao
        anos = delta.days // 365
        meses = (delta.days % 365) // 30
        return f"{anos} anos e {meses} meses"

class EvolucaoSalarial(db.Model):
    __tablename__ = 'evolucao_salarial'
    id = db.Column(db.Integer, primary_key=True)
    funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionarios.id'), nullable=False)
    cargo_anterior = db.Column(db.String(100), nullable=False)
    salario_anterior = db.Column(db.Numeric(10, 2), nullable=False)
    cargo_novo = db.Column(db.String(100), nullable=False)
    salario_novo = db.Column(db.Numeric(10, 2), nullable=False)
    data_promocao = db.Column(db.Date, nullable=False)
    observacao = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'cargo_anterior': self.cargo_anterior,
            'salario_anterior': float(self.salario_anterior),
            'cargo_novo': self.cargo_novo,
            'salario_novo': float(self.salario_novo),
            'data_promocao': self.data_promocao.strftime('%d/%m/%Y'),
            'observacao': self.observacao
        }

class Falta(db.Model):
    __tablename__ = 'faltas'
    id = db.Column(db.Integer, primary_key=True)
    funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionarios.id'), nullable=False)
    data_falta = db.Column(db.Date, nullable=False)
    atestada = db.Column(db.Boolean, default=False)
    motivo = db.Column(db.Text, nullable=True)
    arquivo_atestado = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'funcionario_id': self.funcionario_id,
            'data_falta': self.data_falta.strftime('%d/%m/%Y'),
            'data_falta_iso': self.data_falta.strftime('%Y-%m-%d'),
            'atestada': self.atestada,
            'motivo': self.motivo,
            'arquivo_atestado': self.arquivo_atestado
        }

class FolgaTrabalhada(db.Model):
    __tablename__ = 'folgas_trabalhadas'
    id = db.Column(db.Integer, primary_key=True)
    funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionarios.id'), nullable=False)
    data_folga = db.Column(db.Date, nullable=False)
    motivo = db.Column(db.String(100), nullable=False)  # 'Reforço por demanda' ou 'Substituição por falta'
    valor_diaria = db.Column(db.Numeric(10, 2), nullable=False)
    funcionario_substituido_id = db.Column(db.Integer, db.ForeignKey('funcionarios.id'), nullable=True)
    observacao = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamento com o funcionário substituído
    funcionario_substituido = db.relationship('Funcionario', foreign_keys=[funcionario_substituido_id])
    
    def to_dict(self):
        return {
            'id': self.id,
            'funcionario_id': self.funcionario_id,
            'data_folga': self.data_folga.strftime('%d/%m/%Y'),
            'data_folga_iso': self.data_folga.strftime('%Y-%m-%d'),
            'motivo': self.motivo,
            'valor_diaria': float(self.valor_diaria),
            'funcionario_substituido_id': self.funcionario_substituido_id,
            'funcionario_substituido_nome': self.funcionario_substituido.nome if self.funcionario_substituido else None,
            'observacao': self.observacao
        }

class OcorrenciaDisciplinar(db.Model):
    __tablename__ = 'ocorrencias_disciplinares'
    id = db.Column(db.Integer, primary_key=True)
    funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionarios.id'), nullable=False)
    data_ocorrencia = db.Column(db.Date, nullable=False)
    tipo = db.Column(db.String(50), nullable=False)  # Advertência, Suspensão 1/3/5 dias
    motivo = db.Column(db.String(100), nullable=False)  # Faltas, Procedimento, Desinteligência, Outros
    motivo_detalhado = db.Column(db.Text, nullable=True)  # Para quando motivo = Outros
    descricao = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'funcionario_id': self.funcionario_id,
            'data_ocorrencia': self.data_ocorrencia.strftime('%d/%m/%Y'),
            'data_ocorrencia_iso': self.data_ocorrencia.strftime('%Y-%m-%d'),
            'tipo': self.tipo,
            'motivo': self.motivo,
            'motivo_detalhado': self.motivo_detalhado,
            'descricao': self.descricao
        }

class Cliente(db.Model):
    __tablename__ = 'clientes'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    cnpj = db.Column(db.String(18), unique=True, nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    data_ativacao = db.Column(db.Date, nullable=True)
    data_inativacao = db.Column(db.Date, nullable=True)
    nr_atendimentos = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamento com endereços
    enderecos = db.relationship('Endereco', backref='cliente', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'cnpj': self.cnpj,
            'ativo': self.ativo,
            'data_ativacao': self.data_ativacao.strftime('%d/%m/%Y') if self.data_ativacao else None,
            'data_inativacao': self.data_inativacao.strftime('%d/%m/%Y') if self.data_inativacao else None,
            'nr_atendimentos': self.nr_atendimentos,
            'total_enderecos': len(self.enderecos),
            'enderecos_ativos': sum(1 for e in self.enderecos if e.ativo)
        }


class Regiao(db.Model):
    __tablename__ = 'regioes'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True, nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamento com endereços
    enderecos = db.relationship('Endereco', backref='regiao', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'ativo': self.ativo,
            'total_enderecos': len(self.enderecos),
            'enderecos_ativos': sum(1 for e in self.enderecos if e.ativo)
        }


class Endereco(db.Model):
    __tablename__ = 'enderecos'
    id = db.Column(db.Integer, primary_key=True)
    regiao_id = db.Column(db.Integer, db.ForeignKey('regioes.id'), nullable=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    nr_contrato = db.Column(db.String(50), nullable=False)
    data_ativacao_contrato = db.Column(db.Date, nullable=False)
    data_validade_contrato = db.Column(db.Date, nullable=False)
    
    # Endereço
    logradouro = db.Column(db.String(200), nullable=False)
    numero = db.Column(db.String(20), nullable=False)
    bairro = db.Column(db.String(100), nullable=False)
    cep = db.Column(db.String(10), nullable=False)
    cidade = db.Column(db.String(100), nullable=False)
    estado = db.Column(db.String(2), nullable=False)
    
    # Tipo de endereço
    tipo_endereco = db.Column(db.String(20), default='Condomínio')  # Unidade ou Condomínio
    
    # Campos específicos para Condomínio
    portaria_remota = db.Column(db.Boolean, default=False)
    monitoramento = db.Column(db.Boolean, default=False)
    nr_apartamentos = db.Column(db.Integer, nullable=True)
    
    # Internet
    tipo_internet = db.Column(db.String(20), default='Nenhuma')
    fornecedor_internet = db.Column(db.String(100), nullable=True)
    
    # Equipamentos
    tipo_nobreak = db.Column(db.String(50), nullable=False)
    tipo_gravacao = db.Column(db.String(20), nullable=False)
    tipo_manutencao = db.Column(db.String(20), nullable=False)
    
    # Contrato
    valor_contrato = db.Column(db.Numeric(10, 2), nullable=False)
    percentual_reajuste = db.Column(db.Numeric(5, 2), nullable=False)
    periodo_atendimento = db.Column(db.String(50), nullable=False)
    periodo_atendimento_personalizado = db.Column(db.String(100), nullable=True)
    locacao_sistema = db.Column(db.Boolean, default=False)
    
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamento com atendimentos
    atendimentos = db.relationship('Atendimento', backref='endereco', lazy=True, cascade='all, delete-orphan')
    
    # Rondas Virtuais
    possui_rondas_virtuais = db.Column(db.Boolean, default=False)
    qtd_cameras_rondas = db.Column(db.Integer, nullable=True)
    frequencia_rondas = db.Column(db.String(20), nullable=True)  # '1hora', '2horas', '3horas'
    periodo_recebimento_rondas = db.Column(db.String(20), nullable=True)  # 'diario', 'semanal', 'quinzenal', 'mensal'

    def to_dict(self):
        return {
            'id': self.id,
            'regiao_id': self.regiao_id,
            'cliente_id': self.cliente_id,
            'nr_contrato': self.nr_contrato,
            'data_ativacao_contrato': self.data_ativacao_contrato.strftime('%d/%m/%Y'),
            'data_validade_contrato': self.data_validade_contrato.strftime('%d/%m/%Y'),
            'logradouro': self.logradouro,
            'numero': self.numero,
            'bairro': self.bairro,
            'cep': self.cep,
            'cidade': self.cidade,
            'estado': self.estado,
            'tipo_endereco': self.tipo_endereco,
            'portaria_remota': self.portaria_remota,
            'monitoramento': self.monitoramento,
            'nr_apartamentos': self.nr_apartamentos,
            'tipo_internet': self.tipo_internet,
            'fornecedor_internet': self.fornecedor_internet,
            'tipo_nobreak': self.tipo_nobreak,
            'tipo_gravacao': self.tipo_gravacao,
            'tipo_manutencao': self.tipo_manutencao,
            'valor_contrato': float(self.valor_contrato),
            'percentual_reajuste': float(self.percentual_reajuste),
            'periodo_atendimento': self.periodo_atendimento,
            'periodo_atendimento_personalizado': self.periodo_atendimento_personalizado,
            'locacao_sistema': self.locacao_sistema,
            'ativo': self.ativo,
            'endereco_completo': f"{self.logradouro}, {self.numero} - {self.bairro}, {self.cidade}/{self.estado}",
            'possui_rondas_virtuais': self.possui_rondas_virtuais,
            'qtd_cameras_rondas': self.qtd_cameras_rondas,
            'frequencia_rondas': self.frequencia_rondas,
            'periodo_recebimento_rondas': self.periodo_recebimento_rondas
        }

class Atendimento(db.Model):
    __tablename__ = 'atendimentos'
    id = db.Column(db.Integer, primary_key=True)
    endereco_id = db.Column(db.Integer, db.ForeignKey('enderecos.id'), nullable=False)
    funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionarios.id'), nullable=False)
    data_atendimento = db.Column(db.Date, nullable=False)
    hora_chegada = db.Column(db.Time, nullable=False)
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fim = db.Column(db.Time, nullable=False)
    tempo_deslocamento = db.Column(db.Integer, nullable=False)  # em minutos
    historico = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamento com funcionário
    funcionario = db.relationship('Funcionario', foreign_keys=[funcionario_id])
    
    def calcular_tempo_atendimento(self):
        # Calcula tempo em minutos
        inicio = datetime.combine(datetime.today(), self.hora_inicio)
        fim = datetime.combine(datetime.today(), self.hora_fim)
        delta = fim - inicio
        return int(delta.total_seconds() / 60)
    
    def to_dict(self):
        return {
            'id': self.id,
            'endereco_id': self.endereco_id,
            'funcionario_id': self.funcionario_id,
            'funcionario_nome': self.funcionario.nome if self.funcionario else None,
            'data_atendimento': self.data_atendimento.strftime('%d/%m/%Y'),
            'data_atendimento_iso': self.data_atendimento.strftime('%Y-%m-%d'),
            'hora_chegada': self.hora_chegada.strftime('%H:%M'),
            'hora_inicio': self.hora_inicio.strftime('%H:%M'),
            'hora_fim': self.hora_fim.strftime('%H:%M'),
            'tempo_deslocamento': self.tempo_deslocamento,
            'tempo_atendimento': self.calcular_tempo_atendimento(),
            'historico': self.historico,
            'mes_ano': self.data_atendimento.strftime('%m/%Y')
        }



class AtendimentoProntaResposta(db.Model):
    __tablename__ = 'atendimentos_pronta_resposta'
    id = db.Column(db.Integer, primary_key=True)
    fornecedor_id = db.Column(db.Integer, db.ForeignKey('fornecedores.id'), nullable=False)
    data_atendimento = db.Column(db.Date, nullable=False)
    hora_atendimento = db.Column(db.Time, nullable=False)
    historico = db.Column(db.Text, nullable=False)
    nome_representante = db.Column(db.String(200), nullable=False)
    quantidade_horas = db.Column(db.Numeric(5, 2), nullable=False)  # Quantidade de horas trabalhadas
    valor_hora = db.Column(db.Numeric(10, 2), nullable=False)  # Valor da hora no momento do atendimento
    valor_total = db.Column(db.Numeric(10, 2), nullable=False)  # quantidade_horas * valor_hora
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamento com fornecedor
    fornecedor = db.relationship('Fornecedor', backref='atendimentos_pronta_resposta')
    
    def to_dict(self):
        return {
            'id': self.id,
            'fornecedor_id': self.fornecedor_id,
            'fornecedor_nome': self.fornecedor.nome_empresa if self.fornecedor else None,
            'data_atendimento': self.data_atendimento.strftime('%d/%m/%Y'),
            'data_atendimento_iso': self.data_atendimento.strftime('%Y-%m-%d'),
            'hora_atendimento': self.hora_atendimento.strftime('%H:%M'),
            'historico': self.historico,
            'nome_representante': self.nome_representante,
            'quantidade_horas': float(self.quantidade_horas),
            'valor_hora': float(self.valor_hora),
            'valor_total': float(self.valor_total),
            'mes_ano': self.data_atendimento.strftime('%m/%Y')
        }


class OcorrenciaSistemica(db.Model):
    __tablename__ = 'ocorrencias_sistemicas'
    id = db.Column(db.Integer, primary_key=True)
    endereco_id = db.Column(db.Integer, db.ForeignKey('enderecos.id'), nullable=False)
    data_ocorrencia = db.Column(db.Date, nullable=False)
    hora_ocorrencia = db.Column(db.Time, nullable=False)
    observacao = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Reportada')  # Reportada, Em Análise, Em Correção, Resolvida, Fechada
    prioridade = db.Column(db.String(20), nullable=False, default='Média')  # Baixa, Média, Alta, Crítica
    responsavel = db.Column(db.String(200), nullable=True)
    solucao = db.Column(db.Text, nullable=True)
    data_resolucao = db.Column(db.Date, nullable=True)
    hora_resolucao = db.Column(db.Time, nullable=True)
    arquivo_documento = db.Column(db.String(255), nullable=True)
    arquivo_video = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamento com endereço
    endereco = db.relationship('Endereco', backref='ocorrencias_sistemicas')
    
    def to_dict(self):
        return {
            'id': self.id,
            'cliente_id': self.endereco.cliente_id if self.endereco else None,
            'endereco_id': self.endereco_id,
            'endereco_descricao': f"{self.endereco.cliente.nome} - {self.endereco.logradouro}, {self.endereco.numero}" if self.endereco else 'N/A',
            'cliente_nome': self.endereco.cliente.nome if self.endereco and self.endereco.cliente else 'N/A',
            'data_ocorrencia': self.data_ocorrencia.strftime('%d/%m/%Y'),
            'data_ocorrencia_iso': self.data_ocorrencia.strftime('%Y-%m-%d'),
            'hora_ocorrencia': self.hora_ocorrencia.strftime('%H:%M'),
            'observacao': self.observacao,
            'status': self.status,
            'prioridade': self.prioridade,
            'responsavel': self.responsavel,
            'solucao': self.solucao,
            'data_resolucao': self.data_resolucao.strftime('%d/%m/%Y') if self.data_resolucao else None,
            'data_resolucao_iso': self.data_resolucao.strftime('%Y-%m-%d') if self.data_resolucao else None,
            'hora_resolucao': self.hora_resolucao.strftime('%H:%M') if self.hora_resolucao else None,
            'arquivo_documento': self.arquivo_documento,
            'arquivo_video': self.arquivo_video,
            'created_at': self.created_at.strftime('%d/%m/%Y %H:%M'),
            'tempo_resolucao': self.calcular_tempo_resolucao(),
            'dias_aberto': self.calcular_dias_aberto()
        }
    
    def calcular_tempo_resolucao(self):
        if self.data_resolucao and self.status in ['Resolvida', 'Fechada']:
            inicio = datetime.combine(self.data_ocorrencia, self.hora_ocorrencia)
            fim = datetime.combine(self.data_resolucao, self.hora_resolucao) if self.hora_resolucao else datetime.combine(self.data_resolucao, datetime.min.time())
            diferenca = fim - inicio
            return f"{diferenca.days}d {diferenca.seconds//3600}h"
        return None
    
    def calcular_dias_aberto(self):
        if self.status in ['Reportada', 'Em Análise', 'Em Correção']:
            inicio = datetime.combine(self.data_ocorrencia, self.hora_ocorrencia)
            fim = datetime.now()
            diferenca = fim - inicio
            return diferenca.days
        return 0
    

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Routes das Páginas --------------------------------------------------------------------------------------------
@app.route('/sac')
@login_required
def sac():
    return render_template('sac.html', user=current_user)

@app.route('/sac/novo')
@login_required
def sac_novo():
    return render_template('sac_form.html', user=current_user, ocorrencia=None)

@app.route('/sac/<int:id>/editar')
@login_required
def sac_editar(id):
    ocorrencia = Sac.query.get_or_404(id)
    return render_template('sac_form.html', user=current_user, ocorrencia=ocorrencia)

@app.route('/sac/<int:id>/detalhes')
@login_required
def sac_detalhes(id):
    ocorrencia = Sac.query.get_or_404(id)
    return render_template('sac_detalhes.html', user=current_user, ocorrencia=ocorrencia)

@app.route('/fornecedores')
@login_required
def fornecedores():
    return render_template('fornecedores.html', user=current_user)

@app.route('/fornecedores/novo')
@login_required
def fornecedores_novo():
    return render_template('fornecedores_form.html', user=current_user, fornecedor=None)

@app.route('/fornecedores/<int:id>/editar')
@login_required
def fornecedores_editar(id):
    fornecedor = Fornecedor.query.get_or_404(id)
    return render_template('fornecedores_form.html', user=current_user, fornecedor=fornecedor)
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    return redirect(url_for('login'))


@app.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/register')
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    return render_template('register.html')

@app.route('/home')
@login_required
def home():
    from datetime import datetime
    now = datetime.now()
    # Resumo de atendimentos por cliente no mês corrente
    atendimentos = Atendimento.query.filter(
        db.extract('month', Atendimento.data_atendimento) == now.month,
        db.extract('year', Atendimento.data_atendimento) == now.year
    ).all()
    resumo_clientes = []
    from collections import defaultdict
    clientes_stats = defaultdict(lambda: {'nome': '', 'qtd': 0, 'total_tempo': 0, 'tempos': []})
    for a in atendimentos:
        cliente_nome = a.endereco.cliente.nome if a.endereco and a.endereco.cliente else 'N/A'
        tempo = a.calcular_tempo_atendimento() if hasattr(a, 'calcular_tempo_atendimento') else 0
        cid = a.endereco.cliente_id if a.endereco and a.endereco.cliente else None
        if cid is not None:
            clientes_stats[cid]['nome'] = cliente_nome
            clientes_stats[cid]['qtd'] += 1
            clientes_stats[cid]['total_tempo'] += tempo
            clientes_stats[cid]['tempos'].append(tempo)
    for cid, stats in clientes_stats.items():
        media_tempo = round(stats['total_tempo'] / stats['qtd'], 1) if stats['qtd'] else 0
        maior_tempo = max(stats['tempos']) if stats['tempos'] else 0
        resumo_clientes.append({
            'nome': stats['nome'],
            'qtd': stats['qtd'],
            'total_tempo': stats['total_tempo'],
            'media_tempo': media_tempo,
            'maior_tempo': maior_tempo
        })
    # Contar usuários ativos
    usuarios_ativos = User.query.count()
    clientes_ativos = Cliente.query.filter_by(ativo=True).count()
    from datetime import datetime
    now = datetime.now()
    atendimentos_mes = Atendimento.query.filter(
        db.extract('month', Atendimento.data_atendimento) == now.month,
        db.extract('year', Atendimento.data_atendimento) == now.year
    ).count()

    ocorrencias_sistemicas_mes = OcorrenciaSistemica.query.filter(
        db.extract('month', OcorrenciaSistemica.data_ocorrencia) == now.month,
        db.extract('year', OcorrenciaSistemica.data_ocorrencia) == now.year
    ).count()

    atendimentos_pr_mes = AtendimentoProntaResposta.query.filter(
        db.extract('month', AtendimentoProntaResposta.data_atendimento) == now.month,
        db.extract('year', AtendimentoProntaResposta.data_atendimento) == now.year
    ).count()
    return render_template(
        'home.html',
        user=current_user,
        usuarios_ativos=usuarios_ativos,
        clientes_ativos=clientes_ativos,
        atendimentos_mes=atendimentos_mes,
        ocorrencias_sistemicas_mes=ocorrencias_sistemicas_mes,
        atendimentos_pr_mes=atendimentos_pr_mes,
        now=now,
        resumo_clientes=resumo_clientes
    )

@app.route('/ocorrencias-sistemicas')
@login_required
def ocorrencias_sistemicas():
    return render_template('ocorrencias_sistemicas.html', user=current_user)

@app.route('/ocorrencias-sistemicas/novo')
@login_required
def ocorrencias_sistemicas_novo():
    return render_template('ocorrencias_sistemicas_form.html', user=current_user, ocorrencia=None)

@app.route('/ocorrencias-sistemicas/<int:id>/editar')
@login_required
def ocorrencias_sistemicas_editar(id):
    ocorrencia = OcorrenciaSistemica.query.get_or_404(id)
    return render_template('ocorrencias_sistemicas_form.html', user=current_user, ocorrencia=ocorrencia)

# Página de férias do funcionário
@app.route('/funcionarios/<int:id>/ferias')
@login_required
def funcionarios_ferias(id):
    funcionario = Funcionario.query.get_or_404(id)
    return render_template('funcionarios_ferias.html', user=current_user, funcionario=funcionario)
# API: Listar férias do funcionário
@app.route('/api/funcionarios/<int:id>/ferias', methods=['GET'])
@login_required
def api_ferias_listar(id):
    ferias = Ferias.query.filter_by(funcionario_id=id).order_by(Ferias.data_inicio.desc()).all()
    return jsonify({
        'success': True,
        'ferias': [f.to_dict() for f in ferias]
    })



# Routes das APIs ------------------------------------------------------------------------------------------------

# API: Criar férias
@app.route('/api/funcionarios/<int:id>/ferias', methods=['POST'])
@login_required
def api_ferias_criar(id):
    from datetime import datetime
    # Aceita tanto JSON quanto form-data
    data = request.get_json(silent=True) or request.form
    try:
        data_inicio_str = data.get('data_inicio')
        data_fim_str = data.get('data_fim')
        if not data_inicio_str or not data_fim_str:
            return jsonify({'success': False, 'message': 'Campos data_inicio e data_fim são obrigatórios.'}), 400
        data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
        data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
        dias = int(data.get('dias', 0))
        abono = str(data.get('abono', 'False')).lower() in ['true', '1', 'on']
        observacao = data.get('observacao')
        ferias = Ferias(
            funcionario_id=id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            dias=dias,
            abono=abono,
            observacao=observacao
        )
        db.session.add(ferias)
        db.session.commit()
        return jsonify({'success': True, 'ferias': ferias.to_dict()})
    except Exception as e:
        logger.error(f"Erro : {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 400

# API: Atualizar férias
@app.route('/api/funcionarios/<int:funcionario_id>/ferias/<int:ferias_id>', methods=['PUT'])
@login_required
def api_ferias_atualizar(funcionario_id, ferias_id):
    from datetime import datetime
    ferias = Ferias.query.get_or_404(ferias_id)
    # Aceita tanto JSON quanto form-data
    data = request.get_json(silent=True) or request.form
    try:
        data_inicio_str = data.get('data_inicio')
        data_fim_str = data.get('data_fim')
        if not data_inicio_str or not data_fim_str:
            return jsonify({'success': False, 'message': 'Campos data_inicio e data_fim são obrigatórios.'}), 400
        ferias.data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
        ferias.data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
        ferias.dias = int(data.get('dias', ferias.dias))
        ferias.abono = str(data.get('abono', ferias.abono)).lower() in ['true', '1', 'on']
        ferias.observacao = data.get('observacao', ferias.observacao)
        db.session.commit()
        return jsonify({'success': True, 'ferias': ferias.to_dict()})
    except Exception as e:
        logger.error(f"Erro : {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 400

# API: Deletar férias
@app.route('/api/funcionarios/<int:funcionario_id>/ferias/<int:ferias_id>', methods=['DELETE'])
@login_required
def api_ferias_deletar(funcionario_id, ferias_id):
    ferias = Ferias.query.get_or_404(ferias_id)
    try:
        db.session.delete(ferias)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Erro : {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 400
    


@app.route('/api/sac', methods=['GET'])
@login_required
def api_sac_listar():
    cliente_id = request.args.get('cliente_id')
    status = request.args.get('status')
    prioridade = request.args.get('prioridade')
    categoria = request.args.get('categoria')
    mes = request.args.get('mes')
    
    query = Sac.query
    
    if cliente_id:
        query = query.filter_by(cliente_id=cliente_id)
    if status and status != 'todos':
        query = query.filter_by(status=status)
    if prioridade and prioridade != 'todos':
        query = query.filter_by(prioridade=prioridade)
    if categoria and categoria != 'todos':
        query = query.filter_by(categoria=categoria)
    if mes:
        ano, mes_num = mes.split('-')
        query = query.filter(
            db.extract('year', Sac.data_ocorrencia) == int(ano),
            db.extract('month', Sac.data_ocorrencia) == int(mes_num)
        )
    
    ocorrencias = query.order_by(Sac.data_ocorrencia.desc(), Sac.hora_ocorrencia.desc()).all()
    
    # Buscar clientes para select
    clientes = Cliente.query.filter_by(ativo=True).order_by(Cliente.nome).all()
    enderecos = Endereco.query.filter_by(ativo=True).join(Cliente).order_by(Cliente.nome).all()
    
    # Estatísticas
    total_aberto = Sac.query.filter_by(status='Aberto').count()
    total_andamento = Sac.query.filter_by(status='Em Andamento').count()
    total_resolvido = Sac.query.filter_by(status='Resolvido').count()
    total_urgente = Sac.query.filter_by(prioridade='Urgente', status='Aberto').count()
    
    return jsonify({
        'success': True,
        'ocorrencias': [o.to_dict() for o in ocorrencias],
        'clientes': [{'id': c.id, 'nome': c.nome} for c in clientes],
        'enderecos': [{
            'id': e.id,
            'descricao': f"{e.cliente.nome} - {e.logradouro}, {e.numero}",
            'cliente_id': e.cliente_id,
            'cliente_nome': e.cliente.nome
        } for e in enderecos],
        'estatisticas': {
            'total_aberto': total_aberto,
            'total_andamento': total_andamento,
            'total_resolvido': total_resolvido,
            'total_urgente': total_urgente
        }
    })

@app.route('/api/sac/download/<tipo>/<filename>')
@login_required
def api_sac_download(tipo, filename):
    if tipo not in ['documentos']:
        return jsonify({'success': False, 'message': 'Tipo inválido'}), 400
    
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], tipo, secure_filename(filename))
    
    if not os.path.exists(filepath):
        return jsonify({'success': False, 'message': 'Arquivo não encontrado'}), 404
    
    return send_file(filepath, as_attachment=True)

@app.route('/api/sac/<int:id>', methods=['GET'])
@login_required
def api_sac_obter(id):
    ocorrencia = Sac.query.get_or_404(id)
    return jsonify({
        'success': True,
        'ocorrencia': ocorrencia.to_dict()
    })

@app.route('/api/sac', methods=['POST'])
@login_required
def api_sac_criar():
    try:
        if request.content_type.startswith('application/json'):
            data = request.get_json()
            arquivo_anexo = data.get('arquivo_anexo')
        else:
            data = request.form
            arquivo_anexo = save_uploaded_file(request.files.get('arquivo_anexo'), 'documento')
        
        ocorrencia = Sac(
            cliente_id=data['cliente_id'],
            endereco_id=data.get('endereco_id'),
            data_ocorrencia=datetime.strptime(data['data_ocorrencia'], '%Y-%m-%d').date(),
            hora_ocorrencia=datetime.strptime(data['hora_ocorrencia'], '%H:%M').time(),
            tipo_contato=data['tipo_contato'],
            canal_entrada=data['canal_entrada'],
            assunto=data['assunto'],
            descricao=data['descricao'],
            categoria=data['categoria'],
            prioridade=data['prioridade'],
            status=data.get('status', 'Aberto'),
            responsavel=data.get('responsavel'),
            arquivo_anexo=arquivo_anexo
        )
        
        db.session.add(ocorrencia)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Ocorrência SAC registrada com sucesso',
            'ocorrencia': ocorrencia.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro : {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/sac/<int:id>', methods=['PUT'])
@login_required
def api_sac_atualizar(id):
    ocorrencia = Sac.query.get_or_404(id)
    
    try:
        if request.content_type.startswith('application/json'):
            data = request.get_json()
        else:
            data = request.form
            
            # Processar upload de novo arquivo
            novo_arquivo = request.files.get('arquivo_anexo')
            if novo_arquivo and novo_arquivo.filename:
                # Remover arquivo antigo se existir
                if ocorrencia.arquivo_anexo:
                    old_path = os.path.join(app.config['UPLOAD_FOLDER'], 'documentos', ocorrencia.arquivo_anexo)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                ocorrencia.arquivo_anexo = save_uploaded_file(novo_arquivo, 'documento')
        
        ocorrencia.cliente_id = data.get('cliente_id', ocorrencia.cliente_id)
        ocorrencia.endereco_id = data.get('endereco_id', ocorrencia.endereco_id)
        ocorrencia.data_ocorrencia = datetime.strptime(data['data_ocorrencia'], '%Y-%m-%d').date()
        ocorrencia.hora_ocorrencia = datetime.strptime(data['hora_ocorrencia'], '%H:%M').time()
        ocorrencia.tipo_contato = data.get('tipo_contato', ocorrencia.tipo_contato)
        ocorrencia.canal_entrada = data.get('canal_entrada', ocorrencia.canal_entrada)
        ocorrencia.assunto = data.get('assunto', ocorrencia.assunto)
        ocorrencia.descricao = data.get('descricao', ocorrencia.descricao)
        ocorrencia.categoria = data.get('categoria', ocorrencia.categoria)
        ocorrencia.prioridade = data.get('prioridade', ocorrencia.prioridade)
        ocorrencia.status = data.get('status', ocorrencia.status)
        ocorrencia.responsavel = data.get('responsavel', ocorrencia.responsavel)
        ocorrencia.solucao = data.get('solucao', ocorrencia.solucao)
        ocorrencia.satisfacao = data.get('satisfacao', ocorrencia.satisfacao)
        ocorrencia.feedback = data.get('feedback', ocorrencia.feedback)
        
        # Se foi resolvido, registrar data/hora de resolução
        if data.get('status') in ['Resolvido', 'Fechado'] and not ocorrencia.data_resolucao:
            ocorrencia.data_resolucao = datetime.now().date()
            ocorrencia.hora_resolucao = datetime.now().time()
        
        # Se voltou para aberto/andamento, limpar data de resolução
        if data.get('status') in ['Aberto', 'Em Andamento'] and ocorrencia.data_resolucao:
            ocorrencia.data_resolucao = None
            ocorrencia.hora_resolucao = None
        
        if request.content_type.startswith('application/json'):
            if data.get('arquivo_anexo') is not None:
                ocorrencia.arquivo_anexo = data['arquivo_anexo']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Ocorrência SAC atualizada com sucesso',
            'ocorrencia': ocorrencia.to_dict()
        })
    except Exception as e:
        logger.error(f"Erro : {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/sac/<int:id>', methods=['DELETE'])
@login_required
def api_sac_deletar(id):
    ocorrencia = Sac.query.get_or_404(id)
    
    try:
        # Remover arquivo físico se existir
        if ocorrencia.arquivo_anexo:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'documentos', ocorrencia.arquivo_anexo)
            if os.path.exists(file_path):
                os.remove(file_path)
        
        db.session.delete(ocorrencia)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Ocorrência SAC excluída com sucesso'})
    except Exception as e:
        logger.error(f"Erro : {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/ocorrencias-sistemicas', methods=['GET'])
@login_required
def api_ocorrencias_sistemicas_listar():
    cliente_id = request.args.get('cliente_id')
    endereco_id = request.args.get('endereco_id')
    status = request.args.get('status')
    prioridade = request.args.get('prioridade')
    mes = request.args.get('mes')
    
    query = OcorrenciaSistemica.query
    
    if endereco_id:
        query = query.filter_by(endereco_id=endereco_id)
    elif cliente_id:
        # Filtrar por cliente através do endereço
        query = query.join(Endereco).filter(Endereco.cliente_id == cliente_id)
    
    if status and status != 'todos':
        query = query.filter_by(status=status)
    
    if prioridade and prioridade != 'todos':
        query = query.filter_by(prioridade=prioridade)
    
    if mes:
        ano, mes_num = mes.split('-')
        query = query.filter(
            db.extract('year', OcorrenciaSistemica.data_ocorrencia) == int(ano),
            db.extract('month', OcorrenciaSistemica.data_ocorrencia) == int(mes_num)
        )
    
    ocorrencias = query.order_by(OcorrenciaSistemica.data_ocorrencia.desc(), OcorrenciaSistemica.hora_ocorrencia.desc()).all()
    
    # Buscar clientes e endereços para selects
    clientes = Cliente.query.filter_by(ativo=True).order_by(Cliente.nome).all()
    enderecos = Endereco.query.filter_by(ativo=True).join(Cliente).order_by(Cliente.nome).all()
    
    # Estatísticas
    total_reportada = OcorrenciaSistemica.query.filter_by(status='Reportada').count()
    total_analise = OcorrenciaSistemica.query.filter_by(status='Em Análise').count()
    total_correcao = OcorrenciaSistemica.query.filter_by(status='Em Correção').count()
    total_resolvida = OcorrenciaSistemica.query.filter_by(status='Resolvida').count()
    total_critica = OcorrenciaSistemica.query.filter_by(prioridade='Crítica', status='Reportada').count()
    
    return jsonify({
        'success': True,
        'ocorrencias': [o.to_dict() for o in ocorrencias],
        'clientes': [{'id': c.id, 'nome': c.nome} for c in clientes],
        'enderecos': [{
            'id': e.id,
            'descricao': f"{e.cliente.nome} - {e.logradouro}, {e.numero} - {e.bairro}",
            'cliente_id': e.cliente_id,
            'cliente_nome': e.cliente.nome
        } for e in enderecos],
        'estatisticas': {
            'total_reportada': total_reportada,
            'total_analise': total_analise,
            'total_correcao': total_correcao,
            'total_resolvida': total_resolvida,
            'total_critica': total_critica
        }
    })

@app.route('/api/ocorrencias-sistemicas/<int:id>', methods=['GET'])
@login_required
def api_ocorrencias_sistemicas_obter(id):
    ocorrencia = OcorrenciaSistemica.query.get_or_404(id)
    return jsonify({
        'success': True,
        'ocorrencia': ocorrencia.to_dict()
    })

@app.route('/api/ocorrencias-sistemicas/download/<tipo>/<filename>')
@login_required
def api_ocorrencias_sistemicas_download(tipo, filename):
    if tipo not in ['documentos', 'videos']:
        return jsonify({'success': False, 'message': 'Tipo inválido'}), 400
    
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], tipo, secure_filename(filename))
    
    if not os.path.exists(filepath):
        return jsonify({'success': False, 'message': 'Arquivo não encontrado'}), 404
    
    return send_file(filepath, as_attachment=True)
@app.route('/api/ocorrencias-sistemicas', methods=['POST'])
@login_required
def api_ocorrencias_sistemicas_criar():
    try:
        if request.content_type.startswith('application/json'):
            data = request.get_json()
            arquivo_documento = data.get('arquivo_documento')
            arquivo_video = data.get('arquivo_video')
        else:
            data = request.form
            arquivo_documento = save_uploaded_file(request.files.get('arquivo_documento'), 'documento')
            arquivo_video = save_uploaded_file(request.files.get('arquivo_video'), 'video')
        
        ocorrencia = OcorrenciaSistemica(
            endereco_id=data['endereco_id'],
            data_ocorrencia=datetime.strptime(data['data_ocorrencia'], '%Y-%m-%d').date(),
            hora_ocorrencia=datetime.strptime(data['hora_ocorrencia'], '%H:%M').time(),
            observacao=data['observacao'],
            status=data.get('status', 'Reportada'),
            prioridade=data.get('prioridade', 'Média'),
            responsavel=data.get('responsavel'),
            arquivo_documento=arquivo_documento,
            arquivo_video=arquivo_video
        )
        
        db.session.add(ocorrencia)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Ocorrência sistêmica registrada com sucesso',
            'ocorrencia': ocorrencia.to_dict()
        })
    except Exception as e:
        logger.error(f"Erro : {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/ocorrencias-sistemicas/<int:id>', methods=['PUT'])
@login_required
def api_ocorrencias_sistemicas_atualizar(id):
    ocorrencia = OcorrenciaSistemica.query.get_or_404(id)
    
    try:
        if request.content_type.startswith('application/json'):
            data = request.get_json()
        else:
            data = request.form
            
            # Processar upload de novos arquivos
            novo_documento = request.files.get('arquivo_documento')
            if novo_documento and novo_documento.filename:
                # Remover arquivo antigo se existir
                if ocorrencia.arquivo_documento:
                    old_path = os.path.join(app.config['UPLOAD_FOLDER'], 'documentos', ocorrencia.arquivo_documento)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                ocorrencia.arquivo_documento = save_uploaded_file(novo_documento, 'documento')
            
            novo_video = request.files.get('arquivo_video')
            if novo_video and novo_video.filename:
                # Remover arquivo antigo se existir
                if ocorrencia.arquivo_video:
                    old_path = os.path.join(app.config['UPLOAD_FOLDER'], 'videos', ocorrencia.arquivo_video)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                ocorrencia.arquivo_video = save_uploaded_file(novo_video, 'video')
        
        ocorrencia.endereco_id = data.get('endereco_id', ocorrencia.endereco_id)
        ocorrencia.data_ocorrencia = datetime.strptime(data['data_ocorrencia'], '%Y-%m-%d').date()
        ocorrencia.hora_ocorrencia = datetime.strptime(data['hora_ocorrencia'], '%H:%M').time()
        ocorrencia.observacao = data.get('observacao', ocorrencia.observacao)
        ocorrencia.status = data.get('status', ocorrencia.status)
        ocorrencia.prioridade = data.get('prioridade', ocorrencia.prioridade)
        ocorrencia.responsavel = data.get('responsavel', ocorrencia.responsavel)
        ocorrencia.solucao = data.get('solucao', ocorrencia.solucao)
        
        # Se foi resolvida, registrar data/hora de resolução
        if data.get('status') in ['Resolvida', 'Fechada'] and not ocorrencia.data_resolucao:
            ocorrencia.data_resolucao = datetime.now().date()
            ocorrencia.hora_resolucao = datetime.now().time()
        
        # Se voltou para status anterior, limpar data de resolução
        if data.get('status') in ['Reportada', 'Em Análise', 'Em Correção'] and ocorrencia.data_resolucao:
            ocorrencia.data_resolucao = None
            ocorrencia.hora_resolucao = None
        
        if request.content_type.startswith('application/json'):
            if data.get('arquivo_documento') is not None:
                ocorrencia.arquivo_documento = data['arquivo_documento']
            if data.get('arquivo_video') is not None:
                ocorrencia.arquivo_video = data['arquivo_video']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Ocorrência sistêmica atualizada com sucesso',
            'ocorrencia': ocorrencia.to_dict()
        })
    except Exception as e:
        logger.error(f"Erro : {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    
@app.route('/api/ocorrencias-sistemicas/<int:id>', methods=['DELETE'])
@login_required
def api_ocorrencias_sistemicas_deletar(id):
    ocorrencia = OcorrenciaSistemica.query.get_or_404(id)
    
    try:
        # Remover arquivos físicos
        if ocorrencia.arquivo_documento:
            doc_path = os.path.join(app.config['UPLOAD_FOLDER'], 'documentos', ocorrencia.arquivo_documento)
            if os.path.exists(doc_path):
                os.remove(doc_path)
        
        if ocorrencia.arquivo_video:
            video_path = os.path.join(app.config['UPLOAD_FOLDER'], 'videos', ocorrencia.arquivo_video)
            if os.path.exists(video_path):
                os.remove(video_path)
        
        db.session.delete(ocorrencia)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Ocorrência sistêmica excluída com sucesso'})
    except Exception as e:
        logger.error(f"Erro : {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    

@app.route('/api/fornecedores', methods=['GET'])
@login_required
def api_fornecedores_listar():
    filtro = request.args.get('filtro', 'todos')
    
    query = Fornecedor.query
    
    if filtro == 'ativos':
        query = query.filter_by(ativo=True)
    elif filtro == 'inativos':
        query = query.filter_by(ativo=False)
    elif filtro == 'pronta_resposta':
        query = query.filter_by(pronta_resposta=True, ativo=True)
    
    fornecedores = query.order_by(Fornecedor.nome_empresa).all()
    return jsonify({
        'success': True,
        'fornecedores': [f.to_dict() for f in fornecedores]
    })

@app.route('/api/fornecedores/<int:id>', methods=['GET'])
@login_required
def api_fornecedores_obter(id):
    fornecedor = Fornecedor.query.get_or_404(id)
    return jsonify({
        'success': True,
        'fornecedor': fornecedor.to_dict()
    })



@app.route('/api/fornecedores', methods=['POST'])
@login_required
def api_fornecedores_criar():
    data = request.get_json()
    
    try:
        # Verificar se CNPJ já existe
        if Fornecedor.query.filter_by(cnpj=data['cnpj']).first():
            return jsonify({'success': False, 'message': 'CNPJ já cadastrado'}), 400
        
        fornecedor = Fornecedor(
            nome_empresa=data['nome_empresa'],
            cnpj=data['cnpj'],
            pronta_resposta=data.get('pronta_resposta', False),
            valor_hora_homem=data['valor_hora_homem'],
            ativo=data.get('ativo', True)
        )
        
        db.session.add(fornecedor)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Fornecedor cadastrado com sucesso',
            'fornecedor': fornecedor.to_dict()
        })
    except Exception as e:
        logger.error(f"Erro : {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/fornecedores/<int:id>', methods=['PUT'])
@login_required
def api_fornecedores_atualizar(id):
    fornecedor = Fornecedor.query.get_or_404(id)
    data = request.get_json()
    
    try:
        # Verificar se está tentando mudar CNPJ para um já existente
        if data.get('cnpj') and data['cnpj'] != fornecedor.cnpj:
            if Fornecedor.query.filter_by(cnpj=data['cnpj']).first():
                return jsonify({'success': False, 'message': 'CNPJ já cadastrado'}), 400
        
        fornecedor.nome_empresa = data.get('nome_empresa', fornecedor.nome_empresa)
        fornecedor.cnpj = data.get('cnpj', fornecedor.cnpj)
        fornecedor.pronta_resposta = data.get('pronta_resposta', fornecedor.pronta_resposta)
        fornecedor.valor_hora_homem = data.get('valor_hora_homem', fornecedor.valor_hora_homem)
        fornecedor.ativo = data.get('ativo', fornecedor.ativo)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Fornecedor atualizado com sucesso',
            'fornecedor': fornecedor.to_dict()
        })
    except Exception as e:
        logger.error(f"Erro : {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/fornecedores/<int:id>', methods=['DELETE'])
@login_required
def api_fornecedores_deletar(id):
    fornecedor = Fornecedor.query.get_or_404(id)
    try:
        db.session.delete(fornecedor)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Fornecedor excluído com sucesso'})
    except Exception as e:
        logger.error(f"Erro : {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    
@app.route('/fornecedores/<int:id>/fornecedores_atendimentos')
@login_required
def fornecedores_atendimentos(id):
    fornecedor = Fornecedor.query.get_or_404(id)
    if not fornecedor.pronta_resposta:
        flash('Este fornecedor não possui serviço de pronta resposta')
        return redirect(url_for('fornecedores'))
    return render_template('fornecedores_atendimentos.html', user=current_user, fornecedor=fornecedor)


 
@app.route('/api/fornecedores/<int:fornecedor_id>/atendimentos', methods=['GET'])
@login_required
def api_fornecedor_atendimentos_listar(fornecedor_id):
    fornecedor = Fornecedor.query.get_or_404(fornecedor_id)
    
    if not fornecedor.pronta_resposta:
        return jsonify({'success': False, 'message': 'Fornecedor não possui serviço de pronta resposta'}), 400
    
    mes = request.args.get('mes')  # Formato: YYYY-MM
    
    query = AtendimentoProntaResposta.query.filter_by(fornecedor_id=fornecedor_id)
    
    if mes:
        ano, mes_num = mes.split('-')
        query = query.filter(
            db.extract('year', AtendimentoProntaResposta.data_atendimento) == int(ano),
            db.extract('month', AtendimentoProntaResposta.data_atendimento) == int(mes_num)
        )
    
    atendimentos = query.order_by(AtendimentoProntaResposta.data_atendimento.desc()).all()
    
    # Calcular totais
    total_atendimentos = len(atendimentos)
    total_horas = sum(float(a.quantidade_horas) for a in atendimentos)
    total_valor = sum(float(a.valor_total) for a in atendimentos)
    
    return jsonify({
        'success': True,
        'fornecedor': fornecedor.to_dict(),
        'atendimentos': [a.to_dict() for a in atendimentos],
        'total_atendimentos': total_atendimentos,
        'total_horas': total_horas,
        'total_valor': total_valor
    })

@app.route('/api/fornecedores/<int:fornecedor_id>/atendimentos', methods=['POST'])
@login_required
def api_fornecedor_atendimentos_criar(fornecedor_id):
    fornecedor = Fornecedor.query.get_or_404(fornecedor_id)
    
    if not fornecedor.pronta_resposta:
        return jsonify({'success': False, 'message': 'Fornecedor não possui serviço de pronta resposta'}), 400
    
    data = request.get_json()
    
    try:
        quantidade_horas = float(data['quantidade_horas'])
        valor_hora = float(fornecedor.valor_hora_homem)
        valor_total = quantidade_horas * valor_hora
        
        atendimento = AtendimentoProntaResposta(
            fornecedor_id=fornecedor_id,
            data_atendimento=datetime.strptime(data['data_atendimento'], '%Y-%m-%d').date(),
            hora_atendimento=datetime.strptime(data['hora_atendimento'], '%H:%M').time(),
            historico=data['historico'],
            nome_representante=data['nome_representante'],
            quantidade_horas=quantidade_horas,
            valor_hora=valor_hora,
            valor_total=valor_total
        )
        
        db.session.add(atendimento)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Atendimento registrado com sucesso',
            'atendimento': atendimento.to_dict()
        })
    except Exception as e:
        logger.error(f"Erro : {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/fornecedores/<int:fornecedor_id>/atendimentos/<int:atendimento_id>', methods=['PUT'])
@login_required
def api_fornecedor_atendimentos_atualizar(fornecedor_id, atendimento_id):
    atendimento = AtendimentoProntaResposta.query.filter_by(
        id=atendimento_id, 
        fornecedor_id=fornecedor_id
    ).first_or_404()
    
    data = request.get_json()
    
    try:
        quantidade_horas = float(data['quantidade_horas'])
        # Usar o valor da hora atual do fornecedor
        valor_hora = float(atendimento.fornecedor.valor_hora_homem)
        valor_total = quantidade_horas * valor_hora
        
        atendimento.data_atendimento = datetime.strptime(data['data_atendimento'], '%Y-%m-%d').date()
        atendimento.hora_atendimento = datetime.strptime(data['hora_atendimento'], '%H:%M').time()
        atendimento.historico = data['historico']
        atendimento.nome_representante = data['nome_representante']
        atendimento.quantidade_horas = quantidade_horas
        atendimento.valor_hora = valor_hora
        atendimento.valor_total = valor_total
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Atendimento atualizado com sucesso',
            'atendimento': atendimento.to_dict()
        })
    except Exception as e:
        logger.error(f"Erro : {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/fornecedores/<int:fornecedor_id>/atendimentos/<int:atendimento_id>', methods=['DELETE'])
@login_required
def api_fornecedor_atendimentos_deletar(fornecedor_id, atendimento_id):
    atendimento = AtendimentoProntaResposta.query.filter_by(
        id=atendimento_id, 
        fornecedor_id=fornecedor_id
    ).first_or_404()
    
    try:
        db.session.delete(atendimento)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Atendimento excluído com sucesso'})
    except Exception as e:
        logger.error(f"Erro : {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    
    
@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html', user=current_user)

@app.route('/funcionarios')
@login_required
def funcionarios():
    return render_template('funcionarios.html', user=current_user)

@app.route('/funcionarios/novo')
@login_required
def funcionarios_novo():
    return render_template('funcionarios_form.html', user=current_user, funcionario=None)

@app.route('/funcionarios/<int:id>/editar')
@login_required
def funcionarios_editar(id):
    funcionario = Funcionario.query.get_or_404(id)
    return render_template('funcionarios_form.html', user=current_user, funcionario=funcionario)

@app.route('/funcionarios/<int:id>/evolucao')
@login_required
def funcionarios_evolucao(id):
    funcionario = Funcionario.query.get_or_404(id)
    return render_template('funcionarios_evolucao.html', user=current_user, funcionario=funcionario)

@app.route('/funcionarios/<int:id>/faltas')
@login_required
def funcionarios_faltas(id):
    funcionario = Funcionario.query.get_or_404(id)
    return render_template('funcionarios_faltas.html', user=current_user, funcionario=funcionario)

@app.route('/funcionarios/<int:id>/folgas')
@login_required
def funcionarios_folgas(id):
    funcionario = Funcionario.query.get_or_404(id)
    return render_template('funcionarios_folgas.html', user=current_user, funcionario=funcionario)

@app.route('/funcionarios/<int:id>/ocorrencias')
@login_required
def funcionarios_ocorrencias(id):
    funcionario = Funcionario.query.get_or_404(id)
    return render_template('funcionarios_ocorrencias.html', user=current_user, funcionario=funcionario)

@app.route('/clientes')
@login_required
def clientes():
    return render_template('clientes.html', user=current_user)

@app.route('/clientes/novo')
@login_required
def clientes_novo():
    return render_template('clientes_form.html', user=current_user, cliente=None)

@app.route('/clientes/<int:id>/editar')
@login_required
def clientes_editar(id):
    cliente = Cliente.query.get_or_404(id)
    return render_template('clientes_form.html', user=current_user, cliente=cliente)

@app.route('/clientes/<int:id>/enderecos')
@login_required
def clientes_enderecos(id):
    cliente = Cliente.query.get_or_404(id)
    # Buscar todas as regiões
    regioes = Regiao.query.order_by(Regiao.nome).all()
    return render_template('clientes_enderecos.html', user=current_user, cliente=cliente, regioes=regioes)

@app.route('/atendimentos')
@login_required
def atendimentos():
    return render_template('atendimentos.html', user=current_user)

@app.route('/atendimentos/novo')
@login_required
def atendimentos_novo():
    return render_template('atendimentos_form.html', user=current_user, atendimento=None)

@app.route('/atendimentos/<int:id>/editar')
@login_required
def atendimentos_editar(id):
    atendimento = Atendimento.query.get_or_404(id)
    return render_template('atendimentos_form.html', user=current_user, atendimento=atendimento)


@app.route('/regioes')
@login_required
def regioes():
    return render_template('regioes.html', user=current_user)

@app.route('/regioes/novo')
@login_required
def regioes_novo():
    return render_template('regioes_form.html', user=current_user, regiao=None)

@app.route('/regioes/<int:id>/editar')
@login_required
def regioes_editar(id):
    regiao = Regiao.query.get_or_404(id)
    return render_template('regioes_form.html', user=current_user, regiao=regiao)


# API Routes - Autenticação
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'success': False, 'message': 'Usuário e senha são obrigatórios'}), 400
    
    user = User.query.filter_by(username=username).first()
    
    if user and user.check_password(password):
        login_user(user)
        return jsonify({'success': True, 'message': 'Login realizado com sucesso'})
    
    return jsonify({'success': False, 'message': 'Usuário ou senha inválidos'}), 401

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    if not username or not email or not password:
        return jsonify({'success': False, 'message': 'Todos os campos são obrigatórios'}), 400
    
    if User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'message': 'Usuário já existe'}), 400
    
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': 'Email já cadastrado'}), 400
    
    user = User(username=username, email=email)
    user.set_password(password)
    
    try:
        db.session.add(user)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Usuário cadastrado com sucesso'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao cadastrar usuário: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Erro ao cadastrar usuário'}), 500

@app.route('/api/logout', methods=['POST'])
@login_required
def api_logout():
    logout_user()
    return jsonify({'success': True, 'message': 'Logout realizado com sucesso'})

@app.route('/api/user', methods=['GET'])
@login_required
def api_user():
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'email': current_user.email
    })

# API Routes - Funcionários
@app.route('/api/funcionarios', methods=['GET'])
@login_required
def api_funcionarios_listar():
    filtro = request.args.get('filtro', 'todos')
    
    query = Funcionario.query
    
    if filtro == 'ativos':
        query = query.filter_by(ativo=True)
    elif filtro == 'inativos':
        query = query.filter_by(ativo=False)
    
    funcionarios = query.order_by(Funcionario.nome).all()
    funcionarios_json = []
    for f in funcionarios:
        d = f.to_dict()
        # Adiciona lista de férias (ordenada por data_inicio)
        d['ferias'] = [ferias.to_dict() for ferias in sorted(f.ferias, key=lambda x: x.data_inicio)]
        funcionarios_json.append(d)
    return jsonify({
        'success': True,
        'funcionarios': funcionarios_json
    })

@app.route('/api/funcionarios/<int:id>', methods=['GET'])
@login_required
def api_funcionarios_obter(id):
    funcionario = Funcionario.query.get_or_404(id)
    return jsonify({
        'success': True,
        'funcionario': funcionario.to_dict()
    })

@app.route('/api/funcionarios', methods=['POST'])
@login_required
def api_funcionarios_criar():
    data = request.get_json()
    
    try:
        # Verificar se RE já existe
        if Funcionario.query.filter_by(re=data['re']).first():
            return jsonify({'success': False, 'message': 'RE já cadastrado'}), 400
        
        funcionario = Funcionario(
            nome=data['nome'],
            re=data['re'],
            cargo=data['cargo'],
            data_admissao=datetime.strptime(data['data_admissao'], '%Y-%m-%d').date(),
            salario_atual=data['salario_atual'],
            ativo=True
        )
        
        db.session.add(funcionario)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Funcionário cadastrado com sucesso',
            'funcionario': funcionario.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro : {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/funcionarios/<int:id>', methods=['PUT'])
@login_required
def api_funcionarios_atualizar(id):
    funcionario = Funcionario.query.get_or_404(id)
    data = request.get_json()
    
    try:
        # Verificar se está tentando mudar RE para um já existente
        if data.get('re') and data['re'] != funcionario.re:
            if Funcionario.query.filter_by(re=data['re']).first():
                return jsonify({'success': False, 'message': 'RE já cadastrado'}), 400
        
        funcionario.nome = data.get('nome', funcionario.nome)
        funcionario.re = data.get('re', funcionario.re)
        funcionario.cargo = data.get('cargo', funcionario.cargo)
        
        if data.get('data_admissao'):
            funcionario.data_admissao = datetime.strptime(data['data_admissao'], '%Y-%m-%d').date()
        
        if data.get('data_demissao'):
            funcionario.data_demissao = datetime.strptime(data['data_demissao'], '%Y-%m-%d').date()
            funcionario.motivo_demissao = data.get('motivo_demissao')
            funcionario.ativo = False
        else:
            funcionario.data_demissao = None
            funcionario.motivo_demissao = None
            funcionario.ativo = True
        
        funcionario.salario_atual = data.get('salario_atual', funcionario.salario_atual)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Funcionário atualizado com sucesso',
            'funcionario': funcionario.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro : {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/funcionarios/<int:id>', methods=['DELETE'])
@login_required
def api_funcionarios_deletar(id):
    funcionario = Funcionario.query.get_or_404(id)
    
    try:
        db.session.delete(funcionario)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Funcionário excluído com sucesso'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro : {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

# API Routes - Evolução Salarial
@app.route('/api/funcionarios/<int:id>/evolucao', methods=['GET'])
@login_required
def api_evolucao_listar(id):
    funcionario = Funcionario.query.get_or_404(id)
    evolucoes = EvolucaoSalarial.query.filter_by(funcionario_id=id).order_by(EvolucaoSalarial.data_promocao.desc()).all()
    
    return jsonify({
        'success': True,
        'funcionario': funcionario.to_dict(),
        'evolucoes': [e.to_dict() for e in evolucoes]
    })

@app.route('/api/funcionarios/<int:id>/evolucao', methods=['POST'])
@login_required
def api_evolucao_criar(id):
    funcionario = Funcionario.query.get_or_404(id)
    data = request.get_json()
    
    try:
        # Registrar evolução
        evolucao = EvolucaoSalarial(
            funcionario_id=id,
            cargo_anterior=funcionario.cargo,
            salario_anterior=funcionario.salario_atual,
            cargo_novo=data['cargo_novo'],
            salario_novo=data['salario_novo'],
            data_promocao=datetime.strptime(data['data_promocao'], '%Y-%m-%d').date(),
            observacao=data.get('observacao')
        )
        
        # Atualizar funcionário
        funcionario.cargo = data['cargo_novo']
        funcionario.salario_atual = data['salario_novo']
        
        db.session.add(evolucao)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Promoção registrada com sucesso',
            'evolucao': evolucao.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro : {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

# API Routes - Faltas
@app.route('/api/funcionarios/<int:id>/faltas', methods=['GET'])
@login_required
def api_faltas_listar(id):
    funcionario = Funcionario.query.get_or_404(id)
    faltas = Falta.query.filter_by(funcionario_id=id).order_by(Falta.data_falta.desc()).all()
    
    return jsonify({
        'success': True,
        'funcionario': funcionario.to_dict(),
        'faltas': [f.to_dict() for f in faltas]
    })

@app.route('/api/funcionarios/<int:id>/faltas', methods=['POST'])
@login_required
def api_faltas_criar(id):
    funcionario = Funcionario.query.get_or_404(id)
    try:
        if request.content_type and request.content_type.startswith('multipart/form-data'):
            data = request.form
            file = request.files.get('arquivo_atestado')
            arquivo_atestado = None
            if file and file.filename:
                filename = secure_filename(file.filename)
                dest_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'documentos')
                os.makedirs(dest_folder, exist_ok=True)
                file.save(os.path.join(dest_folder, filename))
                arquivo_atestado = filename
        else:
            data = request.get_json()
            arquivo_atestado = data.get('arquivo_atestado')

        # Corrigir atestada para booleano
        atestada = data.get('atestada', False)
        if isinstance(atestada, str):
            atestada = atestada.lower() in ['true', '1', 'on']

        falta = Falta(
            funcionario_id=id,
            data_falta=datetime.strptime(data['data_falta'], '%Y-%m-%d').date(),
            atestada=atestada,
            motivo=data.get('motivo'),
            arquivo_atestado=arquivo_atestado
        )
        db.session.add(falta)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Falta registrada com sucesso',
            'falta': falta.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro : {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/funcionarios/<int:funcionario_id>/faltas/<int:falta_id>', methods=['PUT'])
@login_required
def api_faltas_atualizar(funcionario_id, falta_id):
    falta = Falta.query.filter_by(id=falta_id, funcionario_id=funcionario_id).first_or_404()
    try:
        if request.content_type and request.content_type.startswith('multipart/form-data'):
            data = request.form
            file = request.files.get('arquivo_atestado')
            arquivo_atestado = falta.arquivo_atestado
            if file and file.filename:
                filename = secure_filename(file.filename)
                dest_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'documentos')
                os.makedirs(dest_folder, exist_ok=True)
                file.save(os.path.join(dest_folder, filename))
                arquivo_atestado = filename
        else:
            data = request.get_json()
            arquivo_atestado = data.get('arquivo_atestado', falta.arquivo_atestado)

        # Corrigir atestada para booleano
        atestada = data.get('atestada', False)
        if isinstance(atestada, str):
            atestada = atestada.lower() in ['true', '1', 'on']

        falta.data_falta = datetime.strptime(data['data_falta'], '%Y-%m-%d').date()
        falta.atestada = atestada
        falta.motivo = data.get('motivo')
        falta.arquivo_atestado = arquivo_atestado

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Falta atualizada com sucesso',
            'falta': falta.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro : {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/funcionarios/<int:funcionario_id>/faltas/<int:falta_id>', methods=['DELETE'])
@login_required
def api_faltas_deletar(funcionario_id, falta_id):
    falta = Falta.query.filter_by(id=falta_id, funcionario_id=funcionario_id).first_or_404()
    
    try:
        db.session.delete(falta)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Falta excluída com sucesso'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro : {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

# API Routes - Folgas Trabalhadas
@app.route('/api/funcionarios/<int:id>/folgas', methods=['GET'])
@login_required
def api_folgas_listar(id):
    funcionario = Funcionario.query.get_or_404(id)
    folgas = FolgaTrabalhada.query.filter_by(funcionario_id=id).order_by(FolgaTrabalhada.data_folga.desc()).all()
    
    # Buscar todos os funcionários para o select
    todos_funcionarios = Funcionario.query.filter_by(ativo=True).order_by(Funcionario.nome).all()
    
    return jsonify({
        'success': True,
        'funcionario': funcionario.to_dict(),
        'folgas': [f.to_dict() for f in folgas],
        'funcionarios': [{'id': f.id, 'nome': f.nome, 're': f.re} for f in todos_funcionarios]
    })

@app.route('/api/funcionarios/<int:id>/folgas', methods=['POST'])
@login_required
def api_folgas_criar(id):
    funcionario = Funcionario.query.get_or_404(id)
    data = request.get_json()
    
    try:
        folga = FolgaTrabalhada(
            funcionario_id=id,
            data_folga=datetime.strptime(data['data_folga'], '%Y-%m-%d').date(),
            motivo=data['motivo'],
            valor_diaria=data['valor_diaria'],
            funcionario_substituido_id=data.get('funcionario_substituido_id'),
            observacao=data.get('observacao')
        )
        
        db.session.add(folga)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Folga trabalhada registrada com sucesso',
            'folga': folga.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro : {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/funcionarios/<int:funcionario_id>/folgas/<int:folga_id>', methods=['PUT'])
@login_required
def api_folgas_atualizar(funcionario_id, folga_id):
    folga = FolgaTrabalhada.query.filter_by(id=folga_id, funcionario_id=funcionario_id).first_or_404()
    data = request.get_json()
    
    try:
        folga.data_folga = datetime.strptime(data['data_folga'], '%Y-%m-%d').date()
        folga.motivo = data['motivo']
        folga.valor_diaria = data['valor_diaria']
        folga.funcionario_substituido_id = data.get('funcionario_substituido_id')
        folga.observacao = data.get('observacao')
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Folga trabalhada atualizada com sucesso',
            'folga': folga.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro : {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/funcionarios/<int:funcionario_id>/folgas/<int:folga_id>', methods=['DELETE'])
@login_required
def api_folgas_deletar(funcionario_id, folga_id):
    folga = FolgaTrabalhada.query.filter_by(id=folga_id, funcionario_id=funcionario_id).first_or_404()
    
    try:
        db.session.delete(folga)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Folga trabalhada excluída com sucesso'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro : {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

# API Routes - Ocorrências Disciplinares
@app.route('/api/funcionarios/<int:id>/ocorrencias', methods=['GET'])
@login_required
def api_ocorrencias_listar(id):
    funcionario = Funcionario.query.get_or_404(id)
    ocorrencias = OcorrenciaDisciplinar.query.filter_by(funcionario_id=id).order_by(OcorrenciaDisciplinar.data_ocorrencia.desc()).all()
    
    # Buscar última ocorrência
    ultima_ocorrencia = ocorrencias[0] if ocorrencias else None
    
    return jsonify({
        'success': True,
        'funcionario': funcionario.to_dict(),
        'ocorrencias': [o.to_dict() for o in ocorrencias],
        'total_ocorrencias': len(ocorrencias),
        'ultima_ocorrencia': ultima_ocorrencia.to_dict() if ultima_ocorrencia else None
    })

@app.route('/api/funcionarios/<int:id>/ocorrencias', methods=['POST'])
@login_required
def api_ocorrencias_criar(id):
    funcionario = Funcionario.query.get_or_404(id)
    data = request.get_json()
    
    try:
        # Se motivo for "Outros", usar o motivo_detalhado
        motivo = data['motivo']
        motivo_detalhado = None
        
        if motivo == 'Outros':
            motivo_detalhado = data.get('motivo_detalhado')
        
        ocorrencia = OcorrenciaDisciplinar(
            funcionario_id=id,
            data_ocorrencia=datetime.strptime(data['data_ocorrencia'], '%Y-%m-%d').date(),
            tipo=data['tipo'],
            motivo=motivo,
            motivo_detalhado=motivo_detalhado,
            descricao=data.get('descricao')
        )
        
        db.session.add(ocorrencia)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Ocorrência disciplinar registrada com sucesso',
            'ocorrencia': ocorrencia.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro : {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/funcionarios/<int:funcionario_id>/ocorrencias/<int:ocorrencia_id>', methods=['PUT'])
@login_required
def api_ocorrencias_atualizar(funcionario_id, ocorrencia_id):
    ocorrencia = OcorrenciaDisciplinar.query.filter_by(id=ocorrencia_id, funcionario_id=funcionario_id).first_or_404()
    data = request.get_json()
    
    try:
        ocorrencia.data_ocorrencia = datetime.strptime(data['data_ocorrencia'], '%Y-%m-%d').date()
        ocorrencia.tipo = data['tipo']
        ocorrencia.motivo = data['motivo']
        
        if data['motivo'] == 'Outros':
            ocorrencia.motivo_detalhado = data.get('motivo_detalhado')
        else:
            ocorrencia.motivo_detalhado = None
            
        ocorrencia.descricao = data.get('descricao')
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Ocorrência disciplinar atualizada com sucesso',
            'ocorrencia': ocorrencia.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro : {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/funcionarios/<int:funcionario_id>/ocorrencias/<int:ocorrencia_id>', methods=['DELETE'])
@login_required
def api_ocorrencias_deletar(funcionario_id, ocorrencia_id):
    ocorrencia = OcorrenciaDisciplinar.query.filter_by(id=ocorrencia_id, funcionario_id=funcionario_id).first_or_404()
    
    try:
        db.session.delete(ocorrencia)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Ocorrência disciplinar excluída com sucesso'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro : {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

# API Routes - Clientes
@app.route('/api/clientes', methods=['GET'])
@login_required
def api_clientes_listar():
    filtro = request.args.get('filtro', 'todos')
    
    query = Cliente.query
    
    if filtro == 'ativos':
        query = query.filter_by(ativo=True)
    elif filtro == 'inativos':
        query = query.filter_by(ativo=False)
    # Filtros por portaria remota
    elif filtro == 'com_portaria':
        # Filtra clientes que possuem pelo menos um endereço ativo com portaria_remota=True
        clientes_ids = [c.id for c in Cliente.query.all() if any(e.portaria_remota and e.ativo for e in c.enderecos)]
        query = query.filter(Cliente.id.in_(clientes_ids))
    elif filtro == 'sem_portaria':
        # Filtra clientes que não possuem nenhum endereço ativo com portaria_remota=True
        clientes_ids = [c.id for c in Cliente.query.all() if not any(e.portaria_remota and e.ativo for e in c.enderecos)]
        query = query.filter(Cliente.id.in_(clientes_ids))
    
    clientes = query.order_by(Cliente.nome).all()
    clientes_json = []
    from datetime import datetime
    mes_atual = datetime.now().month
    ano_atual = datetime.now().year
    for c in clientes:
        # Verifica se algum endereço do cliente tem portaria_remota=True
        tem_portaria_remota = any(e.portaria_remota for e in c.enderecos if e.ativo)
        cliente_dict = c.to_dict()
        cliente_dict['tem_portaria_remota'] = tem_portaria_remota
        # Somatória e média dos atendimentos do mês para endereços ativos do cliente
        total_atendimentos_mes = 0
        tempos_atendimento = []
        for e in c.enderecos:
            if e.ativo:
                atendimentos = Atendimento.query.filter(
                    Atendimento.endereco_id == e.id,
                    db.extract('month', Atendimento.data_atendimento) == mes_atual,
                    db.extract('year', Atendimento.data_atendimento) == ano_atual
                ).all()
                total_atendimentos_mes += len(atendimentos)
                for a in atendimentos:
                    tempos_atendimento.append(a.calcular_tempo_atendimento())
        cliente_dict['atendimentos_mes'] = total_atendimentos_mes
        if tempos_atendimento:
            cliente_dict['media_tempo_atendimento_mes'] = round(sum(tempos_atendimento) / len(tempos_atendimento), 1)
        else:
            cliente_dict['media_tempo_atendimento_mes'] = 0
        clientes_json.append(cliente_dict)
    return jsonify({
        'success': True,
        'clientes': clientes_json
    })

@app.route('/api/clientes/<int:id>', methods=['GET'])
@login_required
def api_clientes_obter(id):
    cliente = Cliente.query.get_or_404(id)
    return jsonify({
        'success': True,
        'cliente': cliente.to_dict()
    })

@app.route('/api/clientes', methods=['POST'])
@login_required
def api_clientes_criar():
    data = request.get_json()
    
    try:
        if Cliente.query.filter_by(cnpj=data['cnpj']).first():
            return jsonify({'success': False, 'message': 'CNPJ já cadastrado'}), 400
        
        cliente = Cliente(
            nome=data['nome'],
            cnpj=data['cnpj'],
            ativo=data.get('ativo', True),
            data_ativacao=datetime.strptime(data['data_ativacao'], '%Y-%m-%d').date() if data.get('data_ativacao') else None,
            nr_atendimentos=data.get('nr_atendimentos', 0)
        )
        
        db.session.add(cliente)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Cliente cadastrado com sucesso',
            'cliente': cliente.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao cadastrar cliente: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/clientes/<int:id>', methods=['PUT'])
@login_required
def api_clientes_atualizar(id):
    cliente = Cliente.query.get_or_404(id)
    data = request.get_json()
    
    try:
        if data.get('cnpj') and data['cnpj'] != cliente.cnpj:
            if Cliente.query.filter_by(cnpj=data['cnpj']).first():
                return jsonify({'success': False, 'message': 'CNPJ já cadastrado'}), 400
        
        cliente.nome = data.get('nome', cliente.nome)
        cliente.cnpj = data.get('cnpj', cliente.cnpj)
        
        ativo_anterior = cliente.ativo
        cliente.ativo = data.get('ativo', cliente.ativo)
        
        # Gerenciar datas de ativação/inativação
        if cliente.ativo and not ativo_anterior:
            cliente.data_ativacao = datetime.now().date()
            cliente.data_inativacao = None
        elif not cliente.ativo and ativo_anterior:
            cliente.data_inativacao = datetime.now().date()
        
        cliente.nr_atendimentos = data.get('nr_atendimentos', cliente.nr_atendimentos)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Cliente atualizado com sucesso',
            'cliente': cliente.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/clientes/<int:id>', methods=['DELETE'])
@login_required
def api_clientes_deletar(id):
    cliente = Cliente.query.get_or_404(id)
    
    try:
        db.session.delete(cliente)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Cliente excluído com sucesso'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# API Routes - Endereços
@app.route('/api/clientes/<int:cliente_id>/enderecos', methods=['GET'])
@login_required
def api_enderecos_listar(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    filtro = request.args.get('filtro', 'todos')
    
    query = Endereco.query.filter_by(cliente_id=cliente_id)
    
    if filtro == 'ativos':
        query = query.filter_by(ativo=True)
    elif filtro == 'inativos':
        query = query.filter_by(ativo=False)
    
    enderecos = query.order_by(Endereco.created_at.desc()).all()
    
    return jsonify({
        'success': True,
        'cliente': cliente.to_dict(),
        'enderecos': [e.to_dict() for e in enderecos]
    })

@app.route('/api/clientes/<int:cliente_id>/enderecos', methods=['POST'])
@login_required
def api_enderecos_criar(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    data = request.get_json()
    
    try:
        endereco = Endereco(
            cliente_id=cliente_id,
            regiao_id=data.get('regiao_id'),
            nr_contrato=data['nr_contrato'],
            data_ativacao_contrato=datetime.strptime(data['data_ativacao_contrato'], '%Y-%m-%d').date(),
            data_validade_contrato=datetime.strptime(data['data_validade_contrato'], '%Y-%m-%d').date(),
            logradouro=data['logradouro'],
            numero=data['numero'],
            bairro=data['bairro'],
            cep=data['cep'],
            cidade=data['cidade'],
            estado=data['estado'],
            tipo_endereco=data['tipo_endereco'],
            portaria_remota=data.get('portaria_remota', False),
            monitoramento=data.get('monitoramento', False),
            nr_apartamentos=data.get('nr_apartamentos'),
            tipo_internet=data['tipo_internet'],
            fornecedor_internet=data.get('fornecedor_internet'),
            tipo_nobreak=data['tipo_nobreak'],
            tipo_gravacao=data['tipo_gravacao'],
            tipo_manutencao=data['tipo_manutencao'],
            valor_contrato=data['valor_contrato'],
            percentual_reajuste=data['percentual_reajuste'],
            periodo_atendimento=data['periodo_atendimento'],
            periodo_atendimento_personalizado=data.get('periodo_atendimento_personalizado'),
            locacao_sistema=data.get('locacao_sistema', False),
            ativo=data.get('ativo', True),
            possui_rondas_virtuais=data.get('possui_rondas_virtuais', False),
            qtd_cameras_rondas=data.get('qtd_cameras_rondas'),
            frequencia_rondas=data.get('frequencia_rondas'),
            periodo_recebimento_rondas=data.get('periodo_recebimento_rondas')
        )
        
        db.session.add(endereco)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Endereço cadastrado com sucesso',
            'endereco': endereco.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro : {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/clientes/<int:cliente_id>/enderecos/<int:endereco_id>', methods=['PUT'])
@login_required
def api_enderecos_atualizar(cliente_id, endereco_id):
    endereco = Endereco.query.filter_by(id=endereco_id, cliente_id=cliente_id).first_or_404()
    data = request.get_json()
    
    try:
        endereco.regiao_id = data.get('regiao_id', endereco.regiao_id)
        endereco.nr_contrato = data.get('nr_contrato', endereco.nr_contrato)
        endereco.data_ativacao_contrato = datetime.strptime(data['data_ativacao_contrato'], '%Y-%m-%d').date()
        endereco.data_validade_contrato = datetime.strptime(data['data_validade_contrato'], '%Y-%m-%d').date()
        endereco.logradouro = data.get('logradouro', endereco.logradouro)
        endereco.numero = data.get('numero', endereco.numero)
        endereco.bairro = data.get('bairro', endereco.bairro)
        endereco.cep = data.get('cep', endereco.cep)
        endereco.cidade = data.get('cidade', endereco.cidade)
        endereco.estado = data.get('estado', endereco.estado)
        endereco.tipo_endereco = data.get('tipo_endereco', endereco.tipo_endereco)
        endereco.portaria_remota = data.get('portaria_remota', False)
        endereco.monitoramento = data.get('monitoramento', False)
        endereco.nr_apartamentos = data.get('nr_apartamentos')
        endereco.tipo_internet = data.get('tipo_internet', endereco.tipo_internet)
        endereco.fornecedor_internet = data.get('fornecedor_internet')
        endereco.tipo_nobreak = data.get('tipo_nobreak', endereco.tipo_nobreak)
        endereco.tipo_gravacao = data.get('tipo_gravacao', endereco.tipo_gravacao)
        endereco.tipo_manutencao = data.get('tipo_manutencao', endereco.tipo_manutencao)
        endereco.valor_contrato = data.get('valor_contrato', endereco.valor_contrato)
        endereco.percentual_reajuste = data.get('percentual_reajuste', endereco.percentual_reajuste)
        endereco.periodo_atendimento = data.get('periodo_atendimento', endereco.periodo_atendimento)
        endereco.periodo_atendimento_personalizado = data.get('periodo_atendimento_personalizado')
        endereco.locacao_sistema = data.get('locacao_sistema', False)
        endereco.ativo = data.get('ativo', endereco.ativo)
        endereco.possui_rondas_virtuais = data.get('possui_rondas_virtuais', False)
        endereco.qtd_cameras_rondas = data.get('qtd_cameras_rondas')
        endereco.frequencia_rondas = data.get('frequencia_rondas')
        endereco.periodo_recebimento_rondas = data.get('periodo_recebimento_rondas')
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Endereço atualizado com sucesso',
            'endereco': endereco.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro : {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/clientes/<int:cliente_id>/enderecos/<int:endereco_id>', methods=['DELETE'])
@login_required
def api_enderecos_deletar(cliente_id, endereco_id):
    endereco = Endereco.query.filter_by(id=endereco_id, cliente_id=cliente_id).first_or_404()
    
    try:
        db.session.delete(endereco)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Endereço excluído com sucesso'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro : {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

# API Routes - Atendimentos
@app.route('/api/atendimentos', methods=['GET'])
@login_required
def api_atendimentos_listar():
    mes = request.args.get('mes')  # Formato: YYYY-MM
    endereco_id = request.args.get('endereco_id')
    
    query = Atendimento.query
    
    if endereco_id:
        query = query.filter_by(endereco_id=endereco_id)
    
    if mes:
        ano, mes_num = mes.split('-')
        query = query.filter(
            db.extract('year', Atendimento.data_atendimento) == int(ano),
            db.extract('month', Atendimento.data_atendimento) == int(mes_num)
        )
    
    atendimentos = query.order_by(Atendimento.data_atendimento.desc(), Atendimento.hora_chegada.desc()).all()
    
    # Buscar endereços e funcionários para selects
    enderecos = Endereco.query.filter_by(ativo=True).join(Cliente).order_by(Cliente.nome).all()
    funcionarios = Funcionario.query.filter_by(ativo=True).order_by(Funcionario.nome).all()
    
    return jsonify({
        'success': True,
        'atendimentos': [a.to_dict() for a in atendimentos],
        'enderecos': [{
            'id': e.id,
            'descricao': f"{e.cliente.nome} - {e.logradouro}, {e.numero} - {e.bairro}, {e.cidade}/{e.estado}",
            'cliente_nome': e.cliente.nome
        } for e in enderecos],
        'funcionarios': [{'id': f.id, 'nome': f.nome, 're': f.re} for f in funcionarios]
    })

@app.route('/api/atendimentos/estatisticas', methods=['GET'])
@login_required
def api_atendimentos_estatisticas():
    mes = request.args.get('mes')  # Formato: YYYY-MM
    
    query = Atendimento.query
    
    if mes:
        ano, mes_num = mes.split('-')
        query = query.filter(
            db.extract('year', Atendimento.data_atendimento) == int(ano),
            db.extract('month', Atendimento.data_atendimento) == int(mes_num)
        )
    
    atendimentos = query.all()
    
    # Agrupar por endereço
    por_endereco = {}
    for atend in atendimentos:
        end_id = atend.endereco_id
        if end_id not in por_endereco:
            por_endereco[end_id] = {
                'endereco': atend.endereco.endereco_completo,
                'cliente': atend.endereco.cliente.nome,
                'total': 0,
                'tempo_total': 0
            }
        por_endereco[end_id]['total'] += 1
        por_endereco[end_id]['tempo_total'] += atend.calcular_tempo_atendimento()
    
    return jsonify({
        'success': True,
        'por_endereco': list(por_endereco.values()),
        'total_geral': len(atendimentos)
    })

@app.route('/api/atendimentos/<int:id>', methods=['GET'])
@login_required
def api_atendimentos_obter(id):
    atendimento = Atendimento.query.get_or_404(id)
    return jsonify({
        'success': True,
        'atendimento': atendimento.to_dict()
    })

@app.route('/api/atendimentos', methods=['POST'])
@login_required
def api_atendimentos_criar():
    data = request.get_json()
    
    try:
        atendimento = Atendimento(
            endereco_id=data['endereco_id'],
            funcionario_id=data['funcionario_id'],
            data_atendimento=datetime.strptime(data['data_atendimento'], '%Y-%m-%d').date(),
            hora_chegada=datetime.strptime(data['hora_chegada'], '%H:%M').time(),
            hora_inicio=datetime.strptime(data['hora_inicio'], '%H:%M').time(),
            hora_fim=datetime.strptime(data['hora_fim'], '%H:%M').time(),
            tempo_deslocamento=int(data['tempo_deslocamento']),
            historico=data['historico']
        )
        
        db.session.add(atendimento)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Atendimento registrado com sucesso',
            'atendimento': atendimento.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro : {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/atendimentos/<int:id>', methods=['PUT'])
@login_required
def api_atendimentos_atualizar(id):
    atendimento = Atendimento.query.get_or_404(id)
    data = request.get_json()
    
    try:
        atendimento.endereco_id = data.get('endereco_id', atendimento.endereco_id)
        atendimento.funcionario_id = data.get('funcionario_id', atendimento.funcionario_id)
        atendimento.data_atendimento = datetime.strptime(data['data_atendimento'], '%Y-%m-%d').date()
        atendimento.hora_chegada = datetime.strptime(data['hora_chegada'], '%H:%M').time()
        atendimento.hora_inicio = datetime.strptime(data['hora_inicio'], '%H:%M').time()
        atendimento.hora_fim = datetime.strptime(data['hora_fim'], '%H:%M').time()
        atendimento.tempo_deslocamento = int(data['tempo_deslocamento'])
        atendimento.historico = data.get('historico', atendimento.historico)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Atendimento atualizado com sucesso',
            'atendimento': atendimento.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro : {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/atendimentos/<int:id>', methods=['DELETE'])
@login_required
def api_atendimentos_deletar(id):
    atendimento = Atendimento.query.get_or_404(id)
    
    try:
        db.session.delete(atendimento)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Atendimento excluído com sucesso'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro : {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500




@app.route('/api/regioes', methods=['GET'])
@login_required
def api_regioes_listar():
    filtro = request.args.get('filtro', 'todos')
    
    query = Regiao.query
    
    if filtro == 'ativos':
        query = query.filter_by(ativo=True)
    elif filtro == 'inativos':
        query = query.filter_by(ativo=False)
    
    regioes = query.order_by(Regiao.nome).all()
    return jsonify({
        'success': True,
        'regioes': [r.to_dict() for r in regioes]
    })

@app.route('/api/regioes/<int:id>', methods=['GET'])
@login_required
def api_regioes_obter(id):
    regiao = Regiao.query.get_or_404(id)
    return jsonify({
        'success': True,
        'regiao': regiao.to_dict()
    })

@app.route('/api/regioes', methods=['POST'])
@login_required
def api_regioes_criar():
    data = request.get_json()
    
    try:
        # Verificar se região já existe
        if Regiao.query.filter_by(nome=data['nome']).first():
            return jsonify({'success': False, 'message': 'Região já cadastrada'}), 400
        
        regiao = Regiao(
            nome=data['nome'],
            ativo=data.get('ativo', True)
        )
        
        db.session.add(regiao)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Região cadastrada com sucesso',
            'regiao': regiao.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro : {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/regioes/<int:id>', methods=['PUT'])
@login_required
def api_regioes_atualizar(id):
    regiao = Regiao.query.get_or_404(id)
    data = request.get_json()
    
    try:
        # Verificar se está tentando mudar nome para um já existente
        if data.get('nome') and data['nome'] != regiao.nome:
            if Regiao.query.filter_by(nome=data['nome']).first():
                return jsonify({'success': False, 'message': 'Região já cadastrada'}), 400
        
        regiao.nome = data.get('nome', regiao.nome)
        regiao.ativo = data.get('ativo', regiao.ativo)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Região atualizada com sucesso',
            'regiao': regiao.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro : {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/regioes/<int:id>', methods=['DELETE'])
@login_required
def api_regioes_deletar(id):
    regiao = Regiao.query.get_or_404(id)
    
    try:
        # Verificar se há endereços vinculados
        if len(regiao.enderecos) > 0:
            return jsonify({
                'success': False, 
                'message': 'Não é possível excluir região com endereços vinculados'
            }), 400
        
        db.session.delete(regiao)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Região excluída com sucesso'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao excluir região: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

# API Dashboard - Estatísticas filtradas por mês/ano
@app.route('/api/dashboard')
@login_required
def api_dashboard():
    mes = request.args.get('mes')  # formato YYYY-MM
    from datetime import datetime
    if mes:
        try:
            ano, mes_num = mes.split('-')
            ano = int(ano)
            mes_num = int(mes_num)
        except Exception:
            now = datetime.now()
            ano = now.year
            mes_num = now.month
    else:
        now = datetime.now()
        ano = now.year
        mes_num = now.month

    # Usuários e clientes ativos (não dependem do mês)
    usuarios_ativos = User.query.filter_by(ativo=True).count() if hasattr(User, 'ativo') else User.query.count()
    clientes_ativos = Cliente.query.filter_by(ativo=True).count()

    # Atendimentos
    atendimentos_mes = Atendimento.query.filter(
        db.extract('month', Atendimento.data_atendimento) == mes_num,
        db.extract('year', Atendimento.data_atendimento) == ano
    ).count()

    # Ocorrências Sistêmicas
    ocorrencias_sistemicas_mes = OcorrenciaSistemica.query.filter(
        db.extract('month', OcorrenciaSistemica.data_ocorrencia) == mes_num,
        db.extract('year', OcorrenciaSistemica.data_ocorrencia) == ano
    ).count()

    # Atendimentos Pronta Resposta
    atendimentos_pr_mes = AtendimentoProntaResposta.query.filter(
        db.extract('month', AtendimentoProntaResposta.data_atendimento) == mes_num,
        db.extract('year', AtendimentoProntaResposta.data_atendimento) == ano
    ).count()

    # Resumo de atendimentos por cliente
    atendimentos = Atendimento.query.filter(
        db.extract('month', Atendimento.data_atendimento) == mes_num,
        db.extract('year', Atendimento.data_atendimento) == ano
    ).all()
    from collections import defaultdict
    clientes_stats = defaultdict(lambda: {'nome': '', 'qtd': 0, 'total_tempo': 0, 'tempos': []})
    for a in atendimentos:
        cliente = a.endereco.cliente if a.endereco and a.endereco.cliente else None
        if cliente:
            cid = cliente.id
            clientes_stats[cid]['nome'] = cliente.nome
            clientes_stats[cid]['qtd'] += 1
            tempo = a.calcular_tempo_atendimento() if hasattr(a, 'calcular_tempo_atendimento') else 0
            clientes_stats[cid]['total_tempo'] += tempo
            clientes_stats[cid]['tempos'].append(tempo)
    resumo_clientes = []
    for cid, stats in clientes_stats.items():
        media_tempo = int(stats['total_tempo'] / stats['qtd']) if stats['qtd'] > 0 else 0
        maior_tempo = max(stats['tempos']) if stats['tempos'] else 0
        resumo_clientes.append({
            'nome': stats['nome'],
            'qtd': stats['qtd'],
            'total_tempo': stats['total_tempo'],
            'media_tempo': media_tempo,
            'maior_tempo': maior_tempo
        })

    # Resumo de Ocorrências Sistêmicas por status
    from sqlalchemy import func
    resumo_ocorrencias_query = db.session.query(
        OcorrenciaSistemica.status,
        func.count(OcorrenciaSistemica.id)
    ).filter(
        db.extract('month', OcorrenciaSistemica.data_ocorrencia) == mes_num,
        db.extract('year', OcorrenciaSistemica.data_ocorrencia) == ano
    ).group_by(OcorrenciaSistemica.status).all()

    resumo_ocorrencias = [
        {'status': status, 'total': total}
        for status, total in resumo_ocorrencias_query
    ]
        
    # Resumo de Portarias Remotas
    portarias_remotas = Endereco.query.filter_by(
        portaria_remota=True, 
        ativo=True
    ).all()

    portarias_remotas_count = len(portarias_remotas)
    total_cameras_portarias = 0
    portarias_detalhes = []

    for endereco in portarias_remotas:
        # Supondo que qtd_cameras_rondas representa o total de câmeras
        qtd_cameras = endereco.qtd_cameras_rondas or 0
        total_cameras_portarias += qtd_cameras
        
        portarias_detalhes.append({
            'cliente_nome': endereco.cliente.nome if endereco.cliente else 'N/A',
            'endereco': f"{endereco.logradouro}, {endereco.numero} - {endereco.bairro}",
            'qtd_cameras': qtd_cameras,
            'rondas_virtuais': endereco.possui_rondas_virtuais
        })

    return jsonify({
        'usuarios_ativos': usuarios_ativos,
        'clientes_ativos': clientes_ativos,
        'atendimentos_mes': atendimentos_mes,
        'ocorrencias_sistemicas_mes': ocorrencias_sistemicas_mes,
        'atendimentos_pr_mes': atendimentos_pr_mes,
        'resumo_clientes': resumo_clientes,
        'resumo_ocorrencias': resumo_ocorrencias,
        'portarias_remotas': portarias_remotas_count,
        'total_cameras_portarias': total_cameras_portarias,
        'portarias_detalhes': portarias_detalhes
    })

# Inicializar banco de dados
def init_db():
    with app.app_context():
        # Popular regiões iniciais se não existirem
        def popular_regioes_iniciais():
            """Popula as regiões iniciais se não existirem"""
            regioes_padrao = ['Norte', 'Sul', 'Leste', 'Oeste', 'Centro']
            
            for nome_regiao in regioes_padrao:
                if not Regiao.query.filter_by(nome=nome_regiao).first():
                    regiao = Regiao(nome=nome_regiao, ativo=True)
                    db.session.add(regiao)
            
            db.session.commit()
            print('✅ Regiões padrão criadas')
                    
        db.create_all()
        # Criar usuário admin padrão se não existir
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='admin@example.com')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print('✅ Usuário admin criado: admin/admin123')

        popular_regioes_iniciais()
        print('✅ Banco de dados inicializado')




if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)