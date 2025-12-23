// Supabase Edge Function: busca-produtos-vetor
// Endpoint para o agente buscar produtos por similaridade vetorial
// Deploy: supabase functions deploy busca-produtos-vetor

import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

// Usar Google Generative AI para embeddings
async function getEmbedding(text: string, apiKey: string): Promise<number[]> {
    const response = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key=${apiKey}`,
        {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                model: 'models/text-embedding-004',
                content: { parts: [{ text }] }
            })
        }
    )

    const data = await response.json()
    return data.embedding?.values || []
}

serve(async (req) => {
    // Handle CORS preflight
    if (req.method === 'OPTIONS') {
        return new Response('ok', { headers: corsHeaders })
    }

    try {
        const { query, limite = 5, threshold = 0.4 } = await req.json()

        if (!query) {
            return new Response(
                JSON.stringify({ error: 'Query é obrigatória' }),
                { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
            )
        }

        // Configurações
        const supabaseUrl = Deno.env.get('SUPABASE_URL')!
        const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
        const googleApiKey = Deno.env.get('GOOGLE_API_KEY')!

        const supabase = createClient(supabaseUrl, supabaseKey)

        // Gerar embedding da query
        console.log(`Gerando embedding para: "${query}"`)
        const queryEmbedding = await getEmbedding(query, googleApiKey)

        if (!queryEmbedding.length) {
            return new Response(
                JSON.stringify({ error: 'Falha ao gerar embedding' }),
                { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
            )
        }

        // Buscar produtos similares
        const { data: produtos, error } = await supabase.rpc('buscar_produtos_similares', {
            query_embedding: queryEmbedding,
            limite,
            threshold
        })

        if (error) {
            console.error('Erro na busca:', error)
            return new Response(
                JSON.stringify({ error: error.message }),
                { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
            )
        }

        // Formatar resposta
        const response = {
            query,
            total: produtos?.length || 0,
            produtos: produtos?.map((p: any) => ({
                ean: p.ean,
                nome: p.nome,
                preco: p.preco,
                unidade: p.unidade,
                categoria: p.categoria,
                similaridade: Math.round(p.similaridade * 100)
            })) || []
        }

        console.log(`Encontrados ${response.total} produtos para "${query}"`)

        return new Response(
            JSON.stringify(response),
            { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )

    } catch (err) {
        console.error('Erro:', err)
        return new Response(
            JSON.stringify({ error: err.message }),
            { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
    }
})
