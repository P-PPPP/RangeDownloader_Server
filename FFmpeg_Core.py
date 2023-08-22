# FFmpeg_Core
# Author: @ProgressPP, For all video creators :)
import os
import subprocess
from threading import Thread
import time
import psutil
import sys
import shlex
import shutil
from concurrent.futures import ThreadPoolExecutor


class ITEM:
    def __init__(self,threadNum:int,Save_Name:str) -> None:
        self.item = {}
        [self.item.update({str(thread):{"running":1,"out":"","progress":0.00}}) for thread in range(threadNum)]
        self.item["Save_Name"] = Save_Name
        self.item["Threads"] = threadNum

    def change_status(self,Threads,k,v):
        self.item[str(Threads)][k] = v
    
    def add_item(self,k,v):
        self.item.update({k,v})

    def get_item(self,k:str):
        return self.item[k]

class PROGRESS:
    def __init__(self) -> None:
        self.Progress = {}

    def add_task(self,seg_key:str,threadNum:int,Save_Name:str):
        self.Progress.update({seg_key:ITEM(threadNum=threadNum,Save_Name=Save_Name)})
    
    def update(self,seg_key:str,v:ITEM):
        self.Progress.update({seg_key:v})

    def get_item(self,seg_key:str)->ITEM:
        return self.Progress[seg_key]

    def get_item_instance(self,seg_key:str,k:str):
        return self.get_item(seg_key=seg_key).get_item(k=k)
#{
#  "uuid-uuid-uuid-uuid": {  -> seg_key
#    "0": {
#      "running": 1, -> 0:Suspended 1:running, 2:Restart(Temp,For siginal only), 3:Finished, 4:Terminate a task
#      "out": "", -> Output of ffmpeg
#      "progress": 1 -> Progress of the ffmpeg (e.g. : 0.03)
#    },
#    ...
#}
Progress = PROGRESS()
Seg_Keys = {}
def Multi_Thread_Seeking(Start_Time:int,End_Time:int,Url:str,Save_Name:str,seg_key:str,Seek_type:str="Input",Threads:int=1,Args:str="",filetype:str="video",filesuffix:str="mp4"):
    #   http://trac.ffmpeg.org/wiki/Seeking
    #   In the documentation, the following is the format of the seek command:
    #       Input\Output
    def main():
        Working_Threads = [] #Reset Working_Threads
        Each_Duration = (End_Time - Start_Time) / Threads
        Commands = []
        start_time = Start_Time
        for i in range(Threads):
            end_time = start_time + Each_Duration
            _k = " -avoid_negative_ts 1 "
            if Seek_type.lower()=="input":
                # Removed "-avoid_negative_ts 1", in dash it will occur dismatch of audio and video / but will occur other problems
                cmd =f'ffmpeg  {Args} -i "{Url}" -to {end_time} -avoid_negative_ts 1 -c copy "{i}_{seg_key}.{filesuffix}" -y 2>&1' if start_time==0 else f'ffmpeg  {Args} -ss {start_time} -i "{Url}" -to {end_time-start_time} {_k} -c copy "{i}_{seg_key}.{filesuffix}" -y 2>&1'
            elif Seek_type.lower() == "output":
                cmd = f'ffmpeg  {Args} -i "{Url}" -to {end_time} -avoid_negative_ts 1 -c copy "{i}_{seg_key}.{filesuffix}" -y 2>&1' if start_time==0 else f'ffmpeg  {Args} -ss {start_time} -i "{Url}" -to {end_time} {_k} -c copy "{i}_{seg_key}.{filesuffix}" -y 2>&1'
            Commands.append(cmd)
            start_time = end_time
        # Run Commands
        for i in range(Threads):
            Working_Threads.append(Thread(target=evaule_command,args=(Commands[i],i,seg_key,Each_Duration))) 
        # Wait for all threads to finish
        for i in range(Threads):
            Working_Threads[i].start()
        for i in range(Threads):
            Working_Threads[i].join()
        # Merge Files
        if Threads>1:
            #One thread dont need this
            if Progress.get_item(seg_key=seg_key)[0]["running"] != 4 :
                open(f"{seg_key}.txt","w",encoding="utf-8").write("\n".join([f'file {i}_{seg_key}.{filesuffix}' for i in range(Threads)]))
                subprocess.call(f'ffmpeg -f concat -safe 0 -i {seg_key}.txt -c copy "{Save_Name}_{filetype}.{filesuffix}"',shell=True)
                os.remove(f"{seg_key}.txt")
            else: print(f"{seg_key} : Thread Has Been Killed!")
            # Delete Files
            for i in range(Threads):
                os.remove(f"{i}_{seg_key}.{filesuffix}")
        elif Threads ==1 :
            #os.rename(f"0_{seg_key}.{filesuffix}",f"{Save_Name}_{filetype}.{filesuffix}")
            shutil.move(f"0_{seg_key}.{filesuffix}",f"{Save_Name}_{filetype}.{filesuffix}") # Same As Rename
        return True
    Seg_Keys.update({seg_key:1})
    Save_Name = shlex.quote(Save_Name) # Issue3
    Progress.add_task(seg_key=seg_key,Save_Name=Save_Name)
    Thread(target=main).start()
    return seg_key

