import sys 
import random
import queue
from time import sleep, time
from typing import Tuple, List, Dict
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

    tempo_permanencia = entrada_bruta[3]
    if tempo_permanencia <= 0:
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

    return n_atracoes, n_pessoas, n_vagas, tempo_permanencia, max_intervalo, semente, unidade_tempo


def criar_atracoes(n_atracoes: int) -> List[str]:
    return [f'AT-{i}' for i in range(1, n_atracoes + 1)]


def criar_dict_estatistica(atracoes: List[str]) -> Tuple[Dict[str, int], Dict[str, float]]:
    tempos = {}
    qtd = {}
    for atracao in atracoes:
        tempos[atracao] = 0.0
        qtd[atracao] = 0
    
    return qtd, tempos


def criar_pessoas(n_pessoas: int, tempo_permanencia: int, unidade_tempo: int, atracoes: List[str]) -> List[Thread]:
    return [
            Thread(
                target=rotina_pessoa, 
                args=(
                    atracoes[random.randint(0, n_atracoes-1)], 
                    Semaphore(0),
                    tempo_permanencia,
                    unidade_tempo
                )
            ) for _ in range(n_pessoas)
        ]


def exibir_relatorio(tempo_total_simulacao: float) -> None:
    global qtd_pessoas_por_atracao, tempos_espera_atracao, tempo_fim_atracoes, tempo_inicio_atracoes

    print()
    print("Tempo medio de espera:")
    for atracao, valor in tempos_espera_atracao.items():
        tempo = (valor * 1000) / qtd_pessoas_por_atracao[atracao]
        print(f"Experiencia {atracao}: {tempo:.2f}")
    
    tempo_atracao_funcionando = 0
    for i in range(len(tempo_inicio_atracoes)):
        tempo_atracao_funcionando += tempo_fim_atracoes[i] - tempo_inicio_atracoes[i]


    taxa_ocupacao = tempo_atracao_funcionando / tempo_total_simulacao
    print()
    print(f"Taxa de ocupacao: {taxa_ocupacao:.2f}")

    
def rotina_gerador_pessoas(max_intervalo: int, n_pessoas: int, tempo_permanencia: int, unidade_tempo: int, atracoes: List[str]) -> None:
    pessoas = criar_pessoas(n_pessoas, tempo_permanencia, unidade_tempo, atracoes)
    for p in pessoas:
        p.start()
        sleep(random.randint(0, max_intervalo * unidade_tempo))

    
    for p in pessoas: 
        p.join()
    

def rotina_pessoa(atracao: str, sem: Semaphore, tempo_permanencia: int, unidade_tempo: int) -> None:
    global fila_principal, fila_interna, lock_estatisticas, lock_ordem, lock_qtd_pessoas_atracao, ordem, qtd_pessoas_atracao, qtd_pessoas_por_atracao, sem_pessoas_na_fila_principal, sem_proxima_atracao, sem_total_vagas, tempos_espera_atracao, tempo_inicio_atracoes

    with lock_ordem:
        priv_ordem = ordem
        ordem += 1
        fila_principal.put({'atracao': atracao, 'ordem': priv_ordem, 'semaforo': sem}) # Coloca pessoa na fila
        print(f"[Pessoa {priv_ordem} / {atracao}] Aguardando na fila.")
        sem_pessoas_na_fila_principal.release() # Sinaliza que tem pessoa na fila

    # Pessoa aguarda a vez dela na fila_principal
    tempo_inicio_espera = time()
    sem.acquire()

    # Pessoa entra na atração
    with lock_qtd_pessoas_atracao:
        qtd_pessoas_atracao += 1
        print(f"[Pessoa {priv_ordem} / {atracao}] Entrou na NASA Experiences (quantidade = {qtd_pessoas_atracao}).")

    with lock_estatisticas:
        qtd_pessoas_por_atracao[atracao] += 1
        tempos_espera_atracao[atracao] += time() - tempo_inicio_espera

    fila_interna.put(fila_principal.get()) # Pessoa sai da fila de entrada e entra na fila de saída
    sem_proxima_pessoa.release() # Libera proxima pessoa da fila_principal

    sleep(tempo_permanencia * unidade_tempo)

    with fila_interna.mutex:
        primeiro_a_sair_atracao = fila_interna.queue[0]
             
    if primeiro_a_sair_atracao["ordem"] != priv_ordem:
        sem.acquire() # Pessoa aguarda para sair

    with lock_qtd_pessoas_atracao:
        qtd_pessoas_atracao -= 1
        print(f"[Pessoa {priv_ordem} / {atracao}] Saiu da NASA Experiences (quantidade = {qtd_pessoas_atracao}).")
        if qtd_pessoas_atracao == 0:
            tempo_fim_atracoes.append(time())
            if fila_principal.empty():
                print(f"[NASA] Pausando a experiencia {atracao_atual}.")
            sem_proxima_atracao.release()
        
        fila_interna.get() # Pessoa sai da atração
        if not fila_interna.empty():
            proximo_a_sair_atracao = fila_interna.queue[0]
            proximo_a_sair_atracao["semaforo"].release() # Libera o proximo da fila de saída para sair
        sem_total_vagas.release()
    
    # Última pessoa da simulação, sinaliza que pode finalizar
    if priv_ordem == n_pessoas:
        sem_finalizar_simulacao.release()
        
         
