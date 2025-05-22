import tkinter as tk
from tkinter import messagebox, ttk, simpledialog, filedialog
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import sqlite3  
from sqlite3 import IntegrityError

conn = sqlite3.connect("sistema.db")
cursor = conn.cursor()


cursor.execute("""
CREATE TABLE IF NOT EXISTS produtos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT UNIQUE NOT NULL,
    quantidade REAL NOT NULL,
    preco REAL NOT NULL
)
""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT UNIQUE NOT NULL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS compras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER NOT NULL,
    produto_id INTEGER NOT NULL,
    quantidade REAL NOT NULL,
    forma_pagamento TEXT NOT NULL,
    status TEXT NOT NULL,
    FOREIGN KEY(cliente_id) REFERENCES clientes(id),
    FOREIGN KEY(produto_id) REFERENCES produtos(id)
)
""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS compras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER NOT NULL,
    produto_id INTEGER NOT NULL,
    quantidade REAL NOT NULL,
    forma_pagamento TEXT NOT NULL,
    status TEXT NOT NULL,
    FOREIGN KEY(cliente_id) REFERENCES clientes(id),
    FOREIGN KEY(produto_id) REFERENCES produtos(id)
)
""")

try:
    cursor.execute(
        "ALTER TABLE compras ADD COLUMN data TEXT NOT NULL DEFAULT (date('now'))"
    )
except sqlite3.OperationalError:
    pass

conn.commit()

cursor.execute("SELECT nome, quantidade, preco FROM produtos")
estoque = [
    {"nome": row[0], "quantidade": row[1], "preco": row[2]}
    for row in cursor.fetchall()
]

clientes = {}
cursor.execute("SELECT id, nome FROM clientes")
for client_id, nome in cursor.fetchall():
    clientes[nome] = {"id": client_id, "compras": []}

cursor.execute("""
    SELECT c.nome, p.nome, co.quantidade, co.forma_pagamento, co.status
    FROM compras co
    JOIN clientes c ON co.cliente_id = c.id
    JOIN produtos p ON co.produto_id = p.id
""")
for nome_cliente, produto, qtd, pag, stat in cursor.fetchall():
    clientes[nome_cliente]["compras"].append({
        "produto": produto,
        "quantidade": qtd,
        "forma_pagamento": pag,
        "status": stat
    })
    
next_cliente_id = 1
tree_clientes = None 

# FUNÇÕES DE GESTÃO DO ESTOQUE
def adicionar_produto(entrada_nome, entrada_quantidade, entrada_preco, tabela, combo_produto):
    nome = entrada_nome.get().strip()
    quantidade = entrada_quantidade.get().strip()
    preco = entrada_preco.get().strip()

    try:
        qtd = float(quantidade)
        preco_float = float(preco)

        if not (nome and qtd >= 0 and preco_float >= 0):
            raise ValueError
        try:
            cursor.execute(
                "INSERT INTO produtos (nome, quantidade, preco) VALUES (?, ?, ?)",
                (nome, qtd, preco_float)
            )
        except IntegrityError:
            cursor.execute(
                "UPDATE produtos SET quantidade = quantidade + ?, preco = ? WHERE nome = ?",
                (qtd, preco_float, nome)
            )
        conn.commit()

        prod = next((p for p in estoque if p["nome"] == nome), None)
        if prod:
            prod["quantidade"] += qtd
            prod["preco"] = preco_float
        else:
            estoque.append({"nome": nome, "quantidade": qtd, "preco": preco_float})

        atualizar_tabela(tabela)
        atualizar_dashboard()
        combo_produto["values"] = [p["nome"] for p in estoque]
        entrada_nome.delete(0, tk.END)
        entrada_quantidade.delete(0, tk.END)
        entrada_preco.delete(0, tk.END)

        messagebox.showinfo("Sucesso", f"Produto '{nome}' adicionado/atualizado com sucesso!")

    except ValueError:
        messagebox.showerror("Erro", "Preencha os campos corretamente com valores numéricos positivos!")
        
