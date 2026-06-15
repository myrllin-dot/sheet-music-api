from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import base64
import os
import tempfile

# ==========================================
# 🚨 關鍵啟動指令：這行絕對不能漏掉！
# ==========================================
app = FastAPI()

# ==========================================
# 1. 資料格式定義
# ==========================================
class MusicData(BaseModel):
    title: str
    key: str
    time_signature: str
    tempo: int
    score_type: str
    parts: int
    notes_flute: str = ""
    chords: list[str] = []

# ==========================================
# 2. 終極和弦字典建造機
# ==========================================
def build_chord_db():
    base_chords = {
        "C":   ("c'", "e'", "g'", "c,", "g,"),
        "Cm":  ("c'", "ees'", "g'", "c,", "g,"),
        "C#m": ("cis'", "e'", "gis'", "cis,", "gis,"),
        "Db":  ("des'", "f'", "aes'", "des,", "aes,"),
        "D":   ("d'", "fis'", "a'", "d,", "a,"),
        "Dm":  ("d'", "f'", "a'", "d,", "a,"),
        "Eb":  ("ees'", "g'", "bes'", "ees,", "bes,"),
        "E":   ("e'", "gis'", "b'", "e,", "b,"),
        "Em":  ("e'", "g'", "b'", "e,", "b,"),
        "F":   ("f'", "a'", "c''", "f,", "c"),
        "Fm":  ("f'", "aes'", "c''", "f,", "c"),
        "F#m": ("fis'", "a'", "cis''", "fis,", "cis"),
        "G":   ("g'", "b'", "d''", "g,", "d"),
        "Gm":  ("g'", "bes'", "d''", "g,", "d"),
        "G7":  ("g'", "b'", "f''", "g,", "d"),
        "Ab":  ("aes'", "c''", "ees''", "aes,", "ees"),
        "A":   ("a'", "cis''", "e''", "a,", "e"),
        "Am":  ("a'", "c''", "e''", "a,", "e"),
        "A7":  ("a'", "cis''", "g''", "a,", "e"),
        "Bb":  ("bes'", "d''", "f''", "bes,", "f"),
        "B":   ("b'", "dis''", "fis''", "b,", "fis"),
        "Bm":  ("b'", "d''", "fis''", "b,", "fis"),
    }
    
    db = {"4/4": {}, "3/4": {}, "2/4": {}, "6/8": {}}
    
    for chord, (r1, r2, r3, l1, l2) in base_chords.items():
        db["4/4"][chord] = {"rh": f"{r1}4 {r2}4 {r3}4 {r2}4", "lh": f"{l1}2 {l2}2"}
        db["3/4"][chord] = {"rh": f"{r1}4 {r2}4 {r3}4",       "lh": f"{l1}2."}
        db["2/4"][chord] = {"rh": f"{r1}8 {r2}8 {r3}8 {r2}8", "lh": f"{l1}2"}
        db["6/8"][chord] = {"rh": f"{r1}8 {r2}8 {r3}8 {r3}8 {r2}8 {r1}8", "lh": f"{l1}2."}
        
    return db

# 初始化全域字典
CHORD_DB = build_chord_db()

# ==========================================
# 3. 伴奏生成器
# ==========================================
def generate_accompaniment(chords: list[str], time_sig: str) -> tuple[str, str]:
    rest_map = {"4/4": "r1", "3/4": "r2.", "2/4": "r2", "6/8": "r2."}
    default_rest = rest_map.get(time_sig, "r1")
    current_db = CHORD_DB.get(time_sig, CHORD_DB["4/4"])
    
    rh_notes, lh_notes = [], []
    for chord in chords:
        mapping = current_db.get(chord, {"rh": default_rest, "lh": default_rest})
        rh_notes.append(mapping["rh"])
        lh_notes.append(mapping["lh"])
        
    return " ".join(rh_notes), " ".join(lh_notes)

# ==========================================
# 4. 核心 API 路由
# ==========================================
@app.post("/generate_pdf")
def generate_pdf(data: MusicData):
    
    # --- 共通的版權與編曲者設定 ---
    arranger_text = "Arr. 鄭宇泰 Myrllin Cheng"
    copyright_text = "長笛玩家工作室 Flute Gamer Studio" # 改為 copyright
    
    # --- 根據 score_type 切換排版 ---
    if data.score_type == "solo":
        lilypond_code = f"""
        \\version "2.22.1"
        \\header {{ 
          title = "{data.title}" 
          subtitle = "Flute Solo" 
          arranger = "{arranger_text}"
          copyright = "{copyright_text}"  % 顯示在第一頁正下方
          tagline = ##f                 % 徹底關閉 LilyPond 預設浮水印
        }}
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
        rh_music, lh_music = generate_accompaniment(data.chords, data.time_signature)
        lilypond_code = f"""
        \\version "2.22.1"
        \\header {{ 
          title = "{data.title}" 
          subtitle = "Flute & Piano" 
          arranger = "{arranger_text}"
          tagline = "{tagline_text}"
        }}
        \\score {{
          <<
            \\new Staff \\with {{ instrumentName = "Flute" }} {{ 
              \\key {data.key.lower()} \\major
              \\time {data.time_signature}
              \\tempo 4 = {data.tempo}
              {data.notes_flute} 
            }}
            \\new PianoStaff \\with {{ instrumentName = "Piano" }} <<
              \\new Staff {{ 
                \\key {data.key.lower()} \\major
                \\time {data.time_signature}
                {rh_music}
              }}
              \\new Staff {{ \\clef bass 
                \\key {data.key.lower()} \\major
                \\time {data.time_signature}
                {lh_music}
              }}
            >>
          >>
          \\layout {{ }}
        }}
        """

    elif data.score_type == "ensemble":
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
        \\header {{ 
          title = "{data.title}" 
          subtitle = "Flute Ensemble ({data.parts} parts)" 
          arranger = "{arranger_text}"
          tagline = "{tagline_text}"
        }}
        \\score {{
          <<
            {staffs}
          >>
          \\layout {{ }}
        }}
        """
        
    elif data.score_type == "beatbox":
        lilypond_code = f"""
        \\version "2.22.1"
        \\header {{ 
          title = "{data.title}" 
          subtitle = "Beatbox Flute" 
          arranger = "{arranger_text}"
          tagline = "{tagline_text}"
        }}
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
        lilypond_code = f"""
        \\version "2.22.1"
        \\header {{ 
          title = "{data.title}" 
          arranger = "{arranger_text}"
          tagline = "{tagline_text}"
        }}
        \\score {{
          \\new Staff {{ 
            \\key {data.key.lower()} \\major
            \\time {data.time_signature}
            \\tempo 4 = {data.tempo}
            {data.notes_flute} 
          }}
        }}
        """

    # --- 執行 LilyPond 編譯 ---
    with tempfile.TemporaryDirectory() as temp_dir:
        ly_file_path = os.path.join(temp_dir, "score.ly")
        with open(ly_file_path, "w", encoding="utf-8") as f:
            f.write(lilypond_code)
            
        try:
            subprocess.run(
                ["lilypond", "--output", os.path.join(temp_dir, "score"), ly_file_path], 
                check=True, capture_output=True
            )
            pdf_file_path = os.path.join(temp_dir, "score.pdf")
            with open(pdf_file_path, "rb") as pdf_file:
                pdf_bytes = pdf_file.read()
                
            return {"status": "success", "pdf_base64": base64.b64encode(pdf_bytes).decode('utf-8')}
            
        except subprocess.CalledProcessError as e:
            raise HTTPException(status_code=500, detail=f"LilyPond error: {e.stderr.decode()}")
