#!/usr/bin/env python3
"""Optional vision-based review: no fake score when model or evidence missing."""
import base64,json,os,subprocess,sys,tempfile,urllib.request
from pathlib import Path
LIMITS={"hook":20,"fun_reversal":25,"ranking":15,"flow":15,"original_captions":10}
def run(video,out):
    report={"status":"UNVERIFIED","editorial_score_100":None,"editorial_80_verified":False,"youtube_upload_permitted":False}
    key=os.getenv("OPENAI_API_KEY")
    if not key:
        report["reason"]="OPENAI_API_KEY secret not configured"
    else:
        try:
            with tempfile.TemporaryDirectory() as d:
                images=[]
                for i,t in enumerate((0.5,2,4,7,10,13,16,19,22,25,27)):
                    p=Path(d)/f"{i}.jpg"
                    subprocess.run(["ffmpeg","-v","error","-ss",str(t),"-i",video,"-frames:v","1","-vf","scale=360:-2","-y",str(p)],check=True,timeout=30)
                    images.append({"type":"input_image","image_url":"data:image/jpeg;base64,"+base64.b64encode(p.read_bytes()).decode()})
                prompt=("Assess chronological frames from a Korean TOP5 dog short. Respond ONLY as JSON with "
                        "scores object: hook (0-20), fun_reversal (0-25), ranking (0-15), flow (0-15), "
                        "original_captions (0-10), and weaknesses and recommended_repairs arrays. "
                        "Conservatively score visible evidence. Do not infer unseen motion, audio, or legal rights.")
                payload={"model":os.getenv("TOP5_VISION_MODEL","gpt-4.1-mini"),
                         "input":[{"role":"user","content":[{"type":"input_text","text":prompt}]+images}],
                         "text":{"format":{"type":"json_object"}},"max_output_tokens":850}
                req=urllib.request.Request("https://api.openai.com/v1/responses",data=json.dumps(payload).encode(),
                    headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"})
                with urllib.request.urlopen(req,timeout=120) as r: data=json.load(r)
                raw="".join(c.get("text","") for item in data.get("output",[]) for c in item.get("content",[]) if c.get("type")=="output_text")
                result=json.loads(raw)
                scores=result.get("scores",{})
                valid={k:(v if isinstance(v,(int,float)) and not isinstance(v,bool) and 0<=v<=mx else None)
                       for k,mx in LIMITS.items() for v in [scores.get(k)]}
                report.update({"status":"PARTIAL_VISION_REVIEW","visible_scores":valid,
                               "visible_total":sum(v for v in valid.values() if v is not None),
                               "visible_max":sum(LIMITS[k] for k,v in valid.items() if v is not None),
                               "weaknesses":result.get("weaknesses",[]),
                               "recommended_repairs":result.get("recommended_repairs",[]),
                               "reason":"11 stills cannot certify audio (10 points), rights (5 points), or complete motion; 80 remains unverified"})
        except Exception as e:
            report.update({"status":"REVIEW_ERROR","reason":type(e).__name__+": "+str(e)[:200]})
    p=Path(out);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+chr(10))
    print(json.dumps(report,ensure_ascii=False))
if __name__=="__main__":run(sys.argv[1],sys.argv[2])
