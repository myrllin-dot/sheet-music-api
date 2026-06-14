{\rtf1\ansi\ansicpg950\cocoartf2867
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 # \uc0\u20351 \u29992 \u36629 \u37327 \u32026 \u30340  Python \u26144 \u20687 \u27284 \
FROM python:3.10-slim\
\
# \uc0\u23433 \u35037  LilyPond\
RUN apt-get update && apt-get install -y lilypond && rm -rf /var/lib/apt/lists/*\
\
# \uc0\u35373 \u23450 \u24037 \u20316 \u30446 \u37636 \
WORKDIR /app\
\
# \uc0\u35079 \u35069  requirements.txt \u20006 \u23433 \u35037 \u22871 \u20214 \
COPY requirements.txt .\
RUN pip install --no-cache-dir -r requirements.txt\
\
# \uc0\u35079 \u35069 \u25152 \u26377 \u31243 \u24335 \u30908 \u21040 \u23481 \u22120 \u20839 \
COPY . .\
\
# \uc0\u21855 \u21205  FastAPI \u20282 \u26381 \u22120 \
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]}
