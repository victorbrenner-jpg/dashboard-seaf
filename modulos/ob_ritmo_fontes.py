"""Gráfico de ritmo mensal por fonte de recurso (substitui a tabela da tela de OB).

Cada fonte vira uma linha com 12 barras (JAN a DEZ), com o valor escrito acima de
cada barra, ponto de pico, hover sincronizado entre as linhas e rodapé consolidado.

Uso no app.py:

    fontes = ob_ritmo_fontes.fontes_de_pivot(df_matriz_fonte, "Fonte_Tratada",
                                             ordem_meses_ano, lista_meses_fixa)
    ob_ritmo_fontes.render_ritmo_fontes(fontes, ano=ano_ob)
"""
import json
import re

import streamlit.components.v1 as components

_FONTES_WEB = (
    "<link rel='preconnect' href='https://fonts.googleapis.com'>"
    "<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
    "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700"
    "&family=JetBrains+Mono:wght@400;500;600;700&display=swap' rel='stylesheet'>"
)

_CSS = r"""
.obr{--ink:#0f172a;--mut:#64748b;--line:#e2e8f0;--bar:#7c90a8;--peak:#0b2545;--hv:#2563eb;--amb:#f59e0b;
     border:1px solid var(--line);border-radius:14px;overflow:hidden;background:#fff;color:var(--ink);
     font-family:Inter,-apple-system,"Segoe UI",Roboto,sans-serif}
.obr *{box-sizing:border-box}
.obr-head{display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:space-between;
          padding:12px 18px;background:#092c4c;color:#fff;font-weight:700;font-size:15px}
.obr-ctl{display:flex;flex-wrap:wrap;gap:8px}
.obr-seg{display:inline-flex;background:#051b30;border:1px solid rgba(255,255,255,.15);border-radius:8px;padding:2px}
.obr-seg button{border:0;background:transparent;color:#cbd5e1;font-family:inherit;font-weight:500;font-size:11px;
                padding:5px 10px;border-radius:6px;cursor:pointer}
.obr-seg button:hover{color:#fff}
.obr-seg button.on{background:#fff;color:#092c4c;font-weight:600}
.obr-scroll{overflow-x:auto}
.obr-in{min-width:1520px}
.obr-row{display:grid;grid-template-columns:minmax(270px,21%) 1fr 180px;align-items:center}
.obr-hd{background:#f8fafc;border-bottom:1px solid var(--line);font-size:11.5px;font-weight:700;color:#94a3b8;
        text-transform:uppercase;letter-spacing:.06em;min-height:48px}
.obr-hd .st.v{text-align:center;padding:0 20px 0 0;white-space:nowrap}
.obr-hd .vh.hv{color:var(--hv)}
.st{position:sticky;z-index:2;background:#fff}
.obr-hd .st{background:#f8fafc}
.st.l{left:0;padding-left:18px;box-shadow:4px 0 8px -4px rgba(15,23,42,.08)}
.st.v{right:0;box-shadow:-4px 0 8px -4px rgba(15,23,42,.08)}
.obr-mm{display:grid;grid-template-columns:repeat(12,1fr)}
.obr-ax{text-align:center;padding:6px 0;cursor:default;user-select:none;border-radius:4px}
.obr-ax.off{opacity:.35}
.obr-ax.hv{background:var(--hv);color:#fff}
.obr-line{min-height:84px;border-bottom:1px solid #f1f5f9}
.obr-line:hover,.obr-line:hover .st{background:#f8fafc}
.obr-src{display:flex;align-items:center;gap:10px;min-width:0;padding-right:14px}
.obr-code{flex:none;font-size:12.5px;font-weight:700;color:#475569;background:#f1f5f9;border:1px solid var(--line);
          border-radius:6px;padding:2px 7px;font-variant-numeric:tabular-nums}
.obr-nm{font-size:13px;font-weight:700;line-height:1.3;color:#1e293b;text-transform:uppercase;
        display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.obr-sub{font-size:11.5px;color:#94a3b8;margin-top:3px;font-weight:500}
.obr-sub b{color:#64748b;font-weight:600}
.obr-c{height:70px;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;cursor:default}
.obr-dot{display:block;width:6px;height:6px;border-radius:50%;background:var(--amb);margin-bottom:2px;flex:none}
.obr-lb{font-family:"JetBrains Mono",ui-monospace,Consolas,"Liberation Mono",monospace;font-size:12.5px;line-height:1;
        margin-bottom:4px;white-space:nowrap;color:#475569;font-weight:500;font-variant-numeric:tabular-nums}
.obr.ex .obr-lb{font-size:10.5px;letter-spacing:-.04em}
.obr-lb.pk{color:var(--peak);font-weight:700}
.obr-b{display:block;width:40px;flex:none;background:var(--bar);border-radius:3px 3px 0 0;
       transition:height .3s cubic-bezier(.16,1,.3,1),background .12s}
.obr-b.pk{background:var(--peak)}
.obr-b.nul{height:0;border-bottom:1px dotted #cbd5e1;border-radius:0;background:transparent;margin-bottom:3px}
.obr-c.hv .obr-b:not(.nul){background:var(--hv)}
.obr-c.hv .obr-lb{color:var(--hv);font-weight:700}
.obr-val{text-align:right;padding-right:20px;font-size:15px;font-weight:700;font-variant-numeric:tabular-nums;
         font-family:"JetBrains Mono",ui-monospace,Consolas,monospace}
.obr-val.hv{color:var(--hv)}
.obr-foot{background:#081f37;color:#fff;min-height:92px;font-size:12.5px;font-weight:700;letter-spacing:.04em}
.obr-foot .st{background:#081f37}
.obr-foot .st.l{box-shadow:4px 0 10px -2px rgba(0,0,0,.35)}
.obr-foot .obr-b{background:#60a5fa}
.obr-foot .obr-b.pk{background:#fbbf24}
.obr-foot .obr-b.nul{border-color:#64748b}
.obr-foot .obr-lb{color:#bae6fd}
.obr-foot .obr-lb.pk{color:#fbbf24}
.obr-foot .obr-dot{background:#fbbf24}
.obr-foot .obr-c.hv .obr-b:not(.nul){background:#fff}
.obr-foot .obr-c.hv .obr-lb{color:#fff}
.obr-foot .obr-fval{text-align:right;padding-right:20px;font-size:16px;color:#fbbf24;font-variant-numeric:tabular-nums;
                    font-family:"JetBrains Mono",ui-monospace,Consolas,monospace}
.obr-empty{padding:30px;text-align:center;color:var(--mut);font-size:13px}
"""

