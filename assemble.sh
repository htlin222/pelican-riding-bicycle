#!/bin/sh
# usage: assemble.sh silent_in.mp4 score.wav out.mp4 [t_start t_dur]   -> grade + titles + sound
IN="$1"; WAV="$2"; OUT="$3"
FB=/usr/share/fonts/opentype/noto/NotoSerifCJK-Black.ttc; FR=/usr/share/fonts/opentype/noto/NotoSerifCJK-Medium.ttc
al(){ echo "if(lt(t,$1),0,if(lt(t,$1+$3),(t-$1)/$3,if(lt(t,$2-$3),1,if(lt(t,$2),($2-t)/$3,0))))"; }
T1="drawtext=fontfile=$FB:text='逐日':fontsize=h*0.24:fontcolor=0xf3e9dc:x=(w-text_w)/2:y=h*0.34:alpha='$(al 0.4 5.6 0.9)':shadowcolor=0xe8743a@0.35:shadowx=0:shadowy=0"
T2="drawtext=fontfile=$FR:text='C H A S I N G   T H E   S U N':fontsize=h*0.036:fontcolor=0xf3e9dc:x=(w-text_w)/2:y=h*0.66:alpha='$(al 0.8 5.6 0.9)'"
T3="drawtext=fontfile=$FR:text='A   P E L I C A N   ·   A   B I C Y C L E':fontsize=h*0.030:fontcolor=0xf0b46a:x=(w-text_w)/2:y=h*0.25:alpha='$(al 0.8 5.6 0.9)'"
C1="drawtext=fontfile=$FR:text='牠有翅膀。牠選了輪子。':fontsize=h*0.052:fontcolor=0xf3e9dc:x=(w-text_w)/2:y=h*0.86:alpha='$(al 13.5 18.5 0.7)':shadowcolor=black@0.7:shadowx=1:shadowy=2"
C2="drawtext=fontfile=$FR:text='一路向東，追著太陽。':fontsize=h*0.052:fontcolor=0xf3e9dc:x=(w-text_w)/2:y=h*0.86:alpha='$(al 33 38 0.7)':shadowcolor=black@0.7:shadowx=1:shadowy=2"
C3="drawtext=fontfile=$FR:text='直到，路沒有了。':fontsize=h*0.052:fontcolor=0xf3e9dc:x=(w-text_w)/2:y=h*0.86:alpha='$(al 47 51 0.7)':shadowcolor=black@0.7:shadowx=1:shadowy=2"
E1="drawtext=fontfile=$FB:text='終':fontsize=h*0.22:fontcolor=0xf3e9dc:x=(w-text_w)/2:y=h*0.33:alpha='$(al 62.4 65.8 0.9)'"
E2="drawtext=fontfile=$FR:text='逐日  ·  C H A S I N G   T H E   S U N':fontsize=h*0.032:fontcolor=0xf0b46a:x=(w-text_w)/2:y=h*0.64:alpha='$(al 62.8 65.8 0.9)'"
GRADE="format=gbrp,split[a][b];[b]curves=all='0/0 0.62/0 1/1',gblur=sigma=22[bl];[a][bl]blend=all_mode=screen:all_opacity=0.8,eq=contrast=1.06:saturation=1.10:gamma=1.04,colorbalance=bs=0.035:rs=-0.01:rm=0.035:bm=-0.045:rh=0.03:bh=-0.05,colorbalance=rm=0.05:bm=-0.07:rh=0.035:bh=-0.05:enable='between(t,12,30)',colorbalance=rm=0.03:bm=-0.04:enable='between(t,44,52)',vignette=angle=PI/8.5,noise=alls=4:allf=t,fade=t=in:st=0.2:d=2.2,fade=t=out:st=61.3:d=1.9"
ffmpeg -y -loglevel error -i "$IN" -i "$WAV" -filter_complex "[0:v]$GRADE,$T1,$T2,$T3,$C1,$C2,$C3,$E1,$E2,format=yuv420p[v]" -map "[v]" -map 1:a -c:v libx264 -crf 17 -preset slow -c:a aac -b:a 256k -movflags +faststart -shortest "$OUT"
