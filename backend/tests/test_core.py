"""
Unit tests for the Multi-Agent AI Research Platform core components.
Tests text chunking, citation manager, cost tracking, and errors.
Uses the standard library unittest module.
"""
import unittest
import os
import sys

# Ensure backend root is in import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.rag.chunker import TextChunker
from app.services.citation_manager import CitationManager
from app.services.cost_tracker import CostTracker
from app.schemas.internal import Source


class TestCoreComponents(unittest.TestCase):

    def test_text_chunker(self):
        chunker = TextChunker(chunk_size=100, overlap=20)
        text = (
            "This is a long sentence that should go into the first chunk. "
            "Here is another sentence that will exceed the size and start the second chunk. "
            "Finally, this is the last part of our test document."
        )
        chunks = chunker.chunk(text, source_url="https://test.com")
        
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all("text" in c for c in chunks))
        self.assertTrue(all(c["source_url"] == "https://test.com" for c in chunks))

    def test_citation_manager(self):
        cm = CitationManager()
        
        source1 = Source(url="https://nvidia.com", title="Nvidia Revenue", source_type="web", credibility_score=0.9)
        source2 = Source(url="https://amd.com", title="AMD Revenue", source_type="web", credibility_score=0.85)
        source3 = Source(url="https://nvidia.com", title="Nvidia AI Chip", source_type="web", credibility_score=0.9) # duplicate URL
        
        ref1 = cm.collect(source1)
        ref2 = cm.collect(source2)
        ref3 = cm.collect(source3)
        
        self.assertEqual(ref1, "[1]")
        self.assertEqual(ref2, "[2]")
        self.assertEqual(ref3, "[1]")  # Deduplicated
        self.assertEqual(cm.count, 2)
        
        ref_list = cm.format_references_markdown()
        self.assertIn("[1]", ref_list)
        self.assertIn("https://nvidia.com", ref_list)

    def test_cost_tracker(self):
        tracker = CostTracker()
        
        tracker.record(
            agent="SearchAgent",
            model="gemini-2.0-flash",
            input_tokens=1000,
            output_tokens=500,
            duration_seconds=1.5
        )
        
        summary = tracker.get_summary()
        self.assertEqual(summary["total_tokens"], 1500)
        self.assertGreater(summary["total_cost_usd"], 0)
        self.assertIn("SearchAgent", summary["by_agent"])


if __name__ == '__main__':
    unittest.main()
