#!/usr/bin/env python3
"""V24 review-only editorial overlays and 5-original-source end card.

Use actual source frames from input V22.1, not invented/stock illustration.
Original audio stream passes through unchanged. This is not publishing approval.
"""
import argparse
import json
import subprocess
from pathlib import Path
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageOps

W,H=1080,1920
GOLD='#F5D555'
MUTED='#C8D3DC'
FONT='/usr/share/fonts/truetype/nanum/NanumSquareB.ttf'
if not Path(FONT).exists():
    FONT=subprocess.check_output(['fc-match','-f','%{file}','NanumSquare'],text=True).strip()

def font(size):
    return ImageFont.truetype(FONT,size)

def centered(d,msg,y,size,color='#F7FAFC'):
    f=font(size);bb=d.textbbox((0,0),msg,font=f)
    d.text(((W-(bb[2]-bb[0]))//2,y),msg,font=f,fill=color)

def corners(d,rect,fill,outline=None,radius=20,width=2):
    d.rounded_rectangle(rect,radius,fill=fill,outline=outline,width=width)

def note(rank,topic,observation):
    im=Image.new('RGBA',(W,H),(0,0,0,0))
    d=ImageDraw.Draw(im)
    # Use actual black letterbox below source picture; never cover the animal.
    corners(d,(65,1514,1015,1735),fill=(18,27,39,229),
            outline=(95,112,129,200),radius=26)
    corners(d,(86,1540,198,1597),fill=(242,205,79,235),radius=13)
    d.text((103,1548),f'{rank}위',font=font(30),fill='#131925')
    d.text((220,1545),topic,font=font(37),fill='#FFFFFF')
    d.line([(93,1616),(987,1616)],fill='#56636F',width=2)
    d.text((95,1644),observation,font=font(32),fill='#D5E0E9')
    d.text((92,1700),'EDITORIAL NOTE · 원본 행동 관찰 기반',
           font=font(18),fill='#A2AEB9')
    return im

def real_frame(video,t):
    cap=cv2.VideoCapture(str(video))
    cap.set(cv2.CAP_PROP_POS_MSEC,t*1000)
    ok,frame=cap.read();cap.release()
    if not ok:
        raise ValueError(f'Cannot inspect actual frame at {t}s')
    return Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB))

def poster_card(canvas,rect,frame,title,descriptor,lead=False):
    d=ImageDraw.Draw(canvas)
    x0,y0,x1,y1=rect
    corners(d,rect,'#1F2A36',outline='#506070',radius=16)
    target=(x1-x0-20,y1-y0-102)
    img=ImageOps.fit(frame,target,method=Image.Resampling.LANCZOS)
    canvas.paste(img,(x0+10,y0+10))
    d.text((x0+17,y1-76),title,font=font(34 if lead else 26),fill=GOLD)
    d.text((x0+17,y1-40),descriptor,font=font(24 if lead else 22),
           fill='#D5DEE7')

def outro(video,opening=False):
    im=Image.new('RGB',(W,H),'#05080F')
    d=ImageDraw.Draw(im)
    d.text((54,67),'고양이 돌발 행동 TOP5',font=font(43),fill=GOLD)
    d.line([(54,139),(1026,139)],fill='#596778',width=2)
    centered(d,'어떤 순간이 가장 예상 밖이었나요?',236,47)
    centered(d,'점프 거리 · 반응 속도 · 반전의 선명함',307,28,MUTED)
    poses=[(23.35,(100,430,1050,1200)),
           (17.74,(100,430,1050,1200)),
           (13.5,(245,415,875,1225)),
           (7.12,(200,430,910,1220)),
           (2.55,(190,400,935,1240))]
    stills=[real_frame(video,t).crop(crop) for t,crop in poses]
    poster_card(im,(57,414,528,1035),stills[0],
                '1위 · 건물 점프','가장 먼 도약',True)
    poster_card(im,(552,414,1023,1035),stills[1],
                '2위 · 카메라 돌진','가장 가까운 반전',True)
    for i,values in enumerate([('3위 · 의자 점프','착지'),
                               ('4위 · 높은 곳 착지','도약'),
                               ('5위 · 상자 잠입','숨기')]):
        x=57+i*335
        poster_card(im,(x,1080,x+306,1514),stills[i+2],values[0],values[1])
    d=ImageDraw.Draw(im)
    corners(d,(63,1570,1017,1710),'#1A2532',outline='#6C7788')
    centered(d,'당신이 뽑는 진짜 1위는?',1594,43)
    centered(d,'댓글에 순위를 남겨주세요',1656,28,'#DCE4EA')
    d.text((67,1805),'TOP5 · REVIEW COPY / RIGHTS NOT CLEARED',
           font=font(21),fill='#BBC5CF')
    if opening:
        layer=Image.new('RGBA',(W,H),(0,0,0,75))
        im=Image.alpha_composite(im.convert('RGBA'),layer).convert('RGB')
        d=ImageDraw.Draw(im)
        corners(d,(112,826,968,1042),'#131C29',outline=GOLD,radius=35,width=3)
        centered(d,'5개의 순간, 당신의 선택은?',894,45,GOLD)
    return im

