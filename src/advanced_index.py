"""
Advanced Multimodal Indexing Pipeline for World Development Report 2025.
Extracts:
1. Text paragraphs with chapter/section context and bounding boxes
2. Structured Markdown tables with column headers and units
3. Visual figures, charts, and diagrams with crop images and structured captions
"""
import sys
import json
import time
import re
from pathlib import Path

# Add Day 6 site-packages for sentence-transformers
day6_site_packages = Path(r"E:\Projects\Lab6Vinuni\K5-L3B-DAY06-NguyenVanLam-2A202604115-DataIngestion\starter\.venv\Lib\site-packages")
if day6_site_packages.exists() and str(day6_site_packages) not in sys.path:
    sys.path.insert(0, str(day6_site_packages))

import fitz  # PyMuPDF
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
PDF_PATH = ROOT / "data" / "advanced" / "raw" / "World Development Report 2025 – Standards for Development.pdf"
IMAGES_DIR = ROOT / "data" / "advanced" / "images"
PAGES_DIR = ROOT / "data" / "advanced" / "pdf_pages"
PROCESSED_DIR = ROOT / "data" / "advanced" / "processed"

IMAGES_DIR.mkdir(parents=True, exist_ok=True)
PAGES_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def get_toc_sections(doc):
    """Map page numbers to Chapter and Section titles."""
    toc = doc.get_toc()
    # Sort by page
    page_to_section = {}
    current_chapter = "Overview"
    current_section = "Overview"

    for lvl, title, page in toc:
        if lvl == 1:
            current_chapter = title.strip()
            current_section = title.strip()
        elif lvl == 2:
            current_section = title.strip()
        
        # Assign to page
        page_to_section[page] = {
            "chapter": current_chapter,
            "section": current_section
        }
    return page_to_section


def extract_table_markdown(table):
    """Convert fitz table extract into clean Markdown table."""
    raw_data = table.extract()
    if not raw_data or len(raw_data) < 2:
        return None
    
    # Clean rows and cells
    cleaned_rows = []
    for row in raw_data:
        clean_row = [str(cell).strip().replace("\n", " ") if cell is not None else "" for cell in row]
        if any(clean_row):
            cleaned_rows.append(clean_row)
            
    if len(cleaned_rows) < 2:
        return None
        
    num_cols = max(len(r) for r in cleaned_rows)
    for r in cleaned_rows:
        while len(r) < num_cols:
            r.append("")
            
    headers = cleaned_rows[0]
    md_lines = ["| " + " | ".join(headers) + " |"]
    md_lines.append("| " + " | ".join(["---"] * num_cols) + " |")
    for r in cleaned_rows[1:]:
        md_lines.append("| " + " | ".join(r) + " |")
        
    return "\n".join(md_lines)


