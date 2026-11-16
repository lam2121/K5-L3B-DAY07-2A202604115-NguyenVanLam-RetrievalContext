"""Generates a self-contained HTML visualizer for the Day 7 Advanced Challenge (WDR 2025)
with original PDF page rendering and animated yellow bounding-box highlighting.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="vi" class="light">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>WDR 2025 Advanced Challenge · Multimodal PDF & Agent Traces Explorer</title>
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
    @keyframes pulseGlow {
      0%, 100% {
        background-color: rgba(254, 240, 138, 0.65);
        box-shadow: 0 0 6px rgba(234, 179, 8, 0.5);
      }
      50% {
        background-color: rgba(253, 224, 71, 0.85);
        box-shadow: 0 0 16px rgba(234, 179, 8, 0.95);
      }
    }
    .pdf-highlight-box {
      animation: pulseGlow 2.5s infinite ease-in-out;
      mix-blend-mode: multiply;
      pointer-events: none;
      transition: all 0.25s ease-out;
    }
    .dark .pdf-highlight-box {
      mix-blend-mode: screen;
      background-color: rgba(202, 138, 4, 0.6) !important;
      border-color: #facc15 !important;
    }
    pre code { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-thumb { background: #94a3b8; border-radius: 4px; }
    .dark ::-webkit-scrollbar-thumb { background: #475569; }
  </style>
</head>
<body class="bg-slate-50 text-slate-800 dark:bg-slate-900 dark:text-slate-100 min-h-screen flex flex-col font-sans transition-colors duration-200">
  <!-- Top Navigation -->
  <header class="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 sticky top-0 z-30 shadow-sm">
    <div class="max-w-[1700px] mx-auto px-4 py-3 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <span class="p-2 bg-emerald-600 text-white rounded-lg font-bold text-lg shadow-sm">WDR</span>
        <div>
          <h1 class="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
            World Development Report 2025 · Advanced Challenge Explorer
            <span class="text-xs px-2 py-0.5 bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300 rounded font-semibold border border-emerald-300 dark:border-emerald-700">93.3% PASS (QUALIFIED)</span>
          </h1>
          <p class="text-xs text-slate-500 dark:text-slate-400">408 Pages · 3,473 Chunks · Multimodal Indexing with Page BBoxes · Claude 5.5 Haiku Controller</p>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <a href="benchmark_viewer.html" class="px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 hover:text-primary border border-slate-300 dark:border-slate-600 rounded-lg">Open Day 7 Standard Viewer</a>
        <button id="themeToggle" class="p-2 rounded-lg bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600">
          <span class="dark:hidden">🌙</span>
          <span class="hidden dark:inline">☀️</span>
        </button>
      </div>
    </div>
  </header>

  <!-- Metric Badges Row -->
  <div class="max-w-[1700px] mx-auto px-4 py-3 w-full grid grid-cols-2 md:grid-cols-6 gap-3">
    <div class="bg-white dark:bg-slate-800 p-2.5 rounded-xl border border-slate-200 dark:border-slate-700 shadow-xs">
      <div class="text-[11px] text-slate-500 dark:text-slate-400">Test Accuracy</div>
      <div class="text-lg font-bold text-emerald-600 dark:text-emerald-400">28 / 30 (93.3%)</div>
      <div class="text-[10px] text-emerald-600 font-semibold">Ngưỡng ≥90.0% · ĐẠT 15/15 BONUS</div>
    </div>
    <div class="bg-white dark:bg-slate-800 p-2.5 rounded-xl border border-slate-200 dark:border-slate-700 shadow-xs">
      <div class="text-[11px] text-slate-500 dark:text-slate-400">Table (Bảng)</div>
      <div class="text-lg font-bold text-slate-900 dark:text-white">5 / 6 (83.3%)</div>
      <div class="text-[10px] text-slate-500">Yêu cầu tối thiểu ≥6 câu</div>
    </div>
    <div class="bg-white dark:bg-slate-800 p-2.5 rounded-xl border border-slate-200 dark:border-slate-700 shadow-xs">
      <div class="text-[11px] text-slate-500 dark:text-slate-400">Image/Diagram (Sơ đồ)</div>
      <div class="text-lg font-bold text-emerald-600 dark:text-emerald-400">5 / 5 (100%)</div>
      <div class="text-[10px] text-emerald-600 font-semibold">Yêu cầu tối thiểu ≥5 câu</div>
    </div>
    <div class="bg-white dark:bg-slate-800 p-2.5 rounded-xl border border-slate-200 dark:border-slate-700 shadow-xs">
      <div class="text-[11px] text-slate-500 dark:text-slate-400">Chart (Biểu đồ)</div>
      <div class="text-lg font-bold text-emerald-600 dark:text-emerald-400">5 / 5 (100%)</div>
      <div class="text-[10px] text-emerald-600 font-semibold">Yêu cầu tối thiểu ≥5 câu</div>
    </div>
    <div class="bg-white dark:bg-slate-800 p-2.5 rounded-xl border border-slate-200 dark:border-slate-700 shadow-xs">
      <div class="text-[11px] text-slate-500 dark:text-slate-400">Multi-hop (Đa bước)</div>
      <div class="text-lg font-bold text-slate-900 dark:text-white">3 / 4 (75.0%)</div>
      <div class="text-[10px] text-slate-500">Yêu cầu tối thiểu ≥4 câu</div>
    </div>
    <div class="bg-white dark:bg-slate-800 p-2.5 rounded-xl border border-slate-200 dark:border-slate-700 shadow-xs">
      <div class="text-[11px] text-slate-500 dark:text-slate-400">Unanswerable (Thiếu)</div>
      <div class="text-lg font-bold text-emerald-600 dark:text-emerald-400">6 / 6 (100%)</div>
      <div class="text-[10px] text-emerald-600 font-semibold">Từ chối an toàn tuyệt đối</div>
    </div>
  </div>

  <!-- Main 3-Column Studio -->
  <div class="max-w-[1700px] mx-auto px-4 py-2 w-full flex-1 grid grid-cols-1 lg:grid-cols-12 gap-4 pb-8">
    <!-- Column 1: Questions Sidebar (3 cols) -->
    <div class="lg:col-span-3 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-xs flex flex-col h-[780px]">
      <div class="p-3 border-b border-slate-200 dark:border-slate-700 flex flex-col gap-2">
        <div class="flex items-center justify-between">
          <span class="text-xs font-bold uppercase text-slate-500 dark:text-slate-400">Câu hỏi Test Split (30)</span>
          <span class="text-[11px] font-semibold text-emerald-600 dark:text-emerald-400">28 Pass</span>
        </div>
        <input id="searchInput" type="text" placeholder="Tìm kiếm câu hỏi..." class="w-full text-xs px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 focus:outline-none focus:border-primary" oninput="renderList()" />
        <div class="flex flex-wrap gap-1">
          <button onclick="filterCat('all')" class="cat-btn text-[10px] px-2 py-0.5 rounded bg-slate-900 text-white dark:bg-white dark:text-slate-900 font-medium">All</button>
          <button onclick="filterCat('Table')" class="cat-btn text-[10px] px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">Table (6)</button>
          <button onclick="filterCat('Image/Diagram')" class="cat-btn text-[10px] px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">Diagram (5)</button>
          <button onclick="filterCat('Chart')" class="cat-btn text-[10px] px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">Chart (5)</button>
          <button onclick="filterCat('Multi-hop')" class="cat-btn text-[10px] px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">Hop (4)</button>
          <button onclick="filterCat('Text')" class="cat-btn text-[10px] px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">Text (4)</button>
          <button onclick="filterCat('Unanswerable')" class="cat-btn text-[10px] px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">Unans (6)</button>
        </div>
      </div>
      <div id="qList" class="flex-1 overflow-y-auto divide-y divide-slate-100 dark:divide-slate-700/50">
        <!-- Rendered by JS -->
      </div>
    </div>

    <!-- Column 2: Agent Response & Trace (4 cols) -->
    <div id="detailView" class="lg:col-span-4 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-xs flex flex-col h-[780px] overflow-y-auto p-4">
      <div class="text-center text-slate-400 my-auto text-xs">Chọn câu hỏi để xem câu trả lời của Agent và chuỗi Trace tìm kiếm.</div>
    </div>

    <!-- Column 3: Original PDF Page Viewer with Yellow Highlighting (5 cols) -->
    <div id="pdfView" class="lg:col-span-5 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-xs flex flex-col h-[780px] overflow-hidden">
      <!-- PDF Header & Tabs -->
      <div class="p-3 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between bg-slate-50/50 dark:bg-slate-800/80">
        <div class="flex items-center gap-2">
          <span class="text-xs font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
            📄 Trang PDF Gốc (Bôi Vàng Dữ Liệu)
          </span>
          <span id="pdfPageBadge" class="text-[10px] font-mono px-2 py-0.5 bg-primary/10 text-primary font-semibold rounded">Trang --</span>
        </div>
        <div id="pageSwitchTabs" class="flex items-center gap-1">
          <!-- Multi-page switcher tabs rendered by JS -->
        </div>
      </div>

      <!-- PDF Canvas Container -->
      <div class="flex-1 overflow-y-auto p-4 bg-slate-100 dark:bg-slate-900/80 flex flex-col items-center">
        <div id="pdfContainer" class="relative inline-block w-full max-w-[620px] border border-slate-300 dark:border-slate-600 rounded-lg overflow-hidden shadow-md bg-white">
          <img id="pdfPageImg" class="w-full h-auto block select-none pointer-events-none" src="" alt="Trang PDF gốc" />
          <div id="highlightLayer" class="absolute inset-0 pointer-events-none"></div>
        </div>
        <div id="evidenceSnippetBox" class="w-full max-w-[620px] mt-3 p-3 bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800/60 rounded-xl text-xs text-amber-900 dark:text-amber-200">
          <div class="font-bold text-[11px] uppercase text-amber-800 dark:text-amber-400 mb-0.5 flex items-center gap-1">
            <span>✨ Bằng chứng được bôi vàng (Yellow Highlight):</span>
          </div>
          <div id="evidenceSnippetText" class="italic leading-relaxed font-serif">--</div>
        </div>
      </div>
    </div>
  </div>

  <script>
    const DATA = __MERGED_DATA__;
    let activeCat = 'all';
    let activeIdx = 0;
    let activePageIdx = 0;

    const themeToggle = document.getElementById('themeToggle');
    themeToggle.addEventListener('click', () => {
      document.documentElement.classList.toggle('dark');
    });

    function filterCat(cat) {
      activeCat = cat;
      document.querySelectorAll('.cat-btn').forEach(b => {
        if (b.innerText.toLowerCase().startsWith(cat.toLowerCase()) || (cat === 'all' && b.innerText === 'All')) {
          b.className = 'cat-btn text-[10px] px-2 py-0.5 rounded bg-slate-900 text-white dark:bg-white dark:text-slate-900 font-medium';
        } else {
          b.className = 'cat-btn text-[10px] px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300';
        }
      });
      renderList();
    }

    function renderList() {
      const listEl = document.getElementById('qList');
      const query = (document.getElementById('searchInput')?.value || '').toLowerCase();
      listEl.innerHTML = '';
      
      DATA.forEach((item, idx) => {
        const c = item.case;
        const rev = item.review;
        if (activeCat !== 'all' && c.category !== activeCat) return;
        if (query && !c.question.toLowerCase().includes(query) && !c.id.toLowerCase().includes(query)) return;

        const isPassed = rev.passed;
        const btn = document.createElement('button');
        btn.className = `w-full text-left p-2.5 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition flex items-start gap-2.5 ${idx === activeIdx ? 'bg-emerald-50 dark:bg-emerald-950/30 border-l-4 border-emerald-500' : ''}`;
        btn.onclick = () => { activeIdx = idx; activePageIdx = 0; renderList(); renderDetail(); renderPdf(); };

        const passBadge = isPassed
          ? `<span class="px-1.5 py-0.5 text-[9px] font-bold rounded bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300">PASS</span>`
          : `<span class="px-1.5 py-0.5 text-[9px] font-bold rounded bg-rose-100 text-rose-800 dark:bg-rose-900/60 dark:text-rose-300">FAIL</span>`;

        btn.innerHTML = `
          <div class="mt-0.5">${passBadge}</div>
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-1.5 text-[11px] text-slate-500 dark:text-slate-400">
              <span class="font-mono font-medium">${c.id}</span> · <span>${c.category}</span>
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
        ? `<span class="px-2 py-0.5 text-[11px] font-bold rounded bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700">PASS (2/2)</span>`
        : `<span class="px-2 py-0.5 text-[11px] font-bold rounded bg-rose-100 text-rose-800 dark:bg-rose-900/60 dark:text-rose-300 border border-rose-300 dark:border-rose-700">FAIL</span>`;

      let cropHtml = '';
      if (item.crops && item.crops.length > 0) {
        cropHtml = item.crops.map(crop => `
          <div class="mt-2.5 p-2 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg">
            <div class="text-[10px] font-semibold text-slate-500 mb-1">Ảnh Crop Bảng / Sơ đồ trích xuất:</div>
            <img src="${crop}" class="max-h-48 rounded object-contain mx-auto" alt="Crop preview" />
          </div>
        `).join('');
      }

      let eventsHtml = '';
      if (t.events && t.events.length > 0) {
        eventsHtml = t.events.map((ev, i) => {
          if (ev.event === 'search') {
            const results = (ev.results || []).map(res => `
              <div class="bg-white dark:bg-slate-800 p-2 rounded border border-slate-200 dark:border-slate-700 text-xs mt-1 shadow-2xs">
                <div class="flex items-center justify-between font-mono text-[11px] text-primary font-semibold">
                  <span>${res.id} (Trang ${res.page})</span>
                  <span class="text-slate-500 text-[10px]">Score: ${res.score}</span>
                </div>
                <div class="text-slate-600 dark:text-slate-300 text-[11px] mt-0.5 line-clamp-2">${res.text}</div>
              </div>
            `).join('');
            return `
              <div class="border-l-2 border-primary pl-2.5 py-1">
                <div class="text-[11px] font-bold text-primary">Turn ${i+1}: Search Tool Call</div>
                <div class="text-[11px] text-slate-700 dark:text-slate-300 font-mono mt-0.5 bg-slate-100 dark:bg-slate-700 px-2 py-0.5 rounded">"${ev.query}"</div>
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
        <div class="border-b border-slate-200 dark:border-slate-700 pb-2 mb-3">
          <div class="flex items-center justify-between">
            <span class="text-[11px] font-mono text-slate-500 dark:text-slate-400">${c.id} · ${c.category}</span>
            ${passTag}
          </div>
          <h2 class="text-sm font-bold text-slate-900 dark:text-white mt-1 leading-snug">${c.question}</h2>
        </div>

        <!-- Model Answer Card -->
        <div class="bg-slate-50 dark:bg-slate-900/60 p-3 rounded-xl border border-slate-200 dark:border-slate-700 mb-3">
          <div class="text-[11px] font-bold uppercase text-slate-500 dark:text-slate-400 mb-1 flex items-center justify-between">
            <span>Agent Answer (Claude 5.5 Haiku)</span>
            <span class="font-mono text-[10px] text-slate-400">${t.elapsed_ms || 0} ms</span>
          </div>
          <div class="text-xs text-slate-800 dark:text-slate-200 font-medium leading-relaxed">${t.answer || 'Không có câu trả lời'}</div>
          <div class="mt-2 pt-2 border-t border-slate-200 dark:border-slate-700 flex items-center gap-1.5 flex-wrap">
            <span class="text-[10px] text-slate-500">Citations:</span>
            ${citesList}
          </div>
        </div>

        <!-- Ground Truth Card -->
        <div class="bg-amber-50/60 dark:bg-amber-950/20 p-3 rounded-xl border border-amber-200 dark:border-amber-800/40 mb-3">
          <div class="text-[11px] font-bold uppercase text-amber-900 dark:text-amber-300 mb-1">Đáp án đối chiếu (Ground-Truth)</div>
          <div class="text-xs text-amber-900 dark:text-amber-200 font-medium mb-1.5">${c.gold_answer || 'Kỳ vọng từ chối an toàn'}</div>
          <div class="text-[11px] text-amber-800 dark:text-amber-300/80">Tiêu chí: ${c.criteria || 'N/A'}</div>
          ${cropHtml}
        </div>

        <!-- Execution Timeline -->
        <div class="flex-1">
          <div class="text-[11px] font-bold uppercase text-slate-500 dark:text-slate-400 mb-1.5">Lịch sử Truy vết Agent (Execution Trace)</div>
          <div class="flex flex-col gap-2.5">
            ${eventsHtml || '<div class="text-xs text-slate-400 italic">Không có sự kiện tìm kiếm</div>'}
          </div>
        </div>
      `;
    }

    function renderPdf() {
      const item = DATA[activeIdx];
      if (!item) return;
      const pages = item.evidence_pages || [];
      const tabsEl = document.getElementById('pageSwitchTabs');
      const badgeEl = document.getElementById('pdfPageBadge');
      const imgEl = document.getElementById('pdfPageImg');
      const hlLayer = document.getElementById('highlightLayer');
      const snipText = document.getElementById('evidenceSnippetText');
      const snipBox = document.getElementById('evidenceSnippetBox');

      hlLayer.innerHTML = '';
      tabsEl.innerHTML = '';

      if (pages.length === 0) {
        // Unanswerable or no evidence
        badgeEl.textContent = 'Thiếu bằng chứng';
        imgEl.src = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="600" height="800" viewBox="0 0 600 800"><rect width="600" height="800" fill="%23f8fafc"/><text x="300" y="400" font-family="sans-serif" font-size="16" fill="%2394a3b8" text-anchor="middle">Không có trang PDF dẫn chứng (Câu hỏi Unanswerable)</text></svg>';
        snipBox.className = 'w-full max-w-[620px] mt-3 p-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs text-slate-500';
        snipText.textContent = 'Câu hỏi không có bằng chứng trong báo cáo WDR 2025. Agent từ chối trả lời là hành vi chính xác tuyệt đối.';
        return;
      }

      if (activePageIdx >= pages.length) activePageIdx = 0;
      const currentPage = pages[activePageIdx];

      // Render Tabs if multi-page
      if (pages.length > 1) {
        pages.forEach((p, idx) => {
          const tab = document.createElement('button');
          tab.className = `text-[10px] font-semibold px-2 py-0.5 rounded transition ${idx === activePageIdx ? 'bg-primary text-white shadow-xs' : 'bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-300'}`;
          tab.textContent = p.label || `Trang ${p.page}`;
          tab.title = p.tag || '';
          tab.onclick = () => { activePageIdx = idx; renderPdf(); };
          tabsEl.appendChild(tab);
        });
      }

      badgeEl.innerHTML = `<span class="font-bold text-slate-800 dark:text-white">Trang ${currentPage.page} / 408</span> ${currentPage.tag ? '<span class="ml-1.5 px-1.5 py-0.5 bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300 rounded text-[10px] font-medium">' + currentPage.tag + '</span>' : ''}`;
      imgEl.src = currentPage.page_img;
      snipBox.className = 'w-full max-w-[620px] mt-3 p-3 bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800/60 rounded-xl text-xs text-amber-900 dark:text-amber-200';
      snipText.innerHTML = `<div class="font-semibold text-[11px] text-amber-800 dark:text-amber-300 mb-0.5">${currentPage.chunk_id ? '[' + currentPage.chunk_id + '] ' : ''}${currentPage.tag ? '· ' + currentPage.tag : ''}:</div><div class="italic">"${currentPage.snippet || 'Dữ liệu bằng chứng chuẩn'}"</div>`;

      // Highlight Box Overlay
      const r = currentPage.rect;
      if (r && r.length === 4) {
        const [left, top, width, height] = r;
        const box = document.createElement('div');
        box.className = 'pdf-highlight-box absolute rounded-xs';
        box.style.left = `${left}%`;
        box.style.top = `${top}%`;
        box.style.width = `${width}%`;
        box.style.height = `${height}%`;
        box.style.backgroundColor = 'rgba(254, 240, 138, 0.7)';
        box.style.border = '2px solid #eab308';
        box.title = currentPage.chunk_id || '';

        if (currentPage.chunk_id) {
          const pill = document.createElement('span');
          pill.className = 'absolute -top-4 left-0 px-1 py-0.2 bg-amber-600 text-white text-[9px] font-bold rounded shadow-xs whitespace-nowrap pointer-events-auto';
          pill.textContent = currentPage.chunk_id;
          box.appendChild(pill);
        }
        hlLayer.appendChild(box);
      }
    }

    renderList();
    renderDetail();
    renderPdf();
  </script>
</body>
</html>
"""

