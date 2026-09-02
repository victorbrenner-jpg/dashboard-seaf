"""Ajustes de infraestrutura compartilhados pelos módulos do painel."""

import time
import urllib.request


_PD_PUBLICACAO_MARKER = (
    "2PACX-1vRsMrqzxYHgTRv_tBJnDU_Rg1OpFmh_FCCo55w671Kna-IE8FIPD4rhL7O-bDwCsNMQW4Qj7UZGaBFP"
)
_URLLIB_URLOPEN_ORIGINAL = urllib.request.urlopen


def _urlopen_com_atualizacao_pd(requisicao, *args, **kwargs):
    """Evita reutilizar uma publicação CSV antiga somente na base de PD."""
    try:
        url = (
            requisicao.full_url
            if isinstance(requisicao, urllib.request.Request)
            else str(requisicao)
        )

        if _PD_PUBLICACAO_MARKER in url and "output=csv" in url:
            separador = "&" if "?" in url else "?"
            url_atualizada = f"{url}{separador}_ts={int(time.time() * 1000)}"

            if isinstance(requisicao, urllib.request.Request):
                requisicao = urllib.request.Request(
                    url_atualizada,
                    data=requisicao.data,
                    headers=dict(requisicao.header_items()),
                    method=requisicao.get_method(),
                )
            else:
                requisicao = url_atualizada
    except Exception:
        pass

    return _URLLIB_URLOPEN_ORIGINAL(requisicao, *args, **kwargs)


# O app importa este pacote antes de definir carregar_dados_pd(). Assim,
# somente a leitura da publicação CSV da PD recebe um parâmetro anti-cache;
# todas as demais URLs continuam usando o comportamento original.
if urllib.request.urlopen is not _urlopen_com_atualizacao_pd:
    urllib.request.urlopen = _urlopen_com_atualizacao_pd
