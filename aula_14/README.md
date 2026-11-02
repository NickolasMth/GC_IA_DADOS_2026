# API Casa de Sucos

API REST em Python com FastAPI para consultar frutas na Fruityvice e cadastrar
sucos com o total de calorias e açúcar. Os valores nutricionais consideram
100 g de cada fruta.

## Requisitos

- Python 3.10 ou superior
- Acesso à internet para consultar a Fruityvice

## Instalação e execução no Windows

No PowerShell, na pasta do projeto:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python Consulta.py
```

O servidor inicia em `http://127.0.0.1:8000`. Acesse
`http://127.0.0.1:8000/docs` para abrir o Swagger e testar as rotas.
Também é possível iniciar com `python -m uvicorn Consulta:app --reload`.

## Rotas

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/frutas/{nome}` | Consulta calorias e açúcar de uma fruta |
| `POST` | `/sucos` | Cadastra um suco e calcula seus valores nutricionais |
| `GET` | `/sucos` | Lista os sucos cadastrados |
| `PUT` | `/sucos/{id}` | Atualiza as frutas de um suco e recalcula os totais |

O endpoint de frutas aceita nomes em português e em inglês. Nomes comuns em
português são convertidos por um mapeamento local; se o nome não estiver nesse
mapeamento e não for encontrado diretamente, a API tenta traduzi-lo
automaticamente do idioma detectado para inglês com `deep-translator` e então
consulta a Fruityvice. Exemplos: `maçã`/`maca` → `apple`, `morango` →
`strawberry`, `abacaxi` → `pineapple` e `maracujá` → `passionfruit`. A
tradução automática precisa de internet e depende do serviço de tradução; se
esse serviço estiver indisponível, a API retorna `502`.

## Exemplos para testar no Swagger

Abra `/docs`, expanda a rota desejada, clique em **Try it out** e depois em
**Execute**.

### Consultar fruta em português

Na rota `GET /frutas/{nome}`, informe `maçã` no campo `nome`.

Exemplo de resposta (`200`):

```json
{
  "nome": "maçã",
  "calorias": 52.0,
  "acucar": 10.3
}
```

Os valores de calorias e açúcar vêm da Fruityvice e podem variar conforme os
dados fornecidos pelo serviço. Outro teste é consultar `banana`; a resposta
deve conter o nome informado e os dados nutricionais retornados pela API.

### Cadastrar suco

Na rota `POST /sucos`, use:

```json
{
  "nome": "Tropical",
  "frutas": ["banana", "morango"],
  "descricao_gosto": "Doce e refrescante"
}
```

Com as frutas válidas, a resposta é `201 Created` e inclui `id`, nome,
descrição, frutas e os totais de calorias e açúcar. Cada fruta conta como
100 g no cálculo.

Exemplo de resposta para as frutas `banana` e `morango`:

```json
{
  "id": 1,
  "nome": "Tropical",
  "frutas": ["banana", "morango"],
  "descricao_gosto": "Doce e refrescante",
  "calorias": 125.0,
  "acucar": 22.6
}
```

### Listar e atualizar sucos

1. Execute `GET /sucos` para consultar os sucos cadastrados.
2. Em `PUT /sucos/{id}`, informe o `id` retornado e o corpo:

```json
{
  "frutas": ["maçã", "laranja"]
}
```

A resposta contém a lista atualizada e os novos totais nutricionais.

### Erro de fruta não encontrada

Consulte um nome inexistente em `GET /frutas/{nome}` ou use-o no cadastro de
um suco. A API retorna `404` com uma mensagem informando qual fruta não foi
encontrada.

## Persistência

Os sucos são armazenados em memória e ficam disponíveis enquanto o processo
da API estiver em execução. Eles são apagados ao reiniciar o servidor.
