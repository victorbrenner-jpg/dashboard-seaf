# Painel SEAF — Versão 2

Ambiente paralelo de homologação da aplicação, mantido sem alterar a versão em
produção.

## Executar localmente

```powershell
cd C:\Users\victor.brenner\Documents\GitHub\dashboard-seaf
python -m streamlit run app.py
```

## Estrutura

- `app.py`: aplicação V2, com a lógica validada da versão atual e navegação
  para a página inicial.
- `modulos/home.py`: página inicial de acesso ao sistema.
- `modelos/`: modelos Excel usados nas exportações.

A lógica das telas foi preservada. A modularização será feita gradualmente,
uma tela por vez, sempre com validação funcional antes da próxima etapa.
