from flask import Flask, render_template, request, flash, redirect, url_for, session, send_from_directory, send_file
from flask_bcrypt import generate_password_hash, check_password_hash
import fdb
from fpdf import FPDF

app = Flask(__name__)
app.secret_key = 'qualquercoisa'

# Configurações do banco de dados
host = 'localhost'
database = r'C:\Users\Aluno\Desktop\BANCO\BANCO.fdb'
user = 'sysdba'
password = 'sysdba'

con = fdb.connect(host=host, database=database, user=user, password=password)

# Página inicial
@app.route('/')
def index():
    return render_template('index.html')

# Listagem de livros
@app.route('/livro')
def livro():
    cursor = con.cursor()
    cursor.execute("SELECT ID_LIVRO, TITULO, AUTOR, ANO_PUBLICACAO FROM LIVRO")
    livros = cursor.fetchall()
    cursor.close()
    return render_template('livros.html', livros=livros)

# Formulário de novo livro
@app.route('/novo')
def novo():
    if "id_usuario" not in session:
        flash('Você precisa estar logado')
        return redirect(url_for('abrirlogin'))
    return render_template('novo.html', titulo="Novo Livro")

# Formulário de novo usuário
@app.route('/novousuario')
def novousuario():
    return render_template('novousuario.html', titulo="Novo Usuário")

# Criação de novo livro
@app.route('/criar', methods=["POST"])
def criar():
    titulo = request.form['titulo']
    autor = request.form['autor']
    ano_publicacao = request.form['ano_publicacao']

    cursor = con.cursor()
    try:
        cursor.execute(
            "INSERT INTO livro (TITULO, AUTOR, ANO_PUBLICACAO) VALUES (?, ?, ?) RETURNING id_livro",
            (titulo, autor, ano_publicacao)
        )
        id_livro = cursor.fetchone()[0]

        if cursor.fetchone():
            flash('Esse livro já está cadastrado.')
            return redirect(url_for('novo'))

        con.commit()

        # Salvar o arquivo de capa
        arquivo = request.files['arquivo']
        arquivo.save(f'uploads/capa{id_livro}.jpg')


        flash('O livro foi cadastrado com sucesso.')
    finally:
        cursor.close()

    return redirect(url_for('livro'))

@app.route('/uploads/<nome_arquivo>')
def imagem(nome_arquivo):
    return send_from_directory('uploads', nome_arquivo)

# Criação de novo usuário
@app.route('/criarusuario', methods=["POST"])
def criarusuario():
    nome = request.form['nome']
    email = request.form['email']
    senha = request.form['senha']
    senha_cripto = generate_password_hash(senha).decode('utf-8')
    cursor = con.cursor()
    try:
        cursor.execute('SELECT 1 FROM USUARIOS WHERE EMAIL = ?', (email,))
        if cursor.fetchone():
            flash('Esse usuário já está cadastrado.')
            return redirect(url_for('novousuario'))

        cursor.execute('INSERT INTO USUARIOS (NOME, EMAIL, SENHA) VALUES (?, ?, ?)',
                       (nome, email, senha_cripto))
        con.commit()
        flash('Usuário cadastrado com sucesso.')
    finally:
        cursor.close()

    return redirect(url_for('usuarios'))

# Edição de livro
@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    if "id_usuario" not in session:
        flash('Você precisa estar logado')
        return redirect(url_for('abrirlogin'))

    cursor = con.cursor()
    cursor.execute("SELECT ID_LIVRO, TITULO, AUTOR, ANO_PUBLICACAO FROM LIVRO WHERE ID_LIVRO = ?", (id,))
    livro = cursor.fetchone()
    cursor.close()

    if not livro:
        flash("Livro não encontrado.")
        return redirect(url_for('livro'))

    if request.method == 'POST':
        titulo = request.form['titulo']
        autor = request.form['autor']
        ano_publicacao = request.form['ano_publicacao']

        cursor = con.cursor()
        cursor.execute("UPDATE LIVRO SET TITULO = ?, AUTOR = ?, ANO_PUBLICACAO = ? WHERE ID_LIVRO = ?",
                       (titulo, autor, ano_publicacao, id))
        con.commit()
        cursor.close()
        flash("Livro atualizado com sucesso.")
        return redirect(url_for('livro'))

    return render_template('editar.html', livro=livro, titulo='Editar Livro')

