import time
import httpx
from typing import List, Dict, Optional, Any, Tuple
from .models import PaperSearchRequest, PaperItem, SearchResponse
from .key_manager import KeyManager

BASE_URL = "https://api.consensus.app/v1/search"

# Sample realistic mock papers for offline/demo/testing mode
MOCK_PAPERS = [
    {
        "id": "mock-1",
        "title": "Machine Learning and Multi-Criteria Decision-Making in Clinical Registry Evaluation: A Systematic Review",
        "authors": ["Jamshiddoost, Z.", "Mirzazadeh, M. N.", "Hassanzadeh, M."],
        "journal_name": "Journal of Medical Systems & Health Informatics",
        "publish_year": 2024,
        "publish_date": "2024-03-15",
        "doi": "10.1007/s10916-024-02051-x",
        "url": "https://consensus.app/papers/machine-learning-mcdm-clinical-registry",
        "abstract": "Clinical registries are essential for quality assessment and disease surveillance. This study evaluates the integration of multi-criteria decision making (MCDM) methods such as AHP and TOPSIS with machine learning models to benchmark registry performance across hospital networks.",
        "takeaway": "Combining MCDM with automated data quality scoring significantly improves registry performance evaluation and prioritizes intervention areas in hospital data systems.",
        "citation_count": 48,
        "influential_citation_count": 9,
        "study_type": "Systematic Review",
        "sample_size": 124,
        "population_type": "Hospital Clinical Registries",
        "sjr_best_quartile": 1,
        "is_preprint": False
    },
    {
        "id": "mock-2",
        "title": "Task-Technology Fit and Technology Acceptance of Health Information Systems: An Empirical Multi-Hospital Study",
        "authors": ["Goodhue, D. L.", "Thompson, R. L.", "Rahimi, B."],
        "journal_name": "International Journal of Medical Informatics",
        "publish_year": 2023,
        "publish_date": "2023-08-20",
        "doi": "10.1016/j.ijmedinf.2023.105120",
        "url": "https://consensus.app/papers/task-technology-fit-health-information-systems",
        "abstract": "The success of healthcare IT implementations heavily depends on user perception and workflow alignment. We surveyed 520 healthcare professionals across three tertiary centers to evaluate Task-Technology Fit (TTF) and individual performance impacts.",
        "takeaway": "High Task-Technology Fit directly correlates with a 42% increase in electronic record adoption and perceived clinical decision efficiency.",
        "citation_count": 92,
        "influential_citation_count": 21,
        "study_type": "Cross-Sectional Observational Study",
        "sample_size": 520,
        "population_type": "Physicians and Health Informatics Specialists",
        "sjr_best_quartile": 1,
        "is_preprint": False
    },
    {
        "id": "mock-3",
        "title": "Standardized Clinical Documentation and Disease Registries: Overcoming Fragmentation in National Health Data",
        "authors": ["Smith, A. E.", "Chen, W.", "Al-Mansour, K."],
        "journal_name": "BMC Health Services Research",
        "publish_year": 2024,
        "publish_date": "2024-01-10",
        "doi": "10.1186/s12913-024-10652-3",
        "url": "https://consensus.app/papers/standardized-clinical-documentation-registries",
        "abstract": "Fragmented data silos hinder evidence-based policymaking. We investigated national registry architectures across seven countries to identify common barriers in data standardization and interoperability using HL7 FHIR and ICD standards.",
        "takeaway": "Adopting unified terminologies and automated registry extractors reduced data discrepancies by 68% and accelerated epidemiological reporting.",
        "citation_count": 35,
        "influential_citation_count": 6,
        "study_type": "Comparative Policy Analysis",
        "sample_size": 28,
        "population_type": "National Registry Systems",
        "sjr_best_quartile": 1,
        "is_preprint": False
    },
    {
        "id": "mock-4",
        "title": "Evaluating Artificial Intelligence Decision Support Systems in Hospital Emergency Triage",
        "authors": ["Vanderbilt, P.", "Kowalski, J.", "Zhang, L."],
        "journal_name": "The Lancet Digital Health",
        "publish_year": 2024,
        "publish_date": "2024-05-18",
        "doi": "10.1016/S2589-7500(24)00045-8",
        "url": "https://consensus.app/papers/ai-decision-support-hospital-emergency-triage",
        "abstract": "Emergency triage requires rapid and accurate risk stratification. This prospective randomized trial compared standard nurse triage with an AI-augmented decision support tool across 14,000 emergency admissions.",
        "takeaway": "AI decision support reduced overtriage by 23% and undertriage by 18% without increasing wait times or provider burnout.",
        "citation_count": 67,
        "influential_citation_count": 15,
        "study_type": "Randomized Controlled Trial",
        "sample_size": 14200,
        "population_type": "Emergency Department Patients",
        "sjr_best_quartile": 1,
        "is_preprint": False
    },
    {
        "id": "mock-5",
        "title": "A Framework for Benchmarking Hospital Quality Indicators: Integration of Entropy Weight and TOPSIS",
        "authors": ["Opricovic, S.", "Tzeng, G. H.", "Farahani, R."],
        "journal_name": "European Journal of Operational Research",
        "publish_year": 2023,
        "publish_date": "2023-11-04",
        "doi": "10.1016/j.ejor.2023.09.012",
        "url": "https://consensus.app/papers/benchmarking-hospital-quality-indicators-topsis",
        "abstract": "Evaluating hospital performance across multi-dimensional metrics poses subjective weighting challenges. This paper establishes an objective Shannon entropy weighting model combined with TOPSIS ranking for 45 regional hospitals.",
        "takeaway": "The entropy-TOPSIS model eliminates subjective bias in hospital ranking, achieving 94% consistency with clinical peer review audits.",
        "citation_count": 110,
        "influential_citation_count": 28,
        "study_type": "Methodological Development & Validation",
        "sample_size": 45,
        "population_type": "Tertiary Care Hospitals",
        "sjr_best_quartile": 1,
        "is_preprint": False
    }
]

