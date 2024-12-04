import sys 
import random
import queue
from time import sleep
from typing import Tuple, List
from threading import Thread, current_thread, Lock, Semaphore


def validar_entrada(entrada_bruta: List[int]) -> Tuple[int, int, int, int, int, int, int]:
    if len(entrada_bruta) != 7:
        raise ValueError("Quantidade de argumentos insuficiente")

    n_atracoes = entrada_bruta[0]
    if n_atracoes <= 1:
        raise ValueError("O número de atrações deve ser maior do que 1")

    n_pessoas = entrada_bruta[1]
    if n_pessoas <= 0:
        raise ValueError("O número de pessoas deve ser maior do que 0")

    n_vagas = entrada_bruta[2]
    if n_vagas <= 0:
        raise ValueError("O número de vagas deve ser maior do que 0")

    tempo_permanecia = entrada_bruta[3]
    if tempo_permanecia <= 0:
        raise ValueError("O tempo de permanência deve ser maior do que 0")

    max_intervalo = entrada_bruta[4]
    if max_intervalo <= 0:
        raise ValueError("O tempo máximo de intervalo deve ser maior do que 0")

    semente = entrada_bruta[5]
    if semente < 0:
        raise ValueError("A semente deve conter um valor maior ou igual a 0")

    unidade_tempo = entrada_bruta[6]
    if unidade_tempo <= 0:
        raise ValueError("A quantidade unitária de tempo deve ser maior do que 0")

    return n_atracoes, n_pessoas, n_vagas, tempo_permanecia, max_intervalo, semente, unidade_tempo

def criar_atracoes(n_atracoes: int) -> List[str]:
    return [f'AT-{i}' for i in range(n_atracoes)]

def criar_pessoas(n_pessoas: int) -> List[Thread]:
    global atracoes
    return [Thread(target=rotina_pessoa, args=(atracoes[random.randint(0,n_atracoes-1)],)) for i in range(n_pessoas)]

def rotina_pessoa(atracao: str):
    global fila, ordem, lock_ordem, atracao_atual, quantidade_pessoas_na_atracao, lock_quantidade_pessoas_na_atracao, sem_pessoas_na_atracao, sem_iniciar_atracao
    # pessoa = current_thread()

    with lock_ordem:
        # fila.put(pessoa)
        priv_ordem = ordem
        print(f'[Pessoa {priv_ordem} / {atracao}] Aguardando na fila.')
        ordem += 1
    
    if atracao_atual != atracao:
        sem_iniciar_atracao.acquire()
        atracao_atual = atracao
        print(f'[NASA] Iniciando a experiência {atracao_atual}.')
    
    sem_pessoas_na_atracao.acquire()
    with lock_quantidade_pessoas_na_atracao:
        quantidade_pessoas_na_atracao += 1
        print(f'[Pessoa {priv_ordem} / {atracao}] Entrou na NASA Experiences (quantidade = {quantidade_pessoas_na_atracao}).')

    sleep(tempo_permanecia * unidade_tempo)

    with lock_quantidade_pessoas_na_atracao:
        quantidade_pessoas_na_atracao -= 1
        print(f'[Pessoa {priv_ordem} / {atracao}] Saiu da NASA Experiences (quantidade = {quantidade_pessoas_na_atracao}).')
        sem_pessoas_na_atracao.release()
        if quantidade_pessoas_na_atracao == 0:
            sem_iniciar_atracao.release()

            
            

def rotina_nasa():
    global n_pessoas, max_intervalo

    pessoas = criar_pessoas(n_pessoas)
    print('[NASA] Simulacao iniciada.')
    for p in pessoas:
        sleep(random.randint(0, max_intervalo))
        p.start()

    for p in pessoas:
        p.join()
    
    print('[NASA] Simulacao finalizada.')
    

        

if __name__ == '__main__':
    entrada_bruta = [int(arg) for arg in sys.argv[1:]]

    n_atracoes, n_pessoas, n_vagas, tempo_permanecia, max_intervalo, semente, unidade_tempo = validar_entrada(entrada_bruta)

    # Configurando a semente
    random.seed(semente)

    atracoes = criar_atracoes(n_atracoes)
    atracao_atual = ''
    ordem = 1
    lock_ordem = Lock()
    lock_quantidade_pessoas_na_atracao = Lock()
    sem_pessoas_na_atracao = Semaphore(n_vagas)
    sem_iniciar_atracao = Semaphore(1)
    quantidade_pessoas_na_atracao = 0
    fila = queue.Queue()
    nasa = Thread(target=rotina_nasa)

    nasa.start()
    nasa.join()
