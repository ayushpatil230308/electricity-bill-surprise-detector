"""Global CSS – aurora background + glassmorphism.

Readability rules used everywhere:
  * glass panels are mostly-white (>=58% opacity) so dark ink text keeps strong contrast
  * the hero is solid navy with white text
  * buttons use white text on a deep-blue gradient (never on cyan)
  * pop-up menus (select lists) stay opaque
Motion is limited to: one hero entrance, a slow background drift, hover feedback and a
short rise-in on cards. Everything is switched off for people who prefer reduced motion.
"""

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Sora:wght@600;700;800&display=swap');

:root{
  --navy:#0B2A5B; --navy-2:#123D82; --blue:#0A6CFF; --blue-dark:#0850C2; --cyan:#22B8E8; --amber:#F5A400;
  --ink:#0B1F3A; --muted:#3D5273; --bg:#EAF2FE; --line:#D3E2F5;
  --glass:rgba(255,255,255,.62); --glass-strong:rgba(255,255,255,.78);
  --glass-line:rgba(255,255,255,.75);
  --glass-shadow:0 10px 30px rgba(11,42,91,.10), inset 0 1px 0 rgba(255,255,255,.85);
  --font-body:'Manrope','Segoe UI',system-ui,-apple-system,sans-serif;
  --font-head:'Sora','Manrope','Segoe UI',system-ui,sans-serif;
}

/* ------------------------------------------------------------ aurora background */
.stApp{background:var(--bg); isolation:isolate; font-family:var(--font-body);}
.stApp::before, .stApp::after{
  content:""; position:fixed; z-index:-1; pointer-events:none; border-radius:50%; filter:blur(70px);
  will-change:transform;
}
.stApp::before{
  width:60vw; height:60vw; left:-15vw; top:-20vw;
  background:radial-gradient(circle at 30% 30%, rgba(10,108,255,.55), rgba(34,184,232,.32) 55%, transparent 72%);
  animation:bw-drift-a 26s ease-in-out infinite alternate;
}
.stApp::after{
  width:52vw; height:52vw; right:-14vw; bottom:-18vw;
  background:radial-gradient(circle at 60% 60%, rgba(245,164,0,.38), rgba(34,184,232,.30) 55%, transparent 72%);
  animation:bw-drift-b 32s ease-in-out infinite alternate;
}
@keyframes bw-drift-a{to{transform:translate(14vw,10vh) scale(1.12);}}
@keyframes bw-drift-b{to{transform:translate(-12vw,-8vh) scale(1.1);}}

[data-testid="stHeader"]{background:transparent;}
.block-container{padding-top:1.2rem; padding-bottom:3rem; max-width:1180px;}
.stApp, .stApp p, .stApp li, .stApp label, .stApp span, .stApp div{font-family:var(--font-body);}
.stApp, .stApp p, .stApp li, .stApp label, .stApp span{color:var(--ink);}
.stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp h5{color:var(--navy); font-family:var(--font-head); font-weight:700; letter-spacing:-.01em;}
.stApp h2{margin-top:2.4rem; padding-bottom:.55rem; position:relative; display:inline-block;}
.stApp h2::after{content:""; position:absolute; left:0; bottom:0; width:64px; height:4px; border-radius:4px;
  background:linear-gradient(90deg,var(--blue),var(--cyan));}

/* ------------------------------------------------------------------- sidebar */
[data-testid="stSidebar"]{
  background:rgba(255,255,255,.55);
  -webkit-backdrop-filter:blur(22px) saturate(160%); backdrop-filter:blur(22px) saturate(160%);
  border-right:1px solid var(--glass-line);
}
[data-testid="stSidebar"] *{color:var(--ink);}

