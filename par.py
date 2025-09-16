import xmlrpc.client
import socket
import threading
import time
import os
import random
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configurações do sistema
URL_RASTREADOR = "http://localhost:8000"  # URL do servidor tracker
NOME_ARQUIVO = "ubuntu-teste.iso"         # Nome do arquivo compartilhado
TAMANHO_ARQUIVO_MB = 500                  # Tamanho total do arquivo em MB
TAMANHO_PEDACO = 1024 * 1024              # Tamanho de cada pedaço (1MB)
TOTAL_PEDACOS = TAMANHO_ARQUIVO_MB        # Total de pedaços do arquivo

# Configurações de otimização de download
BASE_DOWNLOADS_SIMULTANEOS = 5            # Número base de downloads simultâneos
INCREMENTO_POR_SEED = 5                   # Incremento por seed disponível
INCREMENTO_POR_PEER = 2                   # Incremento por peer disponível
MAX_CONEXOES_SERVIDOR = 50                # Máximo de conexões do servidor
INTERVALO_ATUALIZACAO = 1                 # Intervalo de atualização do tracker (segundos)
TIMEOUT_CONEXAO = 10                      # Timeout das conexões (segundos)
BUFFER_SIZE = 64 * 1024                   # Tamanho do buffer de transferência

class Par:
    def __init__(self, host_servidor, porta_servidor, eh_semeador=False):
        self.host_servidor = host_servidor
        self.porta_servidor = porta_servidor
        self.id_par = f"{host_servidor}:{porta_servidor}"
        self.rastreador = xmlrpc.client.ServerProxy(URL_RASTREADOR)  # Cliente do tracker

        self.eh_semeador_inicial = eh_semeador
        self.meus_pedacos = set()          # Conjunto de pedaços possuídos
        self.pedacos_sendo_baixados = set()  # Pedaços em download
        self.lock_pedacos = threading.Lock()  # Lock para operações nos conjuntos

        # Gerenciamento de downloads
        self.max_downloads_atual = BASE_DOWNLOADS_SIMULTANEOS
        self.downloads_ativos = {}         # Downloads em andamento
        # Thread pool para executar downloads em paralelo
        self.executor_downloads = ThreadPoolExecutor(max_workers=100)

        # Inicialização do peer
        if self.eh_semeador_inicial:
            # Semeador começa com todos os pedaços
            self.meus_pedacos = set(range(TOTAL_PEDACOS))
            print(f"Par {self.id_par} iniciado como SEMEADOR com {TOTAL_PEDACOS} pedaços.")
        else:
            # Leecher cria arquivo vazio do tamanho correto
            caminho_arquivo_destino = self.id_par.replace(":", "_") + "_" + NOME_ARQUIVO
            if not os.path.exists(caminho_arquivo_destino):
                with open(caminho_arquivo_destino, 'wb') as f:
                    f.truncate(TAMANHO_ARQUIVO_MB * 1024 * 1024)

        # Inicia threads do servidor e cliente
        threading.Thread(target=self.executar_servidor, daemon=True).start()
        threading.Thread(target=self.iniciar_download, daemon=True).start()

    def calcular_downloads_otimos(self, info_todos_pares):
        """Calcula número ideal de downloads com base na disponibilidade de peers"""
        if not info_todos_pares:
            return BASE_DOWNLOADS_SIMULTANEOS

        total_seeds = sum(1 for id_par, pedacos in info_todos_pares.items() 
                         if id_par != self.id_par and len(pedacos) == TOTAL_PEDACOS)
        total_peers = sum(1 for id_par, pedacos in info_todos_pares.items() 
                         if id_par != self.id_par and 0 < len(pedacos) < TOTAL_PEDACOS)
        
        downloads_otimos = min(100, BASE_DOWNLOADS_SIMULTANEOS + 
                              (total_seeds * INCREMENTO_POR_SEED) + 
                              (total_peers * INCREMENTO_POR_PEER))
        
        print(f"Seeds: {total_seeds}, Peers: {total_peers}, Downloads: {downloads_otimos}")
        return downloads_otimos

    def executar_servidor(self):
        """Servidor para atender requisições de outros peers"""
        socket_servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        socket_servidor.bind((self.host_servidor, self.porta_servidor))
        socket_servidor.listen(MAX_CONEXOES_SERVIDOR)
        print(f"Servidor {self.id_par} escutando em {self.host_servidor}:{self.porta_servidor}")
        
        executor_servidor = ThreadPoolExecutor(max_workers=MAX_CONEXOES_SERVIDOR)
        
        while True:
            try:
                socket_cliente, _ = socket_servidor.accept()
                executor_servidor.submit(self.lidar_com_requisicao, socket_cliente)
            except Exception as e:
                print(f"Erro ao aceitar conexão: {e}")

    def lidar_com_requisicao(self, socket_cliente):
        """Processa requisição de envio de pedaço"""
        try:
            socket_cliente.settimeout(TIMEOUT_CONEXAO)
            requisicao = socket_cliente.recv(1024).decode()
            if requisicao.startswith("GET"):
                indice_pedaco = int(requisicao.split(" ")[1])
                
                with self.lock_pedacos:
                    if indice_pedaco in self.meus_pedacos:
                        # Define arquivo fonte dependendo se é seed ou leecher
                        arquivo_origem = NOME_ARQUIVO if self.eh_semeador_inicial else self.id_par.replace(":", "_") + "_" + NOME_ARQUIVO
                        
                        with open(arquivo_origem, 'rb') as f:
                            f.seek(indice_pedaco * TAMANHO_PEDACO)
                            dados = f.read(TAMANHO_PEDACO)
                            
                            # Envia dados em chunks
                            bytes_enviados = 0
                            while bytes_enviados < len(dados):
                                chunk = dados[bytes_enviados:bytes_enviados + BUFFER_SIZE]
                                socket_cliente.sendall(chunk)
                                bytes_enviados += len(chunk)

                        print(f"Enviado pedaço {indice_pedaco}")
                    else:
                        socket_cliente.sendall(b"ERRO: Pedaco nao encontrado")
        except Exception as e:
            print(f"Erro na requisição: {e}")
        finally:
            try:
                socket_cliente.close()
            except:
                pass

    def iniciar_download(self):
        """Loop principal de download do peer"""
        if self.eh_semeador_inicial:
            print(f"Semeador {self.id_par} aguardando conexões.")
            self.rastreador.registrar(self.id_par, list(self.meus_pedacos))
            return

        ultima_atualizacao_pool = 0
        
        # Loop até completar download
        while len(self.meus_pedacos) < TOTAL_PEDACOS:
            print(f"\nProgresso {self.id_par}: {len(self.meus_pedacos)}/{TOTAL_PEDACOS} ({(len(self.meus_pedacos)/TOTAL_PEDACOS)*100:.1f}%)")
            
            # Atualiza estado no tracker
            with self.lock_pedacos:
                self.rastreador.registrar(self.id_par, list(self.meus_pedacos))
            
            info_todos_pares = self.rastreador.obter_pares()
            
            # Atualiza número de downloads a cada 5 segundos
            tempo_atual = time.time()
            if tempo_atual - ultima_atualizacao_pool > 5:
                self.max_downloads_atual = self.calcular_downloads_otimos(info_todos_pares)
                ultima_atualizacao_pool = tempo_atual
            
            # Limpa downloads concluídos
            self._processar_downloads_concluidos()
            
            # Inicia novos downloads
            self._iniciar_novos_downloads(info_todos_pares)
            
            time.sleep(INTERVALO_ATUALIZACAO)
        
        print(f"\n*** {self.id_par}: DOWNLOAD COMPLETO! ***")
        self.rastreador.registrar(self.id_par, list(self.meus_pedacos))
        
        # Transforma-se em seed após completar
        while True:
            time.sleep(60)

    def _processar_downloads_concluidos(self):
        """Remove downloads finalizados da lista ativa"""
        concluidos = []
        for pedaco, future in self.downloads_ativos.items():
            if future.done():
                concluidos.append(pedaco)
                try:
                    sucesso = future.result()
                    if not sucesso:
                        with self.lock_pedacos:
                            self.pedacos_sendo_baixados.discard(pedaco)
                except Exception as e:
                    print(f"Erro no download do pedaço {pedaco}: {e}")
                    with self.lock_pedacos:
                        self.pedacos_sendo_baixados.discard(pedaco)
        
        for pedaco in concluidos:
            del self.downloads_ativos[pedaco]

    def _iniciar_novos_downloads(self, info_todos_pares):
        """Inicia novos downloads respeitando o limite máximo"""
        downloads_disponiveis = len(self.downloads_ativos)
        slots_livres = self.max_downloads_atual - downloads_disponiveis
        
        if slots_livres <= 0:
            return
        
        # Obtém pedaços disponíveis ordenados por raridade
        pedacos_disponiveis = self.obter_todos_pedacos_disponiveis(info_todos_pares)
        pedacos_para_baixar = pedacos_disponiveis[:slots_livres]
        
        # Submete novos downloads
        futures_batch = []
        for pedaco, pares_disponiveis in pedacos_para_baixar:
            # Prioriza seeds sobre peers
            seeds = [p for p in pares_disponiveis if len(info_todos_pares.get(p, [])) == TOTAL_PEDACOS]
            peers = [p for p in pares_disponiveis if p not in seeds]
            
            par_escolhido = random.choice(seeds) if seeds else (random.choice(peers) if peers else None)
            if not par_escolhido:
                continue
                
            host, porta = par_escolhido.split(":")
            
            with self.lock_pedacos:
                self.pedacos_sendo_baixados.add(pedaco)
            
            # Submete tarefa de download
            future = self.executor_downloads.submit(
                self.requisitar_pedaco_do_par, host, int(porta), pedaco
            )
            self.downloads_ativos[pedaco] = future
            futures_batch.append((pedaco, par_escolhido))
        
        if futures_batch:
            print(f"Iniciando {len(futures_batch)} downloads simultâneos")
            for pedaco, par in futures_batch:
                print(f"  Pedaço {pedaco} de {par}")

    def obter_todos_pedacos_disponiveis(self, info_todos_pares):
        """Retorna lista de pedaços disponíveis ordenados por raridade"""
        contagem_pedacos = defaultdict(list)
        
        # Contabiliza pedaços disponíveis
        for id_par, pedacos in info_todos_pares.items():
            if id_par != self.id_par:
                for pedaco in pedacos:
                    with self.lock_pedacos:
                        if pedaco not in self.meus_pedacos and pedaco not in self.pedacos_sendo_baixados:
                            contagem_pedacos[pedaco].append(id_par)
        
        if not contagem_pedacos:
            return []
        
        # Ordena por menor disponibilidade (rarest first)
        return sorted(contagem_pedacos.items(), key=lambda item: (len(item[1]), item[0]))

    def requisitar_pedaco_do_par(self, host, porta, indice_pedaco):
        """Baixa um pedaço específico de outro par"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(TIMEOUT_CONEXAO)
                s.connect((host, porta))
                s.sendall(f"GET {indice_pedaco}".encode())
                
                # Recebe dados do pedaço
                dados = b''
                while len(dados) < TAMANHO_PEDACO:
                    try:
                        pacote = s.recv(min(BUFFER_SIZE, TAMANHO_PEDACO - len(dados)))
                        if not pacote:
                            break
                        dados += pacote
                    except socket.timeout:
                        break
                
                if len(dados) == TAMANHO_PEDACO:
                    self.salvar_pedaco(indice_pedaco, dados)
                    return True
                else:
                    print(f"Dados incompletos para pedaço {indice_pedaco}: {len(dados)}/{TAMANHO_PEDACO}")
                    return False
        except Exception as e:
            print(f"Falha ao baixar pedaço {indice_pedaco} de {host}:{porta}: {e}")
            return False
        finally:
            with self.lock_pedacos:
                self.pedacos_sendo_baixados.discard(indice_pedaco)

    def salvar_pedaco(self, indice_pedaco, dados):
        """Salva pedaço baixado no arquivo local"""
        caminho_arquivo = self.id_par.replace(":", "_") + "_" + NOME_ARQUIVO
        
        with self.lock_pedacos:
            # Escreve no arquivo
            with open(caminho_arquivo, 'r+b') as f:
                f.seek(indice_pedaco * TAMANHO_PEDACO)
                f.write(dados)
            
            self.meus_pedacos.add(indice_pedaco)
            self.pedacos_sendo_baixados.discard(indice_pedaco)
        
        print(f"Pedaço {indice_pedaco} salvo. Total: {len(self.meus_pedacos)}")

    def __del__(self):
        """Destrutor - garante shutdown limpo do executor"""
        if hasattr(self, 'executor_downloads'):
            self.executor_downloads.shutdown(wait=True)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 4:
        print("Uso: python par.py <host> <porta> <semeador (true/false)>")
        sys.exit(1)
        
    host = sys.argv[1]
    porta = int(sys.argv[2])
    eh_semeador = sys.argv[3].lower() == 'true'
    
    par = Par(host, porta, eh_semeador)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Encerrando o par...")