"""Global CSS. Every colour pair below is chosen for strong contrast:
navy (#0B2A5B) with white text, white cards with ink (#0B1F3A) text."""

CSS = """
<style>
:root{
  --navy:#0B2A5B; --blue:#0A6CFF; --blue-dark:#0850C2; --cyan:#22B8E8;
  --ink:#0B1F3A; --muted:#3D5273; --bg:#F4F8FD; --card:#FFFFFF; --line:#D3E2F5; --amber:#F5A400;
}
.stApp{background:var(--bg);}
.block-container{padding-top:1.2rem; padding-bottom:3rem; max-width:1180px;}
.stApp, .stApp p, .stApp li, .stApp label, .stApp span{color:var(--ink);}
.stApp h1,.stApp h2,.stApp h3,.stApp h4{color:var(--navy); font-weight:700;}
.stApp h2{margin-top:2.2rem; padding-bottom:.35rem; border-bottom:3px solid var(--cyan); display:inline-block;}

/* Sidebar (light, so every widget stays readable) */
[data-testid="stSidebar"]{background:#E8F1FC; border-right:1px solid var(--line);}
[data-testid="stSidebar"] *{color:var(--ink);}

/* Buttons: white label on solid blue */
.stButton>button,.stFormSubmitButton>button,.stDownloadButton>button{
  background:var(--blue); color:#fff; border:0; border-radius:8px;
  font-weight:600; padding:.55rem 1.2rem; min-height:44px;}
.stButton>button p,.stFormSubmitButton>button p,.stDownloadButton>button p{color:#fff !important;}
.stButton>button:hover,.stFormSubmitButton>button:hover,.stDownloadButton>button:hover{background:var(--blue-dark); color:#fff;}

/* Hero */
.bw-hero{background:var(--navy); border-radius:14px; padding:1.6rem 1.6rem 1.3rem; border-bottom:5px solid var(--amber);}
.bw-hero, .bw-hero *{color:#fff !important;}
.bw-hero h1{font-size:2.2rem; margin:0 0 .3rem 0; line-height:1.2;}
.bw-hero p{font-size:1.1rem; margin:0 0 .9rem 0;}
.bw-badge{display:inline-block; background:rgba(255,255,255,.14); border:1px solid rgba(255,255,255,.55);
  border-radius:999px; padding:.25rem .75rem; margin:.2rem .35rem .2rem 0; font-size:.85rem; font-weight:600;}

/* Cards */
.bw-card{background:var(--card); border:1px solid var(--line); border-top:4px solid var(--cyan);
  border-radius:12px; padding:1rem 1.2rem; height:100%;}
.bw-card h4{margin:0 0 .4rem 0; color:var(--navy);}
.bw-card ul{margin:.3rem 0 0 1.1rem; padding:0;} .bw-card li, .bw-card p{color:var(--ink); font-size:.95rem;}
.bw-metric{background:var(--card); border:1px solid var(--line); border-left:5px solid var(--blue);
  border-radius:10px; padding:.8rem 1rem; margin-bottom:.6rem;}
.bw-metric .l{color:var(--muted); font-size:.82rem; font-weight:600; text-transform:uppercase; letter-spacing:.03em;}
.bw-metric .v{color:var(--navy); font-size:1.6rem; font-weight:800; line-height:1.25;}
.bw-metric .s{color:var(--muted); font-size:.82rem;}
.bw-predict{background:#FFFFFF; border:1px solid var(--line); border-left:6px solid var(--amber); border-radius:12px; padding:1.1rem 1.3rem; margin:.6rem 0;}
.bw-predict .l{color:var(--muted); font-weight:600;} .bw-predict .big{color:var(--navy); font-size:2.2rem; font-weight:800;}
.bw-predict .r{color:var(--ink); font-size:1.05rem; font-weight:600;}

/* Messages */
.bw-warn{background:#FFF4D6; border:1px solid var(--amber); color:#4A3000; border-radius:8px; padding:.6rem .9rem; margin:.35rem 0;}
.bw-warn *{color:#4A3000;}
.bw-info{background:#E5F1FF; border:1px solid #9CC4F5; color:var(--navy); border-radius:8px; padding:.6rem .9rem; margin:.35rem 0;}
.bw-info *{color:var(--navy);}
.bw-ok{background:#E3F6EC; border:1px solid #7CC9A0; color:#0B4A2A; border-radius:8px; padding:.6rem .9rem; margin:.35rem 0;}
.bw-ok *{color:#0B4A2A;}
.bw-file{background:#fff; border:1px solid var(--line); border-radius:8px; padding:.55rem .9rem; margin:.4rem 0; color:var(--ink); font-weight:600;}

/* OCR evidence */
.bw-ocr{background:#F8FBFF; color:var(--ink); border:1px solid var(--line); border-radius:8px; padding:.8rem;
  max-height:280px; overflow:auto; white-space:pre-wrap; font-family:ui-monospace,Menlo,Consolas,monospace; font-size:.85rem;}

/* Tables */
.bw-table-wrap{overflow-x:auto; border:1px solid var(--line); border-radius:10px; background:#fff;}
.bw-table{width:100%; border-collapse:collapse; font-size:.95rem; color:var(--ink);}
.bw-table th{background:var(--navy); color:#fff; padding:.6rem .8rem; text-align:left; white-space:nowrap;}
.bw-table td{padding:.55rem .8rem; border-bottom:1px solid #E1ECF8; color:var(--ink); white-space:nowrap; background:#fff;}
.bw-table tr:nth-child(even) td{background:#F4F8FD;}
.bw-table td.up{color:#B42318; font-weight:700;} .bw-table td.down{color:#087443; font-weight:700;}

/* Flow steps */
.bw-flow{color:var(--muted); font-size:.9rem;}

/* Always render light, even when the browser/OS is in dark mode */
html{color-scheme:light;}
header[data-testid="stHeader"]{background:var(--bg) !important;}
header[data-testid="stHeader"] *{color:var(--ink) !important;}

/* Expanders: light header with navy text (Streamlit's default can turn dark) */
[data-testid="stExpander"]{background:#FFFFFF !important; border:1px solid var(--line) !important; border-radius:10px !important;}
[data-testid="stExpander"] details, [data-testid="stExpander"] summary{background:#E8F1FC !important; color:var(--navy) !important;}
[data-testid="stExpander"] summary *{color:var(--navy) !important; font-weight:600;}
[data-testid="stExpander"] summary svg{fill:var(--navy) !important; stroke:var(--navy) !important;}
[data-testid="stExpander"] summary:hover{background:#D9E8FA !important;}

/* Captions and help text: dark enough to read */
[data-testid="stCaptionContainer"], .stCaption, [data-testid="stCaptionContainer"] *{color:var(--muted) !important; font-size:.9rem !important;}

@media (max-width:640px){
  .bw-hero h1{font-size:1.6rem;} .bw-hero p{font-size:1rem;}
  .bw-predict .big{font-size:1.8rem;} .bw-metric .v{font-size:1.35rem;}
}
</style>
"""
