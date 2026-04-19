import json
import webview
from datetime import datetime
from pathlib import Path

ANIMAL_EMOJI = {
    "owl": "🦉", "fox": "🦊", "dolphin": "🐬", "lion": "🦁",
    "wolf": "🐺", "elephant": "🐘", "eagle": "🦅", "deer": "🦌",
    "octopus": "🐙", "tiger": "🐯", "bear": "🐻", "butterfly": "🦋",
    "horse": "🐴", "raven": "🐦", "cat": "🐱", "dog": "🐶",
    "cheetah": "🐆", "penguin": "🐧", "parrot": "🦜", "panda": "🐼",
}

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Personality Mirror</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  background:#09090b;color:#f4f4f5;
  min-height:100vh;display:flex;flex-direction:column;align-items:center;
  padding:28px 16px 48px;
}
h1{font-size:15px;font-weight:600;color:#a1a1aa;letter-spacing:.04em;margin-bottom:24px;text-transform:uppercase}

.card{
  width:100%;max-width:480px;
  background:#18181b;border:1px solid #27272a;border-radius:20px;
  padding:24px;margin-bottom:14px;
}

/* Avatar */
.avatar-wrap{display:flex;flex-direction:column;align-items:center;gap:8px;margin-bottom:4px}
.avatar{
  width:96px;height:96px;border-radius:50%;
  background:linear-gradient(135deg,#7c3aed,#4f46e5);
  display:flex;align-items:center;justify-content:center;
  font-size:48px;border:3px solid #3f3f46;
}
.animal-name{font-size:13px;color:#a1a1aa;font-weight:500}
.animal-reason{font-size:11px;color:#52525b;text-align:center;max-width:300px;font-style:italic;margin-top:2px}

/* Spider chart */
#spider-wrap{display:flex;justify-content:center;margin:8px 0}
svg.spider{overflow:visible}
.axis-label{font-size:11px;fill:#71717a;font-family:-apple-system,sans-serif}
.spoke{stroke:#27272a;stroke-width:1}
.ring{fill:none;stroke:#27272a;stroke-width:.8}
.area{fill:rgba(124,58,237,.25);stroke:#8b5cf6;stroke-width:2;stroke-linejoin:round}
.dot{fill:#8b5cf6}

/* OCEAN bars */
.trait{margin-bottom:11px}
.trait-row{display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px}
.trait-name{color:#d4d4d8}
.trait-pct{color:#71717a}
.bar-bg{height:5px;background:#27272a;border-radius:9999px;overflow:hidden}
.bar{height:100%;border-radius:9999px;transition:width 1.2s ease}
.b-o{background:#8b5cf6}.b-c{background:#3b82f6}
.b-e{background:#10b981}.b-a{background:#f59e0b}.b-n{background:#f43f5e}

/* Interests */
.tags{display:flex;flex-wrap:wrap;gap:7px}
.tag{
  padding:4px 12px;border-radius:9999px;font-size:12px;
  background:rgba(124,58,237,.18);color:#c4b5fd;
  border:1px solid rgba(124,58,237,.28);
}

/* Fun fact */
.fun-fact{
  font-size:13px;color:#a1a1aa;font-style:italic;line-height:1.65;
  padding:14px 16px;background:#09090b;border-radius:10px;
  border-left:3px solid #7c3aed;
}

/* Status bar */
.status{
  width:100%;max-width:480px;
  display:flex;align-items:center;justify-content:center;gap:8px;
  padding:11px;font-size:12px;color:#52525b;
  background:#18181b;border:1px solid #27272a;border-radius:12px;
}
.dot-pulse{
  width:8px;height:8px;border-radius:50%;background:#10b981;
  animation:pulse 2s ease-in-out infinite;
}
.dot-spin{
  width:10px;height:10px;border-radius:50%;
  border:2px solid #818cf8;border-top-color:transparent;
  animation:spin .7s linear infinite;
}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
@keyframes spin{to{transform:rotate(360deg)}}

/* Export */
.export-btn{
  margin-top:6px;padding:10px 24px;
  background:transparent;border:1px solid #3f3f46;border-radius:10px;
  color:#a1a1aa;font-size:13px;cursor:pointer;transition:all .15s;
}
.export-btn:hover{background:#27272a;color:#f4f4f5;border-color:#52525b}

.empty{text-align:center;padding:48px 0;color:#3f3f46}
.empty .big{font-size:48px;margin-bottom:12px}
.ts{font-size:10px;color:#3f3f46;margin-top:10px;text-align:right}
</style>
</head>
<body>
<h1>Personality Mirror</h1>
<div id="root"></div>

<script>
const TRAITS=[
  {key:'openness',       label:'Openness',          cls:'b-o'},
  {key:'conscientiousness',label:'Conscientiousness',cls:'b-c'},
  {key:'extraversion',   label:'Extraversion',       cls:'b-e'},
  {key:'agreeableness',  label:'Agreeableness',       cls:'b-a'},
  {key:'neuroticism',    label:'Neuroticism',         cls:'b-n'},
];

function spider(values, size=220){
  const cx=size/2, cy=size/2, r=size*0.36;
  const n=values.length;
  const angle=i=>( (i/n)*2*Math.PI - Math.PI/2 );
  const pt=(i,frac)=>({
    x: cx + r*frac*Math.cos(angle(i)),
    y: cy + r*frac*Math.sin(angle(i))
  });
  const labels=['Openness','Conscientious','Extraversion','Agreeable','Neuroticism'];
  const labelOffset=1.28;

  let rings='';
  [.25,.5,.75,1].forEach(f=>{
    const pts=values.map((_,i)=>pt(i,f));
    rings+=`<polygon class="ring" points="${pts.map(p=>p.x+','+p.y).join(' ')}"/>`;
  });

  let spokes='';
  values.forEach((_,i)=>{
    const end=pt(i,1);
    spokes+=`<line class="spoke" x1="${cx}" y1="${cy}" x2="${end.x}" y2="${end.y}"/>`;
  });

  const areaPts=values.map((v,i)=>pt(i,v));
  const areaStr=areaPts.map(p=>p.x+','+p.y).join(' ');

  let dots='';
  areaPts.forEach(p=>{dots+=`<circle class="dot" cx="${p.x}" cy="${p.y}" r="4"/>`;});

  let lbls='';
  values.forEach((_,i)=>{
    const p=pt(i,labelOffset);
    const anchor=p.x<cx-4?'end':p.x>cx+4?'start':'middle';
    lbls+=`<text class="axis-label" x="${p.x}" y="${p.y}" text-anchor="${anchor}" dominant-baseline="middle">${labels[i]}</text>`;
  });

  return `<svg class="spider" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
    ${rings}${spokes}
    <polygon class="area" points="${areaStr}"/>
    ${dots}${lbls}
  </svg>`;
}

function render(profile, status){
  const root=document.getElementById('root');
  if(!profile){
    root.innerHTML=`
      <div class="card empty">
        <div class="big">🧠</div>
        <p>Watching your activity…</p>
        <p style="font-size:12px;margin-top:6px;color:#52525b">First profile generates in ~2 minutes.</p>
      </div>
      <div class="status">
        <div class="${status.spin?'dot-spin':'dot-pulse'}"></div>
        ${status.text}
      </div>`;
    return;
  }

  const o=profile.ocean;
  const vals=[o.openness,o.conscientiousness,o.extraversion,o.agreeableness,o.neuroticism];
  const bars=TRAITS.map(t=>{
    const pct=Math.round(o[t.key]*100);
    return `<div class="trait">
      <div class="trait-row"><span class="trait-name">${t.label}</span><span class="trait-pct">${pct}%</span></div>
      <div class="bar-bg"><div class="bar ${t.cls}" style="width:${pct}%"></div></div>
    </div>`;
  }).join('');

  const tags=(profile.interests||[]).map(i=>`<span class="tag">${i}</span>`).join('');
  const emoji=profile.spirit_animal_emoji||'🐾';
  const animal=(profile.spirit_animal||'').charAt(0).toUpperCase()+(profile.spirit_animal||'').slice(1);
  const ts=profile.updated_at?new Date(profile.updated_at).toLocaleString():'';

  root.innerHTML=`
    <div class="card">
      <div class="avatar-wrap">
        <div class="avatar">${emoji}</div>
        <div class="animal-name">Your Spirit Animal: ${animal}</div>
        ${profile.spirit_animal_reason?`<div class="animal-reason">${profile.spirit_animal_reason}</div>`:''}
      </div>
    </div>

    <div class="card">
      <div id="spider-wrap">${spider(vals)}</div>
      ${bars}
    </div>

    ${tags?`<div class="card">
      <div style="font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:#52525b;margin-bottom:12px">Top Interests</div>
      <div class="tags">${tags}</div>
    </div>`:''}

    ${profile.fun_fact?`<div class="card">
      <div style="font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:#52525b;margin-bottom:12px">Behavioral Insight</div>
      <div class="fun-fact">${profile.fun_fact}</div>
    </div>`:''}

    <div class="status">
      <div class="${status.spin?'dot-spin':'dot-pulse'}"></div>
      ${status.text}
    </div>

    <button class="export-btn" onclick="exportCard()">Export as JSON</button>
    ${ts?`<div class="ts">Last updated: ${ts}</div>`:''}`;
}

async function exportCard(){
  await window.pywebview.api.export_json();
}

async function poll(){
  try{
    const raw=await window.pywebview.api.get_state();
    const s=JSON.parse(raw);
    render(s.profile,s.status);
  }catch(e){console.error(e)}
}

window.addEventListener('pywebviewready',()=>{
  poll();
  setInterval(poll,4000);
});
</script>
</body>
</html>"""


class Api:
    def __init__(self):
        self._profile = None
        self._status = {"text": "Monitoring activity…", "spin": True}
        self._window = None

    def get_state(self) -> str:
        return json.dumps({"profile": self._profile, "status": self._status})

    def set_profile(self, profile: dict):
        profile["updated_at"] = datetime.now().isoformat()
        profile["spirit_animal_emoji"] = ANIMAL_EMOJI.get(
            profile.get("spirit_animal", ""), "🐾"
        )
        self._profile = profile
        self._status = {"text": "Profile up to date · updates every 2 min", "spin": False}

    def set_status(self, text: str, spin: bool = False):
        self._status = {"text": text, "spin": spin}

    def export_json(self):
        if not self._profile:
            return
        path = Path.home() / "Downloads" / f"personality_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path.write_text(json.dumps(self._profile, indent=2))
        if self._window:
            self._window.evaluate_js(
                f"document.querySelector('.export-btn').textContent='Saved to Desktop ✓'"
            )


_api = Api()


def start(on_ready=None):
    window = webview.create_window(
        "Personality Mirror",
        html=HTML,
        js_api=_api,
        width=560,
        height=900,
        resizable=True,
        background_color="#09090b",
    )
    _api._window = window
    # edgechromium uses the Edge WebView2 runtime (built into Windows 11)
    webview.start(on_ready, window, gui="edgechromium", debug=False)


def update_profile(profile: dict):
    _api.set_profile(profile)


def update_status(text: str, spin: bool = False):
    _api.set_status(text, spin)
