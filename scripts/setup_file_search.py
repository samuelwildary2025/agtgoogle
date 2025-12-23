"""
Script para configurar o Google File Search com produtos do supermercado
Usa REST API diretamente (mais compatível)

Uso: python3 scripts/setup_file_search.py --criar
"""

import os
import json
import time
import requests

# API key
API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("Configure GOOGLE_API_KEY ou GEMINI_API_KEY")

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

# Nome do store
STORE_DISPLAY_NAME = "produtos-supermercado-queiroz"


def criar_file_search_store():
    """Cria um novo FileSearchStore para os produtos."""
    print(f"📦 Criando FileSearchStore: {STORE_DISPLAY_NAME}")
    
    url = f"{BASE_URL}/fileSearchStores?key={API_KEY}"
    payload = {"displayName": STORE_DISPLAY_NAME}
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Store criado: {data.get('name')}")
        return data
    else:
        print(f"❌ Erro: {response.status_code}")
        print(response.text)
        return None


def listar_stores():
    """Lista todos os FileSearchStores existentes."""
    print("📋 Listando stores existentes:")
    
    url = f"{BASE_URL}/fileSearchStores?key={API_KEY}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        stores = data.get("fileSearchStores", [])
        for store in stores:
            print(f"  - {store.get('name')} ({store.get('displayName')})")
        return stores
    else:
        print(f"❌ Erro: {response.status_code}")
        print(response.text)
        return []


def upload_produtos(store_name: str, arquivo_json: str):
    """
    Faz upload de um arquivo JSON de produtos para o FileSearchStore.
    """
    print(f"📤 Fazendo upload de {arquivo_json} para {store_name}")
    
    # Primeiro, fazer upload do arquivo para a Files API
    upload_url = f"{BASE_URL}/files?key={API_KEY}"
    
    with open(arquivo_json, 'rb') as f:
        file_content = f.read()
    
    # Metadata
    metadata = {
        "file": {
            "displayName": os.path.basename(arquivo_json)
        }
    }
    
    # Upload multipart
    files = {
        'metadata': (None, json.dumps(metadata), 'application/json'),
        'file': (os.path.basename(arquivo_json), file_content, 'application/json')
    }
    
    # Upload para o File Search Store
    url = f"https://generativelanguage.googleapis.com/upload/v1beta/{store_name}:uploadfile?key={API_KEY}"
    
    with open(arquivo_json, 'rb') as f:
        response = requests.post(
            url,
            files={'file': (os.path.basename(arquivo_json), f, 'application/json')},
            data={'display_name': os.path.basename(arquivo_json)}
        )
    
    if response.status_code in [200, 201]:
        print("✅ Upload concluído!")
        print(response.json())
        return response.json()
    else:
        print(f"❌ Erro no upload: {response.status_code}")
        print(response.text)
        return None


def criar_arquivo_produtos_exemplo():
    """Cria um arquivo JSON de exemplo com produtos para teste."""
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
            "sinonimos": ["agua sanitaria", "kiboa", "quiboa", "clorito", "desinfetante"],
            "preco": 3.49,
            "unidade": "un",
            "categoria": "limpeza",
            "descricao": "Água sanitária 1 litro"
        },
        {
            "ean": "243",
            "nome": "COXA SOBRECOXA MQ",
            "sinonimos": ["sobrecoxa", "coxa de frango", "coxa e sobrecoxa"],
            "preco": 12.99,
            "unidade": "kg",
            "categoria": "açougue",
            "descricao": "Coxa e sobrecoxa de frango"
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
    parser.add_argument("--exemplo", action="store_true", help="Criar arquivo de produtos de exemplo")
    parser.add_argument("--search", type=str, help="Buscar produtos por query (requer GOOGLE_API_KEY)")
    
    args = parser.parse_args()
    
    if args.exemplo:
        criar_arquivo_produtos_exemplo()
    
    if args.listar:
        listar_stores()
    
    if args.criar:
        store = criar_file_search_store()
        if store:
            print(f"\n💡 Use este nome no agente: {store.get('name')}")
    
    if args.upload and args.store:
        upload_produtos(args.store, args.upload)
    
    if args.search:
        import sys
        sys.path.append(os.getcwd())
        # Tentar importar de http_tools, se falhar, implementar busca direta
        try:
            from tools.http_tools import busca_file_search
            print(f"\n🔍 Buscando '{args.search}' no File Search...")
            resultado = busca_file_search(args.search)
            print("\nRESULTADO RAW:")
            print(resultado)
        except Exception as e:
            print(f"❌ Erro ao importar/buscar: {e}")
            # Fallback para implementação local caso imports falhem
            pass
    
    if not any([args.criar, args.listar, args.upload, args.exemplo, args.search]):
        print("Uso:")
        print("  python3 setup_file_search.py --criar              # Criar store")
        print("  python3 setup_file_search.py --listar             # Listar stores")
        print("  python3 setup_file_search.py --exemplo            # Criar JSON exemplo")
        print("  python3 setup_file_search.py --store NOME --upload arquivo.json")
        print("  python3 setup_file_search.py --search 'tomate'    # Testar busca")
