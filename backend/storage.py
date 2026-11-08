import json
import os
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIBRARY_FILE = os.path.join(WORKSPACE_DIR, "papers_library.json")
PROJECTS_FILE = os.path.join(WORKSPACE_DIR, "paper_projects.json")

class Storage:
    def __init__(self):
        self.library_file = LIBRARY_FILE
        self.projects_file = PROJECTS_FILE
        self._init_files()

    def _init_files(self):
        if not os.path.exists(self.library_file):
            with open(self.library_file, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
        if not os.path.exists(self.projects_file):
            with open(self.projects_file, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)

    def get_library_papers(self) -> List[Dict[str, Any]]:
        try:
            with open(self.library_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def save_paper_to_library(self, paper_dict: Dict[str, Any]) -> Dict[str, Any]:
        papers = self.get_library_papers()
        # Avoid duplicate DOI or title
        doi = paper_dict.get("doi")
        title = (paper_dict.get("title") or "").strip().lower()

        for p in papers:
            if doi and p.get("doi") == doi:
                return p
            if title and (p.get("title") or "").strip().lower() == title:
                return p

        if "id" not in paper_dict or not paper_dict["id"]:
            paper_dict["id"] = str(uuid.uuid4())[:8]

        paper_dict["saved_at"] = datetime.now().isoformat()
        papers.insert(0, paper_dict)

        with open(self.library_file, "w", encoding="utf-8") as f:
            json.dump(papers, f, ensure_ascii=False, indent=2)
        return paper_dict

    def remove_paper_from_library(self, paper_id: str) -> bool:
        papers = self.get_library_papers()
        new_papers = [p for p in papers if str(p.get("id")) != str(paper_id) and str(p.get("doi")) != str(paper_id)]
        if len(new_papers) < len(papers):
            with open(self.library_file, "w", encoding="utf-8") as f:
                json.dump(new_papers, f, ensure_ascii=False, indent=2)
            return True
        return False

    def clear_library(self):
        with open(self.library_file, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)

    def get_projects(self) -> List[Dict[str, Any]]:
        try:
            with open(self.projects_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def save_project(self, project: Dict[str, Any]) -> Dict[str, Any]:
        projects = self.get_projects()
        p_id = project.get("id") or str(uuid.uuid4())[:8]
        project["id"] = p_id
        project["updated_at"] = datetime.now().isoformat()

        found = False
        for i, p in enumerate(projects):
            if p.get("id") == p_id:
                projects[i] = project
                found = True
                break
        if not found:
            project["created_at"] = datetime.now().isoformat()
            projects.insert(0, project)

        with open(self.projects_file, "w", encoding="utf-8") as f:
            json.dump(projects, f, ensure_ascii=False, indent=2)
        return project

    def delete_project(self, project_id: str) -> bool:
        projects = self.get_projects()
        new_p = [p for p in projects if p.get("id") != project_id]
        if len(new_p) < len(projects):
            with open(self.projects_file, "w", encoding="utf-8") as f:
                json.dump(new_p, f, ensure_ascii=False, indent=2)
            return True
        return False