_JS = r"""
(function (global) {
  var MESES = ['JAN','FEV','MAR','ABR','MAI','JUN','JUL','AGO','SET','OUT','NOV','DEZ'];
  var BRL = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
  var N2 = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  var N1 = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  var N0 = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 });
  var BAR_PX = 40;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function pct(v) { return v.toFixed(1).replace('.', ',') + '%'; }

  function render(container, opts) {
    var ano = opts.ano || new Date().getFullYear();
    var titulo = opts.titulo || 'Origem dos Recursos e Fluxo de Saída Monetária';
    var state = { scale: opts.escalaInicial || 'individual', unit: opts.unidadeInicial || 'compact', hover: null };
    var rows = [], monthTotals = [], grand = 0, globalMax = 0, footerMax = 0;

    function prepare() {
      rows = (opts.fontes || []).map(function (f) {
        var vals = [];
        for (var i = 0; i < 12; i++) {
          var v = f.valores && f.valores[i];
          vals.push(v == null || isNaN(Number(v)) ? null : Number(v));
        }
        var total = 0, max = 0, peak = -1;
        vals.forEach(function (v, i) {
          if (v != null) total += v;
          if (v != null && v > max) { max = v; peak = i; }
        });
        return { codigo: f.codigo, nome: f.nome, vals: vals, total: total, max: max, peak: peak };
      }).sort(function (a, b) { return b.total - a.total; });

      monthTotals = [];
      for (var m = 0; m < 12; m++) {
        var has = false, s = 0;
        rows.forEach(function (r) { if (r.vals[m] != null) { has = true; s += r.vals[m]; } });
        monthTotals.push(has ? s : null);
      }
      grand = rows.reduce(function (a, r) { return a + r.total; }, 0);
      globalMax = rows.reduce(function (a, r) { return Math.max(a, r.max); }, 0);
      footerMax = monthTotals.reduce(function (a, v) { return Math.max(a, v || 0); }, 0);
      rows.forEach(function (r) { r.share = grand > 0 ? (r.total / grand) * 100 : 0; });
    }

    // Valor mostrado na coluna da direita (sempre exato)
    function fmt(v) { return v == null ? '—' : BRL.format(v); }

    // Rotulo acima da barra: compacto (20,1 Mi / 815 mil) ou exato
    function labelOf(v) {
      if (v == null || v <= 0) return '';
      if (state.unit === 'exact') return N2.format(v);
      if (v >= 1e6) return N1.format(v / 1e6) + ' Mi';
      if (v >= 1e3) return N0.format(Math.round(v / 1e3)) + ' mil';
      return N0.format(v);
    }

    function barsHTML(vals, maxRef, peak) {
      var h = '<div class="obr-mm">';
      for (var i = 0; i < 12; i++) {
        var v = vals[i], inner, tip;
        if (v == null) {
          tip = MESES[i] + '/' + ano + ': sem dados';
          inner = '<i class="obr-b nul"></i>';
        } else if (v <= 0) {
          tip = MESES[i] + '/' + ano + ': sem movimentação';
          inner = '<i class="obr-b nul"></i>';
        } else {
          var hp = Math.max(3, Math.round((maxRef > 0 ? v / maxRef : 0) * BAR_PX));
          var pk = i === peak;
          tip = MESES[i] + '/' + ano + ': ' + BRL.format(v);
          inner = (pk ? '<u class="obr-dot"></u>' : '') +
                  '<span class="obr-lb' + (pk ? ' pk' : '') + '">' + labelOf(v) + '</span>' +
                  '<i class="obr-b' + (pk ? ' pk' : '') + '" style="height:' + hp + 'px"></i>';
        }
        h += '<div class="obr-c" data-m="' + i + '" title="' + esc(tip) + '">' + inner + '</div>';
      }
      return h + '</div>';
    }

    function draw() {
      if (!rows.length) {
        container.innerHTML = '<div class="obr"><div class="obr-head">' + esc(titulo) + '</div><div class="obr-empty">Sem dados para exibir.</div></div>';
        return;
      }
      var axis = '<div class="obr-mm">' + MESES.map(function (m, i) {
        return '<div class="obr-ax' + (monthTotals[i] == null ? ' off' : '') + '" data-m="' + i + '">' + m + '</div>';
      }).join('') + '</div>';

      var body = rows.map(function (r) {
        var maxRef = state.scale === 'global' ? globalMax : r.max;
        return '<div class="obr-row obr-line">' +
          '<div class="st l obr-src">' + (r.codigo ? '<span class="obr-code">' + esc(r.codigo) + '</span>' : '') +
            '<div style="min-width:0"><div class="obr-nm" title="' + esc(r.codigo ? r.codigo + ' - ' + r.nome : r.nome) + '">' + esc(r.nome) + '</div>' +
            '<div class="obr-sub">' + (r.peak >= 0 ? 'Pico: <b>' + MESES[r.peak] + '</b>' : 'Sem movimento') + '</div></div></div>' +
          '<div>' + barsHTML(r.vals, maxRef, r.peak) + '</div>' +
          '<div class="st v obr-val"></div>' +
        '</div>';
      }).join('');

      var footPeak = monthTotals.indexOf(footerMax);
      var foot = '<div class="obr-row obr-foot">' +
        '<div class="st l obr-flabel"></div>' +
        '<div>' + barsHTML(monthTotals, footerMax, footPeak) + '</div>' +
        '<div class="st v obr-fval"></div>' +
      '</div>';

      function seg(group, list) {
        return '<div class="obr-seg">' + list.map(function (o) {
          return '<button data-act="' + group + ':' + o[0] + '" class="' + (state[group] === o[0] ? 'on' : '') + '">' + o[1] + '</button>';
        }).join('') + '</div>';
      }

      container.innerHTML =
        '<div class="obr' + (state.unit === 'exact' ? ' ex' : '') + '">' +
          '<div class="obr-head"><span>' + esc(titulo) + '</span>' +
            '<div class="obr-ctl">' +
              seg('scale', [['individual', 'Escala individual'], ['global', 'Escala global']]) +
              seg('unit', [['compact', 'R$ compacto'], ['exact', 'R$ exato']]) +
            '</div></div>' +
          '<div class="obr-scroll"><div class="obr-in">' +
            '<div class="obr-row obr-hd"><div class="st l">Fonte de recurso</div><div>' + axis + '</div>' +
              '<div class="st v r vh">Total ' + ano + '</div></div>' +
            body + foot +
          '</div></div>' +
        '</div>';

      applyHover();
    }

    // Atualiza so textos e classes (sem recriar o DOM) para o hover ficar fluido
    function applyHover() {
      var m = state.hover;
      container.querySelectorAll('[data-m]').forEach(function (el) {
        el.classList.toggle('hv', m !== null && +el.dataset.m === m);
      });
      var vh = container.querySelector('.vh');
      if (vh) {
        vh.textContent = m === null ? 'Total ' + ano : MESES[m] + '/' + ano;
        vh.classList.toggle('hv', m !== null);
      }
      var vals = container.querySelectorAll('.obr-line .obr-val');
      rows.forEach(function (r, i) {
        var v = m === null ? r.total : r.vals[m];
        if (vals[i]) { vals[i].textContent = fmt(v); vals[i].classList.toggle('hv', m !== null); }
      });
      var fl = container.querySelector('.obr-flabel'), fv = container.querySelector('.obr-fval');
      if (fl) fl.textContent = m === null ? 'TOTAL GERAL CONSOLIDADO (' + rows.length + ' FONTES)'
                                          : 'TOTAL CONSOLIDADO (' + MESES[m] + '/' + String(ano).slice(2) + ')';
      if (fv) fv.textContent = fmt(m === null ? grand : monthTotals[m]);
    }

    function setHover(m) {
      if (state.hover === m) return;
      state.hover = m;
      applyHover();
    }

    container.addEventListener('mouseover', function (e) {
      var c = e.target.closest ? e.target.closest('[data-m]') : null;
      setHover(c ? +c.dataset.m : null);
    });
    container.addEventListener('mouseleave', function () { setHover(null); });
    container.addEventListener('click', function (e) {
      var b = e.target.closest ? e.target.closest('[data-act]') : null;
      if (!b) return;
      var p = b.dataset.act.split(':');
      state[p[0]] = p[1];
      draw();
    });

    prepare();
    draw();
  }

  global.renderRitmoFontes = render;
})(window);
"""