def evaule_command(Command:str,Instance_id:int,seg_key:str,Duration:int):
    # Instance_id: Thread_Id
    Progress.get_item_instance(seg_key=seg_key,k=str(Instance_id))["progress"] = 0
    p = subprocess.Popen(Command,shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,bufsize=1,universal_newlines=True,encoding="utf-8")
    while p.poll() is None:
        time.sleep(0.1)
        ###### Update Progress ######
        out = p.stdout.readline()
        p.stdout.flush()
        Progress.get_item_instance(seg_key=seg_key,k=str(Instance_id))["out"] = out
        if out.count("time="):
            Progress.get_item_instance(seg_key=seg_key,k=str(Instance_id))["progress"] = to_seconds_time(out.split("time=")[1].split(".")[0])/Duration
        ####### thread operation#######
        if Progress.get_item_instance(seg_key=seg_key,k=str(Instance_id))["running"] == 4:
            Kill_FFmpeg(p.pid)
            Seg_Keys.update({seg_key:2})
            return False
        if Progress.get_item_instance(seg_key=seg_key,k=str(Instance_id))["running"] == 2:
            #restart thread when thread is running 
            Kill_FFmpeg(p.pid)
            Progress.get_item_instance(seg_key=seg_key,k=str(Instance_id))["progress"] = 0
            Progress.get_item_instance(seg_key=seg_key,k=str(Instance_id))["running"] = 1
            return evaule_command(Command,Instance_id,seg_key,Duration)
        if Progress.get_item_instance(seg_key=seg_key,k=str(Instance_id))["running"] == 0:
            #   Maybe you wanna suspend the thread for a while...
            #       0. Stop The Thread
            #       1. restart the thread
            #       2. resume the thread
            #       3. Thread has finished
            #       4. Thread has been killed
            psutil.Process(p.pid).suspend()
            while Progress.get_item_instance(seg_key=seg_key,k=str(Instance_id))["running"]==0:
                time.sleep(1)
                if Progress.get_item_instance(seg_key=seg_key,k=str(Instance_id))["running"]==1:
                    #resume thread
                    psutil.Process(p.pid).resume()
                if Progress.get_item_instance(seg_key=seg_key,k=str(Instance_id))["running"]==2:
                    #restart thread
                    p.kill()
                    Progress.get_item_instance(seg_key=seg_key,k=str(Instance_id))["running"]=1
                    return evaule_command(Command,Instance_id,seg_key,Duration)
    #Maybe the thread is finished...without any risk...
    Progress.get_item_instance(seg_key=seg_key,k=str(Instance_id))["progress"] = 1
    Progress.get_item_instance(seg_key=seg_key,k=str(Instance_id))["running"]=3
    Seg_Keys.update({seg_key:3})

def Kill_FFmpeg(pid):
    # Exit Thread
    # It is because we started a new thread using 'shel=True' this will open up a individual ffmpeg process
    # Cause p.kill() and p.termate() cannot stop immediately
    # for more reason and solution please :
    # https://stackoverflow.com/questions/4789837/how-to-terminate-a-python-subprocess-launched-with-shell-true
    #
    if sys.platform == "win32":
        subprocess.call(f'TASKKILL /F /PID {pid} /T')
    else:
        import signal,os
        os.killpg(os.getpgid(pid), signal.SIGTERM)

def to_seconds_time(a:str)->int:
    if a.count(":")==1:
        return int(a.split(":")[0])*60+int(a.split(":")[1])
    if a.count(":")==2:
        return int(a.split(":")[0])*3600+int(a.split(":")[1])*60+int(a.split(":")[2])
    return int(a)

def thread_operation(seg_key:str,Instance_id:int,running:int):
    # Change Thread Status
    Progress.get_item_instance(seg_key=seg_key,k=str(Instance_id))["running"]=running
    return True


def Getstatus(seg_key:str):
    try: return Seg_Keys.get(seg_key)
    except: return -1

#### __init__####
threadPool = ThreadPoolExecutor(max_workers=1,thread_name_prefix='Segment_Thread')