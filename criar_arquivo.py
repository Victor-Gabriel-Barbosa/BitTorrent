import os

def criar_arquivo_teste(nome_arquivo, tamanho_mb):
    """
    Cria um arquivo de teste com tamanho específico preenchido com bytes nulos.
    """
    tamanho_bytes = tamanho_mb * 1024 * 1024

    if os.path.exists(nome_arquivo):
        print(f"O arquivo '{nome_arquivo}' já existe.")
        return
        
    print(f"Criando o arquivo de teste '{nome_arquivo}' com {tamanho_mb} MB...")
    
    with open(nome_arquivo, 'wb') as f:
        tamanho_bloco = 1024 * 1024  # 1 MB
        numero_blocos = tamanho_mb
        
        for _ in range(numero_blocos):
            f.write(b'\0' * tamanho_bloco)
            
    print("Arquivo de teste criado com sucesso!")

if __name__ == "__main__":
    NOME_ARQUIVO = "ubuntu-teste.iso"
    TAMANHO_ARQUIVO_MB = 500
    
    criar_arquivo_teste(NOME_ARQUIVO, TAMANHO_ARQUIVO_MB)