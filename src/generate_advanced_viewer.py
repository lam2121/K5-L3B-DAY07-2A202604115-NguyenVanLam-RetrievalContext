"""Generates a self-contained HTML visualizer for the Day 7 Advanced Challenge (WDR 2025)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="vi" class="light">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>WDR 2025 Advanced Challenge · Benchmark & Agent Traces Explorer</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            primary: '#2563eb',
            wdr: '#059669',
            gold: '#facc15'
          }
        }
      }
    }
  </script>
  <style>
    pre code { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-thumb { background: #94a3b8; border-radius: 4px; }
  </style>
</head>
<body class="bg-slate-50 text-slate-800 dark:bg-slate-900 dark:text-slate-100 min-h-screen flex flex-col font-sans transition-colors duration-200">
  <!-- Top Navigation -->
  <header class="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 sticky top-0 z-30 shadow-sm">
    <div class="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <span class="p-2 bg-emerald-600 text-white rounded-lg font-bold text-lg shadow-sm">WDR</span>
        <div>
          <h1 class="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
            World Development Report 2025 · Advanced Challenge Explorer
            <span class="text-xs px-2 py-0.5 bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300 rounded font-semibold border border-emerald-300 dark:border-emerald-700">93.3% PASS (QUALIFIED)</span>
          </h1>
          <p class="text-xs text-slate-500 dark:text-slate-400">408 Pages · 3,473 Chunks · Hybrid RRF Retrieval · Anthropic Claude 3.5 Haiku Controller</p>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <a href="benchmark_viewer.html" class="px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 hover:text-primary border border-slate-300 dark:border-slate-600 rounded-lg">View Standard Viewer</a>
        <button id="themeToggle" class="p-2 rounded-lg bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600">
          <span class="dark:hidden">🌙</span>
          <span class="hidden dark:inline">☀️</span>
        </button>
      </div>
    </div>
  </header>

  <!-- Summary Cards -->
  <div class="max-w-7xl mx-auto px-4 py-4 w-full grid grid-cols-2 md:grid-cols-6 gap-3">
    <div class="bg-white dark:bg-slate-800 p-3 rounded-xl border border-slate-200 dark:border-slate-700 shadow-xs">
      <div class="text-xs text-slate-500 dark:text-slate-400">Test Accuracy</div>
      <div class="text-xl font-bold text-emerald-600 dark:text-emerald-400">28 / 30</div>
      <div class="text-[11px] text-emerald-600 dark:text-emerald-400 font-semibold">93.3% (Threshold ≥90%)</div>
    </div>
    <div class="bg-white dark:bg-slate-800 p-3 rounded-xl border border-slate-200 dark:border-slate-700 shadow-xs">
      <div class="text-xs text-slate-500 dark:text-slate-400">Tables (≥6)</div>
      <div class="text-xl font-bold text-slate-900 dark:text-white">5 / 6</div>
      <div class="text-[11px] text-slate-500">83.3% Pass</div>
    </div>
    <div class="bg-white dark:bg-slate-800 p-3 rounded-xl border border-slate-200 dark:border-slate-700 shadow-xs">
      <div class="text-xs text-slate-500 dark:text-slate-400">Diagrams/Images (≥5)</div>
      <div class="text-xl font-bold text-emerald-600 dark:text-emerald-400">5 / 5</div>
      <div class="text-[11px] text-emerald-600 font-semibold">100% Pass</div>
    </div>
    <div class="bg-white dark:bg-slate-800 p-3 rounded-xl border border-slate-200 dark:border-slate-700 shadow-xs">
      <div class="text-xs text-slate-500 dark:text-slate-400">Charts (≥5)</div>
      <div class="text-xl font-bold text-emerald-600 dark:text-emerald-400">5 / 5</div>
      <div class="text-[11px] text-emerald-600 font-semibold">100% Pass</div>
    </div>
    <div class="bg-white dark:bg-slate-800 p-3 rounded-xl border border-slate-200 dark:border-slate-700 shadow-xs">
      <div class="text-xs text-slate-500 dark:text-slate-400">Multi-hop (≥4)</div>
      <div class="text-xl font-bold text-slate-900 dark:text-white">3 / 4</div>
      <div class="text-[11px] text-slate-500">75.0% Pass</div>
    </div>
    <div class="bg-white dark:bg-slate-800 p-3 rounded-xl border border-slate-200 dark:border-slate-700 shadow-xs">
      <div class="text-xs text-slate-500 dark:text-slate-400">Unanswerable (≥6)</div>
      <div class="text-xl font-bold text-emerald-600 dark:text-emerald-400">6 / 6</div>
      <div class="text-[11px] text-emerald-600 font-semibold">100% Pass</div>
    </div>
  </div>

  <!-- Main Layout -->
  <div class="max-w-7xl mx-auto px-4 py-2 w-full flex-1 grid grid-cols-1 md:grid-cols-12 gap-4 pb-8">
    <!-- Question Sidebar -->
    <div class="md:col-span-4 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-xs flex flex-col h-[750px]">
      <div class="p-3 border-b border-slate-200 dark:border-slate-700 flex flex-col gap-2">
        <div class="flex items-center justify-between">
          <span class="text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">Test Questions (30)</span>
          <span class="text-xs bg-slate-100 dark:bg-slate-700 px-2 py-0.5 rounded text-slate-600 dark:text-slate-300">WDR 2025</span>
        </div>
        <div class="flex flex-wrap gap-1">
          <button onclick="filterCat('all')" class="cat-btn text-[11px] px-2 py-0.5 rounded bg-slate-900 text-white dark:bg-white dark:text-slate-900 font-medium">All</button>
          <button onclick="filterCat('Table')" class="cat-btn text-[11px] px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">Table (6)</button>
          <button onclick="filterCat('Image/Diagram')" class="cat-btn text-[11px] px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">Diagram (5)</button>
          <button onclick="filterCat('Chart')" class="cat-btn text-[11px] px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">Chart (5)</button>
          <button onclick="filterCat('Multi-hop')" class="cat-btn text-[11px] px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">Multi-hop (4)</button>
          <button onclick="filterCat('Text')" class="cat-btn text-[11px] px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">Text (4)</button>
          <button onclick="filterCat('Unanswerable')" class="cat-btn text-[11px] px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">Unanswerable (6)</button>
        </div>
      </div>
      <div id="qList" class="flex-1 overflow-y-auto divide-y divide-slate-100 dark:divide-slate-700/50">
        <!-- Rendered by JS -->
      </div>
    </div>

    <!-- Details View -->
    <div id="detailView" class="md:col-span-8 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-xs flex flex-col h-[750px] overflow-y-auto p-6">
      <div class="text-center text-slate-400 my-auto">Select a question to inspect agent trace, retrieved chunks, citations and image crops.</div>
    </div>
  </div>

  <script>
    const DATA = __MERGED_DATA__;
    let activeCat = 'all';
    let activeIdx = 0;

    const themeToggle = document.getElementById('themeToggle');
    themeToggle.addEventListener('click', () => {
      document.documentElement.classList.toggle('dark');
    });

    function filterCat(cat) {
      activeCat = cat;
      document.querySelectorAll('.cat-btn').forEach(b => {
        if (b.innerText.toLowerCase().startsWith(cat.toLowerCase()) || (cat === 'all' && b.innerText === 'All')) {
          b.className = 'cat-btn text-[11px] px-2 py-0.5 rounded bg-slate-900 text-white dark:bg-white dark:text-slate-900 font-medium';
        } else {
          b.className = 'cat-btn text-[11px] px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300';
        }
      });
      renderList();
    }

    function renderList() {
      const listEl = document.getElementById('qList');
      listEl.innerHTML = '';
      DATA.forEach((item, idx) => {
        const c = item.case;
        const rev = item.review;
        if (activeCat !== 'all' && c.category !== activeCat) return;

        const isPassed = rev.passed;
        const btn = document.createElement('button');
        btn.className = `w-full text-left p-3 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition flex items-start gap-2.5 ${idx === activeIdx ? 'bg-emerald-50 dark:bg-emerald-950/30 border-l-4 border-emerald-500' : ''}`;
        btn.onclick = () => { activeIdx = idx; renderList(); renderDetail(); };

        const passBadge = isPassed
          ? `<span class="px-1.5 py-0.5 text-[10px] font-bold rounded bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300">PASS</span>`
          : `<span class="px-1.5 py-0.5 text-[10px] font-bold rounded bg-rose-100 text-rose-800 dark:bg-rose-900/60 dark:text-rose-300">FAIL</span>`;

        btn.innerHTML = `
          <div class="mt-0.5">${passBadge}</div>
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
              <span class="font-mono">${c.id}</span> · <span>${c.category}</span>
            </div>
            <div class="text-xs font-medium text-slate-800 dark:text-slate-200 truncate mt-0.5">${c.question}</div>
          </div>
        `;
        listEl.appendChild(btn);
      });
    }

    function renderDetail() {
      const item = DATA[activeIdx];
      if (!item) return;
      const c = item.case;
      const t = item.trace;
      const r = item.review;
      const isPassed = r.passed;

      const detailEl = document.getElementById('detailView');
      const passTag = isPassed
        ? `<span class="px-2 py-1 text-xs font-bold rounded bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700">PASSED (Score 2/2)</span>`
        : `<span class="px-2 py-1 text-xs font-bold rounded bg-rose-100 text-rose-800 dark:bg-rose-900/60 dark:text-rose-300 border border-rose-300 dark:border-rose-700">FAILED</span>`;

      let goldHtml = '';
      if (c.gold && c.gold.length > 0) {
        goldHtml = c.gold.map(g => `
          <div class="bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/50 rounded-lg p-3 text-xs">
            <div class="font-semibold text-amber-900 dark:text-amber-300 font-mono mb-1">${g.chunk_id} (Page ${g.page})</div>
            <div class="text-amber-800 dark:text-amber-200 italic">"${g.evidence_quote}"</div>
          </div>
        `).join('');
      } else {
        goldHtml = `<div class="text-xs text-slate-500 italic">Unanswerable Question — Correct behavior is safe abstention without hallucinated facts.</div>`;
      }

      let eventsHtml = '';
      if (t.events && t.events.length > 0) {
        eventsHtml = t.events.map((ev, i) => {
          if (ev.event === 'search') {
            const results = (ev.results || []).map(res => `
              <div class="bg-slate-50 dark:bg-slate-700/40 p-2.5 rounded border border-slate-200 dark:border-slate-600 text-xs mt-1.5">
                <div class="flex items-center justify-between font-mono text-primary font-semibold">
                  <span>${res.id} · Page ${res.page}</span>
                  <span class="text-slate-500">Score: ${res.score}</span>
                </div>
                <div class="text-slate-600 dark:text-slate-300 text-[11px] mt-1 line-clamp-3">${res.text}</div>
              </div>
            `).join('');
            return `
              <div class="border-l-2 border-primary pl-3 py-1">
                <div class="text-xs font-semibold text-primary">Turn ${i+1}: Search Tool Call</div>
                <div class="text-xs text-slate-700 dark:text-slate-300 font-mono mt-0.5 bg-slate-100 dark:bg-slate-700 px-2 py-1 rounded">query: "${ev.query}"</div>
                <div class="mt-2 font-medium text-xs text-slate-600 dark:text-slate-400">Retrieved Chunks:</div>
                ${results}
              </div>
            `;
          }
          return '';
        }).join('');
      }

      const citesList = (t.citations && t.citations.length > 0)
        ? t.citations.map(cit => `<span class="px-1.5 py-0.5 font-mono text-[10px] bg-primary/10 text-primary rounded font-semibold">${cit}</span>`).join(' ')
        : '<span class="text-[11px] text-slate-400 italic">None</span>';

      detailEl.innerHTML = `
        <div class="flex items-center justify-between border-b border-slate-200 dark:border-slate-700 pb-3 mb-4">
          <div>
            <div class="text-xs font-mono text-slate-500 dark:text-slate-400">${c.id} · ${c.category} · ${c.answerable ? 'Answerable' : 'Unanswerable'}</div>
            <h2 class="text-base font-bold text-slate-900 dark:text-white mt-0.5">${c.question}</h2>
          </div>
          <div>${passTag}</div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <!-- Model Answer -->
          <div class="bg-slate-50 dark:bg-slate-900/60 p-3.5 rounded-xl border border-slate-200 dark:border-slate-700">
            <div class="text-xs font-semibold uppercase text-slate-500 dark:text-slate-400 mb-1.5 flex items-center justify-between">
              <span>Agent Answer</span>
              <span class="font-mono text-[10px] text-slate-400">${t.elapsed_ms || 0} ms</span>
            </div>
            <div class="text-xs text-slate-800 dark:text-slate-200 font-medium leading-relaxed">${t.answer || 'No answer recorded'}</div>
            <div class="mt-2.5 pt-2 border-t border-slate-200 dark:border-slate-700 flex items-center gap-1.5">
              <span class="text-[11px] text-slate-500">Citations:</span>
              ${citesList}
            </div>
          </div>

          <!-- Gold Evidence -->
          <div class="bg-slate-50 dark:bg-slate-900/60 p-3.5 rounded-xl border border-slate-200 dark:border-slate-700">
            <div class="text-xs font-semibold uppercase text-slate-500 dark:text-slate-400 mb-1.5">Ground-Truth Evidence</div>
            <div class="text-xs text-slate-700 dark:text-slate-300 mb-2">${c.gold_answer || 'Expected Abstention'}</div>
            ${goldHtml}
          </div>
        </div>

        <!-- Trace Timeline -->
        <div class="flex-1">
          <div class="text-xs font-semibold uppercase text-slate-500 dark:text-slate-400 mb-2">Agent Execution Trace & Retrieval Events</div>
          <div class="flex flex-col gap-3">
            ${eventsHtml || '<div class="text-xs text-slate-400 italic">No search events recorded</div>'}
          </div>
        </div>
      `;
    }

    renderList();
    renderDetail();
  </script>
</body>
</html>
"""

