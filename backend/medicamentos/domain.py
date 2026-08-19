import re


CLASSIFICACAO_MANIPULADO = "MANIPULADO"
MARCADOR_MANIPULADO_RE = re.compile(r"\(\s*MANIPULADO\s*\)", re.IGNORECASE)


def descricao_possui_marcador_manipulado(descricao):
    return bool(MARCADOR_MANIPULADO_RE.search(descricao or ""))


def nome_classificacao_manipulado(nome):
    return (nome or "").strip().casefold() == CLASSIFICACAO_MANIPULADO.casefold()
