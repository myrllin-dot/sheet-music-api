from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from pydantic import BaseModel

# 1. 更新資料格式，接收新參數
class MusicData(BaseModel):
    title: str
    key: str
    time_signature: str
    tempo: int
    score_type: str  # 例如: "solo", "piano", "ensemble", "beatbox"
    parts: int       # 聲部數量
    notes: str = "c4 d e f" # 先暫代音符

@app.post("/generate_pdf")
def generate_pdf(data: MusicData):
    
    # 2. 根據不同的 score_type，給予不同的 LilyPond 模板
    if data.score_type == "solo":
        # 單行樂譜 (長笛獨奏)
        lilypond_code = f"""
        \\version "2.22.1"
        \\header {{ title = "{data.title}" }}
        \\score {{
          \\new Staff {{
            \\key {data.key.lower()} \\major
            \\time {data.time_signature}
            {data.notes}
          }}
        }}
        """
        
    elif data.score_type == "piano":
        # 長笛 + 鋼琴 (需要大譜表 PianoStaff)
        lilypond_code = f"""
        \\version "2.22.1"
        \\header {{ title = "{data.title}" }}
        \\score {{
          <<
            \\new Staff \\with {{ instrumentName = "Flute" }} {{ 
              % 長笛音符
              {data.notes} 
            }}
            \\new PianoStaff \\with {{ instrumentName = "Piano" }} <<
              \\new Staff {{ % 鋼琴右手 
                 c'4 e' g' c'' 
              }}
              \\new Staff {{ \\clef bass % 鋼琴左手 
                 c2 g2 
              }}
            >>
          >>
        }}
        """
        
    elif data.score_type == "beatbox":
        # 長笛 Beatbox (需要更換符頭為叉叉)
        lilypond_code = f"""
        \\version "2.22.1"
        \\header {{ title = "{data.title}" }}
        \\score {{
          \\new Staff {{
            \\override NoteHead.style = #'cross  % 將符頭改成打擊樂的叉叉
            {data.notes}
          }}
        }}
        """
        
    else:
        # 預設處理
        pass 

    # ...(後面接續原本寫好的寫入檔案與編譯 PDF 程式碼)...

import subprocess
import base64
import os
import tempfile

app = FastAPI()

# 定義 n8n 傳過來的資料格式
class MusicData(BaseModel):
    title: str
    key: str
    time_signature: str
    tempo: int
    # 這裡先預留音符欄位，稍後你可以決定怎麼傳進來
    notes: str = "c4 d e f | g1" 

@app.post("/generate_pdf")
def generate_pdf(data: MusicData):
    # 組合 LilyPond 語法
    lilypond_code = f"""
    \\version "2.22.1"
    \\header {{ title = "{data.title}" }}
    \\score {{
      \\relative c' {{
        \\key {data.key.lower()} \\major
        \\time {data.time_signature}
        \\tempo 4 = {data.tempo}
        {data.notes}
      }}
      \\layout {{ }}
    }}
    """
    
    with tempfile.TemporaryDirectory() as temp_dir:
        ly_file_path = os.path.join(temp_dir, "score.ly")
        with open(ly_file_path, "w", encoding="utf-8") as f:
            f.write(lilypond_code)
            
        try:
            # 執行 LilyPond
            subprocess.run(
                ["lilypond", "--output", os.path.join(temp_dir, "score"), ly_file_path], 
                check=True, capture_output=True
            )
            
            pdf_file_path = os.path.join(temp_dir, "score.pdf")
            with open(pdf_file_path, "rb") as pdf_file:
                pdf_bytes = pdf_file.read()
                
            # 回傳 Base64 格式
            return {"status": "success", "pdf_base64": base64.b64encode(pdf_bytes).decode('utf-8')}
            
        except subprocess.CalledProcessError as e:
            # 如果編譯失敗，回傳錯誤訊息
            raise HTTPException(status_code=500, detail=f"LilyPond error: {e.stderr.decode()}")
