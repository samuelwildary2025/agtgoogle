"""
Script para configurar o Google File Search com produtos do supermercado
Uso: python scripts/setup_file_search.py

Requisitos:
- pip install google-genai
- Exportar GEMINI_API_KEY ou passar como argumento
"""

import os
import json
import time
from google import genai
from google.genai import types

# Configurar cliente
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("Configure GEMINI_API_KEY ou GOOGLE_API_KEY")

client = genai.Client(api_key=api_key)

# Nome do store (pode ser customizado)
STORE_NAME = "produtos-supermercado-queiroz"


def criar_file_search_store():
    """Cria um novo FileSearchStore para os produtos."""
    print(f"📦 Criando FileSearchStore: {STORE_NAME}")
    
    file_search_store = client.file_search_stores.create(
        config={'display_name': STORE_NAME}
    )
    
    print(f"✅ Store criado: {file_search_store.name}")
    return file_search_store


def listar_stores():
    """Lista todos os FileSearchStores existentes."""
    print("📋 Listando stores existentes:")
    for store in client.file_search_stores.list():
        print(f"  - {store.name} ({store.display_name})")
    return list(client.file_search_stores.list())


def upload_produtos(store_name: str, arquivo_json: str):
    """
    Faz upload de um arquivo JSON de produtos para o FileSearchStore.
    O arquivo deve conter uma lista de produtos com nome, ean, preço, etc.
    """
    print(f"📤 Fazendo upload de {arquivo_json} para {store_name}")
    
    # Iniciar upload
    operation = client.file_search_stores.upload_to_file_search_store(
        file=arquivo_json,
        file_search_store_name=store_name,
        config={
            'display_name': os.path.basename(arquivo_json),
        }
    )
    
    # Aguardar conclusão
    print("⏳ Aguardando processamento...")
    while not operation.done:
        time.sleep(5)
        operation = client.operations.get(operation)
        print("  ...ainda processando")
    
    print("✅ Upload concluído e indexado!")
    return operation


def testar_busca(store_name: str, query: str):
    """Testa uma busca semântica no FileSearchStore."""
    print(f"\n🔍 Testando busca: '{query}'")
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"Encontre produtos relacionados a: {query}. Liste nome, preço e EAN.",
        config=types.GenerateContentConfig(
            tools=[
                types.Tool(
                    file_search=types.FileSearch(
                        file_search_store_names=[store_name]
                    )
                )
            ]
        )
    )
    
    print(f"📝 Resposta:\n{response.text}")
    return response


def criar_arquivo_produtos_exemplo():
    """Cria um arquivo JSON de exemplo com produtos."""
    produtos = [
        {
            "ean": "550",
            "nome": "FRANGO ABATIDO INTEIRO",
            "sinonimos": ["frango", "frango inteiro", "galinha"],
            "preco": 15.99,
            "unidade": "kg",
            "categoria": "açougue",
            "descricao": "Frango abatido inteiro resfriado"
        },
        {
            "ean": "751320919434",
            "nome": "SALSINHA EFRAIM",
            "sinonimos": ["salsa", "salsinha", "tempero verde"],
            "preco": 2.59,
            "unidade": "un",
            "categoria": "hortifruti",
            "descricao": "Salsinha fresca para tempero"
        },
        {
            "ean": "7896221600012",
            "nome": "AGUA SANITARIA DRAGAO 1L",
            "sinonimos": ["agua sanitaria", "clorito", "desinfetante"],
            "preco": 3.49,
            "unidade": "un",
            "categoria": "limpeza",
            "descricao": "Água sanitária 1 litro"
        }
    ]
    
    arquivo = "scripts/produtos_exemplo.json"
    with open(arquivo, 'w', encoding='utf-8') as f:
        json.dump(produtos, f, ensure_ascii=False, indent=2)
    
    print(f"📄 Arquivo de exemplo criado: {arquivo}")
    return arquivo


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Gerenciar Google File Search para produtos")
    parser.add_argument("--criar", action="store_true", help="Criar novo FileSearchStore")
    parser.add_argument("--listar", action="store_true", help="Listar stores existentes")
    parser.add_argument("--upload", type=str, help="Fazer upload de arquivo JSON")
    parser.add_argument("--store", type=str, help="Nome do store para operações")
    parser.add_argument("--buscar", type=str, help="Testar busca com uma query")
    parser.add_argument("--exemplo", action="store_true", help="Criar arquivo de produtos de exemplo")
    
    args = parser.parse_args()
    
    if args.exemplo:
        criar_arquivo_produtos_exemplo()
    
    if args.listar:
        listar_stores()
    
    if args.criar:
        store = criar_file_search_store()
        print(f"\n💡 Use este nome no agente: {store.name}")
    
    if args.upload and args.store:
        upload_produtos(args.store, args.upload)
    
    if args.buscar and args.store:
        testar_busca(args.store, args.buscar)
    
    if not any([args.criar, args.listar, args.upload, args.buscar, args.exemplo]):
        print("Uso:")
        print("  python setup_file_search.py --criar              # Criar store")
        print("  python setup_file_search.py --listar             # Listar stores")
        print("  python setup_file_search.py --exemplo            # Criar JSON exemplo")
        print("  python setup_file_search.py --store NOME --upload arquivo.json")
        print("  python setup_file_search.py --store NOME --buscar 'frango'")
