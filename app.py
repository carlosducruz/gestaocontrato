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