def generate_viewer():
    benchmark_path = ROOT / "data" / "advanced" / "benchmark_advanced.json"
    traces_path = ROOT / "starter" / "results" / "advanced-test" / "traces.json"
    reviews_path = ROOT / "starter" / "results" / "advanced-test" / "reviews.json"
    chunks_path = ROOT / "data" / "advanced" / "processed" / "chunks_advanced.json"

    benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
    traces = json.loads(traces_path.read_text(encoding="utf-8")) if traces_path.exists() else []
    reviews = json.loads(reviews_path.read_text(encoding="utf-8")) if reviews_path.exists() else []
    chunks = json.loads(chunks_path.read_text(encoding="utf-8")) if chunks_path.exists() else []
    chunk_map = {c["id"]: c for c in chunks}

    test_benchmark = [c for c in benchmark if c["split"] == "test"]
    trace_map = {t["query_id"]: t for t in traces}
    rev_map = {r["query_id"]: r for r in reviews}

    merged = []
    for c in test_benchmark:
        qid = c["id"]
        golds = c.get("gold", [])
        t = trace_map.get(qid, {})
        agent_cits = t.get("citations", [])
        evidence_pages = []
        crops = []
        seen_entries = set()

        # Priority 1: Chunks cited by Agent in actual answer
        for cid in agent_cits:
            chk = chunk_map.get(cid)
            if not chk:
                continue
            page = chk.get("page")
            if not page:
                continue

            bbox = chk.get("bbox", [0, 0, 576, 756])
            left = round((bbox[0] / 576.0) * 100, 2)
            top = round((bbox[1] / 756.0) * 100, 2)
            width = round(((bbox[2] - bbox[0]) / 576.0) * 100, 2)
            height = round(((bbox[3] - bbox[1]) / 756.0) * 100, 2)

            crop_path = chk.get("image_crop")
            if crop_path and crop_path not in crops:
                crops.append(crop_path)

            is_gold = any(g.get("chunk_id") == cid for g in golds)
            tag = "Dẫn chứng Trùng khớp 100%" if is_gold else "Dẫn chứng Agent Trích dẫn"

            entry_key = (page, cid)
            if entry_key not in seen_entries:
                seen_entries.add(entry_key)
                short_label = cid.replace("wdr2025-", "").replace("figure-", "fig.").upper()
                evidence_pages.append({
                    "page": page,
                    "page_img": f"data/advanced/pdf_pages/page_{page}.jpg",
                    "chunk_id": cid,
                    "rect": [left, top, width, height],
                    "label": f"Trang {page} · {short_label}",
                    "tag": tag,
                    "snippet": chk.get("text", "")[:180]
                })

        # Priority 2: Gold benchmark chunks (for abstained questions or ground-truth comparison)
        for g in golds:
            cid = g.get("chunk_id")
            chk = chunk_map.get(cid, {})
            page = g.get("page") or chk.get("page", 1)
            bbox = chk.get("bbox", [0, 0, 576, 756])
            left = round((bbox[0] / 576.0) * 100, 2)
            top = round((bbox[1] / 756.0) * 100, 2)
            width = round(((bbox[2] - bbox[0]) / 576.0) * 100, 2)
            height = round(((bbox[3] - bbox[1]) / 756.0) * 100, 2)

            crop_path = chk.get("image_crop")
            if crop_path and crop_path not in crops:
                crops.append(crop_path)

            entry_key = (page, cid)
            if entry_key not in seen_entries:
                seen_entries.add(entry_key)
                short_label = cid.replace("wdr2025-", "").replace("figure-", "fig.").upper() if cid else f"P{page}"
                evidence_pages.append({
                    "page": page,
                    "page_img": f"data/advanced/pdf_pages/page_{page}.jpg",
                    "chunk_id": cid or f"gold-p{page}",
                    "rect": [left, top, width, height],
                    "label": f"Trang {page} · Ground Truth",
                    "tag": "Ground-Truth Chuẩn",
                    "snippet": g.get("evidence_quote") or chk.get("text", "")[:180]
                })

        merged.append({
            "case": c,
            "trace": t,
            "review": rev_map.get(qid, {}),
            "evidence_pages": evidence_pages,
            "crops": crops
        })

    merged_json = json.dumps(merged, ensure_ascii=False)
    html_out = HTML_TEMPLATE.replace("__MERGED_DATA__", merged_json)
    out_file = ROOT / "advanced_viewer.html"
    out_file.write_text(html_out, encoding="utf-8")
    print(f"[AdvancedViewer] Successfully generated {out_file} ({len(html_out)} bytes)")


if __name__ == "__main__":
    generate_viewer()