def run_indexing():
    print(f"[1/4] Opening PDF: {PDF_PATH.name}")
    doc = fitz.open(str(PDF_PATH))
    total_pages = len(doc)
    print(f"      Total pages to process: {total_pages}")
    
    toc_map = get_toc_sections(doc)
    
    chunks = []
    current_ch = "Front Matter"
    current_sec = "Intro"
    
    print("[2/4] Extracting Text, Tables, and Visual Figures...")
    start_time = time.perf_counter()
    
    for pno in range(total_pages):
        page_num = pno + 1
        page = doc[pno]
        
        if page_num in toc_map:
            current_ch = toc_map[page_num]["chapter"]
            current_sec = toc_map[page_num]["section"]
            
        page_rect = page.rect
        page_width, page_height = page_rect.width, page_rect.height
        
        # 1. Extract Tables
        tab_bboxes = []
        try:
            tabs = page.find_tables()
            if tabs and tabs.tables:
                for tidx, tab in enumerate(tabs.tables):
                    t_bbox = list(tab.bbox)
                    tab_bboxes.append(t_bbox)
                    md_table = extract_table_markdown(tab)
                    if md_table:
                        # Extract table caption/title from text above table
                        above_rect = fitz.Rect(t_bbox[0] - 10, max(0, t_bbox[1] - 60), t_bbox[2] + 10, t_bbox[1])
                        caption_text = page.get_text("text", clip=above_rect).strip().replace("\n", " ")
                        
                        chunk_text = f"### [TABLE] {caption_text}\n" if caption_text else "### [TABLE]\n"
                        chunk_text += f"{md_table}\n"
                        chunk_text += f"Location: Page {page_num} | Chapter: {current_ch}"
                        
                        chunks.append({
                            "id": f"wdr2025-p{page_num:03d}-table{tidx+1:02d}",
                            "source_id": "World_Development_Report_2025.pdf",
                            "page": page_num,
                            "chunk_type": "table",
                            "chapter": current_ch,
                            "section": current_sec,
                            "bbox": t_bbox,
                            "text": chunk_text
                        })
        except Exception as e:
            pass
            
        # 2. Extract Figures, Charts, Diagrams, Maps, Boxes
        blocks = page.get_text("blocks")
        fig_candidates = []
        
        for bidx, b in enumerate(blocks):
            b_text = b[4].strip()
            # Detect Figure / Map / Box headings
            m = re.match(r'^(Figure|Map|Box|Table)\s+([A-Z0-9\.]+)\b', b_text, re.IGNORECASE)
            if m:
                fig_type = m.group(1).capitalize()
                fig_num = m.group(2)
                fig_bbox = list(b[:4])
                
                # Expand bbox to include the visual chart or following description
                # Gather text in following blocks belonging to this visual
                full_fig_text = [b_text]
                for next_b in blocks[bidx+1:]:
                    nb_text = next_b[4].strip()
                    if re.match(r'^(Figure|Map|Box|Table)\s+[A-Z0-9\.]+', nb_text, re.IGNORECASE):
                        break
                    if "World Development Report 2025" in nb_text:
                        continue
                    full_fig_text.append(nb_text)
                    fig_bbox[2] = max(fig_bbox[2], next_b[2])
                    fig_bbox[3] = max(fig_bbox[3], next_b[3])
                    if len(" ".join(full_fig_text)) > 900:
                        break
                        
                combined_fig_text = "\n".join(full_fig_text)
                
                # Crop image of the figure
                clip_rect = fitz.Rect(
                    max(0, fig_bbox[0] - 5),
                    max(0, fig_bbox[1] - 5),
                    min(page_width, fig_bbox[2] + 5),
                    min(page_height, fig_bbox[3] + 5)
                )
                
                img_filename = f"crop_p{page_num:03d}_{fig_type.lower()}_{fig_num.replace('.', '_')}.png"
                img_path = IMAGES_DIR / img_filename
                
                try:
                    pix = page.get_pixmap(clip=clip_rect, dpi=150)
                    pix.save(str(img_path))
                except Exception:
                    img_filename = None
                    
                chunks.append({
                    "id": f"wdr2025-p{page_num:03d}-{fig_type.lower()}-{fig_num.replace('.', '_')}",
                    "source_id": "World_Development_Report_2025.pdf",
                    "page": page_num,
                    "chunk_type": "figure" if fig_type in ("Figure", "Box") else ("map" if fig_type == "Map" else "table"),
                    "chapter": current_ch,
                    "section": current_sec,
                    "bbox": fig_bbox,
                    "image_crop": f"data/advanced/images/{img_filename}" if img_filename else None,
                    "text": f"### [{fig_type.upper()} {fig_num}] {combined_fig_text}\nLocation: Page {page_num} | Chapter: {current_ch}"
                })
                
        # 3. Extract Text Paragraphs (excluding already captured tables)
        for bidx, b in enumerate(blocks):
            b_text = b[4].strip()
            if len(b_text) < 50:
                continue
            if "World Development Report 2025" in b_text:
                continue
            # Skip if inside table bbox
            b_rect = fitz.Rect(b[:4])
            is_in_table = any(fitz.Rect(tb).intersects(b_rect) for tb in tab_bboxes)
            if is_in_table:
                continue
                
            clean_p = " ".join(b_text.split())
            if len(clean_p) > 60:
                chunk_content = f"[{current_ch} | Page {page_num}]\n{clean_p}"
                chunks.append({
                    "id": f"wdr2025-p{page_num:03d}-para{bidx:03d}",
                    "source_id": "World_Development_Report_2025.pdf",
                    "page": page_num,
                    "chunk_type": "text",
                    "chapter": current_ch,
                    "section": current_sec,
                    "bbox": list(b[:4]),
                    "text": chunk_content
                })
                
    elapsed = time.perf_counter() - start_time
    print(f"      Extracted {len(chunks)} chunks in {elapsed:.1f}s")
    
    # Save chunks
    chunks_path = PROCESSED_DIR / "chunks_advanced.json"
    chunks_path.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"      Saved chunks to: {chunks_path}")
    
    # 3. Generate Dense Embeddings
    print("[3/4] Generating Embeddings using SentenceTransformer ('all-MiniLM-L6-v2')...")
    from sentence_transformers import SentenceTransformer
    embedder = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
    
    texts_to_embed = [c["text"] for c in chunks]
    batch_size = 64
    all_embeddings = []
    
    for i in range(0, len(texts_to_embed), batch_size):
        batch = texts_to_embed[i:i+batch_size]
        batch_embs = embedder.encode(batch, normalize_embeddings=True)
        all_embeddings.extend(batch_embs.tolist())
        if (i // batch_size) % 10 == 0:
            print(f"      Embedded {min(i+batch_size, len(texts_to_embed))}/{len(texts_to_embed)} chunks...")
            
    embeddings_map = {c["id"]: all_embeddings[idx] for idx, c in enumerate(chunks)}
    embs_path = PROCESSED_DIR / "chunk_embeddings_advanced.json"
    embs_path.write_text(json.dumps(embeddings_map), encoding="utf-8")
    print(f"      Saved embeddings to: {embs_path}")
    
    # 4. Render sample page images for viewer
    print("[4/4] Pre-rendering key pages for Visual PDF Viewer...")
    pages_to_render = set(c["page"] for c in chunks if c["chunk_type"] in ("table", "figure", "map"))
    print(f"      Rendering {len(pages_to_render)} visual pages to JPEG...")
    for p in pages_to_render:
        page_img_path = PAGES_DIR / f"page_{p}.jpg"
        if not page_img_path.exists():
            pix = doc[p-1].get_pixmap(dpi=150)
            pix.save(str(page_img_path))
            
    print("[DONE] Advanced indexing completed successfully!")


if __name__ == "__main__":
    run_indexing()
