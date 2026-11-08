import asyncio
import os
import sys

# Test imports
from backend.models import ConsensusApiKey, PaperSearchRequest, SectionGenerateRequest
from backend.key_manager import KeyManager
from backend.consensus_client import ConsensusClient
from backend.paper_generator import PaperGenerator
from backend.exporter import Exporter
from backend.storage import Storage

def run_tests():
    print("=== 1. Testing Key Manager ===")
    test_keys_file = os.path.join(os.path.dirname(__file__), "test_keys.json")
    if os.path.exists(test_keys_file):
        os.remove(test_keys_file)
    km = KeyManager(filepath=test_keys_file)
    km.keys = []  # clear template slots for clean assertion
    k1 = km.add_key("test_key_1", "اکانت تست ۱")
    k2 = km.add_key("test_key_2", "اکانت تست ۲")
    k3 = km.add_key("test_key_3", "اکانت تست ۳")
    assert len(km.keys) == 3, f"Expected 3 keys, got {len(km.keys)}"
    print("✓ Added 3 keys successfully")

    # Round robin test
    async def test_rotation():
        key_seq = []
        for _ in range(6):
            k = await km.get_next_available_key()
            key_seq.append(k.name)
        return key_seq

    seq = asyncio.run(test_rotation())
    print(f"✓ Round robin sequence: {seq}")
    assert seq[0] != seq[1], "Keys should alternate!"

    # Simulate 429 Rate Limit Failover
    print("\n=== 2. Testing 429 Rate Limit Failover ===")
    km.record_failure(k1.id, 429, "Too Many Requests")
    assert k1.status == "rate_limited", "Key 1 should be rate_limited"
    assert k1.cooldown_until is not None, "Cooldown should be set"
    print(f"✓ Key 1 status after 429: {k1.status} (Cooldown set)")

    # Next key should automatically skip k1
    async def test_failover_skip():
        k = await km.get_next_available_key()
        return k.name

    next_key = asyncio.run(test_failover_skip())
    print(f"✓ Next key selected automatically: {next_key} (Key 1 was skipped!)")
    assert next_key != "اکانت تست ۱", "Key 1 should have been skipped due to rate limit"

    # Simulate 403 Quota Exhaustion
    print("\n=== 3. Testing 403 Quota Exhaustion Failover ===")
    km.record_failure(k2.id, 403, "Quota Exceeded")
    assert k2.status == "quota_exhausted", "Key 2 should be quota_exhausted"
    print(f"✓ Key 2 status after 403: {k2.status}")

    # Now only k3 remains eligible
    next_key = asyncio.run(test_failover_skip())
    print(f"✓ Remaining key selected: {next_key}")
    assert next_key == "اکانت تست ۳", "Key 3 must be selected as only active key"

    # Reset all keys
    km.reset_all_stats()
    assert k1.status == "active" and k2.status == "active", "Keys should reset to active"
    print("✓ Reset all keys successful")

    print("\n=== 4. Testing Consensus Client & Mock Search ===")
    cc = ConsensusClient(km)
    cc.demo_mode = True  # Enable demo mode for unit test without live internet
    search_req = PaperSearchRequest(query="clinical registry evaluation", page_size=5)
    search_res = asyncio.run(cc.search(search_req))
    print(f"✓ Search returned {len(search_res.results)} papers in {search_res.execution_time_ms} ms")
    assert len(search_res.results) > 0, "Should return results"
    sample_paper = search_res.results[0]
    print(f"  Sample paper: '{sample_paper.title}' by {sample_paper.authors}")

    print("\n=== 5. Testing Paper Generator & Evidence Synthesis ===")
    pg = PaperGenerator()
    papers_dict = [p.model_dump() for p in search_res.results]

    gen_req = SectionGenerateRequest(
        topic="ارزیابی عملکرد نظام‌های ثبت بالینی",
        section_type="literature_review",
        language="fa",
        citation_style="APA",
        custom_papers=papers_dict
    )
    result = pg.generate_section(gen_req)
    print(f"✓ Literature review generated ({len(result['content'])} chars, {len(result['references'])} references)")
    assert "## ۲. مبانی نظری" in result["content"], "Literature review header missing"
    assert len(result["references"]) == len(papers_dict), "References count mismatch"

    # Test full paper generation
    full_req = SectionGenerateRequest(
        topic="ارزیابی عملکرد نظام‌های ثبت بالینی",
        section_type="full_paper",
        language="fa",
        citation_style="APA",
        custom_papers=papers_dict
    )
    full_result = pg.generate_section(full_req)
    print(f"✓ Full paper generated ({len(full_result['content'])} chars)")
    assert "چکیده" in full_result["content"], "Abstract missing in full paper"
    assert "روش‌ پژوهش" in full_result["content"], "Methods missing in full paper"

    print("\n=== 6. Testing DOCX Exporter ===")
    docx_bytes = Exporter.export_to_docx(
        title="ارزیابی عملکرد نظام‌های ثبت بالینی",
        markdown_content=full_result["content"],
        is_rtl=True
    )
    print(f"✓ DOCX generated successfully ({len(docx_bytes)} bytes)")
    assert len(docx_bytes) > 1000, "DOCX file too small"

    # Save sample docx
    sample_docx_path = os.path.join(os.path.dirname(__file__), "test_generated_paper.docx")
    with open(sample_docx_path, "wb") as f:
        f.write(docx_bytes)
    print(f"  Saved test docx to: {sample_docx_path}")

    print("\n=== 7. Testing EndNote Exporters (.ris and .enw) ===")
    ris = Exporter.export_to_ris(papers_dict)
    enw = Exporter.export_to_enw(papers_dict)
    print(f"✓ RIS export: {len(ris.splitlines())} lines")
    print(f"✓ ENW export: {len(enw.splitlines())} lines")
    assert "TY  - JOUR" in ris, "RIS tag missing"
    assert "%0 Journal Article" in enw, "ENW tag missing"

    print("\n========================================================")
    print("   ALL UNIT AND INTEGRATION TESTS PASSED WITH 100%!     ")
    print("========================================================")

if __name__ == "__main__":
    run_tests()
