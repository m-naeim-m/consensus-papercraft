from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class ConsensusApiKey(BaseModel):
    id: str
    name: str
    key: str
    status: str = "active"  # active, rate_limited, quota_exhausted, invalid, disabled
    requests_count: int = 0
    consecutive_errors: int = 0
    last_used: Optional[str] = None
    cooldown_until: Optional[float] = None
    last_error: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class KeyAddRequest(BaseModel):
    name: Optional[str] = None
    key: str

class BulkKeysRequest(BaseModel):
    keys_text: str  # multiple keys, one per line or comma-separated

class KeyUpdateRequest(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None

class PaperSearchRequest(BaseModel):
    query: str
    year_min: Optional[int] = None
    year_max: Optional[int] = None
    page: Optional[int] = 1
    page_size: Optional[int] = 10
    include_full_text: Optional[bool] = False

class PaperItem(BaseModel):
    id: Optional[str] = None
    title: str
    authors: List[str] = []
    journal_name: Optional[str] = None
    publish_year: Optional[int] = None
    publish_date: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    abstract: Optional[str] = None
    takeaway: Optional[str] = None
    citation_count: Optional[int] = 0
    influential_citation_count: Optional[int] = 0
    study_type: Optional[str] = None
    sample_size: Optional[int] = None
    population_type: Optional[str] = None
    sjr_best_quartile: Optional[int] = None
    is_preprint: Optional[bool] = False

class SearchResponse(BaseModel):
    query: str
    results: List[PaperItem]
    page: int = 1
    page_size: int = 10
    is_end: bool = True
    key_used: str
    failovers_count: int = 0
    execution_time_ms: float = 0.0

class SectionGenerateRequest(BaseModel):
    topic: str
    section_type: str  # title, abstract, introduction, literature_review, methodology, results_discussion, conclusion, full_paper
    language: str = "fa"  # fa or en
    paper_ids: List[str] = []  # IDs of selected papers from library
    additional_notes: Optional[str] = None
    custom_papers: Optional[List[Dict[str, Any]]] = None
    citation_style: str = "APA"  # APA, Vancouver, IEEE

class ProjectDraft(BaseModel):
    id: str
    title: str
    topic: str
    language: str = "fa"
    citation_style: str = "APA"
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    sections: Dict[str, str] = {}
    selected_papers: List[Dict[str, Any]] = []