class ConsensusClient:
    def __init__(self, key_manager: KeyManager):
        self.key_manager = key_manager
        self.demo_mode = False

    def has_configured_keys(self) -> bool:
        """Returns True if at least one active key has a non-empty token."""
        return any(k.status == "active" and bool(k.key.strip()) for k in self.key_manager.keys)

    def _parse_paper(self, raw: Dict[str, Any], index: int) -> PaperItem:
        """Parses a Consensus API paper object into PaperItem."""
        authors = raw.get("authors") or []
        if isinstance(authors, list):
            # Authors can be list of strings or list of objects
            clean_authors = []
            for a in authors:
                if isinstance(a, str):
                    clean_authors.append(a)
                elif isinstance(a, dict) and "name" in a:
                    clean_authors.append(a["name"])
            authors = clean_authors
        else:
            authors = [str(authors)]

        return PaperItem(
            id=str(raw.get("doi") or raw.get("url") or f"paper-{index}"),
            title=raw.get("title") or "بدون عنوان",
            authors=authors,
            journal_name=raw.get("journal_name") or raw.get("publisher_name"),
            publish_year=raw.get("publish_year"),
            publish_date=raw.get("publish_date"),
            doi=raw.get("doi"),
            url=raw.get("url"),
            abstract=raw.get("abstract"),
            takeaway=raw.get("takeaway"),
            citation_count=raw.get("citation_count") or 0,
            influential_citation_count=raw.get("influential_citation_count") or 0,
            study_type=raw.get("study_type"),
            sample_size=raw.get("sample_size"),
            population_type=raw.get("population_type"),
            sjr_best_quartile=raw.get("sjr_best_quartile"),
            is_preprint=raw.get("is_preprint", False)
        )

    async def search(self, req: PaperSearchRequest) -> SearchResponse:
        """
        Executes a search query against Consensus API with automatic load balancing
        and immediate failover across configured keys.
        """
        start_time = time.time()
        failed_key_ids = []
        failovers = 0

        # If user explicitly enables demo mode or has not configured any keys yet:
        if self.demo_mode or not self.has_configured_keys():
            self.key_manager.log_event(
                "info", 
                f"اجرای جستجو در حالت پیش‌نمایش/شبیه‌سازی برای عبارت: '{req.query}' (کلید فعالی ثبت نشده یا حالت آزمایشی فعال است).", 
                "سیستم آزمایشی"
            )
            time.sleep(0.3)
            # Filter mock papers loosely
            q_lower = req.query.lower()
            filtered = [
                PaperItem(**p) for p in MOCK_PAPERS 
                if any(w in p["title"].lower() or w in (p["abstract"] or "").lower() for w in q_lower.split() if len(w) > 2)
            ]
            if not filtered:
                filtered = [PaperItem(**p) for p in MOCK_PAPERS]

            exec_time = round((time.time() - start_time) * 1000, 2)
            return SearchResponse(
                query=req.query,
                results=filtered,
                page=req.page or 1,
                page_size=req.page_size or 10,
                is_end=True,
                key_used="حالت پیش‌نمایش (Demo Mode)",
                failovers_count=0,
                execution_time_ms=exec_time
            )

        # Loop through keys with failover
        while True:
            key_obj = await self.key_manager.get_next_available_key(exclude_ids=failed_key_ids)
            
            if not key_obj:
                msg = "تمام کلیدهای موجود در استخر کلیدها با محدودیت (۴۲۹/۴۰۳) یا خطا مواجه شده‌اند. لطفاً چند لحظه دیگر دوباره تلاش کنید یا کلید جدید اضافه نمایید."
                self.key_manager.log_event("error", msg)
                raise RuntimeError(msg)

            # Build query params
            params = {"query": req.query}
            if req.year_min:
                params["year_min"] = req.year_min
            if req.year_max:
                params["year_max"] = req.year_max
            if req.page:
                params["page"] = req.page
            if req.page_size:
                params["page_size"] = req.page_size
            if req.include_full_text:
                params["include_full_text_chunks"] = "true"

            headers = {
                "x-api-key": key_obj.key,
                "User-Agent": "ConsensusPaperCraft/1.0"
            }

            try:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    res = await client.get(BASE_URL, headers=headers, params=params)

                if res.status_code == 200:
                    # Success!
                    self.key_manager.record_success(key_obj.id)
                    data = res.json()
                    raw_results = data.get("results") or []
                    parsed_papers = [self._parse_paper(p, idx) for idx, p in enumerate(raw_results)]

                    exec_time = round((time.time() - start_time) * 1000, 2)
                    self.key_manager.log_event(
                        "success", 
                        f"درخواست موفقیت‌آمیز برای [{req.query}] با کلید [{key_obj.name}]. دریافت {len(parsed_papers)} مقاله.", 
                        key_obj.name
                    )

                    return SearchResponse(
                        query=req.query,
                        results=parsed_papers,
                        page=data.get("page", req.page or 1),
                        page_size=data.get("page_size", req.page_size or 10),
                        is_end=data.get("is_end", True),
                        key_used=key_obj.name,
                        failovers_count=failovers,
                        execution_time_ms=exec_time
                    )

                else:
                    # Error status code: 429, 403, 402, 401, 500, etc.
                    self.key_manager.record_failure(key_obj.id, res.status_code, res.text[:200])
                    failed_key_ids.append(key_obj.id)
                    failovers += 1
                    # Will loop to next key automatically!
                    continue

            except httpx.RequestError as exc:
                self.key_manager.record_failure(key_obj.id, 0, f"خطای شبکه: {str(exc)}")
                failed_key_ids.append(key_obj.id)
                failovers += 1
                continue
