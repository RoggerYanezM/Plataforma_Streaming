from datetime import datetime, timedelta
import os
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = 'clave_secreta_super_segura_streaming'

# Configuración de base de datos dinámica (PostgreSQL en Railway o SQLite local)
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = (
    database_url or 'sqlite:///streaming_gestor.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


class StreamingAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    screens_total = db.Column(db.Integer, nullable=False)
    screens_available = db.Column(db.Integer, nullable=False)
    expiry_date = db.Column(db.String(20), nullable=False)
    cost_price = db.Column(db.Float, nullable=False)


class ClientSale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    platform = db.Column(db.String(50), nullable=False)
    sale_price = db.Column(db.Float, nullable=False)
    expiry_sale = db.Column(db.String(20), nullable=False)
    screens_count = db.Column(db.Integer, default=1, nullable=False)


class Withdrawal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200), nullable=False)
    date = db.Column(db.String(20), nullable=False)


with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        hashed_password = generate_password_hash('yul1415341620$')
        admin_user = User(username='admin', password=hashed_password)
        db.session.add(admin_user)
        db.session.commit()


@app.route('/')
def home():
    session.clear()  # Borra la sesión al entrar al enlace principal
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_input = request.form['username']
        pass_input = request.form['password']
        user = User.query.filter_by(username=user_input).first()

        if user and check_password_hash(user.password, pass_input):
            session['user'] = user_input
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
            return render_template('login.html')

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    # OPCIÓN A: Validar obligatoriamente si existe sesión activa
    if 'user' not in session:
        return redirect(url_for('login'))

    active_tab = request.args.get('tab', 'overview')

    accounts = StreamingAccount.query.all()
    sales = ClientSale.query.all()
    withdrawals = Withdrawal.query.all()

    # Calcular métricas financieras básicas
    total_sales = sum(s.sale_price for s in sales)
    total_costs = sum(a.cost_price for a in accounts)
    total_withdrawals = sum(w.amount for w in withdrawals)
    net_profit = total_sales - total_costs - total_withdrawals

    return render_template(
        'dashboard.html',
        active_tab=active_tab,
        accounts=accounts,
        sales=sales,
        withdrawals=withdrawals,
        total_sales=total_sales,
        total_costs=total_costs,
        total_withdrawals=total_withdrawals,
        net_profit=net_profit,
    )


@app.route('/logout')
def logout():
    # OPCIÓN B: Limpiar por completo la sesión para borrar credenciales almacenadas
    session.clear()
    return redirect(url_for('login'))


@app.route('/add_account', methods=['POST'])
def add_account():
    if 'user' not in session:
        return redirect(url_for('login'))
    new_acc = StreamingAccount(
        platform=request.form['platform'],
        email=request.form['email'],
        password=request.form['password'],
        screens_total=int(request.form['screens_total']),
        screens_available=int(request.form['screens_total']),
        expiry_date=request.form['expiry_date'],
        cost_price=float(request.form['cost_price']),
    )
    db.session.add(new_acc)
    db.session.commit()
    return redirect(url_for('dashboard', tab='accounts'))


@app.route('/add_sale', methods=['POST'])
def add_sale():
    if 'user' not in session:
        return redirect(url_for('login'))

    screens = int(request.form.get('screens_count', 1))
    new_sale = ClientSale(
        client_name=request.form['client_name'],
        phone=request.form['phone'],
        platform=request.form['platform'],
        sale_price=float(request.form['sale_price']),
        expiry_sale=request.form['expiry_sale'],
        screens_count=screens,
    )
    db.session.add(new_sale)
    db.session.commit()
    return redirect(url_for('dashboard', tab='sales'))


@app.route('/delete_sale/<int:id>')
def delete_sale(id):
    if 'user' not in session:
        return redirect(url_for('login'))
    sale = ClientSale.query.get_or_404(id)
    db.session.delete(sale)
    db.session.commit()
    return redirect(url_for('dashboard', tab='sales'))


@app.route('/renew_sale/<int:id>')
def renew_sale(id):
    if 'user' not in session:
        return redirect(url_for('login'))
    sale = ClientSale.query.get_or_404(id)
    try:
        current_expiry = datetime.strptime(sale.expiry_sale, '%Y-%m-%d').date()
        base_date = max(current_expiry, datetime.now().date())
        new_expiry = base_date + timedelta(days=30)
        sale.expiry_sale = new_expiry.strftime('%Y-%m-%d')
        db.session.commit()
    except:
        pass
    return redirect(url_for('dashboard', tab='sales'))


@app.route('/add_withdrawal', methods=['POST'])
def add_withdrawal():
    if 'user' not in session:
        return redirect(url_for('login'))
    new_w = Withdrawal(
        amount=float(request.form['amount']),
        description=request.form['description'],
        date=request.form['date'],
    )
    db.session.add(new_w)
    db.session.commit()
    return redirect(url_for('dashboard', tab='finances'))


if __name__ == '__main__':
    app.run(debug=True)