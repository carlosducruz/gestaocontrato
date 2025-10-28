from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://appuser:apppass123@localhost:5432/appdb')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Models
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


class Endereco(db.Model):
    __tablename__ = 'enderecos'
    id = db.Column(db.Integer, primary_key=True)
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
    
    def to_dict(self):
        return {
            'id': self.id,
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
            'endereco_completo': f"{self.logradouro}, {self.numero} - {self.bairro}, {self.cidade}/{self.estado}"
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

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes - Páginas
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
    return render_template('home.html', user=current_user)

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
    return render_template('clientes_enderecos.html', user=current_user, cliente=cliente)

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
    return jsonify({
        'success': True,
        'funcionarios': [f.to_dict() for f in funcionarios]
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
    data = request.get_json()
    
    try:
        falta = Falta(
            funcionario_id=id,
            data_falta=datetime.strptime(data['data_falta'], '%Y-%m-%d').date(),
            atestada=data.get('atestada', False),
            motivo=data.get('motivo'),
            arquivo_atestado=data.get('arquivo_atestado')
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
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/funcionarios/<int:funcionario_id>/faltas/<int:falta_id>', methods=['PUT'])
@login_required
def api_faltas_atualizar(funcionario_id, falta_id):
    falta = Falta.query.filter_by(id=falta_id, funcionario_id=funcionario_id).first_or_404()
    data = request.get_json()
    
    try:
        falta.data_falta = datetime.strptime(data['data_falta'], '%Y-%m-%d').date()
        falta.atestada = data.get('atestada', False)
        falta.motivo = data.get('motivo')
        if data.get('arquivo_atestado'):
            falta.arquivo_atestado = data['arquivo_atestado']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Falta atualizada com sucesso',
            'falta': falta.to_dict()
        })
    except Exception as e:
        db.session.rollback()
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
            ativo=data.get('ativo', True)
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
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/clientes/<int:cliente_id>/enderecos/<int:endereco_id>', methods=['PUT'])
@login_required
def api_enderecos_atualizar(cliente_id, endereco_id):
    endereco = Endereco.query.filter_by(id=endereco_id, cliente_id=cliente_id).first_or_404()
    data = request.get_json()
    
    try:
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
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Endereço atualizado com sucesso',
            'endereco': endereco.to_dict()
        })
    except Exception as e:
        db.session.rollback()
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
        return jsonify({'success': False, 'message': str(e)}), 500

# Inicializar banco de dados
def init_db():
    with app.app_context():
        db.create_all()
        # Criar usuário admin padrão se não existir
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='admin@example.com')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print('✅ Usuário admin criado: admin/admin123')

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)