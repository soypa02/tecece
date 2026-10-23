from flask import Flask,g,render_template,request,redirect,url_for,flash,session,send_from_directory
from datetime import date
from models.classEmpresa import Empresa
from models.Database import Database
UPLOAD_FOLDER=r"C:\Users\soypa\OneDrive\Documentos\soso\TCC\TCC_Conecta_CIESP\uploads"

#Fazer contador do dia, de 3 em 3 meses e por ano

app = Flask(__name__)  

app.secret_key="ApexD3v"

@app.teardown_appcontext
def close_connection(exception):
    db_conn = g.pop('db',None)
    if db_conn is not None:
        db_conn.close()
        print("CONEXÃO ENCERRADA COM SUCESSO!!")

banco = Database()

# logica para cadastro 

@app.route("/")
def index():
    
    banco.execute_non_query("""
   CREATE TABLE empresas (
    id INT AUTO_INCREMENT PRIMARY KEY,        
    isoc VARCHAR(50) UNIQUE DEFAULT NULL,    
    razao_social VARCHAR(255) NOT NULL,       
    cnpj VARCHAR(20) UNIQUE NOT NULL,   
    imagem VARCHAR(255) DEFAULT NULL,     
    nome VARCHAR(255) DEFAULT NULL,
    descricao VARCHAR(255) DEFAULT NULL,
    site_link VARCHAR(255) DEFAULT NULL,
    drmd VARCHAR(100) DEFAULT 'Rio Claro',    
    area_atuacao VARCHAR(100) NOT NULL,       
    status_associacao BOOLEAN DEFAULT FALSE,
    senha INT VARCHAR(255)    
);
""")

    
    return render_template('./index.html')

#renderiza a tela de cadastro de empresas
@app.route("/cadastro")
def cadastro():
    return render_template("./cadastro.html")

#logica para cadastro do login das empresas
@app.route("/cadastrar",methods=["POST"])
def cadastrar():
    #O certo seria criar a classe usuario e instanciar o objetos
    #Porem como a classe é preguiçosa criamos 2 variaveis locais
    login = request.form["login"]
    senha= request.form["senha"]
    
    banco.execute_non_query(r"""
    insert into Empresas(razao_social,senha) values (?,?)""",login,senha)

    flash("CONTA CRIADA COM SUCESSO!")
    return redirect(url_for('index'))


#logica para login de empresas
@app.route("/entrar",methods=["POST"])
def entrar():
    login = request.form["login"]
    senha = request.form["senha"]
    
    dados = banco.execute_query(r"""
    SELECT * FROM Empresas WHERE razao_social=? and senha =?""",login,senha)

    if dados:
        session['login']=login
        session['senha']=senha
        flash("LOGIN EFETUADO COM SUCESSO!")
        return redirect(url_for("catalogo"))
    else:
        flash("LOGIN OU SENHA INCORRETOS")
        return redirect(url_for("index"))

#renderiza a tela de catalogo de empresas
@app.route("/catalogo")
def portal():
    # Pega todas as empresas cadastradas no banco
    empresas = Empresa.query.all()
    return render_template('catalogo.html', empresas=empresas)

#renderiza tela para cadastrar nova empresa
@app.route("/cadastrar_nova_empresa")
def cadastrar_nova_empresa():
    return render_template('cadastro.html')

@app.route("/post_empresa",methods=["POST"])
def post_empresa():
    #todos os dados do formulario de cadastro de empresa são capturados e armazenados em um objeto da classe Empresa
    obj = Empresa()
    obj.razao_social = request.form["razao_social"]
    obj.area_atuacao = request.form["area_atuacao"]
    obj.status_associacao = request.form.get("status_associacao") == "on" #no html, colocar botao tipo "ligar e desligar" e pegar o valor e converter para booleano
    obj.drmd = request.form["drmd"] #deixar pre preenchido com "Rio Claro" e deixar o usuario alterar se quiser
    obj.senha = request.form["senha"]
    obj.isoc = request.form["isoc"]
    obj.cnpj = request.form["cnpj"]

    obj.imagem=""
    
    #Capturando o arquivo de imagem do produto
    arquivo= request.files["imagem"]
    
    if arquivo.filename!="":
        nomearquivo=f"{arquivo.filename}" 
        obj.imagem= UPLOAD_FOLDER+f"\{nomearquivo}"
        arquivo.save(obj.imagem)
    
    
    banco.execute_non_query(r"""
    INSERT INTO Produtos(nome,preco,pastaimagem,nomeimagem) values(?,?,?,?)"""
    ,obj.produto,obj.preco,UPLOAD_FOLDER,nomearquivo)
    
    return redirect(url_for('catalogo'))

  # Busca a empresa pelo ID ou retorna 404 se não achar
  #apenas o perfil da empresa é renderizado, sem a parte de estatisticas de visitas
@app.route('/empresa/<int:id>')
def perfil_empresa(id):
  # Busca a empresa pelo ID ou retorna 404 se não achar
  empresa = Empresa.query.get_or_404(id)
  return render_template('perfil_empresa.html', empresa=empresa)

#gera o relatorio da empresa, com estatisticas de visitas, vendas, etc.
@app.route("/perfil_empresa/relatorio/<int:id>")
def telaempresa(id): 
    hoje = date.today().isoformat() # Pega a data de hoje no formato YYYY-MM-DD
    ano_atual = hoje[:4]            # Extrai apenas o ano atual (ex: '2026')

    # 1. Registra ou incrementa a visita do dia atual
    banco.execute_non_query("""
        INSERT INTO Visitas (empresa_id, data_acesso, quantidade)
        VALUES (?, ?, 1)
        ON CONFLICT(empresa_id, data_acesso) 
        DO UPDATE SET quantidade = quantidade + 1
    """, id, hoje)

    # --- CONTADOR 1: Visitas de Hoje ---
    res_hoje = banco.execute_query("""
        SELECT quantidade FROM Visitas WHERE empresa_id = ? AND data_acesso = ?
    """, id, hoje)
    visitas_hoje = res_hoje[0][0] if res_hoje else 0

    # --- CONTADOR 2: Visitas nos últimos 3 meses (trimestre móvel) ---
    # O SQLite entende o modificador '-3 months' para voltar 3 meses a partir de 'hoje'
    res_3meses = banco.execute_query("""
        SELECT SUM(quantidade) FROM Visitas 
        WHERE empresa_id = ? AND data_acesso >= date(?, '-3 months')
    """, id, hoje)
    visitas_3meses = res_3meses[0][0] if res_3meses and res_3meses[0][0] else 0

    # --- CONTADOR 3: Total de visitas no ano atual ---
    # Filtra tudo a partir do dia 1º de janeiro do ano corrente
    res_ano = banco.execute_query("""
        SELECT SUM(quantidade) FROM Visitas 
        WHERE empresa_id = ? AND data_acesso >= ?
    """, id, f"{ano_atual}-01-01")
    visitas_ano = res_ano[0][0] if res_ano and res_ano[0][0] else 0

    # Busca os dados cadastrais da empresa
    dados = banco.execute_query(""" 
        SELECT * FROM Empresas WHERE ISOC = ?
    """, id)

    if dados:
        empresa_encontrada = dados[0]
        return render_template(
            'perfil_empresa.html', 
            empresa=empresa_encontrada,
            visitas_hoje=visitas_hoje,
            visitas_3meses=visitas_3meses,
            visitas_ano=visitas_ano

        )
    else:
        flash("Empresa não encontrada!")
        return redirect(url_for('perfil_empresa'))