def fontes_de_dataframe(df, col_codigo, col_nome, cols_meses):
    """Converte um DataFrame (uma linha por fonte, uma coluna por mês) na lista
    que o gráfico espera. cols_meses pode ter menos de 12 colunas: os meses
    restantes ficam como 'sem dados' (linha pontilhada, fora de total e pico)."""
    fontes = []
    for _, linha in df.iterrows():
        valores = []
        for col in cols_meses:
            v = linha[col]
            try:
                v = None if v is None or v != v else float(v)  # v != v => NaN
            except (TypeError, ValueError):
                v = None
            valores.append(v)
        fontes.append({
            "codigo": str(linha[col_codigo]),
            "nome": str(linha[col_nome]),
            "valores": valores,
        })
    return fontes


def fontes_de_pivot(df, col_fonte, ordem_meses, meses_com_dado):
    """Para a tabela pivotada do app (uma linha por fonte, uma coluna por mês no
    formato 'Jan/2026'): monta a lista do gráfico, colocando cada mês na sua
    posição do ano. Meses fora de meses_com_dado ficam como 'sem dados'.
    'Fonte_Tratada' no formato '500-NOME DA FONTE' vira código '500' + nome."""
    fontes = []
    for _, linha in df.iterrows():
        texto = str(linha[col_fonte]).strip()
        achou = re.match(r"^(\d+)\s*-\s*(.+)$", texto)
        if achou:
            codigo, nome = achou.group(1), achou.group(2).strip()
        else:
            codigo, nome = "", texto
        valores = []
        for mes in ordem_meses:
            if mes in meses_com_dado and mes in df.columns:
                v = linha[mes]
                valores.append(None if v is None or v != v else float(v))
            else:
                valores.append(None)
        fontes.append({"codigo": codigo, "nome": nome, "valores": valores})
    return fontes