def finish(source,destination,scratch):
    source=Path(source);destination=Path(destination);scratch=Path(scratch)
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.parent.mkdir(exist_ok=True,parents=True)
    scratch.mkdir(parents=True,exist_ok=True)
    scenes=[(5,'상자 진입','도약 뒤 화면 밖으로 숨는 짧은 반전',2,6),
            (4,'높은 곳 착지','높은 가장자리에서 아래로 내려오는 동작',6,11),
            (3,'의자 착지','한 번에 목표 지점까지 올라서는 동작',11,15),
            (2,'근접 돌진','카메라까지 순식간에 가까워진 거리',15,21),
            (1,'건물 사이 점프','출발과 착지 사이의 빈 공간이 포인트',21,27)]
    for rank,topic,obs,_,_ in scenes:
        note(rank,topic,obs).save(scratch/f'note{rank}.png')
    outro(source,True).save(scratch/'outro_intro.png')
    outro(source,False).save(scratch/'outro_grid.png')
    sources=['-i',str(source)]
    for rank,*_ in scenes:
        sources+=['-i',str(scratch/f'note{rank}.png')]
    sources+=['-i',str(scratch/'outro_intro.png'),
              '-i',str(scratch/'outro_grid.png')]
    filters=[];previous='[0:v]'
    for idx,(rank,topic,obs,start,end) in enumerate(scenes,1):
        node=f'[v{idx}]'
        filters.append(
          f"{previous}[{idx}:v]overlay=0:0:enable='between(t,{start+.25},{end-.08})':eof_action=repeat{node}")
        previous=node
    filters += [
      f"{previous}[6:v]overlay=0:0:enable='between(t,27,27.68)':eof_action=repeat[v6]",
      "[v6][7:v]overlay=0:0:enable='gte(t,27.68)':eof_action=repeat[v7]"
    ]
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y',*sources,
         '-filter_complex',';'.join(filters),
         '-map','[v7]','-map','0:a:0',
         '-t','30','-r','24','-s','1080x1920',
         '-c:v','libx264','-preset','ultrafast','-crf','19',
         '-pix_fmt','yuv420p','-c:a','copy',
         '-movflags','+faststart',str(destination)]
    subprocess.run(cmd,check=True,timeout=340)
    probe=subprocess.run(
      ['ffprobe','-v','error','-show_entries',
       'format=duration:stream=codec_name,codec_type,r_frame_rate,width,height,duration',
       '-of','json',str(destination)],capture_output=True,text=True,check=True)
    meta=json.loads(probe.stdout)
    if abs(float(meta['format']['duration'])-30)>0.1:
        raise ValueError('V24 output must be exactly 30s')
    vid=[x for x in meta['streams'] if x.get('codec_type')=='video']
    aud=[x for x in meta['streams'] if x.get('codec_type')=='audio']
    if (len(vid)!=1 or len(aud)!=1 or vid[0].get('codec_name')!='h264'
        or aud[0].get('codec_name')!='aac' or vid[0].get('width')!=1080
        or vid[0].get('height')!=1920 or vid[0].get('r_frame_rate')!='24/1'):
        raise ValueError('V24 codec or resolution check failed')
    subprocess.run(['ffmpeg','-v','error','-i',str(destination),
                    '-map','0:v:0','-map','0:a:0','-f','null','-'],
                   check=True,capture_output=True,timeout=210)
    (scratch/'V24_TECHNICAL_QA.json').write_text(
      json.dumps({'file':destination.name,'duration':30,
                  'full_av_decode':'PASS','rights_approved':False,
                  'approved_for_publication':False,'ffprobe':meta},
                 ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('V24 review-only editorial master created and 30s decoded:',destination)

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',default='output/TOP5_V24_AUDIO_REVIEW_ONLY_1080x1920.mp4')
    ap.add_argument('--output',default='output/TOP5_V24_EDITORIAL_REVIEW_ONLY_1080x1920.mp4')
    ap.add_argument('--scratch',default='output/v24_editorial_work')
    a=ap.parse_args()
    finish(a.input,a.output,a.scratch)
