import os
import uvicorn
from fastapi import FastAPI, HTTPException, Response, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional

from backend.models import (
    KeyAddRequest, BulkKeysRequest, KeyUpdateRequest,
    PaperSearchRequest, SectionGenerateRequest, ProjectDraft
)
from backend.key_manager import KeyManager
from backend.consensus_client import ConsensusClient
from backend.paper_generator import PaperGenerator
from backend.exporter import Exporter
from backend.storage import Storage

app = FastAPI(
    title="Consensus PaperCraft Studio",
    description="سیستم هوشمند نگارش مقاله علمی با اتصال به API Consensus و بالانسر توزیع بار",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize core services
key_manager = KeyManager()
consensus_client = ConsensusClient(key_manager)
paper_generator = PaperGenerator()
storage = Storage()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Static files mounting
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Consensus PaperCraft Studio Backend is Running"}

# --- Key Management Endpoints ---

@app.get("/api/keys")
async def get_keys():
    """Returns list of all configured API keys with status and request metrics."""
    keys = key_manager.get_all_keys(mask_keys=True)
    active_count = sum(1 for k in keys if k["status"] == "active" and k["key"])
    rate_limited_count = sum(1 for k in keys if k["status"] == "rate_limited")
    quota_count = sum(1 for k in keys if k["status"] == "quota_exhausted")
    total_calls = sum(k["requests_count"] for k in keys)

    return {
        "keys": keys,
        "total_keys": len(keys),
        "active_keys": active_count,
        "rate_limited_keys": rate_limited_count,
        "quota_exhausted_keys": quota_count,
        "total_requests_served": total_calls,
        "demo_mode": consensus_client.demo_mode
    }

@app.post("/api/keys")
async def add_key(req: KeyAddRequest):
    """Add a new Consensus API key to the pool."""
    try:
        new_k = key_manager.add_key(req.key, req.name)
        return {"success": True, "key": new_k.model_dump()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/keys/bulk")
async def add_bulk_keys(req: BulkKeysRequest):
    """Bulk import multiple keys (e.g. 6 keys from account list)."""
    added, errors = key_manager.add_bulk_keys(req.keys_text)
    return {
        "success": True,
        "added_count": added,
        "errors": errors
    }

@app.put("/api/keys/{key_id}")
async def update_key(key_id: str, req: KeyUpdateRequest):
    k = key_manager.update_key(key_id, req.name, req.status)
    if not k:
        raise HTTPException(status_code=404, detail="کلید مورد نظر یافت نشد.")
    return {"success": True, "key": k.model_dump()}

@app.delete("/api/keys/{key_id}")
async def delete_key(key_id: str):
    success = key_manager.delete_key(key_id)
    if not success:
        raise HTTPException(status_code=404, detail="کلید یافت نشد.")
    return {"success": True}

@app.post("/api/keys/test")
async def test_key(data: Dict[str, str]):
    """Ping tests an API key against Consensus API."""
    key_str = data.get("key", "").strip()
    if not key_str:
        raise HTTPException(status_code=400, detail="کلید ارسال نشده است.")
    is_ok, msg = await key_manager.test_key(key_str)
    return {"valid": is_ok, "message": msg}

@app.post("/api/keys/reset")
async def reset_all_keys():
    """Resets all stats and statuses back to active."""
    key_manager.reset_all_stats()
    return {"success": True, "message": "تمامی کلیدها به حالت فعال بازنشانی شدند."}

@app.get("/api/logs")
async def get_logs():
    """Returns load-balancer and failover activity logs."""
    return {"logs": key_manager.activity_logs}

@app.post("/api/settings/demo")
async def toggle_demo(data: Dict[str, bool]):
    val = data.get("demo_mode", False)
    consensus_client.demo_mode = val
    status_str = "فعال" if val else "غیرفعال"
    key_manager.log_event("info", f"حالت آزمایشی (Demo Mode) {status_str} شد.")
    return {"demo_mode": consensus_client.demo_mode}

# --- Consensus Search & Literature Endpoints ---

@app.post("/api/search")
async def search_papers(req: PaperSearchRequest):
    """Searches scientific literature using Consensus API with round-robin and automatic failover."""
    try:
        response = await consensus_client.search(req)
        return response
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطای غیرمنتظره در ارتباط با سرور: {str(e)}")

# --- Literature Library Endpoints ---

@app.get("/api/library")
async def get_library():
    papers = storage.get_library_papers()
    return {"papers": papers, "count": len(papers)}

@app.post("/api/library")
async def save_to_library(paper: Dict[str, Any]):
    saved = storage.save_paper_to_library(paper)
    return {"success": True, "paper": saved}

@app.delete("/api/library/{paper_id}")
async def remove_from_library(paper_id: str):
    success = storage.remove_paper_from_library(paper_id)
    return {"success": success}

# --- Paper Generation Studio ---

@app.post("/api/generate-section")
async def generate_section(req: SectionGenerateRequest):
    """Synthesizes academic paper sections using Consensus literature evidence."""
    # If no custom papers passed, pull from library
    if not req.custom_papers:
        all_library_papers = storage.get_library_papers()
        if req.paper_ids:
            selected = [p for p in all_library_papers if p.get("id") in req.paper_ids or p.get("doi") in req.paper_ids]
            req.custom_papers = selected
        else:
            req.custom_papers = all_library_papers[:10]

    result = paper_generator.generate_section(req)
    return result

# --- Exporters ---

@app.post("/api/export/docx")
async def export_docx(data: Dict[str, Any]):
    """Exports paper content to Microsoft Word (.docx)."""
    title = data.get("title", "مقاله پژوهشی")
    content = data.get("content", "")
    lang = data.get("language", "fa")
    is_rtl = (lang == "fa")

    docx_bytes = Exporter.export_to_docx(title, content, is_rtl=is_rtl)
    
    filename = f"{title[:40].strip().replace(' ', '_')}.docx"
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@app.post("/api/export/ris")
async def export_ris(data: Dict[str, Any]):
    """Exports library or selected papers to EndNote RIS (.ris) format."""
    papers = data.get("papers") or storage.get_library_papers()
    ris_content = Exporter.export_to_ris(papers)
    return Response(
        content=ris_content,
        media_type="application/x-research-info-systems",
        headers={"Content-Disposition": 'attachment; filename="references.ris"'}
    )

@app.post("/api/export/enw")
async def export_enw(data: Dict[str, Any]):
    """Exports library or selected papers to EndNote (.enw) format."""
    papers = data.get("papers") or storage.get_library_papers()
    enw_content = Exporter.export_to_enw(papers)
    return Response(
        content=enw_content,
        media_type="text/plain",
        headers={"Content-Disposition": 'attachment; filename="references.enw"'}
    )

# --- Projects Management ---

@app.get("/api/projects")
async def get_projects():
    return {"projects": storage.get_projects()}

@app.post("/api/projects")
async def save_project(project: Dict[str, Any]):
    saved = storage.save_project(project)
    return {"success": True, "project": saved}

@app.delete("/api/projects/{p_id}")
async def delete_project(p_id: str):
    success = storage.delete_project(p_id)
    return {"success": success}

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
