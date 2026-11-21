"""Regression: generic 'auto' resolves to a real topic once before rendering."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import topic_discovery_audit


class TopicDiscoveryAuditTests(unittest.TestCase):
    def test_auto_resolves_and_records_actual_selected_subject(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            topics=root/"topics.json"
            topics.write_text(json.dumps([{"topic_id":"human_moments",
                                            "search":["acrobatics"]}]))
            output=root/"audit.json"
            selected={"topic_id":"human_moments","search":["acrobatics"]}
            candidates=[{"title":f"File:Test {i}.webm","source_page":f"https://example.org/{i}"}
                        for i in range(5)]
            standings=[{"topic_id":"human_moments","errors":[]}]
            argv=["topic_discovery_audit.py","--topic","auto",
                  "--topics",str(topics),"--output",str(output)]
            with patch.object(sys,"argv",argv), patch.object(
                    topic_discovery_audit,"choose_topic",
                    return_value=(selected,candidates,standings)) as choose:
                self.assertEqual(topic_discovery_audit.main(),0)
            choose.assert_called_once()
            report=json.loads(output.read_text())
            self.assertEqual(report["requested_topic"],"auto")
            self.assertEqual(report["topic"],"human_moments")
            self.assertEqual(report["candidate_count"],5)
            self.assertEqual(report["status"],"READY_FOR_DOWNLOAD_CHECK")
            self.assertFalse(report["publication_approved"])

    def test_manual_topic_preserved_and_unknown_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            topics=root/"topics.json"
            topics.write_text(json.dumps([{"topic_id":"objects_oddities","search":["domino"]}]))
            output=root/"audit.json"
            argv=["topic_discovery_audit.py","--topic","objects_oddities",
                  "--topics",str(topics),"--output",str(output)]
            with patch.object(sys,"argv",argv),patch.object(
                topic_discovery_audit,"discover_for_topic",return_value=([],[])):
                self.assertEqual(topic_discovery_audit.main(),0)
            result=json.loads(output.read_text())
            self.assertEqual(result["topic"],"objects_oddities")
            self.assertEqual(result["status"],"INSUFFICIENT_CANDIDATES")
            self.assertFalse(result["publication_approved"])
            argv[2]="typo_topic"
            with patch.object(sys,"argv",argv),self.assertRaises(SystemExit):
                topic_discovery_audit.main()


if __name__=="__main__":
    unittest.main()
