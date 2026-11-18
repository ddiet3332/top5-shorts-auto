import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from top5_topic_relevance_gate import topic_metadata_match
class TopicGateTests(unittest.TestCase):
 def test_domino_correct(self):
  q=["domino chain reaction","domino falling"]
  self.assertTrue(topic_metadata_match("dominoes, domino, tile, falling",q))
 def test_domino_wrong(self):
  q=["domino chain reaction","domino falling"]
  for tags in ["nuclear core, chemical reaction","goat, horns, chain","compass, moon, chain","sunset, chain, iron"]:
   self.assertFalse(topic_metadata_match(tags,q))
 def test_empty_query_blocks(self):self.assertFalse(topic_metadata_match("cat",[]))
if __name__=="__main__":unittest.main()
