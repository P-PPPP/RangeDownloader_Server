# FFmpeg_Core_Single
import subprocess, shlex, time , os
from concurrent.futures import ThreadPoolExecutor
#{
#  "uuid-uuid-uuid-uuid": {  -> seg_key
#      "running": 1, -> -1:错误,0:等待 1:运行,2:完成
#      "out": "", -> ffmpeg输出
#      "progress": 1 -> ffmpeg分割百分比 (e.g. : 0.03)
#    ...
#}
Progress = {}
threadPool = ThreadPoolExecutor(max_workers=1)

def Segment(Start_Time:int,End_Time:int,Url:str,Save_Name:str,seg_key:str,Args:str="",download_path:str="./"):
    Progress[seg_key]["running"] = 1 #正在运行此任务
    Progress[seg_key]["progress"] = -1 #正在解析
    Progress[seg_key]["Save_Name"] = shlex.quote(Save_Name) # 防止文件名导致不安全注入
    fullpath = os.path.abspath(os.path.join(download_path,f"{seg_key}.mp4"))
    cmd =f'ffmpeg  {Args} -i "{Url}" -to {End_Time} -avoid_negative_ts 1 -c copy "{fullpath}" -y 2>&1' if Start_Time==0 else f'ffmpeg  {Args} -ss {Start_Time} -i "{Url}" -to {End_Time-Start_Time}  -avoid_negative_ts 1  -c copy "{fullpath}" -y 2>&1'
    # Run Commands
    try:
        evaule_command(cmd,seg_key,End_Time-Start_Time)
        Progress[seg_key]["running"] = 2 #执行完成
        Progress[seg_key]["progress"] = 1.00
    except: Progress[seg_key]["running"] = -1 #执行失败
    
    return seg_key

def evaule_command(Command:str,seg_key:str,Duration:int):
    p = subprocess.Popen(Command,shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,bufsize=1,universal_newlines=True,encoding="utf-8")
    while p.poll() is None:
        time.sleep(0.1)
        ###### 分割中的操作 ######
        out = p.stdout.readline() #记录ffmpeg最新输出(包含时间信息)
        Progress[seg_key]["out"] = out
        p.stdout.flush()
        if out.count("time="):
            Progress[seg_key]["progress"] = to_seconds_time(out.split("time=")[1].split(".")[0])/Duration #提取进度

def to_seconds_time(a:str)->int:
    if a.count(":")==1:  return int(a.split(":")[0])*60+int(a.split(":")[1])
    if a.count(":")==2:  return int(a.split(":")[0])*3600+int(a.split(":")[1])*60+int(a.split(":")[2])
    return int(a)

def check_storage(filepath:os.PathLike="./"):
    for i in os.listdir(filepath):
        if i.endswith(".mp4"): os.remove(os.path.join(filepath,i))
