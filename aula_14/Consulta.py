import unicodedata
from urllib.parse import quote

import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from deep_translator import GoogleTranslator
from deep_translator.exceptions import (
    BaseError as TranslationError,
    RequestError as TranslationRequestError,
    ServerException as TranslationServerError,
    TooManyRequests as TranslationRateLimitError,
)
from pydantic import BaseModel, ValidationError
from requests.exceptions import RequestException

app = FastAPI()
URL_BASE = "https://www.fruityvice.com/api/fruit"
FRUTAS_EM_INGLES = {
    "abacate": "avocado",
    "abacaxi": "pineapple",
    "ameixa": "plum",
    "amora": "blackberry",
    "caqui": "persimmon",
    "cereja": "cherry",
    "figo": "fig",
    "framboesa": "raspberry",
    "goiaba": "guava",
    "jaca": "jackfruit",
    "laranja": "orange",
    "lima": "lime",
    "limao": "lemon",
    "maca": "apple",
    "mamao": "papaya",
    "manga": "mango",
    "maracuja": "passionfruit",
    "melao": "melon",
    "melancia": "watermelon",
    "mirtilo": "blueberry",
    "morango": "strawberry",
    "pera": "pear",
    "pessego": "peach",
    "pitaya": "dragonfruit",
    "roma": "pomegranate",
    "uva": "grape",
}


class FruityviceNutrition(BaseModel):
    calories: float
    sugar: float


class FruityviceFruit(BaseModel):
    name: str
    nutritions: FruityviceNutrition


class FruitResponse(BaseModel):
    nome: str
    calorias: float
    acucar: float


class SucoCreate(BaseModel):
    nome: str
    frutas: list[str]
    descricao_gosto: str


class SucoUpdate(BaseModel):
    frutas: list[str]


class SucoResponse(BaseModel):
    id: int
    nome: str
    frutas: list[str]
    descricao_gosto: str
    calorias: float
    acucar: float


sucos: dict[int, SucoResponse] = {}
next_suco_id = 1


@app.get("/", include_in_schema=False)
def pagina_inicial() -> RedirectResponse:
    return RedirectResponse(url="/docs")


def normalizar_nome_fruta(nome: str) -> str:
    nome_normalizado = unicodedata.normalize("NFKD", nome.strip().casefold())
    return "".join(
        caractere
        for caractere in nome_normalizado
        if not unicodedata.combining(caractere)
    )


def consultar_fruta(nome: str) -> FruityviceFruit:
    nome_limpo = nome.strip()
    nome_normalizado = normalizar_nome_fruta(nome_limpo)
    nome_para_consulta = FRUTAS_EM_INGLES.get(nome_normalizado, nome_limpo)

    try:
        return consultar_fruityvice(nome_para_consulta, nome_limpo)
    except HTTPException as error:
        if error.status_code != 404 or nome_normalizado in FRUTAS_EM_INGLES:
            raise

    try:
        nome_traduzido = GoogleTranslator(source="auto", target="en").translate(
            nome_limpo
        )
    except (
        TranslationError,
        TranslationRequestError,
        TranslationServerError,
        TranslationRateLimitError,
        RequestException,
    ) as error:
        raise HTTPException(
            status_code=502,
            detail="Não foi possível traduzir o nome da fruta. Tente novamente.",
        ) from error

    if not nome_traduzido or normalizar_nome_fruta(nome_traduzido) == nome_normalizado:
        raise HTTPException(
            status_code=404, detail=f"A fruta '{nome}' não foi encontrada."
        )

    return consultar_fruityvice(nome_traduzido, nome_limpo)


def consultar_fruityvice(nome_para_consulta: str, nome_original: str) -> FruityviceFruit:
    url = f"{URL_BASE}/{quote(nome_para_consulta, safe='')}"

    try:
        response = requests.get(url, timeout=10)
    except RequestException as error:
        raise HTTPException(
            status_code=502, detail="Não foi possível consultar o serviço de frutas."
        ) from error

    if response.status_code == 404:
        raise HTTPException(
            status_code=404,
            detail=f"A fruta '{nome_original}' não foi encontrada.",
        )
    if response.status_code >= 400:
        raise HTTPException(
            status_code=502, detail="O serviço de frutas retornou um erro."
        )

    try:
        data = response.json()
    except ValueError as error:
        raise HTTPException(
            status_code=502, detail="Não foi possível consultar o serviço de frutas."
        ) from error

    try:
        return FruityviceFruit(**data)
    except (TypeError, ValidationError) as error:
        raise HTTPException(
            status_code=502, detail="O serviço de frutas retornou dados inválidos."
        ) from error


def calcular_nutrientes(frutas: list[str]) -> tuple[float, float]:
    if not frutas:
        raise HTTPException(
            status_code=422, detail="Informe pelo menos uma fruta."
        )

    calorias = 0.0
    acucar = 0.0
    for nome in frutas:
        fruta = consultar_fruta(nome)
        calorias += fruta.nutritions.calories
        acucar += fruta.nutritions.sugar

    return calorias, acucar


@app.get("/frutas/{nome}", response_model=FruitResponse)
def get_fruta(nome: str) -> FruitResponse:
    fruta = consultar_fruta(nome)
    return FruitResponse(
        nome=nome.strip(),
        calorias=fruta.nutritions.calories,
        acucar=fruta.nutritions.sugar,
    )


@app.post("/sucos", response_model=SucoResponse, status_code=201)
def criar_suco(suco: SucoCreate) -> SucoResponse:
    global next_suco_id

    calorias, acucar = calcular_nutrientes(suco.frutas)
    novo_suco = SucoResponse(
        id=next_suco_id,
        nome=suco.nome,
        frutas=suco.frutas,
        descricao_gosto=suco.descricao_gosto,
        calorias=calorias,
        acucar=acucar,
    )
    sucos[next_suco_id] = novo_suco
    next_suco_id += 1
    return novo_suco


@app.get("/sucos", response_model=list[SucoResponse])
def listar_sucos() -> list[SucoResponse]:
    return list(sucos.values())


@app.put("/sucos/{id}", response_model=SucoResponse)
def atualizar_suco(id: int, atualizacao: SucoUpdate) -> SucoResponse:
    suco = sucos.get(id)
    if suco is None:
        raise HTTPException(
            status_code=404, detail=f"O suco com ID {id} não foi encontrado."
        )

    calorias, acucar = calcular_nutrientes(atualizacao.frutas)
    suco_atualizado = SucoResponse(
        id=suco.id,
        nome=suco.nome,
        frutas=atualizacao.frutas,
        descricao_gosto=suco.descricao_gosto,
        calorias=calorias,
        acucar=acucar,
    )
    sucos[id] = suco_atualizado
    return suco_atualizado


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