def editar_produto(tabela):
    selecionados = tabela.selection()
    if not selecionados:
        return messagebox.showerror("Erro", "Selecione um produto para editar!")
    item = tabela.item(selecionados[0])
    nome_antigo = item["values"][0]
    for produto in estoque:
        if produto["nome"] == nome_antigo:
            win = tk.Toplevel()
            win.title(f"Editar Produto: {nome_antigo}")
            win.geometry("300x200") 
            tk.Label(win, text="Nome:").grid(row=0, column=0, padx=5, pady=5)
            ent_nome = ttk.Entry(win); ent_nome.insert(0, produto["nome"]); ent_nome.grid(row=0, column=1)

            tk.Label(win, text="Quantidade:").grid(row=1, column=0, padx=5, pady=5)
            ent_qtd = ttk.Entry(win); ent_qtd.insert(0, produto["quantidade"]); ent_qtd.grid(row=1, column=1)

            tk.Label(win, text="Preço:").grid(row=2, column=0, padx=5, pady=5)
            ent_pre = ttk.Entry(win); ent_pre.insert(0, produto["preco"]); ent_pre.grid(row=2, column=1)

            def salvar():
                n = ent_nome.get().strip()
                q = ent_qtd.get().strip()
                p = ent_pre.get().strip()
                if n and q.replace('.', '',1).isdigit() and p.replace('.', '',1).isdigit():
                    cursor.execute(
                        "UPDATE produtos SET nome = ?, quantidade = ?, preco = ? WHERE nome = ?",
                        (n, float(q), float(p), nome_antigo)
                    )
                    conn.commit()
                    produto.update({"nome": n, "quantidade": float(q), "preco": float(p)})

                    atualizar_tabela(tabela)
                    atualizar_dashboard()
                    win.destroy()
                    messagebox.showinfo("Sucesso", "Produto atualizado!")
                else:
                    messagebox.showerror("Erro", "Dados inválidos!")
            ttk.Button(win, text="Salvar", command=salvar).grid(row=4, column=0, columnspan=2, pady=10)
            return


def atualizar_tabela(tabela):
    for item in tabela.get_children():
        tabela.delete(item)
    for produto in estoque:
        tabela.insert(
            "",
            "end",
            values=(
                produto["nome"],
                produto["quantidade"],
                f"R${produto['preco']:.2f}"
            )
        )


def pesquisar_produto(entrada_pesquisa, tabela):
    termo = entrada_pesquisa.get().lower().strip()
    resultados = [produto for produto in estoque if termo in produto["nome"].lower()]
    for item in tabela.get_children():
        tabela.delete(item)
    for produto in resultados:
        tabela.insert("", "end", values=(produto["nome"], produto["quantidade"], f"R${produto['preco']:.2f}"))

def limpar_pesquisa(entrada_pesquisa, tabela):
    entrada_pesquisa.delete(0, tk.END)
    atualizar_tabela(tabela)

def salvar_estoque_em_arquivo():
    arquivo = filedialog.asksaveasfilename(defaultextension=".txt",
                                           filetypes=[("Arquivo de Texto", "*.txt")],
                                           title="Salvar Estoque")
    if arquivo:
        try:
            with open(arquivo, "w") as f:
                for produto in estoque:
                    f.write(f"{produto['nome']},{produto['quantidade']},{produto['preco']}\n")
            messagebox.showinfo("Sucesso", f"Estoque salvo em '{arquivo}'!")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar estoque: {e}")
            
# FUNÇÕES DO DASHBOARD
def atualizar_dashboard():
    total_produtos = len(estoque)
    total_valor = sum(produto["quantidade"] * produto["preco"] for produto in estoque)
    valor_medio = total_valor / total_produtos if total_produtos > 0 else 0

    lbl_total_produtos.config(text=f"Total de Produtos: {total_produtos}")
    lbl_total_valor.config(text=f"Valor Total: R${total_valor:.2f}")
    lbl_valor_medio.config(text=f"Valor Médio: R${valor_medio:.2f}")

    nomes = [produto["nome"] for produto in estoque]
    quantidades = [produto["quantidade"] for produto in estoque]
    ax.clear()
    ax.bar(nomes, quantidades)
    ax.set_title("Quantidade por Produto")
    ax.set_ylabel("Quantidade")
    ax.tick_params(axis='x', rotation=45)
    ax.figure.tight_layout()

    canvas.draw()

# FUNÇÕES DE CLIENTES
def atualizar_tabela_clientes(tree):
    for item in tree.get_children():
        tree.delete(item)
    for nome, dados in clientes.items():
        cid = dados.get("id", "?")
        total = sum(
            c["quantidade"] * next((p["preco"] for p in estoque if p["nome"] == c["produto"]), 0)
            for c in dados["compras"]
        )
        pendente = any(c["status"] == "Pendente" for c in dados["compras"])
        tag = "pendente" if pendente else ""
        tree.insert("", "end",
                    values=(cid, nome, f"R${total:.2f}"),
                    tags=(tag,))

