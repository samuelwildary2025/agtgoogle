"""
Script para fazer upload de arquivo para Google File Search
Usa a API REST Media Upload do Google
"""

import os
import json
import requests
import time

API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("Configure GOOGLE_API_KEY")

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
UPLOAD_URL = "https://generativelanguage.googleapis.com/upload/v1beta"

STORE_NAME = "fileSearchStores/produtossupermercadoqueiroz-qhsuc929p2ie"


def upload_to_file_search(arquivo: str):
    """Faz upload de arquivo diretamente para o FileSearchStore usando resumable upload."""
    print(f"📤 Fazendo upload de {arquivo} para {STORE_NAME}")
    
    # Ler arquivo
    with open(arquivo, 'rb') as f:
        content = f.read()
    
    file_size = len(content)
    mime_type = "text/csv" if arquivo.endswith(".csv") else "application/json"
    display_name = os.path.basename(arquivo)
    
    print(f"   Tamanho: {file_size / 1024:.1f} KB | MIME: {mime_type}")
    
    # 1. Iniciar upload resumable
    init_url = f"{UPLOAD_URL}/{STORE_NAME}:uploadToFileSearchStore?key={API_KEY}"
    
    headers = {
        "X-Goog-Upload-Protocol": "resumable",
        "X-Goog-Upload-Command": "start",
        "X-Goog-Upload-Header-Content-Length": str(file_size),
        "X-Goog-Upload-Header-Content-Type": mime_type,
        "Content-Type": "application/json"
    }
    
    metadata = {
        "displayName": display_name
    }
    
    print("   Iniciando upload...")
    init_response = requests.post(init_url, headers=headers, json=metadata)
    
    if init_response.status_code != 200:
        print(f"❌ Erro ao iniciar upload: {init_response.status_code}")
        print(init_response.text)
        return None
    
    # Pegar URL de upload
    upload_uri = init_response.headers.get("X-Goog-Upload-URL")
    if not upload_uri:
        print("❌ Não encontrou URL de upload")
        print(init_response.headers)
        return None
    
    # 2. Fazer upload do conteúdo
    print("   Enviando conteúdo...")
    upload_headers = {
        "X-Goog-Upload-Command": "upload, finalize",
        "X-Goog-Upload-Offset": "0",
        "Content-Type": mime_type
    }
    
    upload_response = requests.post(upload_uri, headers=upload_headers, data=content)
    
    if upload_response.status_code == 200:
        result = upload_response.json()
        print(f"✅ Upload concluído!")
        print(f"   Operação: {result.get('name', 'N/A')}")
        
        # 3. Aguardar processamento (indexação)
        operation_name = result.get("name")
        if operation_name:
            print("⏳ Aguardando indexação...")
            while True:
                time.sleep(5)
                op_url = f"{BASE_URL}/{operation_name}?key={API_KEY}"
                op_response = requests.get(op_url)
                if op_response.status_code == 200:
                    op_data = op_response.json()
                    if op_data.get("done"):
                        print("✅ Indexação concluída!")
                        return op_data
                    else:
                        print("   ...ainda processando")
                else:
                    print(f"   Erro ao verificar status: {op_response.status_code}")
                    break
        return result
    else:
        print(f"❌ Erro no upload: {upload_response.status_code}")
        print(upload_response.text)
        return None


def testar_busca(query: str):
    """Testa busca no FileSearchStore usando generateContent."""
    print(f"\n🔍 Testando busca: '{query}'")
    
    url = f"{BASE_URL}/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    
    payload = {
        "contents": [
            {
                "parts": [{"text": f"Encontre produtos relacionados a: {query}. Liste EAN, nome exato e categoria."}]
            }
        ],
        "tools": [
            {
                "fileSearch": {
                    "fileSearchStoreNames": [STORE_NAME]
                }
            }
        ]
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        data = response.json()
        text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        print(f"📝 Resposta:\n{text}")
        return text
    else:
        print(f"❌ Erro: {response.status_code}")
        print(response.text)
        return None


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python upload_file_search.py upload <arquivo>")
        print("  python upload_file_search.py buscar <query>")
    elif sys.argv[1] == "upload" and len(sys.argv) >= 3:
        upload_to_file_search(sys.argv[2])
    elif sys.argv[1] == "buscar" and len(sys.argv) >= 3:
        testar_busca(" ".join(sys.argv[2:]))
    else:
        print("Comando inválido")