# Edição de usuário
@app.route('/editarusuario/<int:id>', methods=['GET', 'POST'])
def editarusuario(id):
    cursor = con.cursor()
    cursor.execute("SELECT ID_USUARIO, NOME, EMAIL, SENHA FROM USUARIOS WHERE ID_USUARIO = ?", (id,))
    usuario = cursor.fetchone()
    cursor.close()

    if not usuario:
        flash("Usuário não encontrado.")
        return redirect(url_for('usuarios'))

    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']

        if senha:
            senha_cripto = generate_password_hash(senha).decode('utf-8')
        else:
            senha_cripto = usuario[3]

        cursor = con.cursor()
        cursor.execute("UPDATE USUARIOS SET NOME = ?, EMAIL = ?, SENHA = ? WHERE ID_USUARIO = ?",
                       (nome, email, senha_cripto, id))
        con.commit()
        cursor.close()
        flash("Usuário atualizado com sucesso.")
        return redirect(url_for('usuarios'))

    return render_template('editarusuario.html', usuario=usuario, titulo='Editar Usuário')



# Deletar livro
@app.route('/deletar/<int:id>', methods=['POST'])
def deletar(id):
    if "id_usuario" not in session:
        flash('Você precisa estar logado')
        return redirect(url_for('abrirlogin'))

    cursor = con.cursor()
    cursor.execute("DELETE FROM LIVRO WHERE ID_LIVRO = ?", (id,))
    con.commit()
    cursor.close()
    flash("Livro excluído com sucesso.")
    return redirect(url_for('livro'))

# Gerar PDF
@app.route('/livro/relatorio', methods=['GET'])
def gerar_pdf():
    try:
        cursor = con.cursor()
        cursor.execute("SELECT id_livro, titulo, autor, ano_publicacao FROM livro")
        livros = cursor.fetchall()
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Arial", style='B', size=16)
        pdf.cell(200, 10, "Relatorio de Livros", ln=True, align='C')
        pdf.ln(5)  # Espaço entre o título e a linha
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())  # Linha abaixo do título
        pdf.ln(5)  # Espaço após a linha
        pdf.set_font("Arial", size=12)
        for livro in livros:
            pdf.cell(200, 10, f"ID: {livro[0]} - {livro[1]} - {livro[2]} - {livro[3]}", ln=True)
        contador_livros = len(livros)
        pdf.ln(10)  # Espaço antes do contador
        pdf.set_font("Arial", style='B', size=12)
        pdf.cell(200, 10, f"Total de livros cadastrados: {contador_livros}", ln=True, align='C')
        pdf_path = "relatorio_livros.pdf"
        pdf.output(pdf_path)
        return send_file(pdf_path, as_attachment=True, mimetype='application/pdf')
    finally:
        cursor.close()

# Deletar usuário
@app.route('/deletarusuario/<int:id>', methods=['POST'])
def deletarusuario(id):
    cursor = con.cursor()
    cursor.execute("DELETE FROM USUARIOS WHERE ID_USUARIO = ?", (id,))
    con.commit()
    cursor.close()
    flash("Usuário excluído com sucesso.")
    return redirect(url_for('usuarios'))

# Listagem de usuários
@app.route('/usuarios')
def usuarios():
    cursor = con.cursor()
    cursor.execute("SELECT ID_USUARIO, NOME, EMAIL, SENHA FROM USUARIOS")
    usuarios = cursor.fetchall()
    cursor.close()
    return render_template('usuarios.html', usuarios=usuarios)

# Abrir tela de login
@app.route('/abrirlogin')
def abrirlogin():
    return render_template('login.html')

# Login de usuário
@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    senha = request.form['senha']
    cursor = con.cursor()
    try:
        cursor.execute(
            'SELECT ID_USUARIO, NOME, EMAIL, SENHA FROM USUARIOS WHERE LOWER(EMAIL) = ?',
            (email,)
        )
        usuario = cursor.fetchone()
    finally:
        cursor.close()
    if usuario is None:
        flash("Usuário não encontrado")
        return redirect(url_for('abrirlogin'))
    senha_hash = usuario[3]
    if check_password_hash(senha_hash, senha):
        flash('Login realizado com sucesso.')

        session['id_usuario'] = usuario[0]

        return redirect(url_for('usuarios'))
    else:
        flash('Email ou senha incorretos.')
        return redirect(url_for('abrirlogin'))

@app.route('/logout')
def logout():
    if "id_usuario" not in session:
        flash('Você precisa estar logado')
        return redirect(url_for('abrirlogin'))
    flash('Você saiu com sucesso')
    session.pop("id_usuario", None)
    return redirect(url_for('index'))
# Roda o app
if __name__ == '__main__':
    app.run(debug=True)