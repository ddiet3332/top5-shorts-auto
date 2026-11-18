#!/usr/bin/env python3
"""Zero paid API topic planner. Curated catalog and deterministic rotation, NOT AI."""
import argparse,datetime,json,hashlib
from pathlib import Path
CATALOG=[
("animals","강아지의 웃긴 행동 TOP5","funny dog playing","playful puppy"),
("animals","고양이의 예상 밖 행동 TOP5","funny cat jumping","cat playing"),
("animals","새들의 신기한 행동 TOP5","funny bird","parrot playing"),
("animals","야생동물의 놀라운 순간 TOP5","wildlife animal behavior","wild animals"),
("weather","거대한 구름 장면 TOP5","dramatic clouds timelapse","storm clouds"),
("weather","놀라운 번개 장면 TOP5","lightning storm","lightning sky"),
("weather","아름다운 눈 내리는 풍경 TOP5","snowfall landscape","snowing forest"),
("weather","강렬한 파도 장면 TOP5","ocean storm waves","big waves"),
("nature","폭포의 장관 TOP5","waterfall aerial","beautiful waterfall"),
("nature","신비로운 숲 풍경 TOP5","misty forest","forest sun rays"),
("nature","일출과 일몰 TOP5","sunset timelapse","sunrise nature"),
("nature","신기한 바위 풍경 TOP5","rock formations nature","canyon landscape"),
("insects","나비의 아름다운 순간 TOP5","butterfly macro","butterfly flower"),
("insects","벌의 신기한 행동 TOP5","bee macro flower","honeybee closeup"),
("insects","무당벌레의 작은 세계 TOP5","ladybug macro","ladybird insect"),
("insects","잠자리의 비행 TOP5","dragonfly flying","dragonfly macro"),
("people","사람들의 놀라운 균형감각 TOP5","balance skills people","acrobat balance"),
("people","기발한 거리 공연 TOP5","street performance","street performer"),
("people","놀라운 공예 기술 TOP5","handmade craft process","artisan making"),
("people","즐거운 댄스 순간 TOP5","street dancing","dance performance"),
("objects","신기한 도미노 장면 TOP5","domino chain reaction","domino falling"),
("objects","만족스러운 기계 움직임 TOP5","satisfying machinery","mechanical motion"),
("objects","놀라운 비눗방울 TOP5","soap bubbles slow motion","bubble art"),
("objects","신기한 물감 움직임 TOP5","paint mixing macro","color ink water")]
def main():
 p=argparse.ArgumentParser();p.add_argument("--slot",choices=["AM","PM"],required=True);p.add_argument("--history",default="topic_history.json");p.add_argument("--output",default="output/topic_plan.json");p.add_argument("--date",default=None);a=p.parse_args()
 day=a.date or datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date().isoformat()
 datetime.date.fromisoformat(day)
 history=json.loads(Path(a.history).read_text()) if Path(a.history).exists() else []
 if not isinstance(history,list):raise SystemExit("INVALID_HISTORY")
 used={x.get("topic") for x in history[-120:] if isinstance(x,dict)}
 same_day={x.get("category") for x in history if isinstance(x,dict) and x.get("date")==day}
 # AM and PM independently prefer different categories even before history update.
 if a.slot=="PM":same_day.add(CATALOG[(datetime.date.fromisoformat(day).toordinal()*2)%len(CATALOG)][0])
 start=(datetime.date.fromisoformat(day).toordinal()*2+(a.slot=="PM"))%len(CATALOG)
 rotated=CATALOG[start:]+CATALOG[:start]
 eligible=[x for x in rotated if x[0] not in same_day and x[1] not in used]
 if not eligible:eligible=[x for x in rotated if x[0] not in same_day]
 # Repeated manual runs can exhaust all categories for a date. Prefer a new topic
 # even if category repeats; do not fail solely because of category history.
 if not eligible:eligible=[x for x in rotated if x[1] not in used]
 if not eligible:eligible=rotated[:]
 category,topic,q1,q2=eligible[0]
 selected={"topic":topic,"category":category,"search_queries":[q1,q2],"selection_method":"free_curated_catalog_rotation","estimated_topic_score":None}
 report={"date":day,"slot":a.slot,"status":"TOPIC_PLANNED_NOT_PRODUCED","selected":selected,"alternatives":[{"topic":t,"category":c,"search_queries":[x,y]} for c,t,x,y in eligible[1:10]],"minimum_final_video_score":75,"source_footage_verified":False,"video_created":False,"editorial_score":None,"rights_verified":False,"publication_approved":False,"cost_note":"No paid model/API calls; external footage APIs may have limits"}
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2))
 print(json.dumps({"status":report["status"],"topic":topic,"category":category,"slot":a.slot},ensure_ascii=False))
if __name__=="__main__":main()
