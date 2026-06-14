from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import base64
import os
import tempfile

app = FastAPI()

# 1. 定義接收 n8n 傳來的資料格式
class MusicData(BaseModel):
    title: str
    key: str
    time_signature: str
    tempo: int
    score_type: str
    parts: int
    notes_flute: str = ""
    chords: list[str] = []

@app.post("/generate_pdf")
def generate_pdf(data: MusicData):
    
    # 2. 根據不同的 score_type，切換不同的 LilyPond 語法模板
    if data.score_type == "solo":
        # 單行樂譜 (長笛獨奏)
        lilypond_code = f"""
        \\version "2.22.1"
        \\header {{ title = "{data.title}" subtitle = "Flute Solo" }}
        \\score {{
          \\new Staff \\with {{ instrumentName = "Flute" }} {{
            \\key {data.key.lower()} \\major
            \\time {data.time_signature}
            \\tempo 4 = {data.tempo}
            {data.notes_flute}
          }}
          \\layout {{ }}
        }}
        """
        
    elif data.score_type == "piano":
        # 長笛 + 鋼琴 (需要大譜表 PianoStaff)
        lilypond_code = f"""
        \\version "2.22.1"
        \\header {{ title = "{data.title}" subtitle = "Flute & Piano" }}
        \\score {{
          <<
            \\new Staff \\with {{ instrumentName = "Flute" }} {{ 
              \\key {data.key.lower()} \\major
              \\time {data.time_signature}
              \\tempo 4 = {data.tempo}
              {data.notes_flute} 
            }}
            \\new PianoStaff \\with {{ instrumentName = "Piano" }} <<
              \\new Staff {{ % 鋼琴右手預留區塊
                \\key {data.key.lower()} \\major
                \\time {data.time_signature}
                r1
              }}
              \\new Staff {{ \\clef bass % 鋼琴左手預留區塊
                \\key {data.key.lower()} \\major
                \\time {data.time_signature}
                r1
              }}
            >>
          >>
          \\layout {{ }}
        }}
        """

    elif data.score_type == "ensemble":
        # 長笛重奏 (動態生成對應數量的五線譜)
        staffs = ""
        for i in range(1, data.parts + 1):
            staffs += f"""
            \\new Staff \\with {{ instrumentName = "Flute {i}" }} {{
              \\key {data.key.lower()} \\major
              \\time {data.time_signature}
              \\tempo 4 = {data.tempo}
              {data.notes_flute} 
            }}
            """
        lilypond_code = f"""
        \\version "2.22.1"
        \\header {{ title = "{data.title}" subtitle = "Flute Ensemble ({data.parts} parts)" }}
        \\score {{
          <<
            {staffs}
          >>
          \\layout {{ }}
        }}
        """
        
    elif data.score_type == "beatbox":
        # 長笛 Beatbox (更換符頭為叉叉)
        lilypond_code = f"""
        \\version "2.22.1"
        \\header {{ title = "{data.title}" subtitle = "Beatbox Flute" }}
        \\score {{
          \\new Staff \\with {{ instrumentName = "Flute (B.B.)" }} {{
            \\key {data.key.lower()} \\major
            \\time {data.time_signature}
            \\tempo 4 = {data.tempo}
            \\override NoteHead.style = #'cross
            {data.notes_flute}
          }}
          \\layout {{ }}
        }}
        """
        
    else:
        # 防呆預設處理 (當作獨奏處理)
        lilypond_code = f"""
        \\version "2.22.1"
        \\header {{ title = "{data.title}" }}
        \\score {{
          \\new Staff {{ 
            \\key {data.key.lower()} \\major
            \\time {data.time_signature}
            \\tempo 4 = {data.tempo}
            {data.notes_flute} 
          }}
        }}
        """

    # 3. 建立暫存資料夾並執行 LilyPond 編譯
    with tempfile.TemporaryDirectory() as temp_dir:
        ly_file_path = os.path.join(temp_dir, "score.ly")
        
        # 寫入 .ly 檔案
        with open(ly_file_path, "w", encoding="utf-8") as f:
            f.write(lilypond_code)
            
        try:
            # 呼叫系統的 LilyPond 指令
            subprocess.run(
                ["lilypond", "--output", os.path.join(temp_dir, "score"), ly_file_path], 
                check=True, capture_output=True
            )
            
            # 讀取產生出來的 PDF 檔案
            pdf_file_path = os.path.join(temp_dir, "score.pdf")
            with open(pdf_file_path, "rb") as pdf_file:
                pdf_bytes = pdf_file.read()
                
            # 將 PDF 轉換成 Base64 格式並回傳給 n8n
            return {"status": "success", "pdf_base64": base64.b64encode(pdf_bytes).decode('utf-8')}
            
        except subprocess.CalledProcessError as e:
            # 如果編譯失敗，回傳 LilyPond 的錯誤提示
            raise HTTPException(status_code=500, detail=f"LilyPond error: {e.stderr.decode()}")
