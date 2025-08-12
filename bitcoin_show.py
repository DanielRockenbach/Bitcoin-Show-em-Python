import random
import json
import requests
import html
import urllib3

# Adicionando uma variável global para armazenar as perguntas baixadas
PERGUNTAS_BAIXADAS = {
    'easy': [],
    'medium': [],
    'hard': []
}

#  metodo que solicita um token de sessão da API para poder fazer requisições de perguntas.
def get_token():
    try:
        response = requests.get('https://tryvia.ptr.red/api_token.php?command=request')
        dados = response.json()
    except Exception as e:
        print('Não foi possível obter token', e)
        return None
    if dados.get("response_code", 1) != 0:
        print("Não foi possível obter token. Código de resposta", dados.get("response_code"))
        return None
    return dados.get("token")

# metodo que obtém uma lista de perguntas da API com base nos parâmetros fornecidos.
def get_questions(token, qtd_questions, difficulty):
    category = 0
    url = (f'https://tryvia.ptr.red/api.php'
           f'?amount={qtd_questions}'
           f'&category={category}'
           f'&type=multiple'
           f'&difficulty={difficulty}'
           f'&token={token}')
    try:
        response = requests.get(url)
        dados = response.json()
    except Exception as e:
        print(f'Não foi possível obter perguntas {difficulty}', e)
        return None
    if dados.get("response_code", 1) != 0:
        print(f"Não foi possível obter perguntas {difficulty}. Código de resposta", dados.get("response_code"))
        return None
    return dados.get("results", [])

# metodo responsavel por carrega perguntas de todos os níveis de dificuldade e armazena na variável global PERGUNTAS_BAIXADAS.
def load_questions():
    token = get_token()
    if not token:
        print("Não foi possível obter o token da API. O jogo usará perguntas offline se disponíveis.")
        return False

    # Baixar perguntas para cada nível de dificuldade
    for dificuldade in ['easy', 'medium', 'hard']:
        perguntas = get_questions(token, 30, dificuldade)  # Baixa mais perguntas do que necessário
        if perguntas:
            PERGUNTAS_BAIXADAS[dificuldade] = perguntas
            print(f"Perguntas {dificuldade} baixadas com sucesso!")
        else:
            print(f"Não foi possível baixar perguntas {dificuldade}")

    return any(PERGUNTAS_BAIXADAS.values())  # Retorna True se pelo menos um nível foi baixado

# metodo por selecionar aleatoriamente uma pergunta do banco de perguntas baixadas para o nível especificado.
def offline_questions(dificuldade):
    if not PERGUNTAS_BAIXADAS[dificuldade]:
        return None
    return random.choice(PERGUNTAS_BAIXADAS[dificuldade])

# metodo que Decodifica caracteres HTML especiais em texto comum.
def parse_text(html_string: str) -> str:
    return html.unescape(html_string)

# metodo que exibe as intruções/regras do jogo para o jogador
def menu():
    print("""
    Bem vindo ao Bitcoin Show!

    Como funciona o jogo:
    - Consiste em um jogo de perguntas e respostas, o qual o usuario tentará responder
    - Cada pergunta tem 4 alternativas
    - O usuario terá de responder uma serie de 10 perguntas, que vão ficando mais dificeis conforme o avanco
    - A cada pergunta respondida corretamente o usuario recebe 0.1 bitcoin, até terminar o jogo ou ser eliminado
    - Caso a resposta do jogador esteja errada o jogo acaba e o usuario recebe 10% do valor conquistado
    - O usuario terá direito a 3 pulos, isso não o faz progredir, apenas troca a pergunta para outra de mesmo nível
    - A cada nível o jogador terá a opção de desistir e receber metade do prêmio conquistado
    """)

