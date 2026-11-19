"""
Gráfico de ritmo mensal por fonte de recurso (substitui a tabela da tela de OB).

Uso em modulos/ob_base.py:

    from modulos.ob_ritmo_fontes import render_ritmo_fontes, fontes_de_dataframe

    fontes = fontes_de_dataframe(
        df,
        col_codigo="cod_fonte",          # ajuste para o nome real da coluna
        col_nome="nome_fonte",           # ajuste para o nome real da coluna
        cols_meses=["jan", "fev", "mar", "abr", "mai", "jun",
                    "jul", "ago", "set", "out", "nov"],   # só os meses com dado
    )
    render_ritmo_fontes(fontes, ano=2026)
"""
import json
import re

import streamlit.components.v1 as components

_CSS = r"""
.obr{--ink:#0f172a;--mut:#64748b;--line:#e2e8f0;--bar:#7c93b3;--peak:#0f2a4a;--hv:#2563eb;--amb:#f59e0b;
       border:1px solid var(--line);border-radius:10px;overflow:hidden;background:#fff;color:var(--ink);font-family:inherit}
  .obr *{box-sizing:border-box}
  .obr-head{display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:space-between;
            padding:12px 18px;background:linear-gradient(90deg,#0f2a4a,#0b3a5c);color:#fff;font-weight:700;font-size:14px}
  .obr-ctl{display:flex;flex-wrap:wrap;gap:8px}
  .obr-seg{display:inline-flex;background:rgba(255,255,255,.14);border-radius:8px;padding:2px}
  .obr-seg button{border:0;background:transparent;color:#cbd5e1;font-family:inherit;font-weight:600;font-size:11px;
                  padding:5px 10px;border-radius:6px;cursor:pointer}
  .obr-seg button.on{background:#fff;color:#0f2a4a}
  .obr-scroll{overflow-x:auto}
  .obr-in{min-width:1000px}
  .obr-row{display:grid;grid-template-columns:minmax(250px,23%) 1fr 168px 90px;align-items:center;padding:0 18px}
  .obr-hd{background:#f8fafc;border-bottom:2px solid var(--line);font-size:11px;font-weight:700;color:var(--mut);
          text-transform:uppercase;letter-spacing:.05em;min-height:42px}
  .obr-hd .r{text-align:right}
  .obr-hd .vh.hv{color:var(--hv)}
  .obr-mm{display:grid;grid-template-columns:repeat(12,1fr)}
  .obr-ax{text-align:center;padding:6px 0;cursor:default;user-select:none;border-radius:4px}
  .obr-ax.off{opacity:.35}
  .obr-ax.hv{background:var(--hv);color:#fff}
  .obr-line{min-height:62px;border-bottom:1px solid #f1f5f9;transition:background .12s}
  .obr-line:hover{background:#f8fafc}
  .obr-src{display:flex;align-items:center;gap:10px;min-width:0;padding-right:14px}
  .obr-code{flex:none;font-size:11px;font-weight:700;color:#334155;background:#f1f5f9;border:1px solid var(--line);
            border-radius:5px;padding:2px 6px;font-variant-numeric:tabular-nums}
  .obr-nm{font-size:12px;font-weight:600;line-height:1.25;color:var(--ink);
          display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
  .obr-sub{font-size:10px;color:#94a3b8;margin-top:2px}
  .obr-c{position:relative;height:50px;display:flex;align-items:flex-end;justify-content:center;cursor:default;padding:0 3px}
  .obr-b{display:block;width:100%;max-width:38px;background:var(--bar);border-radius:3px 3px 0 0;
         transition:height .3s cubic-bezier(.16,1,.3,1),background .12s}
  .obr-b.pk{background:var(--peak)}
  .obr-b.zero{height:2px;background:#cbd5e1;border-radius:1px}
  .obr-b.nul{height:0;border-top:2px dotted #e2e8f0;background:transparent;border-radius:0}
  .obr-dot{position:absolute;left:50%;width:6px;height:6px;margin-left:-3px;border-radius:50%;background:var(--amb);pointer-events:none}
  .obr-c.hv .obr-b:not(.zero):not(.nul){background:var(--hv)}
  .obr-val{text-align:right;padding-right:14px;font-size:12.5px;font-weight:700;font-variant-numeric:tabular-nums}
  .obr-val.hv{color:var(--hv)}
  .obr-pct{text-align:right;font-size:12px;font-weight:600;color:#334155;font-variant-numeric:tabular-nums}
  .obr-pbar{height:4px;background:#f1f5f9;border-radius:2px;overflow:hidden;margin-top:4px}
  .obr-pbar i{display:block;height:100%;background:var(--hv);border-radius:2px;transition:width .25s}
  .obr-foot{background:#0f172a;color:#fff;min-height:64px;font-size:11px;font-weight:700;letter-spacing:.04em}
  .obr-foot .obr-b{background:#60a5fa}
  .obr-foot .obr-b.pk{background:#fbbf24}
  .obr-foot .obr-b.zero{background:#334155}
  .obr-foot .obr-b.nul{border-color:#334155}
  .obr-foot .obr-c.hv .obr-b{background:#fff!important}
  .obr-foot .obr-fval{text-align:right;padding-right:14px;font-size:14px;color:#fcd34d;font-variant-numeric:tabular-nums}
  .obr-foot .obr-pct{color:#cbd5e1}
  .obr-empty{padding:30px;text-align:center;color:var(--mut);font-size:13px}
"""