/* ------------------------------------------------------------------- buttons */
.stButton>button,.stFormSubmitButton>button,.stDownloadButton>button{
  position:relative; overflow:hidden;
  background:linear-gradient(135deg,var(--blue) 0%,var(--blue-dark) 100%); color:#fff;
  border:1px solid rgba(255,255,255,.35); border-radius:12px;
  font-weight:700; padding:.55rem 1.3rem; min-height:44px;
  box-shadow:0 8px 20px rgba(10,108,255,.28), inset 0 1px 0 rgba(255,255,255,.35);
  transition:transform .2s ease, box-shadow .2s ease;
}
.stButton>button p,.stFormSubmitButton>button p,.stDownloadButton>button p{color:#fff !important; font-weight:700;}
.stButton>button::after,.stFormSubmitButton>button::after,.stDownloadButton>button::after{
  content:""; position:absolute; top:0; left:-60%; width:40%; height:100%;
  background:linear-gradient(100deg,transparent,rgba(255,255,255,.38),transparent);
  transform:skewX(-20deg); transition:left .6s ease;
}
.stButton>button:hover,.stFormSubmitButton>button:hover,.stDownloadButton>button:hover{
  background:linear-gradient(135deg,var(--blue-dark) 0%,var(--navy) 100%); color:#fff; border-color:rgba(255,255,255,.45);
  transform:translateY(-2px); box-shadow:0 12px 26px rgba(10,108,255,.36), inset 0 1px 0 rgba(255,255,255,.35);
}
.stButton>button:hover::after,.stFormSubmitButton>button:hover::after,.stDownloadButton>button:hover::after{left:130%;}
.stButton>button:active,.stFormSubmitButton>button:active,.stDownloadButton>button:active{transform:translateY(0);}
.stButton>button:focus-visible,.stFormSubmitButton>button:focus-visible,.stDownloadButton>button:focus-visible{
  outline:3px solid var(--amber); outline-offset:2px;}

/* -------------------------------------------------------------------- hero */
.bw-hero{
  position:relative; overflow:hidden; border-radius:22px; padding:2rem 2rem 1.7rem;
  background:linear-gradient(120deg,#0B2A5B 0%,#123D82 45%,#0B2A5B 100%); background-size:200% 200%;
  box-shadow:0 20px 50px rgba(11,42,91,.28), inset 0 1px 0 rgba(255,255,255,.25);
  border:1px solid rgba(255,255,255,.18);
  animation:bw-hero-in .8s cubic-bezier(.2,.8,.2,1) both, bw-hero-flow 14s ease-in-out infinite alternate;
}
.bw-hero::before, .bw-hero::after{
  content:""; position:absolute; border-radius:50%; filter:blur(38px); pointer-events:none;
}
.bw-hero::before{width:320px; height:320px; right:-70px; top:-110px;
  background:radial-gradient(circle,rgba(34,184,232,.65),transparent 70%); animation:bw-orb 9s ease-in-out infinite alternate;}
.bw-hero::after{width:260px; height:260px; right:200px; bottom:-150px;
  background:radial-gradient(circle,rgba(245,164,0,.45),transparent 70%); animation:bw-orb 12s ease-in-out infinite alternate-reverse;}
.bw-hero > *{position:relative; z-index:1;}
.bw-hero, .bw-hero *{color:#fff !important;}
.bw-hero h1{font-size:2.5rem; margin:0 0 .4rem 0; line-height:1.15; font-weight:800;
  animation:bw-rise .7s .15s cubic-bezier(.2,.8,.2,1) both;}
.bw-hero h1 .bolt{display:inline-block; animation:bw-bolt 2.6s ease-in-out infinite; transform-origin:50% 60%;}
.bw-hero p{font-size:1.12rem; margin:0 0 1.1rem 0; max-width:640px; opacity:.95;
  animation:bw-rise .7s .28s cubic-bezier(.2,.8,.2,1) both;}
.bw-badge{
  display:inline-block; margin:.22rem .4rem .22rem 0; padding:.32rem .85rem; font-size:.86rem; font-weight:700;
  background:rgba(255,255,255,.14); border:1px solid rgba(255,255,255,.45); border-radius:999px;
  -webkit-backdrop-filter:blur(10px); backdrop-filter:blur(10px);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.35);
  animation:bw-rise .6s cubic-bezier(.2,.8,.2,1) both; transition:background .2s ease, transform .2s ease;
}
.bw-badge:nth-of-type(1){animation-delay:.40s;} .bw-badge:nth-of-type(2){animation-delay:.48s;}
.bw-badge:nth-of-type(3){animation-delay:.56s;} .bw-badge:nth-of-type(4){animation-delay:.64s;}
.bw-badge:nth-of-type(5){animation-delay:.72s;}
.bw-badge:hover{background:rgba(255,255,255,.26); transform:translateY(-2px);}
/* travelling spark along the hero's bottom edge */
.bw-spark{position:absolute !important; left:0; right:0; bottom:0; height:4px; background:rgba(255,255,255,.12); overflow:hidden;}
.bw-spark::before{content:""; position:absolute; top:0; height:100%; width:30%;
  background:linear-gradient(90deg,transparent,var(--amber),var(--cyan),transparent); animation:bw-spark 3.2s linear infinite;}

@keyframes bw-hero-in{from{opacity:0; transform:translateY(18px) scale(.985);} to{opacity:1; transform:none;}}
@keyframes bw-hero-flow{to{background-position:100% 100%;}}
@keyframes bw-orb{to{transform:translate(-40px,30px) scale(1.15);}}
@keyframes bw-rise{from{opacity:0; transform:translateY(12px);} to{opacity:1; transform:none;}}
@keyframes bw-bolt{0%,60%,100%{transform:scale(1) rotate(0); filter:drop-shadow(0 0 0 rgba(245,164,0,0));}
  70%{transform:scale(1.18) rotate(-8deg); filter:drop-shadow(0 0 10px rgba(245,164,0,.9));} 80%{transform:scale(1) rotate(0);}}
@keyframes bw-spark{from{left:-30%;} to{left:100%;}}

/* ------------------------------------------------------------- flow chips */
.bw-steps{display:flex; flex-wrap:wrap; gap:.4rem; margin:1rem 0 .2rem;}
.bw-steps span{
  display:inline-flex; align-items:center; gap:.4rem; padding:.28rem .75rem; border-radius:999px;
  font-size:.82rem; font-weight:700; color:var(--navy);
  background:var(--glass); border:1px solid var(--glass-line); box-shadow:var(--glass-shadow);
  -webkit-backdrop-filter:blur(12px); backdrop-filter:blur(12px);
}
.bw-steps span:not(:last-child)::after{content:"›"; color:var(--blue); font-weight:800; margin-left:.15rem;}

/* ------------------------------------------------------------------- cards */
.bw-card, .bw-metric, .bw-predict{
  background:var(--glass); border:1px solid var(--glass-line); box-shadow:var(--glass-shadow);
  -webkit-backdrop-filter:blur(18px) saturate(170%); backdrop-filter:blur(18px) saturate(170%);
  transition:transform .25s ease, box-shadow .25s ease, background .25s ease;
  animation:bw-rise .5s cubic-bezier(.2,.8,.2,1) both;
}
.bw-card{position:relative; border-radius:18px; padding:1.1rem 1.3rem; height:100%; overflow:hidden;}
.bw-card::before{content:""; position:absolute; left:0; top:0; right:0; height:4px;
  background:linear-gradient(90deg,var(--blue),var(--cyan));}
.bw-card:hover, .bw-metric:hover{transform:translateY(-4px); background:var(--glass-strong);
  box-shadow:0 18px 38px rgba(11,42,91,.16), inset 0 1px 0 rgba(255,255,255,.9);}
.bw-card h4{margin:.2rem 0 .45rem 0; color:var(--navy);}
.bw-card ul{margin:.3rem 0 0 1.1rem; padding:0;} .bw-card li, .bw-card p{color:var(--ink); font-size:.95rem;}

.bw-metric{position:relative; border-radius:16px; padding:.85rem 1.05rem .85rem 1.2rem; margin-bottom:.6rem; overflow:hidden;}
.bw-metric::before{content:""; position:absolute; left:0; top:0; bottom:0; width:5px;
  background:linear-gradient(180deg,var(--blue),var(--cyan));}
.bw-metric .l{color:var(--muted); font-size:.78rem; font-weight:700; letter-spacing:.02em;}
.bw-metric .v{color:var(--navy); font-family:var(--font-head); font-size:1.55rem; font-weight:800; line-height:1.3;}
.bw-metric .s{color:var(--muted); font-size:.82rem;}

/* prediction: the one highlighted moment on the page */
.bw-predict{position:relative; border-radius:20px; padding:1.3rem 1.5rem; margin:.8rem 0; overflow:hidden;
  background:linear-gradient(135deg,rgba(255,255,255,.80),rgba(255,244,214,.72));
  border-color:rgba(245,164,0,.55);
  box-shadow:0 14px 40px rgba(245,164,0,.20), inset 0 1px 0 rgba(255,255,255,.9);}
.bw-predict::before{content:""; position:absolute; width:220px; height:220px; right:-60px; top:-90px; border-radius:50%;
  background:radial-gradient(circle,rgba(245,164,0,.35),transparent 70%); animation:bw-orb 8s ease-in-out infinite alternate;}
.bw-predict > *{position:relative;}
.bw-predict .l{color:var(--muted); font-weight:700;}
.bw-predict .big{font-family:var(--font-head); font-size:2.6rem; font-weight:800; line-height:1.2;
  background:linear-gradient(90deg,var(--navy),var(--blue)); -webkit-background-clip:text; background-clip:text;
  -webkit-text-fill-color:transparent; color:var(--navy);}
.bw-predict .r{color:var(--ink); font-size:1.05rem; font-weight:700;}

/* ---------------------------------------------------------------- messages */
.bw-warn,.bw-info,.bw-ok{border-radius:14px; padding:.7rem 1rem; margin:.4rem 0; border:1px solid;
  -webkit-backdrop-filter:blur(12px); backdrop-filter:blur(12px); animation:bw-rise .4s ease both;}
.bw-warn{background:rgba(255,244,214,.82); border-color:rgba(245,164,0,.7); color:#4A3000;} .bw-warn *{color:#4A3000;}
.bw-info{background:rgba(229,241,255,.82); border-color:rgba(156,196,245,.9); color:var(--navy);} .bw-info *{color:var(--navy);}
.bw-ok{background:rgba(227,246,236,.82); border-color:rgba(124,201,160,.9); color:#0B4A2A;} .bw-ok *{color:#0B4A2A;}
.bw-file{background:var(--glass); border:1px solid var(--glass-line); border-radius:14px; padding:.6rem 1rem; margin:.5rem 0;
  color:var(--ink); font-weight:700; box-shadow:var(--glass-shadow);
  -webkit-backdrop-filter:blur(12px); backdrop-filter:blur(12px);}

/* ------------------------------------------------------------ OCR evidence */
.bw-ocr{background:rgba(248,251,255,.85); color:var(--ink); border:1px solid var(--line); border-radius:12px; padding:.9rem;
  max-height:280px; overflow:auto; white-space:pre-wrap; font-family:ui-monospace,Menlo,Consolas,monospace; font-size:.85rem;}

/* ------------------------------------------------------------------ tables */
.bw-table-wrap{overflow-x:auto; border:1px solid var(--glass-line); border-radius:16px; background:var(--glass);
  box-shadow:var(--glass-shadow); -webkit-backdrop-filter:blur(16px); backdrop-filter:blur(16px);}
.bw-table{width:100%; border-collapse:collapse; font-size:.95rem; color:var(--ink);}
.bw-table th{background:linear-gradient(135deg,var(--navy),var(--navy-2)); color:#fff; padding:.7rem .9rem; text-align:left; white-space:nowrap; font-weight:700;}
.bw-table td{padding:.6rem .9rem; border-bottom:1px solid rgba(11,42,91,.08); color:var(--ink); white-space:nowrap; background:transparent; transition:background .15s ease;}
.bw-table tr:nth-child(even) td{background:rgba(234,242,254,.55);}
.bw-table tbody tr:hover td{background:rgba(34,184,232,.16);}
.bw-table td.up{color:#B42318; font-weight:800;} .bw-table td.down{color:#087443; font-weight:800;}

/* ------------------------------------------------------- streamlit widgets */
[data-testid="stFileUploaderDropzone"]{
  background:var(--glass); border:2px dashed rgba(10,108,255,.55); border-radius:18px; box-shadow:var(--glass-shadow);
  -webkit-backdrop-filter:blur(16px); backdrop-filter:blur(16px); transition:border-color .2s ease, transform .2s ease, box-shadow .2s ease;
}
[data-testid="stFileUploaderDropzone"]:hover{border-color:var(--cyan); transform:translateY(-2px);
  box-shadow:0 16px 36px rgba(10,108,255,.18), inset 0 1px 0 rgba(255,255,255,.9);}
[data-testid="stExpander"] details, [data-testid="stForm"]{
  background:var(--glass); border:1px solid var(--glass-line); border-radius:18px; box-shadow:var(--glass-shadow);
  -webkit-backdrop-filter:blur(16px); backdrop-filter:blur(16px);
}
[data-testid="stExpander"] summary:hover{color:var(--blue-dark);}
[data-testid="stForm"]{padding:1rem 1.1rem;}
div[data-baseweb="input"], div[data-baseweb="select"] > div, div[data-baseweb="base-input"]{
  background:rgba(255,255,255,.85) !important; border-radius:10px !important;}
div[data-baseweb="input"]:focus-within, div[data-baseweb="select"] > div:focus-within{
  box-shadow:0 0 0 3px rgba(10,108,255,.35) !important;}
[data-testid="stPlotlyChart"]{
  background:var(--glass); border:1px solid var(--glass-line); border-radius:18px; padding:.6rem .6rem .2rem; box-shadow:var(--glass-shadow);
  -webkit-backdrop-filter:blur(16px); backdrop-filter:blur(16px);
}
.bw-flow{color:var(--muted); font-size:.9rem;}

/* ----------------------------------------------------------------- fallbacks */
@supports not ((backdrop-filter:blur(1px)) or (-webkit-backdrop-filter:blur(1px))){
  :root{--glass:rgba(255,255,255,.92); --glass-strong:#fff;}
  [data-testid="stSidebar"]{background:#E8F1FC;}
}
@media (max-width:640px){
  .bw-hero{padding:1.4rem 1.2rem 1.3rem; border-radius:18px;}
  .bw-hero h1{font-size:1.75rem;} .bw-hero p{font-size:1rem;}
  .bw-predict .big{font-size:2rem;} .bw-metric .v{font-size:1.35rem;}
  .stApp::before, .stApp::after{filter:blur(50px);}
}
@media (prefers-reduced-motion:reduce){
  *, *::before, *::after{animation:none !important; transition:none !important;}
}
</style>
"""
