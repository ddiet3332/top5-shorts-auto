import json,subprocess,sys,tempfile,unittest
from pathlib import Path
SCRIPT=Path(__file__).resolve().parents[1]/"src/top5_free_topic_planner.py"
class TopicPlannerTests(unittest.TestCase):
 def run_plan(self,slot,history=None,date="2026-11-19"):
  with tempfile.TemporaryDirectory() as d:
   h=Path(d)/"history.json";o=Path(d)/"plan.json"
   h.write_text(json.dumps(history or []))
   p=subprocess.run([sys.executable,str(SCRIPT),"--slot",slot,"--date",date,"--history",str(h),"--output",str(o)],capture_output=True,text=True)
   self.assertEqual(p.returncode,0,p.stderr)
   return json.loads(o.read_text())
 def test_free_without_api_key(self):
  a=self.run_plan("AM");self.assertEqual(a["status"],"TOPIC_PLANNED_NOT_PRODUCED")
  self.assertIsNone(a["editorial_score"]);self.assertFalse(a["publication_approved"])
 def test_am_pm_different(self):
  am=self.run_plan("AM")
  pm=self.run_plan("PM",[{"date":am["date"],"topic":am["selected"]["topic"],"category":am["selected"]["category"]}])
  self.assertNotEqual(am["selected"]["category"],pm["selected"]["category"])
 def test_history_avoids_repeat(self):
  a=self.run_plan("AM")
  b=self.run_plan("AM",[{"date":"2026-11-18","topic":a["selected"]["topic"],"category":a["selected"]["category"]}])
  self.assertNotEqual(a["selected"]["topic"],b["selected"]["topic"])
 def test_all_categories_used_today_falls_back_to_unused_topic(self):
  import importlib.util
  spec=importlib.util.spec_from_file_location("planner",SCRIPT)
  mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
  history=[{"date":"2026-11-19","topic":topic,"category":cat} for cat,topic,_,_ in mod.CATALOG[:12]]
  history.extend({"date":"2026-11-19","topic":"older_"+cat,"category":cat} for cat,_,_,_ in mod.CATALOG[12:])
  result=self.run_plan("PM",history)
  self.assertNotIn(result["selected"]["topic"],{x["topic"] for x in history})
 def test_all_topics_used_still_returns_plan(self):
  import importlib.util
  spec=importlib.util.spec_from_file_location("planner",SCRIPT)
  mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
  history=[{"date":"2026-11-19","topic":topic,"category":cat} for cat,topic,_,_ in mod.CATALOG]
  self.assertEqual(self.run_plan("PM",history)["status"],"TOPIC_PLANNED_NOT_PRODUCED")
if __name__=="__main__":unittest.main()
