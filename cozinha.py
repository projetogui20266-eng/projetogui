import socket
import json
import threading
import os

# ============================================================
# CONFIGURAÇÕES
# ============================================================
IP = "0.0.0.0"          # escuta em todas as placas de rede
PORTA = 5000            # porta onde os clientes se conectam
ARQUIVO = "dados.json"  # arquivo onde tudo fica salvo

# Lock: impede que duas threads mexam nos dados ao mesmo tempo
bloqueio = threading.Lock()


# ============================================================
# DADOS (carregar e salvar em arquivo JSON)
# ============================================================
def carregar():
    """Lê o arquivo JSON. Se não existir, começa vazio."""
    if os.path.exists(ARQUIVO):
        with open(ARQUIVO, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "clientes": [],
        "produtos": [],
        "pedidos": [],
        "proximo_id_pedido": 1,
    }


def salvar():
    """Grava os dados no arquivo (chamar sempre dentro do lock)."""
    with open(ARQUIVO, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


dados = carregar()


# ============================================================
# AÇÕES: cada cadastro/função é uma "ação" que o cliente pede
# Cada função recebe a mensagem (dict) e devolve a resposta (dict)
# ============================================================
def cadastrar_cliente(msg):
    dados["clientes"].append({
        "nome": msg["nome"],
        "telefone": msg["telefone"],
    })
    salvar()
    return {"ok": True}


def cadastrar_produto(msg):
    codigo = len(dados["produtos"]) + 1
    dados["produtos"].append({
        "codigo": codigo,
        "nome": msg["nome"],
        "preco": float(msg["preco"]),
    })
    salvar()
    return {"ok": True, "codigo": codigo}


def listar_produtos(msg):
    return {"ok": True, "produtos": dados["produtos"]}


def listar_clientes(msg):
    return {"ok": True, "clientes": dados["clientes"]}


def adicionar_pedido(msg):
    pedido = {
        "id": dados["proximo_id_pedido"],
        "cliente": msg["cliente"],
        "itens": msg["itens"],
        "status": "Pendente",
    }
    dados["pedidos"].append(pedido)
    dados["proximo_id_pedido"] += 1
    salvar()
    return {"ok": True, "id": pedido["id"]}


def consultar_pedido(msg):
    for pedido in dados["pedidos"]:
        if pedido["id"] == int(msg["id"]):
            return {"ok": True, "status": pedido["status"]}
    return {"ok": False, "erro": "Pedido não encontrado."}


# Tabela que liga o nome da ação à função que trata ela.
# Para criar um cadastro novo: escreva a função e adicione aqui.
ACOES = {
    "cadastrar_cliente": cadastrar_cliente,
    "cadastrar_produto": cadastrar_produto,
    "listar_produtos": listar_produtos,
    "listar_clientes": listar_clientes,
    "adicionar": adicionar_pedido,
    "consultar_pedido": consultar_pedido,
}


# ============================================================
# SOCKET: atende cada cliente que conecta
# ============================================================
def atender(conexao):
    with conexao:
        try:
            # Lê uma linha (a mensagem termina com \n) e converte de JSON
            arquivo = conexao.makefile("r", encoding="utf-8")
            msg = json.loads(arquivo.readline())

            funcao = ACOES.get(msg.get("acao"))

            if funcao is None:
                resposta = {"ok": False, "erro": "Comando inválido."}
            else:
                with bloqueio:
                    resposta = funcao(msg)

        except (ValueError, KeyError, TypeError):
            resposta = {"ok": False, "erro": "Mensagem inválida."}

        # Devolve a resposta ao cliente
        texto = json.dumps(resposta, ensure_ascii=False) + "\n"
        conexao.sendall(texto.encode("utf-8"))


def iniciar_servidor():
    """Cria o socket, fica esperando conexões e abre uma thread por cliente."""
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind((IP, PORTA))
    servidor.listen()

    while True:
        conexao, _ = servidor.accept()
        threading.Thread(target=atender, args=(conexao,), daemon=True).start()


# ============================================================
# MENU LOCAL DA COZINHA (roda na tela do servidor)
# ============================================================
def mostrar_pedidos():
    with bloqueio:
        print("\n===== PEDIDOS =====")

        if not dados["pedidos"]:
            print("Nenhum pedido recebido.")
            return

        for pedido in dados["pedidos"]:
            print(f"\nPedido #{pedido['id']}")
            print(f"Cliente: {pedido['cliente']}")
            print(f"Status: {pedido['status']}")

            for item in pedido["itens"]:
                subtotal = item["preco"] * item["quantidade"]
                print(f"  {item['quantidade']}x {item['produto']} - R$ {subtotal:.2f}")


def marcar_pronto():
    try:
        numero = int(input("Número do pedido pronto: "))
    except ValueError:
        print("Digite um número válido.")
        return

    with bloqueio:
        for pedido in dados["pedidos"]:
            if pedido["id"] == numero:
                pedido["status"] = "Pronto"
                salvar()
                print(f"Pedido #{numero} marcado como pronto!")
                return
        print("Pedido não encontrado.")


# Servidor roda em segundo plano; o menu usa a thread principal
threading.Thread(target=iniciar_servidor, daemon=True).start()
print(f"Cozinha ligada! Aguardando conexões na porta {PORTA}.")

while True:
    print("\n===== COZINHA =====")
    print("1 - Ver pedidos")
    print("2 - Marcar pedido como pronto")
    print("0 - Encerrar")

    opcao = input("Escolha: ")

    if opcao == "1":
        mostrar_pedidos()
    elif opcao == "2":
        marcar_pronto()
    elif opcao == "0":
        print("Cozinha encerrada.")
        break
    else:
        print("Opção inválida!")