def rotina_nasa(n_pessoas: int):
    global atracao_atual, fila_principal, sem_pessoas_na_fila_principal, sem_proxima_pessoa, sem_total_vagas, tempo_inicio_atracoes

    tempo_inicio_simulacao = time()
    print("[NASA] Simulacao iniciada.")

    for _ in range(0, n_pessoas):
        sem_pessoas_na_fila_principal.acquire() # Aguarda ter pessoas na fila

        with fila_principal.mutex:
            pessoa = fila_principal.queue[0]
        
        # Atração da primeia pessoa da fila é diferente da atração atual
        if pessoa['atracao'] != atracao_atual:
            sem_proxima_atracao.acquire() # Espera acabar atração
            atracao_atual = pessoa['atracao'] # Atualiza atração atual
            tempo_inicio_atracoes.append(time())
            print(f"[NASA] Iniciando a experiencia {atracao_atual}.")

        sem_total_vagas.acquire() # Espera ter vagas suficientes
        pessoa['semaforo'].release() # Libera thread da Pessoa
        
        sem_proxima_pessoa.acquire() # Aguarda pessoa entrar na atração

    sem_finalizar_simulacao.acquire()

    print("[NASA] Simulacao finalizada.")
    tempo_finalizao_simulacao = time()

    exibir_relatorio(tempo_finalizao_simulacao - tempo_inicio_simulacao)        
        
if __name__ == '__main__':
    entrada_bruta = [int(arg) for arg in sys.argv[1:]]

    n_atracoes, n_pessoas, n_vagas, tempo_permanencia, max_intervalo, semente, unidade_tempo = validar_entrada(entrada_bruta)

    # Configurando a semente
    random.seed(semente)

    # Variáveis Globais
    atracoes = criar_atracoes(n_atracoes)
    qtd_pessoas_por_atracao, tempos_espera_atracao = criar_dict_estatistica(atracoes)
    tempo_inicio_atracoes = []
    tempo_fim_atracoes = []
    fila_principal = queue.Queue(n_pessoas)
    fila_interna = queue.Queue(n_pessoas) # Fila própria de cada atração
    ordem = 1
    atracao_atual = ''
    qtd_pessoas_atracao = 0
    
    # Semáforos e Mutexes
    lock_ordem = Lock()
    lock_qtd_pessoas_atracao = Lock()
    lock_estatisticas = Lock()
    sem_pessoas_na_fila_principal = Semaphore(0)
    sem_proxima_pessoa = Semaphore(0)
    sem_total_vagas = Semaphore(n_vagas)
    sem_proxima_atracao = Semaphore(1)
    sem_finalizar_simulacao = Semaphore(0)


    nasa = Thread(target=rotina_nasa, args=(n_pessoas,))
    gerador_pessoas = Thread(target=rotina_gerador_pessoas, args=(max_intervalo, n_pessoas, tempo_permanencia, unidade_tempo, atracoes))

    nasa.start()
    gerador_pessoas.start()

    gerador_pessoas.join()
    nasa.join()

    