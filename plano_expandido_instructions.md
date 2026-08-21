# Instruções de Teste Expandidos (Fase 2)

## Requisitos de Implementação

Implemente os novos módulos de teste abaixo mantendo o padrão IEEE 829.

### 1. `tests/test_cidades_autocomplete.py`
Testar a view `CidadesAutocomplete` (`dal.autocomplete.Select2QuerySetView`):
- `test_autocomplete_sem_query`: Retorna queryset base sem filtro.
- `test_autocomplete_com_busca_exata`: Busca "Curitiba", valida ordenação e similaridade.
- `test_autocomplete_com_acentuacao`: Busca "Sao Paulo" sem acento, deve retornar "São Paulo" via `Unaccent`.
- `test_autocomplete_com_erro_ortografico`: Busca "Curtiba" com digitação errada, deve retornar "Curitiba" via `TrigramSimilarity`.
- `test_autocomplete_result_label`: Valida se o rótulo de retorno formatado contém `<p>Nome, Estado</p>`.
- `test_autocomplete_query_vazia_ou_espacos`: Busca apenas com espaços ou string vazia.
- `test_autocomplete_caracteres_especiais`: Busca com caracteres SQL/REGEX (`' OR '1'='1`, `%`, `_`, `<script>`).

### 2. `tests/test_index_view.py` (Melhorar cobertura da view `index`)
- `test_index_get_sucesso`: Requisição GET carrega formulários limpos e status 200.
- `test_index_post_sucesso_sem_arquivos`: Submissão do formulário de denúncia sem anexos de imagem.
- `test_index_post_sucesso_com_multiplas_imagens`: Submissão do formulário com múltiplos arquivos de imagem simultâneos (valida enfileiramento das tarefas `limpar_exif_imagem.delay`).
- `test_index_post_form_invalido`: Submissão com campos obrigatórios ausentes/inválidos renderiza erros no formulário sem redirecionar.
- `test_index_post_rate_limit_excedido`: Dispara mais de 10 POSTs em 1 minuto e valida resposta 429 (`ratelimited_error`).
- `test_index_get_rate_limit_excedido`: Dispara mais de 30 GETs em 1 minuto e valida resposta 429.

### 3. `tests/test_migration_0002.py`
Testar a função `popular_cidades_estados` e os índices de migração:
- `test_popular_cidades_estados_csv_existente`: Executa a função `popular_cidades_estados` com o CSV real e valida se Estados e Cidades são criados no banco de dados.
- `test_popular_cidades_estados_idempotencia`: Executa a função duas vezes consecutivas para garantir que `get_or_create` não duplica registros.
- `test_popular_cidades_estados_csv_inexistente`: Simula a ausência do CSV (mock de `os.path.exists` retornando False) e valida que a função lida com o aviso sem estourar exceção.

### 4. `tests/test_chaos.py` (Testes Adversariais / Cenários de Falha)
Testar cenários onde o código é forçado a falhar ou receber entradas inesperadas:
- `test_denuncia_descricao_payload_gigante`: Submeter uma denúncia com descrição de 500KB de texto para testar limites do banco/view.
- `test_task_exif_com_imagem_corrompida`: Executar `limpar_exif_imagem` com um arquivo binário corrompido (não-imagem) e validar que a exceção é tratada com log de erro sem derrubar o worker.
- `test_task_exif_id_inexistente`: Executar `limpar_exif_imagem` com ID que não existe na tabela `Evidencia`.
- `test_pesquisar_query_nula_e_caracteres_controle`: Buscar no endpoint `/pesquisar/` com `\x00`, `NULL`, strings imensas e caracteres unicodes raros.
- `test_protocolo_inexistente_retorna_404_ou_mensagem`: Buscar um protocolo UUID válido porém inexistente no banco e validar mensagem no template.

---

## Regras
- Crie ou atualize os arquivos no diretório `tests/`.
- Use `pytest`, `@pytest.mark.django_db` e `factory-boy`.
- Garanta que todos os testes passem.