def cadastrar_cliente(nome, produto, quantidade, pagamento, status, tree):
    global next_cliente_id
    if not all([nome, produto, quantidade, pagamento, status]):
        return messagebox.showwarning("Aviso", "Preencha todos os campos.")
    try:
        qtd = float(quantidade)
    except ValueError:
        return messagebox.showerror("Erro", "Quantidade deve ser um número (ex: 1.5).")
    
    prod = next((p for p in estoque if p["nome"] == produto), None)
    if not prod:
        return messagebox.showerror("Erro", "Produto não encontrado no estoque.")
    if qtd > prod["quantidade"]:
        return messagebox.showerror("Erro", f"Apenas {prod['quantidade']} em estoque.")

    prod["quantidade"] -= qtd
    cursor.execute(
        "UPDATE produtos SET quantidade = ? WHERE nome = ?",
        (prod["quantidade"], produto)
    )

    cursor.execute("SELECT id FROM clientes WHERE nome = ?", (nome,))
    row = cursor.fetchone()
    if row:
        cliente_id = row[0]
    else:
        cursor.execute("INSERT INTO clientes (nome) VALUES (?)", (nome,))
        cliente_id = cursor.lastrowid

    cursor.execute(
        "INSERT INTO compras (cliente_id, produto_id, quantidade, forma_pagamento, status) "
        "VALUES ( ?, "
        "(SELECT id FROM produtos WHERE nome = ?), "
        "?, ?, ?)",
        (cliente_id, produto, qtd, pagamento, status)
    )

    conn.commit()

    if nome not in clientes:
        clientes[nome] = {"id": cliente_id, "compras": []}
    clientes[nome]["compras"].append({
        "produto": produto,
        "quantidade": qtd,
        "forma_pagamento": pagamento,
        "status": status
    })

    atualizar_tabela_clientes(tree)
    atualizar_dashboard()
    messagebox.showinfo("Sucesso", f"Cliente ID {cliente_id} cadastrado e compra registrada!")


