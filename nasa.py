import sys 
import random
import queue
from time import sleep
from typing import Tuple, List
from threading import Thread, Lock, Semaphore


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
    return [f'AT-{i}' for i in range(1, n_atracoes + 1)]

def criar_pessoas(n_pessoas: int) -> List[Thread]:
    global atracoes
    pessoas = []
    for i in range(n_pessoas):
        pessoas.append(Thread(
            target=rotina_pessoa, 
            args=(
                atracoes[random.randint(0,n_atracoes-1)],
                Semaphore(0)
            )
        ))

    return pessoas

def rotina_gerador_pessoas() -> None:
    global max_intervalo, n_pessoas
    pessoas = criar_pessoas(n_pessoas)
    for p in pessoas:
        sleep(random.randint(0, max_intervalo))
        p.start()
    
    for p in pessoas: p.join()
    

def rotina_pessoa(atracao: str, sem: Semaphore) -> None:
    global fila_entrar, fila_sair, lock_ordem, lock_qtd_pessoas_atracao, ordem, qtd_pessoas_atracao, sem_pessoas_na_fila_entrar, sem_proxima_atracao, sem_total_vagas, tempo_permanecia, unidade_tempo

    with lock_ordem:
        priv_ordem = ordem
        ordem += 1
        fila_entrar.put({'atracao': atracao, 'ordem': priv_ordem, 'semaforo': sem}) # Coloca pessoa na fila
        print(f"[Pessoa {priv_ordem} / {atracao}] Aguardando na fila_entrar.")
        sem_pessoas_na_fila_entrar.release() # Sinaliza que tem pessoa na fila

    # Pessoa aguarda a vez dela na fila_entrar
    sem.acquire()

    # Pessoa entra na atração
    with lock_qtd_pessoas_atracao:
        qtd_pessoas_atracao += 1
        print(f"[Pessoa {priv_ordem} / {atracao}] Entrou na NASA Experiences (quantidade = {qtd_pessoas_atracao}).")
    
  
    fila_sair.put(fila_entrar.get()) # Pessoa sai da fila de entrada e entra na fila de saída
    sem_proxima_pessoa.release() # Libera proxima pessoa da fila_entrar

    sleep(tempo_permanecia * unidade_tempo)

    with fila_sair.mutex:
        primeiro_a_sair_atracao = fila_sair.queue[0]
             
    if primeiro_a_sair_atracao["ordem"] != priv_ordem:
        sem.acquire() # Pessoa aguarda para sair

    with lock_qtd_pessoas_atracao:
        qtd_pessoas_atracao -= 1
        print(f"[Pessoa {priv_ordem} / {atracao}] Saiu da NASA Experiences (quantidade = {qtd_pessoas_atracao}).")
        if qtd_pessoas_atracao == 0: 
            sem_proxima_atracao.release()
        
        fila_sair.get() # Pessoa sai da atração
        if not fila_sair.empty():
            proximo_a_sair_atracao = fila_sair.queue[0]
            proximo_a_sair_atracao["semaforo"].release() # Libera o proximo da fila de saída para sair
        sem_total_vagas.release()
    
    # Última pessoa da simulação, sinaliza que pode finalizar
    if priv_ordem == n_pessoas:
        sem_finalizar_simulacao.release()
        


            
            

def rotina_nasa():
    global atracao_atual, fila_entrar, n_pessoas, sem_pessoas_na_fila_entrar, sem_proxima_pessoa, sem_total_vagas

    print("[NASA] Simulacao iniciada.")

    for i in range(0, n_pessoas):
        if atracao_atual != '' and qtd_pessoas_atracao == 0 and fila_entrar.empty():
            print(f"[NASA] Pausando a experiencia {atracao_atual}.")

        sem_pessoas_na_fila_entrar.acquire() # Aguarda ter pessoas na fila

        with fila_entrar.mutex:
            pessoa = fila_entrar.queue[0]
        
        # Atração da primeia pessoa da fila é diferente da atração atual
        if pessoa['atracao'] != atracao_atual:
            sem_proxima_atracao.acquire() # Espera acabar atração
            atracao_atual = pessoa['atracao'] # Atualiza atração atual
            print(f"[NASA] Iniciando a experiencia {atracao_atual}.")

        sem_total_vagas.acquire() # Espera ter vagas suficientes
        pessoa['semaforo'].release() # Libera thread da Pessoa
        
        sem_proxima_pessoa.acquire() # Aguarda pessoa entrar na atração

    sem_finalizar_simulacao.acquire()

    print("[NASA] Simulacao finalizada.")
        
            
    

        

if __name__ == '__main__':
    entrada_bruta = [int(arg) for arg in sys.argv[1:]]

    n_atracoes, n_pessoas, n_vagas, tempo_permanecia, max_intervalo, semente, unidade_tempo = validar_entrada(entrada_bruta)

    # Configurando a semente
    random.seed(semente)

    # Variáveis Globais
    fila_entrar = queue.Queue(n_pessoas)
    fila_sair = queue.Queue(n_pessoas)
    ordem = 1
    atracao_atual = ''
    qtd_pessoas_atracao = 0
    
    # Semáforos e Mutexes
    lock_ordem = Lock()
    lock_qtd_pessoas_atracao = Lock()
    sem_pessoas_na_fila_entrar = Semaphore(0)
    sem_proxima_pessoa = Semaphore(0)
    sem_total_vagas = Semaphore(n_vagas)
    sem_proxima_atracao = Semaphore(1)
    sem_finalizar_simulacao = Semaphore(0)

    atracoes = criar_atracoes(n_atracoes)

    nasa = Thread(target=rotina_nasa)
    gerador_pessoas = Thread(target=rotina_gerador_pessoas)

    nasa.start()
    gerador_pessoas.start()

    gerador_pessoas.join()
    nasa.join()

    