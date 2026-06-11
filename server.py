import os
import glob
import logging
from typing import List, Tuple
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Import Backend Engine
from audio_processor import AudioProcessor, get_next_hindi_filename

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("server")

app = FastAPI(title="Techphotons Audio Processor API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State
class PipelineStatus:
    def __init__(self):
        self.status = "idle"  # idle, downloading, processing, success, error
        self.progress = 0.0
        self.message = "Ready"
        self.logs: List[str] = []
        self.result = {}

    def update(self, status: str, progress: float, message: str):
        self.status = status
        self.progress = progress
        self.message = message
        self.log(message)

    def log(self, message: str):
        self.logs.append(message)
        logger.info(message)

    def reset_logs(self):
        self.logs = []

global_status = PipelineStatus()
processor = AudioProcessor()

# Request Models
class DownloadRequest(BaseModel):
    url: str

class LoadRequest(BaseModel):
    filepath: str

class RemoveWasteRequest(BaseModel):
    filepath: str
    waste_intervals: List[Tuple[float, float]]

# API ENDPOINTS

@app.get("/api/status")
def get_status():
    return {
        "status": global_status.status,
        "progress": global_status.progress,
        "message": global_status.message,
        "logs": global_status.logs,
        "result": global_status.result
    }

@app.get("/api/next-filename")
def get_next_filename():
    cleaned_folder = r"C:\Users\prate\Desktop\22hr hindi"
    try:
        next_name = get_next_hindi_filename(cleaned_folder)
        return {"next_filename": next_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files")
def get_files():
    outputs_dir = os.path.abspath("outputs")
    os.makedirs(outputs_dir, exist_ok=True)
    try:
        files = sorted([os.path.basename(f) for f in glob.glob(os.path.join(outputs_dir, "*.wav"))])
        return {"files": files, "folder": outputs_dir}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/download")
def trigger_download(req: DownloadRequest, background_tasks: BackgroundTasks):
    if global_status.status in ["downloading", "processing"]:
        raise HTTPException(status_code=400, detail="Backend is currently busy with another task.")
    
    global_status.status = "downloading"
    global_status.progress = 0.01
    global_status.message = "Starting download..."
    global_status.reset_logs()
    global_status.result = {}
    
    output_dir = os.path.abspath("outputs")
    
    def progress_cb(pct):
        global_status.progress = pct
        
    def log_cb(msg):
        global_status.log(msg)
        
    def completion_cb(wav_path, error_msg):
        if error_msg:
            global_status.status = "error"
            global_status.message = f"Download failed: {error_msg}"
        else:
            global_status.status = "idle"
            global_status.progress = 1.0
            global_status.message = "Download completed successfully."
            global_status.result = {
                "filepath": wav_path,
                "filename": os.path.basename(wav_path)
            }
            
    # Run in background
    background_tasks.add_task(
        processor.download_youtube_audio,
        req.url,
        output_dir,
        progress_cb,
        log_cb,
        completion_cb
    )
    
    return {"message": "Download task started"}

@app.post("/api/load")
def load_audio_file(req: LoadRequest):
    if not os.path.exists(req.filepath):
        # check if it exists in outputs/
        alt_path = os.path.join(os.path.abspath("outputs"), os.path.basename(req.filepath))
        if os.path.exists(alt_path):
            req.filepath = alt_path
        else:
            raise HTTPException(status_code=404, detail="Audio file not found.")
            
    try:
        metadata = processor.get_wav_metadata(req.filepath)
        waveform_data = processor.extract_waveform_points(req.filepath, num_points=400)
        return {
            "metadata": metadata,
            "waveform": waveform_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/remove-waste")
def remove_waste(req: RemoveWasteRequest, background_tasks: BackgroundTasks):
    if global_status.status in ["downloading", "processing"]:
        raise HTTPException(status_code=400, detail="Backend is currently busy with another task.")
    
    if not os.path.exists(req.filepath):
        alt_path = os.path.join(os.path.abspath("outputs"), os.path.basename(req.filepath))
        if os.path.exists(alt_path):
            req.filepath = alt_path
        else:
            raise HTTPException(status_code=404, detail="WAV file not found.")
            
    global_status.status = "processing"
    global_status.progress = 0.05
    global_status.message = "Initializing cleaning pipeline..."
    global_status.reset_logs()
    global_status.result = {}
    
    cleaned_folder = r"C:\Users\prate\Desktop\22hr hindi"
    split_folder = r"C:\Users\prate\Desktop\splitting\split_audio"
    splitting_script = os.path.abspath("splitting.py")
    
    def progress_cb(pct):
        global_status.progress = pct
        
    def log_cb(msg):
        global_status.log(msg)
        
    def completion_cb(cleaned_filename, split_files_created, error_msg):
        if error_msg:
            global_status.status = "error"
            global_status.message = f"Pipeline failed: {error_msg}"
        else:
            global_status.status = "success"
            global_status.progress = 1.0
            global_status.message = "Pipeline completed successfully."
            global_status.result = {
                "cleaned_file": cleaned_filename,
                "split_files_created": split_files_created,
                "split_folder": split_folder
            }
            
    background_tasks.add_task(
        processor.remove_waste_and_split_pipeline_async,
        req.filepath,
        req.waste_intervals,
        cleaned_folder,
        split_folder,
        splitting_script,
        log_cb,
        progress_cb,
        completion_cb
    )
    
    return {"message": "Cleaning pipeline started"}

@app.get("/api/audio/stream")
def stream_audio(filepath: str = Query(..., description="Absolute path of the WAV file")):
    if not os.path.exists(filepath):
        alt_path = os.path.join(os.path.abspath("outputs"), os.path.basename(filepath))
        if os.path.exists(alt_path):
            filepath = alt_path
        else:
            raise HTTPException(status_code=404, detail="Audio file not found")
            
    # FileResponse handles byte-range requests for streaming out-of-the-box
    return FileResponse(filepath, media_type="audio/wav")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