# metodo responsavel pelo funcionamento do jogo
def quiz():
    global PERGUNTAS_BAIXADAS

    # Tentar carregar perguntas no início
    load_questions()

    score = 0
    bitcoins = 0.0
    pulos = 3
    MAX_QUESTOES = 10
    questoes_por_nivel = {'easy': 3, 'medium': 3, 'hard': 4}
    niveis = ['easy', 'medium', 'hard']
    contador = 0

    # laco de repeticao responsavel pela organizacao das perguntas e apresentacao delas
    for nivel in niveis:
        for _ in range(questoes_por_nivel[nivel]):
            if contador >= MAX_QUESTOES:
                break

            # Tentar obter pergunta offline primeiro
            item = offline_questions(nivel)
            if item is None:
                print(f"Não há perguntas disponíveis para o nível {nivel}. O jogo será encerrado.")
                return

            resposta_correta = parse_text(item['correct_answer'])
            respostas_incorretas = [parse_text(x) for x in item['incorrect_answers']]
            alternativas = respostas_incorretas + [resposta_correta]
            random.shuffle(alternativas)
            resposta_correta_idx = alternativas.index(resposta_correta)

            print("\n" + "=" * 50)
            print("Categoria:", parse_text(item['category']))
            print("Pergunta:", parse_text(item['question']))
            print("\nAlternativas:")
            for idx, alt in enumerate(alternativas):
                print(f"{idx + 1}. {alt}")

            # laço de repetição responsável pelas escolhas do jogador ao longo do jogo
            while True:
                resposta = input("\nDigite o número da resposta (1-4), 'p' para pular ou 'd' para desistir: ").lower()

                if resposta == 'p':
                    if pulos > 0:
                        pulos -= 1
                        print(f"Pulo utilizado! Restam {pulos} pulos.")
                        # Obter nova pergunta do mesmo nível (offline)
                        nova_pergunta = offline_questions(nivel)
                        if nova_pergunta:
                            item = nova_pergunta
                            # Reinicia a apresentação da pergunta
                            resposta_correta = parse_text(item['correct_answer'])
                            respostas_incorretas = [parse_text(x) for x in item['incorrect_answers']]
                            alternativas = respostas_incorretas + [resposta_correta]
                            random.shuffle(alternativas)
                            resposta_correta_idx = alternativas.index(resposta_correta)
                            print("\nNova pergunta:")
                            print("Categoria:", parse_text(item['category']))
                            print("Pergunta:", parse_text(item['question']))
                            print("\nAlternativas:")
                            for idx in range(len(alternativas)):
                                print(f"{idx + 1}. {alternativas[idx]}")
                            continue
                        else:
                            print("Não foi possível obter uma nova pergunta.")
                            break
                    else:
                        print("Você não tem mais pulos disponíveis!")
                        continue

                if resposta == 'd':
                    result = bitcoins / 2
                    print(f"\nVocê desistiu! Recebeu {result:.2f} bitcoins")
                    return

                try:
                    resposta = int(resposta) - 1
                    if 0 <= resposta < len(alternativas):
                        break
                    print("Número inválido! Digite entre 1 e 4")
                except ValueError:
                    print("Entrada inválida! Digite um número, 'p' ou 'd'")

            # Verifica resposta
            if resposta == resposta_correta_idx:
                score += 1
                bitcoins += 0.1
                print(f"\n✓ Resposta correta! +0.1 bitcoin (Total: {bitcoins:.1f})")
            else:
                result = bitcoins * 0.1
                print(f"\n✗ Resposta errada! A correta era: {resposta_correta}")
                print(f"Fim de jogo! Você recebe {result:.2f} bitcoins")
                return

            contador += 1

    print(f"\nParabéns! Você completou todas as perguntas!")
    print(f"Pontuação final: {score}/{MAX_QUESTOES}")
    print(f"Total de bitcoins: {bitcoins:.1f}")


def main():
    menu()
    inicio = input("Vamos jogar? Digite s/n: ").lower()
    if inicio == 's':
        quiz()
    else:
        print("Até a próxima!")



main()