from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import base64
import os
import tempfile

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
    # 這裡定義了 20+ 種最常用的和弦（大調、小調、屬七）
    # 格式： "和弦名稱": ("右手音1", "右手音2", "右手音3", "左手根音", "左手五度音")
    # 注意：使用 LilyPond 絕對音高 (無 ', 有 ', 有 '')
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
    
    # 自動根據上述基礎音符，展開成四種節奏的伴奏！
    for chord, (r1, r2, r3, l1, l2) in base_chords.items():
        # 4/4 拍: 四分音符琶音 (4拍)
        db["4/4"][chord] = {"rh": f"{r1}4 {r2}4 {r3}4 {r2}4", "lh": f"{l1}2 {l2}2"}
        # 3/4 拍: 華爾滋上行 (3拍)
        db["3/4"][chord] = {"rh": f"{r1}4 {r2}4 {r3}4",       "lh": f"{l1}2."}
        # 2/4 拍: 進行曲八分音符 (2拍)
        db["2/4"][chord] = {"rh": f"{r1}8 {r2}8 {r3}8 {r2}8", "lh": f"{l1}2"}
        # 6/8 拍: 搖籃曲六連音 (6個八分音符 = 附點二分音符)
        db["6/8"][chord] = {"rh": f"{r1}8 {r2}8 {r3}8 {r3}8 {r2}8 {r1}8", "lh": f"{l1}2."}
        
    return db

# 初始化全域字典
CHORD_DB = build_chord_db()

# ==========================================
# 3. 伴奏生成器
# ==========================================
def generate_accompaniment(chords: list[str], time_sig: str) -> tuple[str, str]:
    # 防呆休止符 (確保找不到和弦時不報錯)
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
    
    # --- 根據 score_type 切換排版 ---
    if data.score_type == "solo":
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
        # 呼叫伴奏生成器，傳入和弦與拍號
        rh_music, lh_music = generate_accompaniment(data.chords, data.time_signature)
        
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
        \\header {{ title = "{data.title}" subtitle = "Flute Ensemble ({data.parts} parts)" }}
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