def registrar_nova_compra(cliente_nome, notebook, tabela, tree_clientes):

    win = tk.Toplevel()
    win.title(f"Nova Compra - {cliente_nome}")
    win.geometry("400x300")
    win.grab_set() 

    container = ttk.Frame(win, padding=20)
    container.pack(expand=True, fill="both")

    ttk.Label(container, text=f"Registrar nova compra para {cliente_nome}", font=("Arial", 14)).grid(row=0, column=0, columnspan=2, pady=10)
    ttk.Label(container, text="Produto:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
    combo = ttk.Combobox(container, values=[p["nome"] for p in estoque], width=28)
    combo.grid(row=1, column=1, padx=5, pady=5)
    ttk.Label(container, text="Quantidade (Kg):").grid(row=2, column=0, padx=5, pady=5, sticky="e")
    entry_qtd = ttk.Entry(container, width=30)
    entry_qtd.grid(row=2, column=1, padx=5, pady=5)
    ttk.Label(container, text="Forma de Pagamento:").grid(row=3, column=0, padx=5, pady=5, sticky="e")
    combo_pag = ttk.Combobox(container, values=["Cartão", "Dinheiro", "Pix"], width=28)
    combo_pag.grid(row=3, column=1, padx=5, pady=5)
    ttk.Label(container, text="Status de Pagamento:").grid(row=4, column=0, padx=5, pady=5, sticky="e")
    combo_status = ttk.Combobox(container, values=["Pago", "Pendente"], width=28)
    combo_status.grid(row=4, column=1, padx=5, pady=5)

    ttk.Button(container, text="Confirmar Compra",
        command=lambda: registrar_compra(
            cliente_nome,
            combo.get(),
            entry_qtd.get(),
            combo_pag.get(),
            combo_status.get(),
            tabela,
            tree_clientes,
            win
        )
    ).grid(row=5, column=0, columnspan=2, pady=20)

def registrar_compra(cliente_nome, produto, quantidade, forma_pagamento, status_pagamento, tabela, tree_cli, janela):
    try:
        qtd = float(quantidade)
    except ValueError:
        return messagebox.showerror("Erro", "Quantidade deve ser um número (ex: 1.5).")

    prod = next((p for p in estoque if p["nome"] == produto), None)
    if not prod:
        return messagebox.showerror("Erro", "Produto não encontrado.")
    if qtd > prod["quantidade"]:
        return messagebox.showerror("Erro", f"Apenas {prod['quantidade']} em estoque.")
    
    cursor.execute(
        "UPDATE produtos SET quantidade = ? WHERE nome = ?",
        (prod["quantidade"] - qtd, produto)
    )
    conn.commit()

    cursor.execute(
        "INSERT INTO compras (cliente_id, produto_id, quantidade, forma_pagamento, status) "
        "VALUES ((SELECT id FROM clientes WHERE nome = ?), "
        "(SELECT id FROM produtos WHERE nome = ?), ?, ?, ?)",
        (cliente_nome, produto, qtd, forma_pagamento, status_pagamento)
    )
    conn.commit()


    prod["quantidade"] -= qtd
    clientes[cliente_nome]["compras"].append({
        "produto": produto,
        "quantidade": qtd,
        "forma_pagamento": forma_pagamento,
        "status": status_pagamento
    })

    atualizar_tabela_clientes(tree_cli)
    atualizar_tabela(tabela)
    atualizar_dashboard()
    janela.destroy()
    messagebox.showinfo("Sucesso", f"Compra de {produto} ({qtd}) registrada para {cliente_nome}!")

# INTERFACE PRINCIPAL
def abrir_estoque():
    global lbl_total_produtos, lbl_total_valor, lbl_valor_medio, ax, canvas, tree_clientes

    janela = tk.Tk()
    janela.title("Sistema de Estoque Moderno")
    janela.geometry("1100x700")
    janela.configure(bg="#f7f7f7")

    style = ttk.Style(janela)
    style.theme_use('clam')
    style.configure("TNotebook.Tab", font=("Helvetica", 12, "bold"), padding=[10,5])
    style.configure("TButton", font=("Helvetica", 12, "bold"))
    style.configure("TLabel", font=("Helvetica", 12))
    
    notebook = ttk.Notebook(janela)
    notebook.pack(fill='both', expand=True, padx=10, pady=10)

    tab_cadastro = ttk.Frame(notebook)
    notebook.add(tab_cadastro, text="Cadastro")

    frame_cadastro = ttk.Frame(tab_cadastro, padding=20)
    frame_cadastro.pack(fill='both', expand=True)
    frame_esquerda = ttk.Frame(frame_cadastro)
    frame_esquerda.pack(side='left', fill='y', padx=10, pady=10)
    frame_direita = ttk.Frame(frame_cadastro)
    frame_direita.pack(side='right', fill='both', expand=True, padx=10, pady=10)
    ttk.Label(frame_esquerda, text="Cadastro de Produto", font=("Arial", 16, "bold")).grid(row=0, column=0, columnspan=2, pady=10)
    ttk.Label(frame_esquerda, text="Nome do Produto:").grid(row=1, column=0, sticky="e", padx=10, pady=10)
    entrada_nome = ttk.Entry(frame_esquerda, width=30)
    entrada_nome.grid(row=1, column=1, sticky="w", padx=10, pady=10)
    ttk.Label(frame_esquerda, text="Quantidade (Kg):").grid(row=2, column=0, sticky="e", padx=10, pady=10)
    entrada_quantidade = ttk.Entry(frame_esquerda, width=30)
    entrada_quantidade.grid(row=2, column=1, sticky="w", padx=10, pady=10)
    ttk.Label(frame_esquerda, text="Preço:").grid(row=3, column=0, sticky="e", padx=10, pady=10)
    entrada_preco = ttk.Entry(frame_esquerda, width=30)
    entrada_preco.grid(row=3, column=1, sticky="w", padx=10, pady=10)

    btn_add = ttk.Button(
        frame_esquerda,
        text="Adicionar Produto",
        command=lambda: adicionar_produto(
            entrada_nome, entrada_quantidade, entrada_preco, tabela, combo_produto
        )
    )
    btn_add.grid(row=4, column=0, columnspan=2, pady=15)

    ttk.Label(frame_direita, text="Resumo Financeiro por Mês", font=("Arial", 16, "bold")).pack(pady=10)

    cursor.execute("""
        SELECT
            strftime('%Y-%m', co.data) AS mes,
            SUM(CASE WHEN co.status='Pago' THEN co.quantidade * p.preco ELSE 0 END) AS total_recebido,
            SUM(CASE WHEN co.status='Pendente' THEN co.quantidade * p.preco ELSE 0 END) AS total_pendente,
            COUNT(co.id) AS num_compras
        FROM compras co
        JOIN produtos p ON co.produto_id = p.id
        GROUP BY mes
        ORDER BY mes;
    """)
    resultados = cursor.fetchall()

    colunas_resumo = ("Mês", "Total Recebido", "Total Pendente", "Nº Compras")
    tabela_resumo = ttk.Treeview(frame_direita, columns=colunas_resumo, show='headings', height=15)
    for col in colunas_resumo:
        tabela_resumo.heading(col, text=col)
        tabela_resumo.column(col, width=150, anchor="center")
    tabela_resumo.pack(fill='both', expand=True)

    for mes, rec, pen, cnt in resultados:
        tabela_resumo.insert(
            '',
            'end',
            values=(
                mes,
                f"R$ {rec:.2f}",
                f"R$ {pen:.2f}",
                str(cnt)
            )
        )

    tab_consulta = ttk.Frame(notebook)
    notebook.add(tab_consulta, text="Consulta")
    frame_consulta = ttk.Frame(tab_consulta, padding=20)
    frame_consulta.pack(fill='both', expand=True)

    frame_pesquisa = ttk.Frame(frame_consulta)
    frame_pesquisa.pack(fill='x', pady=10)
    ttk.Label(frame_pesquisa, text="Pesquisar Produto:").pack(side="left", padx=5)
    entrada_pesquisa = ttk.Entry(frame_pesquisa, width=30)
    entrada_pesquisa.pack(side="left", padx=5)
    btn_pesquisar = ttk.Button(
        frame_pesquisa,
        text="Pesquisar",
        command=lambda: pesquisar_produto(entrada_pesquisa, tabela)
    )
    btn_pesquisar.pack(side="left", padx=5)
    btn_limpar = ttk.Button(
        frame_pesquisa,
        text="Limpar",
        command=lambda: limpar_pesquisa(entrada_pesquisa, tabela)
    )
    btn_limpar.pack(side="left", padx=5)

    cols = ("Nome", "Quantidade", "Preço")
    tabela = ttk.Treeview(frame_consulta, columns=cols, show="headings", height=12)
    for col in cols:
        tabela.heading(col, text=col)
        tabela.column(col, anchor="center")
    tabela.pack(fill='both', expand=True, pady=10)
    scrollbar = ttk.Scrollbar(frame_consulta, orient="vertical", command=tabela.yview)
    tabela.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")

    # Ações: Editar, Salvar e Excluir
    frame_acoes = ttk.Frame(frame_consulta)
    frame_acoes.pack(pady=10)

    btn_editar = ttk.Button(
        frame_acoes,
        text="Editar Produto",
        command=lambda: editar_produto(tabela)
    )
    btn_editar.pack(side="left", padx=10)

    btn_salvar = ttk.Button(
        frame_acoes,
        text="Salvar Estoque",
        command=salvar_estoque_em_arquivo
    )
    btn_salvar.pack(side="left", padx=10)

    def excluir_produto():
        sel = tabela.selection()
        if not sel:
            return messagebox.showwarning("Aviso", "Selecione um produto para excluir.")
        nome = tabela.item(sel[0], "values")[0]

        cursor.execute("DELETE FROM produtos WHERE nome = ?", (nome,))
        conn.commit()

        global estoque
        estoque = [p for p in estoque if p["nome"] != nome]

        atualizar_tabela(tabela)
        atualizar_dashboard()
        combo_produto["values"] = [p["nome"] for p in estoque]
        messagebox.showinfo("Sucesso", f"Produto '{nome}' excluído.")

    btn_excluir = ttk.Button(
        frame_acoes,
        text="Excluir Produto",
        command=excluir_produto
    )
    btn_excluir.pack(side="left", padx=10)


    # Aba Dashboard
    tab_dashboard = ttk.Frame(notebook)
    notebook.add(tab_dashboard, text="Dashboard")
    frame_dashboard = ttk.Frame(tab_dashboard, padding=20)
    frame_dashboard.pack(fill='both', expand=True)
    lbl_total_produtos = ttk.Label(frame_dashboard, text="Total de Produtos: 0", font=("Helvetica", 14))
    lbl_total_produtos.pack(pady=5)
    lbl_total_valor = ttk.Label(frame_dashboard, text="Valor Total: R$0.00", font=("Helvetica", 14))
    lbl_total_valor.pack(pady=5)
    lbl_valor_medio = ttk.Label(frame_dashboard, text="Valor Médio: R$0.00", font=("Helvetica", 14))
    lbl_valor_medio.pack(pady=5)
    fig, ax = plt.subplots(figsize=(6, 3), dpi=100)
    canvas = FigureCanvasTkAgg(fig, master=frame_dashboard)
    canvas.get_tk_widget().pack(pady=10)
    atualizar_dashboard()

    # Aba Clientes
    tab_clientes = ttk.Frame(notebook)
    notebook.add(tab_clientes, text="Clientes")
    frame_clientes = ttk.Frame(tab_clientes, padding=20)
    frame_clientes.pack(fill='both', expand=True)

    form_frame = ttk.Frame(frame_clientes)
    form_frame.pack(side="left", fill="y", padx=20, pady=20)

    ttk.Label(form_frame, text="Cadastro Cliente", font=("Arial", 16, "bold")).grid(row=0, column=0, columnspan=2, pady=10)
    ttk.Label(form_frame, text="Nome do Cliente:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
    entrada_nome_cliente = ttk.Entry(form_frame, width=30)
    entrada_nome_cliente.grid(row=1, column=1, padx=10, pady=5)

    ttk.Label(form_frame, text="Produto:").grid(row=2, column=0, padx=10, pady=5, sticky="e")
    combo_produto = ttk.Combobox(form_frame, values=[], width=28)
    combo_produto.grid(row=2, column=1, padx=10, pady=5)

    ttk.Label(form_frame, text="Quantidade (Kg):").grid(row=3, column=0, padx=10, pady=5, sticky="e")
    entrada_quantidade_cliente = ttk.Entry(form_frame, width=30)
    entrada_quantidade_cliente.grid(row=3, column=1, padx=10, pady=5)

    ttk.Label(form_frame, text="Forma de Pagamento:").grid(row=4, column=0, padx=10, pady=5, sticky="e")
    combo_pagamento = ttk.Combobox(form_frame, values=["Cartão", "Dinheiro", "Pix"], width=28)
    combo_pagamento.grid(row=4, column=1, padx=10, pady=5)

    ttk.Label(form_frame, text="Status do Pagamento:").grid(row=5, column=0, padx=10, pady=5, sticky="e")
    combo_status = ttk.Combobox(form_frame, values=["Pago", "Pendente"], width=28)
    combo_status.grid(row=5, column=1, padx=10, pady=5)

    btn_cadastrar_cliente = ttk.Button(
        form_frame,
        text="Cadastrar Cliente",
        command=lambda: cadastrar_cliente(
            entrada_nome_cliente.get(),
            combo_produto.get(),
            entrada_quantidade_cliente.get(),
            combo_pagamento.get(),
            combo_status.get(),
            tree_clientes
        )
    )
    btn_cadastrar_cliente.grid(row=6, column=0, columnspan=2, pady=10)

    btn_nova_compra = ttk.Button(
        form_frame,
        text="Registrar Nova Compra",
        command=lambda: registrar_nova_compra(
            entrada_nome_cliente.get(),
            notebook,
            tabela,
            tree_clientes
        )
    )
    btn_nova_compra.grid_forget()

    total_label_var = tk.StringVar()
    total_label = ttk.Label(form_frame, textvariable=total_label_var, font=("Arial", 12))
    total_label.grid(row=7, column=0, columnspan=2, pady=10)

    tabela_frame = ttk.Frame(frame_clientes)
    tabela_frame.pack(side="right", fill="both", expand=True, padx=20, pady=20)

    ttk.Label(tabela_frame, text="Tabela Clientes", font=("Arial", 16, "bold")).pack(pady=10)

    cols_clientes = ("ID", "Nome", "Total Gasto")
    tree_clientes = ttk.Treeview(tabela_frame, columns=cols_clientes, show="headings", height=15)
    for col in cols_clientes:
        tree_clientes.heading(col, text=col)
        tree_clientes.column(col, anchor="center")
    tree_clientes.pack(fill="both", expand=True)

    # Botão excluir cliente
    def excluir_cliente():
        sel = tree_clientes.selection()
        if not sel:
            return messagebox.showwarning("Aviso", "Selecione um cliente para excluir.")
        cid, nome, _ = tree_clientes.item(sel[0], "values")

        confirm = messagebox.askyesno("Confirmação", f"Deseja realmente excluir o cliente '{nome}' e todas as suas compras?")
        if not confirm:
            return

        # Remove do banco de dados
        cursor.execute("DELETE FROM compras WHERE cliente_id = ?", (cid,))
        cursor.execute("DELETE FROM clientes WHERE id = ?", (cid,))
        conn.commit()

        # Remove da memória
        if nome in clientes:
            del clientes[nome]

        # Atualiza a interface
        tree_clientes.delete(sel[0])
        atualizar_tabela(tabela)
        atualizar_dashboard()
        messagebox.showinfo("Sucesso", f"Cliente '{nome}' excluído com sucesso!")

    btn_excluir_cliente = ttk.Button(tabela_frame, text="Excluir Cliente", command=excluir_cliente)
    btn_excluir_cliente.pack(pady=10)

    tree_clientes.tag_configure("pendente", background="tomato")


    def cliente_selecionado(event):
        selected = tree_clientes.selection()
        if selected:
            item = tree_clientes.item(selected[0])
            nome_cliente = item["values"][0]
            entrada_nome_cliente.delete(0, tk.END)
            entrada_nome_cliente.insert(0, nome_cliente)
            btn_nova_compra.grid(row=7, column=0, columnspan=2, pady=10)
            if nome_cliente in clientes:
                total = sum(compra["quantidade"] * 1 for compra in clientes[nome_cliente]["compras"])
                total_label_var.set(f"Total Gasto: R${total:.2f}")

    tree_clientes.bind("<<TreeviewSelect>>", lambda e: btn_nova_compra.grid(row=7, column=0, columnspan=2, pady=10))
    def on_double_click(event):
        item_id = tree_clientes.identify_row(event.y)
        if not item_id:
            return
        cid, nome, _ = tree_clientes.item(item_id, "values")

        # Abre aba de histórico 
        for i in range(notebook.index("end")):
            if notebook.tab(i, "text") == f"Histórico - {nome}":
                notebook.select(i)
                return
        aba_hist = ttk.Frame(notebook)
        notebook.add(aba_hist, text=f"Histórico - {nome}")
        notebook.select(aba_hist)

        # Botão fechar aba
        btn_fechar = ttk.Button(
            aba_hist,
            text="✕",
            width=3,
            command=lambda: notebook.forget(aba_hist)
        )
        btn_fechar.pack(anchor="ne", padx=5, pady=5)

        # Cria Treeview de histórico
        cols = ("Produto", "Quantidade", "Pagamento", "Status", "Subtotal")
        tree_h = ttk.Treeview(aba_hist, columns=cols, show="headings")
        for c in cols:
            tree_h.heading(c, text=c)
            tree_h.column(c, anchor="center")
        tree_h.pack(fill="both", expand=True, padx=10, pady=10)

        # Preenche histórico
        total_geral = 0
        for compra in clientes[nome]["compras"]:
            preco = next((p["preco"] for p in estoque if p["nome"] == compra["produto"]), 0)
            subtotal = compra["quantidade"] * preco
            total_geral += subtotal
            tag = "pendente" if compra["status"] == "Pendente" else ""
            tree_h.insert(
                "",
                "end",
                values=(
                    compra["produto"],
                    compra["quantidade"],
                    compra["forma_pagamento"],
                    compra["status"],
                    f"R${subtotal:.2f}"
                ),
                tags=(tag,)
            )
        tree_h.tag_configure("pendente", background="tomato")

        # Botão para excluir a compra selecionada
        def excluir_compra():
            sel = tree_h.selection()
            if not sel:
                return messagebox.showwarning("Aviso", "Selecione uma compra para excluir.")
            vals = tree_h.item(sel[0], "values")
            prod_sel, qtd_sel, pag_sel, stat_sel, _ = vals

            # Exclui do banco
            cursor.execute(
                """
                DELETE FROM compras
                WHERE cliente_id = ?
                  AND produto_id = (SELECT id FROM produtos WHERE nome = ?)
                  AND quantidade = ?
                  AND forma_pagamento = ?
                  AND status = ?
                """,
                (clientes[nome]["id"], prod_sel, float(qtd_sel), pag_sel, stat_sel)
            )
            conn.commit()

            # Remove da estrutura em memória
            for c in clientes[nome]["compras"]:
                if (c["produto"] == prod_sel and
                    c["quantidade"] == float(qtd_sel) and
                    c["forma_pagamento"] == pag_sel and
                    c["status"] == stat_sel):
                    clientes[nome]["compras"].remove(c)
                    break

            # Atualiza tabelas e dashboard
            tree_h.delete(sel[0])
            atualizar_tabela_clientes(tree_clientes)
            atualizar_tabela(tabela)
            atualizar_dashboard()
            messagebox.showinfo("Sucesso", "Compra excluída com sucesso!")

        btn_excluir_compra = ttk.Button(
            aba_hist,
            text="Excluir Compra Selecionada",
            command=excluir_compra
        )
        btn_excluir_compra.pack(pady=5)


        def editar_historico():
            sel = tree_h.selection()
            if not sel:
                return
            prod, qtd, pag, stat, _ = tree_h.item(sel[0], "values")

            win = tk.Toplevel()
            win.title(f"Editar Compra - {prod}")
            win.geometry("300x200") 
            tk.Label(win, text="Quantidade:").grid(row=0, column=0, padx=5, pady=5)
            ent_q = ttk.Entry(win); ent_q.insert(0, qtd); ent_q.grid(row=0, column=1)
            tk.Label(win, text="Pagamento:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
            combo_pagamento = ttk.Combobox(win, values=["Cartão", "Dinheiro", "Pix"], width=28)
            combo_pagamento.set(pag)  # Define o valor inicial com base em 'pag'
            combo_pagamento.grid(row=1, column=1, padx=5, pady=5)
            tk.Label(win, text="Status:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
            combo_status = ttk.Combobox(win, values=["Pago", "Pendente"], width=28)
            combo_status.set(stat)  # Define o valor inicial com base em 'stat'
            combo_status.grid(row=2, column=1, padx=5, pady=5)

            def salvar2():
                for c in clientes[nome]["compras"]:
                    if c["produto"] == prod and str(c["quantidade"]) == qtd and c["status"] == stat:
                        c["quantidade"] = float(ent_q.get())
                        c["forma_pagamento"] = combo_pagamento.get()  
                        c["status"] = combo_status.get()              
                        break
                win.destroy()
                notebook.forget(aba_hist)
                on_double_click(event)

            ttk.Button(win, text="Salvar", command=salvar2).grid(row=3, column=0, columnspan=2, pady=10)
        ttk.Button(aba_hist, text="Editar Seleção", command=editar_historico).pack(pady=5)
        ttk.Label(aba_hist, text=f"Total Gasto: R${total_geral:.2f}", font=("Arial", 12, "bold")).pack(pady=10)
    tree_clientes.bind("<Double-1>", on_double_click)

    def atualizar_produtos_combo():
        combo_produto["values"] = [p["nome"] for p in estoque]
        if estoque:
            combo_produto.current(0)

    def on_tab_changed(event):
        texto = notebook.tab(notebook.select(), "text")
        if texto == "Clientes":
            atualizar_produtos_combo()
            atualizar_tabela_clientes(tree_clientes)

    notebook.bind("<<NotebookTabChanged>>", on_tab_changed) 
    janela.mainloop()

# TELA DE LOGIN
def login():
    
    login_window = tk.Tk()
    login_window.title("Login")
    login_window.geometry("400x300")  
    login_window.resizable(False, False)  
    style = ttk.Style()
    style.configure("TButton", font=("Arial", 12), padding=10)
    style.configure("TLabel", font=("Arial", 12))
    login_window.eval('tk::PlaceWindow %s center' % login_window.winfo_toplevel())
    login_window.configure(bg="#f0f0f0")
    titulo = ttk.Label(login_window, text="Bem-vindo", font=("Arial", 16, "bold"))
    titulo.pack(pady=20)
    ttk.Label(login_window, text="Usuário:").pack(pady=5)
    entrada_usuario = ttk.Entry(login_window, font=("Arial", 12), width=30)
    entrada_usuario.pack(pady=5)
    ttk.Label(login_window, text="Senha:").pack(pady=5)
    entrada_senha = ttk.Entry(login_window, show="*", font=("Arial", 12), width=30)
    entrada_senha.pack(pady=5)
    def verificar_login():
        usuario = entrada_usuario.get().strip()
        senha = entrada_senha.get().strip()
        if usuario == "admin" and senha == "admin":
            login_window.destroy()
            abrir_estoque() 
        else:
            messagebox.showerror("Erro de Login", "Usuário ou senha incorretos!")
    ttk.Button(login_window, text="Entrar", command=verificar_login).pack(pady=20)
    login_window.mainloop()

if __name__ == "__main__":
    login()
