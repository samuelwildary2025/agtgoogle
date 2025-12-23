-- =====================================================
-- SUPABASE VECTOR DATABASE PARA PRODUTOS
-- Execute este script no SQL Editor do Supabase
-- =====================================================

-- 1. Habilitar extensão pgvector (se ainda não estiver)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Criar tabela de produtos com coluna de embedding
CREATE TABLE IF NOT EXISTS produtos_vetorizados (
    id BIGSERIAL PRIMARY KEY,
    ean TEXT UNIQUE NOT NULL,                    -- Código EAN do produto
    nome TEXT NOT NULL,                           -- Nome do produto
    descricao TEXT,                               -- Descrição adicional
    sinonimos TEXT[],                             -- Array de sinônimos/termos regionais
    preco DECIMAL(10,2),                          -- Preço (opcional, pode buscar na API)
    unidade TEXT DEFAULT 'un',                    -- Unidade (un, kg, l, etc)
    categoria TEXT,                               -- Categoria do produto
    embedding vector(768),                        -- Vetor de embedding (768 dimensões para text-embedding-004)
    ativo BOOLEAN DEFAULT TRUE,                   -- Se o produto está ativo
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Criar índice para busca vetorial (HNSW é mais rápido para buscas)
CREATE INDEX IF NOT EXISTS produtos_embedding_idx 
ON produtos_vetorizados 
USING hnsw (embedding vector_cosine_ops);

-- 4. Índice para busca por EAN
CREATE INDEX IF NOT EXISTS produtos_ean_idx ON produtos_vetorizados(ean);

-- 5. Índice para busca por nome (texto)
CREATE INDEX IF NOT EXISTS produtos_nome_idx ON produtos_vetorizados USING gin(to_tsvector('portuguese', nome));

-- 6. Função de busca por similaridade vetorial
CREATE OR REPLACE FUNCTION buscar_produtos_similares(
    query_embedding vector(768),
    limite INT DEFAULT 5,
    threshold FLOAT DEFAULT 0.5
)
RETURNS TABLE (
    id BIGINT,
    ean TEXT,
    nome TEXT,
    descricao TEXT,
    preco DECIMAL,
    unidade TEXT,
    categoria TEXT,
    similaridade FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id,
        p.ean,
        p.nome,
        p.descricao,
        p.preco,
        p.unidade,
        p.categoria,
        1 - (p.embedding <=> query_embedding) as similaridade
    FROM produtos_vetorizados p
    WHERE p.ativo = TRUE
      AND 1 - (p.embedding <=> query_embedding) > threshold
    ORDER BY p.embedding <=> query_embedding
    LIMIT limite;
END;
$$ LANGUAGE plpgsql;

-- 7. Função para upsert de produto (inserir ou atualizar)
CREATE OR REPLACE FUNCTION upsert_produto(
    p_ean TEXT,
    p_nome TEXT,
    p_descricao TEXT DEFAULT NULL,
    p_sinonimos TEXT[] DEFAULT NULL,
    p_preco DECIMAL DEFAULT NULL,
    p_unidade TEXT DEFAULT 'un',
    p_categoria TEXT DEFAULT NULL,
    p_embedding vector(768) DEFAULT NULL
)
RETURNS BIGINT AS $$
DECLARE
    produto_id BIGINT;
BEGIN
    INSERT INTO produtos_vetorizados (ean, nome, descricao, sinonimos, preco, unidade, categoria, embedding)
    VALUES (p_ean, p_nome, p_descricao, p_sinonimos, p_preco, p_unidade, p_categoria, p_embedding)
    ON CONFLICT (ean) DO UPDATE SET
        nome = EXCLUDED.nome,
        descricao = EXCLUDED.descricao,
        sinonimos = COALESCE(EXCLUDED.sinonimos, produtos_vetorizados.sinonimos),
        preco = COALESCE(EXCLUDED.preco, produtos_vetorizados.preco),
        unidade = EXCLUDED.unidade,
        categoria = EXCLUDED.categoria,
        embedding = COALESCE(EXCLUDED.embedding, produtos_vetorizados.embedding),
        updated_at = NOW()
    RETURNING id INTO produto_id;
    
    RETURN produto_id;
END;
$$ LANGUAGE plpgsql;

-- 8. Trigger para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS produtos_updated_at ON produtos_vetorizados;
CREATE TRIGGER produtos_updated_at
    BEFORE UPDATE ON produtos_vetorizados
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- 9. Habilitar RLS (Row Level Security) se necessário
ALTER TABLE produtos_vetorizados ENABLE ROW LEVEL SECURITY;

-- 10. Policy para permitir leitura pública (ajuste conforme necessário)
CREATE POLICY "Permitir leitura pública de produtos"
ON produtos_vetorizados
FOR SELECT
USING (true);

-- 11. Policy para permitir inserção/atualização via service_role
CREATE POLICY "Permitir escrita via service_role"
ON produtos_vetorizados
FOR ALL
USING (auth.role() = 'service_role');

-- =====================================================
-- PRONTO! Agora você pode:
-- 1. Usar o n8n para inserir produtos com embeddings
-- 2. Chamar buscar_produtos_similares() com um vetor de consulta
-- =====================================================
