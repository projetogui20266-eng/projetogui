import socket
import json

# ============================================================
# CONFIGURAÇÕES
# ============================================================
IP_SERVIDOR = input("IP da cozinha: ")
PORTA = 5000


# ============================================================
# SOCKET: função única que todas as opções do menu usam
# ============================================================
def enviar(mensagem):
    """Conecta no servidor, envia um dict em JSON e devolve a resposta."""
    cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    cliente.settimeout(5)  # desiste se o servidor não responder em 5s

    with cliente:
        cliente.connect((IP_SERVIDOR, PORTA))

        # Envia o JSON terminado em \n (marca o fim da mensagem)
        texto = json.dumps(mensagem, ensure_ascii=False) + "\n"
        cliente.sendall(texto.encode("utf-8"))

        # Lê a resposta do servidor
        arquivo = cliente.makefile("r", encoding="utf-8")
        return json.loads(arquivo.readline())


# ============================================================
# OPÇÕES DO MENU (cada uma manda uma "acao" diferente)
# ============================================================
def cadastrar_cliente():
    nome = input("Nome do cliente: ")
    telefone = input("Telefone: ")

    resposta = enviar({
        "acao": "cadastrar_cliente",
        "nome": nome,
        "telefone": telefone,
    })

    if resposta.get("ok"):
        print("Cliente cadastrado!")
    else:
        print("Erro:", resposta.get("erro"))


def cadastrar_produto():
    nome = input("Nome do produto: ")

    try:
        preco = float(input("Preço: ").replace(",", "."))
    except ValueError:
        print("Preço inválido.")
        return

    resposta = enviar({
        "acao": "cadastrar_produto",
        "nome": nome,
        "preco": preco,
    })

    if resposta.get("ok"):
        print(f"Produto cadastrado! Código: {resposta['codigo']}")
    else:
        print("Erro:", resposta.get("erro"))


def novo_pedido():
    # Pede ao servidor a lista de produtos cadastrados (o cardápio)
    resposta = enviar({"acao": "listar_produtos"})
    produtos = {p["codigo"]: p for p in resposta.get("produtos", [])}

    if not produtos:
        print("Nenhum produto cadastrado ainda. Cadastre primeiro.")
        return

    cliente = input("Nome do cliente: ")
    itens = []

    while True:
        print("\n--- CARDÁPIO ---")
        for codigo, p in produtos.items():
            print(f"{codigo} - {p['nome']}: R$ {p['preco']:.2f}")
        print("0 - Finalizar pedido")

        escolha = input("Escolha um produto: ")

        if escolha == "0":
            break

        if not escolha.isdigit() or int(escolha) not in produtos:
            print("Produto inválido!")
            continue

        produto = produtos[int(escolha)]

        try:
            quantidade = int(input("Quantidade: "))
            if quantidade <= 0:
                print("Quantidade deve ser maior que zero.")
                continue
        except ValueError:
            print("Digite uma quantidade válida.")
            continue

        itens.append({
            "produto": produto["nome"],
            "quantidade": quantidade,
            "preco": produto["preco"],
        })
        print("Produto adicionado!")

    if not itens:
        print("Pedido vazio. Nada foi enviado.")
        return

    resposta = enviar({"acao": "adicionar", "cliente": cliente, "itens": itens})

    if resposta.get("ok"):
        print("Pedido enviado para a cozinha!")
        print("Número do pedido:", resposta["id"])
    else:
        print("Erro:", resposta.get("erro"))


def consultar_pedido():
    numero = input("Número do pedido: ")

    resposta = enviar({"acao": "consultar_pedido", "id": numero})

    if resposta.get("ok"):
        print("Status:", resposta["status"])
    else:
        print("Erro:", resposta.get("erro"))


# ============================================================
# MENU PRINCIPAL
# ============================================================
while True:
    print("\n===== SISTEMA DO GARÇOM =====")
    print("1 - Cadastrar cliente")
    print("2 - Cadastrar produto")
    print("3 - Novo pedido")
    print("4 - Consultar pedido")
    print("0 - Sair")

    opcao = input("Escolha: ")

    try:
        if opcao == "1":
            cadastrar_cliente()
        elif opcao == "2":
            cadastrar_produto()
        elif opcao == "3":
            novo_pedido()
        elif opcao == "4":
            consultar_pedido()
        elif opcao == "0":
            print("Encerrando.")
            break
        else:
            print("Opção inválida!")

    except (OSError, ValueError):
        # Qualquer falha de conexão cai aqui
        print("Não foi possível conectar à cozinha.")
