#Main For Alist Ver0.1
import json, argparse , uvicorn , uuid , time
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
    return play_url

@app.get("/ping")
def ping():
    return "pong"

@app.post("/api/create_segment")
def depoly_download(depoly_inf:depoly):
    seg_key = uuid.uuid5(namespace=uuid.NAMESPACE_DNS,name=depoly_inf.url+str(depoly_inf.time_start)+str(depoly_inf.time_end)+str(time.time()))
    FFmpeg_Core.threadPool.submit(FFmpeg_Core.Multi_Thread_Seeking,kwargs={"Start_Time":depoly_inf.time_start,"End_Time":depoly_inf.time_end,
    "Url":get_download_url(depoly_inf.url),"Save_Name":seg_key,"Seek_type":"Input","Threads":1,"Args":"","seg_key":seg_key})
    return seg_key

@app.websocket('/api/pools_status')
async def websocket_endpoint(websocket: WebSocket):
    """
    Req: {"seg_key":"xxxx"}
    Resp: {"code":-1/0/1,"data":"","DownloadUrl":"","error":""}   
    -1: Failed , 0: Running , 1:Finished
    """
    await websocket.accept()
    data = await websocket.receive_json()
    while True:
        await websocket.send_text(f"Message text was: {data}") 

if __name__ == "__main__":
    uvicorn.run(app="main:app",port=Config["SLAVEPORT"],host=Config["SLAVEIP"])