def render_ritmo_fontes(fontes, ano=2026,
                        titulo="Origem dos Recursos e Fluxo de Saída Monetária",
                        escala_inicial="individual", unidade_inicial="compact"):
    """fontes: lista de {"codigo": str, "nome": str, "valores": [até 12 números]}.
    escala_inicial: "individual" (0-100% por fonte) ou "global".
    unidade_inicial: "compact" (20,1 Mi) ou "exact" (20.137.128,43)."""
    payload = json.dumps(
        {"titulo": titulo, "ano": ano, "escalaInicial": escala_inicial,
         "unidadeInicial": unidade_inicial, "fontes": fontes},
        ensure_ascii=False,
    ).replace("</", "<\\/")  # evita fechar a tag <script> por acidente

    # cabeçalho (~60) + eixo (~50) + linhas (~84 cada) + rodapé (~92) + folga
    altura = 60 + 50 + 84 * max(len(fontes), 1) + 92 + 24

    html = (
        _FONTES_WEB
        + "<style>body{margin:0;font-family:Inter,-apple-system,'Segoe UI',Roboto,sans-serif}"
        + _CSS
        + "</style><div id='ob-ritmo'></div><script>"
        + _JS
        + "\nrenderRitmoFontes(document.getElementById('ob-ritmo'), "
        + payload
        + ");</script>"
    )
    components.html(html, height=altura, scrolling=True)
