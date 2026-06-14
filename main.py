{\rtf1\ansi\ansicpg950\cocoartf2867
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 from fastapi import FastAPI, HTTPException\
from pydantic import BaseModel\
import subprocess\
import base64\
import os\
import tempfile\
\
app = FastAPI()\
\
# \uc0\u23450 \u32681  n8n \u20659 \u36942 \u20358 \u30340 \u36039 \u26009 \u26684 \u24335 \
class MusicData(BaseModel):\
    title: str\
    key: str\
    time_signature: str\
    tempo: int\
    # \uc0\u36889 \u35041 \u20808 \u38928 \u30041 \u38899 \u31526 \u27396 \u20301 \u65292 \u31245 \u24460 \u20320 \u21487 \u20197 \u27770 \u23450 \u24590 \u40636 \u20659 \u36914 \u20358 \
    notes: str = "c4 d e f | g1" \
\
@app.post("/generate_pdf")\
def generate_pdf(data: MusicData):\
    # \uc0\u32068 \u21512  LilyPond \u35486 \u27861 \
    lilypond_code = f"""\
    \\\\version "2.22.1"\
    \\\\header \{\{ title = "\{data.title\}" \}\}\
    \\\\score \{\{\
      \\\\relative c' \{\{\
        \\\\key \{data.key.lower()\} \\\\major\
        \\\\time \{data.time_signature\}\
        \\\\tempo 4 = \{data.tempo\}\
        \{data.notes\}\
      \}\}\
      \\\\layout \{\{ \}\}\
    \}\}\
    """\
    \
    with tempfile.TemporaryDirectory() as temp_dir:\
        ly_file_path = os.path.join(temp_dir, "score.ly")\
        with open(ly_file_path, "w", encoding="utf-8") as f:\
            f.write(lilypond_code)\
            \
        try:\
            # \uc0\u22519 \u34892  LilyPond\
            subprocess.run(\
                ["lilypond", "--output", os.path.join(temp_dir, "score"), ly_file_path], \
                check=True, capture_output=True\
            )\
            \
            pdf_file_path = os.path.join(temp_dir, "score.pdf")\
            with open(pdf_file_path, "rb") as pdf_file:\
                pdf_bytes = pdf_file.read()\
                \
            # \uc0\u22238 \u20659  Base64 \u26684 \u24335 \
            return \{"status": "success", "pdf_base64": base64.b64encode(pdf_bytes).decode('utf-8')\}\
            \
        except subprocess.CalledProcessError as e:\
            # \uc0\u22914 \u26524 \u32232 \u35695 \u22833 \u25943 \u65292 \u22238 \u20659 \u37679 \u35492 \u35338 \u24687 \
            raise HTTPException(status_code=500, detail=f"LilyPond error: \{e.stderr.decode()\}")}