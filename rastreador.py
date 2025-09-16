from xmlrpc.server import SimpleXMLRPCServer
import threading
import time
from datetime import datetime
import os

class Rastreador:
    def __init__(self):
        # Estruturas para gerenciar pares e estatísticas
        self._pares = {}  # Dicionário de pares conectados {id_par: [pedacos]}
        self._trava = threading.Lock()  # Lock para acesso thread-safe
        self._stats = {
            'total_registros': 0,
            'total_consultas': 0,
            'inicio': datetime.now(),
            'historico_pedacos': {}  # Rastreia pedaços mais solicitados
        }
        
    def _limpar_tela(self):
        # Limpa o terminal (funciona em Windows e Unix)
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def _mostrar_interface(self):
        # Exibe interface visual do rastreador
        tempo_ativo = datetime.now() - self._stats['inicio']
        
        self._limpar_tela()
        print("╭─────────────────────────────────────────────────────────╮")
        print("│                    🔗 RASTREADOR P2P                    │")
        print("├─────────────────────────────────────────────────────────┤")
        print(f"│ ⏱️  Tempo ativo: {str(tempo_ativo).split('.')[0]:<25}               │")
        print(f"│ 👥 Pares conectados: {len(self._pares):<15}                    │")
        print(f"│ 📊 Total de registros: {self._stats['total_registros']:<13}                    │")
        print(f"│ 🔍 Total de consultas: {self._stats['total_consultas']:<13}                    │")
        print("├─────────────────────────────────────────────────────────┤")
        
        # Lista pares ativos com barras de progresso
        if self._pares:
            print("│                      PARES ATIVOS                       │")
            print("├─────────────────────────────────────────────────────────┤")
            for i, (id_par, pedacos) in enumerate(self._pares.items(), 1):
                status_bar = self._criar_barra_progresso(len(pedacos), 20)
                print(f"│ {i:2d}. {id_par:<20} [{status_bar}] {len(pedacos):3d}     │")
        else:
            print("│           🔍 Aguardando pares se conectarem...          │")
        
        # Mostra pedaços mais populares
        print("├─────────────────────────────────────────────────────────┤")
        if self._stats['historico_pedacos']:
            print("│                  PEDAÇOS POPULARES                      │")
            print("├─────────────────────────────────────────────────────────┤")
            pedacos_ordenados = sorted(self._stats['historico_pedacos'].items(), 
                                     key=lambda x: x[1], reverse=True)[:5]
            for pedaco, count in pedacos_ordenados:
                print(f"│ Pedaço {pedaco:3d}: {count:3d} consultas{'':23}│")
        
        print("╰─────────────────────────────────────────────────────────╯")
        print("\n💡 Pressione Ctrl+C para encerrar o servidor")
    
    def _criar_barra_progresso(self, valor, max_largura=20):
        # Cria barra de progresso visual baseada na completude do peer
        if valor == 0:
            return "░" * max_largura
        
        # Calcula porcentagem baseada no peer mais completo
        max_pedacos = max([len(p) for p in self._pares.values()] + [1])
        porcentagem = min(valor / max_pedacos, 1.0)
        
        blocos_preenchidos = int(porcentagem * max_largura)
        blocos_vazios = max_largura - blocos_preenchidos
        
        return "█" * blocos_preenchidos + "░" * blocos_vazios

    def registrar(self, id_par, pedacos):
        # Registra novo peer ou atualiza lista de pedaços de um peer existente
        with self._trava:
            self._pares[id_par] = pedacos
            self._stats['total_registros'] += 1
            self._mostrar_interface()
        return True

    def obter_pares(self):
        # Retorna lista de todos os pares conectados
        with self._trava:
            self._stats['total_consultas'] += 1
            self._mostrar_interface()
            return self._pares.copy()

    def obter_donos_pedaco(self, indice_pedaco):
        # Retorna lista de pares que possuem um pedaço específico
        with self._trava:
            self._stats['total_consultas'] += 1
            
            # Atualiza estatísticas de popularidade do pedaço
            if indice_pedaco not in self._stats['historico_pedacos']:
                self._stats['historico_pedacos'][indice_pedaco] = 0
            self._stats['historico_pedacos'][indice_pedaco] += 1
            
            # Encontra pares que possuem o pedaço
            donos = [id_par for id_par, pedacos in self._pares.items() 
                    if indice_pedaco in pedacos]
            
            self._mostrar_interface()
            return donos

def executar_rastreador(host='localhost', porta=8000):
    # Inicia servidor XML-RPC
    servidor = SimpleXMLRPCServer((host, porta), allow_none=True)
    rastreador = Rastreador()
    servidor.register_instance(rastreador)
    
    # Mostra interface inicial
    rastreador._mostrar_interface()
    print(f"\n🚀 Servidor iniciado em http://{host}:{porta}")
    
    try:
        # Mantém servidor executando
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\n\n🔴 Encerrando servidor...")
        servidor.shutdown()

if __name__ == "__main__":
    executar_rastreador()