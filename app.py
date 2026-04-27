# SISTEMA HOSPITALAR COMPLETO - AMBULÂNCIAS (VERSÃO AVANÇADA)
# Login + Dashboard com gráfico + Prioridade + Tempo + Equipe + PDF + App desktop

from flask import Flask, render_template_string, request, redirect, session, send_file
import sqlite3, threading, io, datetime
import webview
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)
app.secret_key = "123456"

# ---------------- BANCO ----------------

def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS ambulancias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        placa TEXT,
        status TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS equipe (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        funcao TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS transferencias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        paciente TEXT,
        origem TEXT,
        destino TEXT,
        ambulancia_id INTEGER,
        prioridade TEXT,
        inicio TEXT,
        fim TEXT,
        status TEXT
    )''')

    # usuário padrão
    c.execute("SELECT * FROM usuarios")
    if not c.fetchone():
        c.execute("INSERT INTO usuarios (username, password) VALUES ('admin','123')")

    # ambulância padrão
    c.execute("SELECT * FROM ambulancias")
    if not c.fetchone():
        c.execute("INSERT INTO ambulancias (placa, status) VALUES ('PRINCIPAL-001','disponivel')")

    conn.commit()
    conn.close()

init_db()

# ---------------- HTML ----------------

BASE_STYLE = """
<style>
body {margin:0;font-family:Arial;background:#0f172a;color:white}
.sidebar {width:230px;height:100vh;background:#1e293b;position:fixed;padding:20px}
.sidebar a {display:block;color:white;margin:15px 0;text-decoration:none;font-size:18px}
.main {margin-left:250px;padding:20px}
.card {background:#1e293b;padding:20px;border-radius:12px;margin:10px;display:inline-block;width:220px;text-align:center}
button{padding:12px;border:none;border-radius:10px;background:#22c55e;color:white;font-size:16px;cursor:pointer}
select,input{padding:10px;margin:10px;border-radius:8px;border:none}
.urgente{background:#ef4444}
.normal{background:#22c55e}
</style>
"""

LOGIN = """
<html><body style='background:#0f172a;color:white;text-align:center;padding-top:100px'>
<h1>🚑 Sistema Hospitalar</h1>
<form method='post'>
<input name='username' placeholder='Usuário'><br>
<input name='password' type='password' placeholder='Senha'><br>
<button>Entrar</button>
</form></body></html>
"""

DASH = BASE_STYLE + """
<div class='sidebar'>
<h2>🚑 Menu</h2>
<a href='/dashboard'>📊 Dashboard</a>
<a href='/nova'>➕ Nova</a>
<a href='/equipe'>👥 Equipe</a>
<a href='/relatorio'>📄 Relatório</a>
<a href='/logout'>🚪 Sair</a>
</div>

<div class='main'>
<h1>📊 Dashboard</h1>

<canvas id='grafico' width='400' height='150'></canvas>

{% for a in ambulancias %}
<div class='card'>
<h3>🚑 {{a[1]}}</h3>
<p>Status: {{a[2]}}</p>
</div>
{% endfor %}

<script src='https://cdn.jsdelivr.net/npm/chart.js'></script>
<script>
var ctx = document.getElementById('grafico');
new Chart(ctx, {
    type: 'bar',
    data: {
        labels: ['Disponível','Ocupada'],
        datasets: [{ data: [{{disp}}, {{ocup}}] }]
    }
});
</script>

</div>
"""

NOVA = BASE_STYLE + """
<div class='sidebar'>
<h2>🚑 Menu</h2>
<a href='/dashboard'>📊 Dashboard</a>
<a href='/nova'>➕ Nova</a>
<a href='/equipe'>👥 Equipe</a>
<a href='/relatorio'>📄 Relatório</a>
</div>

<div class='main'>
<h1>➕ Nova Transferência</h1>
<form method='post'>
<input name='paciente' placeholder='Paciente'><br>
<input name='origem' placeholder='Origem'><br>
<input name='destino' placeholder='Destino'><br>

<select name='ambulancia_id'>
{% for a in ambulancias %}
<option value='{{a[0]}}'>{{a[1]}} - {{a[2]}}</option>
{% endfor %}
</select><br>

<select name='prioridade'>
<option value='normal'>Normal</option>
<option value='urgente'>Urgente</option>
</select><br>

<button>Registrar</button>
</form>
</div>
"""

EQUIPE = BASE_STYLE + """
<div class='sidebar'>
<h2>🚑 Menu</h2>
<a href='/dashboard'>📊 Dashboard</a>
<a href='/nova'>➕ Nova</a>
<a href='/equipe'>👥 Equipe</a>
<a href='/relatorio'>📄 Relatório</a>
</div>

<div class='main'>
<h1>👥 Equipe</h1>
<form method='post'>
<input name='nome' placeholder='Nome'>
<select name='funcao'>
<option>Motorista</option>
<option>Enfermeiro</option>
</select>
<button>Cadastrar</button>
</form>

{% for e in equipe %}
<div class='card'>{{e[1]}} - {{e[2]}}</div>
{% endfor %}
</div>
"""

# ---------------- ROTAS ----------------

@app.route('/', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM usuarios WHERE username=? AND password=?",(u,p))
        if c.fetchone():
            session['user']=u
            return redirect('/dashboard')
    return LOGIN

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/')
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM ambulancias")
    ambulancias = c.fetchall()
    c.execute("SELECT COUNT(*) FROM ambulancias WHERE status='disponivel'")
    disp = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM ambulancias WHERE status='ocupada'")
    ocup = c.fetchone()[0]
    conn.close()
    return render_template_string(DASH, ambulancias=ambulancias, disp=disp, ocup=ocup)

@app.route('/nova', methods=['GET','POST'])
def nova():
    if 'user' not in session: return redirect('/')
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    if request.method == 'POST':
        now = datetime.datetime.now().strftime('%H:%M:%S')
        c.execute("INSERT INTO transferencias (paciente,origem,destino,ambulancia_id,prioridade,inicio,status) VALUES (?,?,?,?,?,?,'em andamento')",
                  (request.form['paciente'],request.form['origem'],request.form['destino'],request.form['ambulancia_id'],request.form['prioridade'],now))
        c.execute("UPDATE ambulancias SET status='ocupada' WHERE id=?",(request.form['ambulancia_id'],))
        conn.commit()

    c.execute("SELECT * FROM ambulancias")
    amb = c.fetchall()
    conn.close()
    return render_template_string(NOVA, ambulancias=amb)

@app.route('/equipe', methods=['GET','POST'])
def equipe():
    if 'user' not in session: return redirect('/')
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    if request.method == 'POST':
        c.execute("INSERT INTO equipe (nome,funcao) VALUES (?,?)",
                  (request.form['nome'],request.form['funcao']))
        conn.commit()

    c.execute("SELECT * FROM equipe")
    dados = c.fetchall()
    conn.close()
    return render_template_string(EQUIPE, equipe=dados)

@app.route('/relatorio')
def relatorio():
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT paciente, origem, destino, prioridade FROM transferencias")
    data = c.fetchall()
    conn.close()

    elements = [Paragraph("Relatório de Transferências", styles['Title']), Spacer(1,12)]
    table = Table([["Paciente","Origem","Destino","Prioridade"]] + data)
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.grey)]))
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="relatorio.pdf")

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ---------------- APP DESKTOP ----------------

import os

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)