def generate_viewer():
    benchmark_path = ROOT / "data" / "advanced" / "benchmark_advanced.json"
    traces_path = ROOT / "starter" / "results" / "advanced-test" / "traces.json"
    reviews_path = ROOT / "starter" / "results" / "advanced-test" / "reviews.json"

    benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
    traces = json.loads(traces_path.read_text(encoding="utf-8")) if traces_path.exists() else []
    reviews = json.loads(reviews_path.read_text(encoding="utf-8")) if reviews_path.exists() else []

    test_benchmark = [c for c in benchmark if c["split"] == "test"]
    trace_map = {t["query_id"]: t for t in traces}
    rev_map = {r["query_id"]: r for r in reviews}

    merged = []
    for c in test_benchmark:
        qid = c["id"]
        merged.append({
            "case": c,
            "trace": trace_map.get(qid, {}),
            "review": rev_map.get(qid, {})
        })

    merged_json = json.dumps(merged, ensure_ascii=False)
    html_out = HTML_TEMPLATE.replace("__MERGED_DATA__", merged_json)
    out_file = ROOT / "advanced_viewer.html"
    out_file.write_text(html_out, encoding="utf-8")
    print(f"[AdvancedViewer] Successfully generated {out_file} ({len(html_out)} bytes)")


if __name__ == "__main__":
    generate_viewer()