_JS = r"""
(function (global) {
  var MESES = ['JAN','FEV','MAR','ABR','MAI','JUN','JUL','AGO','SET','OUT','NOV','DEZ'];
  var BRL = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function pct(v) { return v.toFixed(1).replace('.', ',') + '%'; }

  function render(container, opts) {
    var ano = opts.ano || new Date().getFullYear();
    var titulo = opts.titulo || 'Origem dos Recursos e Fluxo de Saída Monetária';
    var state = { scale: opts.escalaInicial || 'individual', unit: 'exact', hover: null };
    var rows = [], monthTotals = [], grand = 0, globalMax = 0, footerMax = 0;

    function prepare() {
      rows = (opts.fontes || []).map(function (f) {
        // valores: até 12 posições; mês sem dado (futuro) = null/undefined
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

    function fmt(v) {
      if (v == null) return '—';
      if (state.unit === 'compact') {
        if (Math.abs(v) >= 1e6) return 'R$ ' + (v / 1e6).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' mi';
        if (Math.abs(v) >= 1e3) return 'R$ ' + (v / 1e3).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + ' mil';
      }
      return BRL.format(v);
    }

    function barsHTML(vals, maxRef, peak) {
      var h = '<div class="obr-mm">';
      for (var i = 0; i < 12; i++) {
        var v = vals[i], inner;
        if (v == null) {
          inner = '<i class="obr-b nul"></i>';
        } else if (v === 0) {
          inner = '<i class="obr-b zero"></i>';
        } else {
          var r = maxRef > 0 ? v / maxRef : 0;
          var hp = Math.max(r * 82, 4);
          var isPk = i === peak;
          inner = '<i class="obr-b' + (isPk ? ' pk' : '') + '" style="height:' + hp.toFixed(1) + '%"></i>' +
                  (isPk ? '<u class="obr-dot" style="bottom:calc(' + hp.toFixed(1) + '% + 4px)"></u>' : '');
        }
        h += '<div class="obr-c" data-m="' + i + '" title="' + MESES[i] + '/' + ano + ': ' +
             (v == null ? 'sem dados' : BRL.format(v)) + '">' + inner + '</div>';
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
          '<div class="obr-src">' + (r.codigo ? '<span class="obr-code">' + esc(r.codigo) + '</span>' : '') +
            '<div style="min-width:0"><div class="obr-nm" title="' + esc(r.codigo ? r.codigo + ' - ' + r.nome : r.nome) + '">' + esc(r.nome) + '</div>' +
            '<div class="obr-sub">' + (r.peak >= 0 ? 'Pico: ' + MESES[r.peak] : 'Sem movimento') + '</div></div></div>' +
          '<div>' + barsHTML(r.vals, maxRef, r.peak) + '</div>' +
          '<div class="obr-val"></div>' +
          '<div><div class="obr-pct"></div><div class="obr-pbar"><i></i></div></div>' +
        '</div>';
      }).join('');

      var footPeak = monthTotals.indexOf(footerMax);
      var foot = '<div class="obr-row obr-foot">' +
        '<div class="obr-flabel"></div>' +
        '<div>' + barsHTML(monthTotals, footerMax, footPeak) + '</div>' +
        '<div class="obr-fval"></div>' +
        '<div class="obr-pct">100,0%</div>' +
      '</div>';

      function seg(group, opts2) {
        return '<div class="obr-seg">' + opts2.map(function (o) {
          return '<button data-act="' + group + ':' + o[0] + '" class="' + (state[group] === o[0] ? 'on' : '') + '">' + o[1] + '</button>';
        }).join('') + '</div>';
      }

      container.innerHTML =
        '<div class="obr">' +
          '<div class="obr-head"><span>' + esc(titulo) + '</span>' +
            '<div class="obr-ctl">' +
              seg('scale', [['individual', 'Escala individual'], ['global', 'Escala global']]) +
              seg('unit', [['exact', 'R$ exato'], ['compact', 'R$ compacto']]) +
            '</div></div>' +
          '<div class="obr-scroll"><div class="obr-in">' +
            '<div class="obr-row obr-hd"><div>Fonte de recurso</div><div>' + axis + '</div>' +
              '<div class="r vh">Total ' + ano + '</div><div class="r">% Part.</div></div>' +
            body + foot +
          '</div></div>' +
        '</div>';

      applyHover();
    }

    // Atualiza só textos/classes (sem recriar o DOM) para o hover ficar fluido
    function applyHover() {
      var m = state.hover;
      var root = container;
      root.querySelectorAll('[data-m]').forEach(function (el) {
        el.classList.toggle('hv', m !== null && +el.dataset.m === m);
      });
      var vh = root.querySelector('.vh');
      if (vh) {
        vh.textContent = m === null ? 'Total ' + ano : MESES[m] + '/' + ano;
        vh.classList.toggle('hv', m !== null);
      }
      var vals = root.querySelectorAll('.obr-line .obr-val');
      var pcts = root.querySelectorAll('.obr-line .obr-pct');
      var pbars = root.querySelectorAll('.obr-line .obr-pbar i');
      rows.forEach(function (r, i) {
        var v = m === null ? r.total : r.vals[m];
        var share = m === null ? r.share : (v != null && monthTotals[m] > 0 ? (v / monthTotals[m]) * 100 : 0);
        if (vals[i]) { vals[i].textContent = fmt(v); vals[i].classList.toggle('hv', m !== null); }
        if (pcts[i]) pcts[i].textContent = pct(share);
        if (pbars[i]) pbars[i].style.width = Math.min(100, share) + '%';
      });
      var fl = root.querySelector('.obr-flabel'), fv = root.querySelector('.obr-fval');
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

    return {
      update: function (fontes) { opts.fontes = fontes; prepare(); draw(); }
    };
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
                        escala_inicial="individual"):
    """fontes: lista de {"codigo": str, "nome": str, "valores": [até 12 números]}.
    escala_inicial: "individual" (0-100% por fonte) ou "global"."""
    payload = json.dumps(
        {"titulo": titulo, "ano": ano, "escalaInicial": escala_inicial, "fontes": fontes},
        ensure_ascii=False,
    ).replace("</", "<\\/")  # evita fechar a tag <script> por acidente

    # cabeçalho (~50) + eixo (~42) + linhas (~62 cada) + rodapé (~64) + folga
    altura = 50 + 42 + 62 * max(len(fontes), 1) + 64 + 24

    html = (
        "<style>body{margin:0;font-family:Inter,-apple-system,'Segoe UI',Roboto,sans-serif}"
        + _CSS
        + "</style><div id='ob-ritmo'></div><script>"
        + _JS
        + "\nrenderRitmoFontes(document.getElementById('ob-ritmo'), "
        + payload
        + ");</script>"
    )
    components.html(html, height=altura, scrolling=True)
