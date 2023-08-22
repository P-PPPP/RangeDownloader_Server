#Main For Alist Ver0.1
import json, argparse , uvicorn , uuid , asyncio
from fastapi import FastAPI , WebSocket
from pydantic import BaseModel
import FFmpeg_Core
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()
parser = argparse.ArgumentParser(description="Running a Slave service.")
parser.add_argument('--config','--c',help="Specify an conofig file.")
par = parser.parse_args()
Config = json.loads(open(par.config,"r",encoding="utf-8").read())
app.add_middleware(CORSMiddleware,allow_origins=Config["SAFTY_IP"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"],)

class depoly(BaseModel):
    url:str
    time_start:int
    time_end :int

def get_download_url(play_url)->str:
    #针对可能需要解析的情况
    return play_url

@app.get("/ping")
def ping():
    return "pong"

@app.post("/api/create_segment")
def depoly_download(depoly_inf:depoly):
    seg_key = uuid.uuid5(namespace=uuid.NAMESPACE_DNS,name=depoly_inf.url+str(depoly_inf.time_start)+str(depoly_inf.time_end))# 生成较为唯一的ID
    if FFmpeg_Core.Seg_Keys.get(seg_key) != None or FFmpeg_Core.Seg_Keys.get(seg_key) in [0,1,3]: return seg_key # 检测是否已经在队列中
    FFmpeg_Core.Seg_Keys.update({seg_key:0}) #  -1: Error , 0: Not Started , 1: Running , 2: Canceled , 3: Finished 
    FFmpeg_Core.threadPool.submit(FFmpeg_Core.Multi_Thread_Seeking,kwargs={"Start_Time":depoly_inf.time_start,"End_Time":depoly_inf.time_end,
    "Url":get_download_url(depoly_inf.url),"Save_Name":seg_key,"Seek_type":"Input","Threads":1,"Args":"","seg_key":seg_key}) #加入到队列池中
    return seg_key

@app.websocket('/api/pools_status')
async def websocket_endpoint(websocket: WebSocket):
    """
    返回状态
    Req: {"seg_key":"xxxx"}
    Resp: {"msg":"","data":"","downloadurl":"","code":""}   
    """
    await websocket.accept()
    seg_k = await websocket.receive_json()
    while True:
        results = FFmpeg_Core.Getstatus(seg_key=seg_k["seg_key"])
        if results == 0 : r = {"msg":"Panding","code":results}
        if results == 1 : r = {"msg":"Downloading","code":results,"Progress":00.00}
        if results == 2 : r = {"msg":"Canceled","code":results}
        if results == 3: r = {"msg":"Finished","DownloadUrl":"","code":results}
        else: r = {"msg":"ERROR","code":results}
        await websocket.send_text(f"Message text was: {r}")
        await asyncio.sleep(1)
        if results == 3 or results == -1 or results == None: break
    websocket.close()

@app.get('/debug')
def s():
    return FFmpeg_Core.Progress

if __name__ == "__main__":
    uvicorn.run(app="main:app",port=Config["SLAVEPORT"],host=Config["SLAVEIP"])
