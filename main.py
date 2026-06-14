from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import base64
import os
import tempfile

app = FastAPI()

# 伴奏生成器
def generate_accompaniment(chords: list[str], time_sig: str) -> tuple[str, str]:
    # 定義動態的防呆休止符 (確保找不到和弦時，休止符的拍數能完美填滿小節)
    rest_map = {
        "4/4": "r1",  # 4拍
        "3/4": "r2.", # 3拍 (附點二分音符)
        "2/4": "r2",  # 2拍
        "6/8": "r2."  # 6個八分音符等同於一個附點二分音符的時間
    }
    default_rest = rest_map.get(time_sig, "r1")
    
    # 建立二維和弦資料庫
    chord_db = {
        "4/4": { # 四分音符分散和弦 (4拍)
            "C":  {"rh": "c'4 e' g' e'",    "lh": "c,2 g,2"},
            "F":  {"rh": "f'4 a' c'' a'",   "lh": "f,2 c2"},
            "G":  {"rh": "g'4 b' d'' b'",   "lh": "g,2 d2"},
            "Am": {"rh": "a'4 c'' e'' c''", "lh": "a,2 e2"},
            "Dm": {"rh": "d'4 f' a' f'",    "lh": "d,2 a,2"},
            "Em": {"rh": "e'4 g' b' g'",    "lh": "e,2 b,2"},
            "G7": {"rh": "g'4 b' f'' b'",   "lh": "g,2 d2"}
        },
        "3/4": { # 華爾滋圓舞曲風格：四分音符上行 (3拍)
            "C":  {"rh": "c'4 e' g'",       "lh": "c,2."},
            "F":  {"rh": "f'4 a' c''",      "lh": "f,2."},
            "G":  {"rh": "g'4 b' d''",      "lh": "g,2."},
            "Am": {"rh": "a'4 c'' e''",     "lh": "a,2."},
            "Dm": {"rh": "d'4 f' a'",       "lh": "d,2."},
            "Em": {"rh": "e'4 g' b'",       "lh": "e,2."},
            "G7": {"rh": "g'4 b' f''",      "lh": "g,2."}
        },
        "2/4": { # 進行曲風格：八分音符滾動 (2拍)
            "C":  {"rh": "c'8 e' g' e'",    "lh": "c,2"},
            "F":  {"rh": "f'8 a' c'' a'",   "lh": "f,2"},
            "G":  {"rh": "g'8 b' d'' b'",   "lh": "g,2"},
            "Am": {"rh": "a'8 c'' e'' c''", "lh": "a,2"},
            "Dm": {"rh": "d'8 f' a' f'",    "lh": "d,2"},
            "Em": {"rh": "e'8 g' b' g'",    "lh": "e,2"},
            "G7": {"rh": "g'8 b' f'' b'",   "lh": "g,2"}
        },
        "6/8": { # 抒情民謠風格：八分音符大跨度琶音 (6個半拍)
            "C":  {"rh": "c'8 e' g' c'' g' e'", "lh": "c,2."},
            "F":  {"rh": "f'8 a' c'' f'' c'' a'", "lh": "f,2."},
            "G":  {"rh": "g'8 b' d'' g'' d'' b'", "lh": "g,2."},
            "Am": {"rh": "a'8 c'' e'' a'' e'' c''", "lh": "a,2."},
            "Dm": {"rh": "d'8 f' a' d'' a' f'", "lh": "d,2."},
            "Em": {"rh": "e'8 g' b' e'' b' g'", "lh": "e,2."},
            "G7": {"rh": "g'8 b' d'' f'' d'' b'", "lh": "g,2."}
        }
    }
    
    # 根據目前的拍號取得對應的伴奏表，若遇到未知的拍號，預設使用 4/4 防呆
    current_db = chord_db.get(time_sig, chord_db["4/4"])
    
    rh_notes = []
    lh_notes = []
    
    for chord in chords:
        # 如果遇到字典裡沒有的和弦，使用預設的休止符來完美填滿小節，避免 LilyPond 報錯
        mapping = current_db.get(chord, {"rh": default_rest, "lh": default_rest})
        rh_notes.append(mapping["rh"])
        lh_notes.append(mapping["lh"])
        
    return " ".join(rh_notes), " ".join(lh_notes)

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
        # 新增傳入 data.time_signature 讓 Python 知道現在是幾分之幾拍
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
                % 塞入自動生成的右手伴奏
                {rh_music}
              }}
              \\new Staff {{ \\clef bass 
                \\key {data.key.lower()} \\major
                \\time {data.time_signature}
                % 塞入自動生成的左手伴奏
                {lh_music}
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
