/* KilnAid companion card. History is fetched through authenticated HA WebSockets. */
class KilnAidHistoryCard extends HTMLElement {
  setConfig(config) {
    if(!config.entity)throw new Error('Set entity to a KilnAid status sensor');
    this.config=config;
    if(!this.shadowRoot)this.attachShadow({mode:'open'});
    this.loaded=0;
  }
  set hass(hass) {this._hass=hass;if(this.graph)this.graph.hass=hass;this.maybeLoad();}
  connectedCallback() {
    this.onHash=()=>this.maybeLoad();window.addEventListener('hashchange',this.onHash);
    this.timer=setInterval(()=>this.maybeLoad(),60000);this.maybeLoad();
  }
  disconnectedCallback() {window.removeEventListener('hashchange',this.onHash);clearInterval(this.timer);}
  getCardSize() {return 6;}
  maybeLoad() {
    if(!this._hass||!this.isConnected||this.loading)return;
    if(this.config?.popup_hash&&location.hash!==this.config.popup_hash)return;
    if(!this.loaded||Date.now()-this.loaded>=60000)this.load();
  }
  esc(v){return String(v??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
  date(t){return new Date(t*1000).toLocaleString(undefined,{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'});}
  async load(force=false){
    if(this.loading)return;this.loading=true;
    if(!this.loaded)this.shadowRoot.innerHTML='<ha-card style="padding:20px">Loading firing archive…</ha-card>';
    try {
      const result=await this._hass.callWS({type:'kilnaid/firings',entity_id:this.config.entity});
      const followLatest=!this.selection||this.selection===this.fires?.[0]?.id;
      this.fires=result.fires;
      if(followLatest||!this.fires.some(f=>f.id===this.selection))this.selection=this.fires[0]?.id;
      await this.render();this.loaded=Date.now();
    } catch(e) {
      this.shadowRoot.innerHTML=`<ha-card style="padding:20px"><p>Firing archive unavailable. ${this.esc(e.message||'Check that KilnAid v0.2.0 or later is loaded.')}</p><button>Retry</button></ha-card>`;
      this.shadowRoot.querySelector('button').onclick=()=>this.load(true);
    } finally {this.loading=false;}
  }
  async render(){
    const esc=v=>this.esc(v);
    if(!this.fires.length){this.shadowRoot.innerHTML='<ha-card style="padding:20px"><h3>Firing archive</h3><p>No recorded firings yet. New firings will appear automatically, including when the kiln is later offline.</p></ha-card>';return;}
    const fire=await this._hass.callWS({type:'kilnaid/firings',entity_id:this.config.entity,firing_id:this.selection});
    const points=fire.samples.map(s=>[s[0],s[1]]);
    const start=fire.start*1000,end=Math.max(points.at(-1)?.[0]??start,start+60000);
    const options=this.fires.map(f=>`<option value="${esc(f.id)}" ${f.id===fire.id?'selected':''}>${esc(this.date(f.start))}${f.partial_start?' (partial)':''}</option>`).join('');
    this.shadowRoot.innerHTML=`<style>
      ha-card{padding:16px;border-radius:12px}h3{margin:0;font-size:18px}select{width:100%;margin:12px 0;padding:10px;background:var(--secondary-background-color);color:var(--primary-text-color);border:1px solid var(--divider-color);border-radius:8px;font:inherit}p{margin:6px 0;color:var(--secondary-text-color);font-size:12px;line-height:1.5}.metrics{display:flex;justify-content:space-between;gap:12px;margin:14px 0}.metrics strong{font-size:18px}.label{font-size:11px;color:var(--secondary-text-color);margin-bottom:4px}#chart{min-height:250px}button{cursor:pointer}
      </style><ha-card><h3>${fire.id===this.fires[0].id?'Last fire':'Previous fire'}</h3>
      <select aria-label="Firing history">${options}</select>
      <div>${esc(fire.program||'Unknown program')}</div><p>${esc(this.date(fire.start))} – ${esc(this.date(end/1000))}</p>
      <div class="metrics"><div><div class="label">RECORDED PEAK</div><strong>${fire.peak===null?'—':Math.round(fire.peak)+esc(fire.unit)}</strong></div><div><div class="label">${fire.end?'HEATING ENDED':'STATUS'}</div><strong style="font-size:14px">${fire.end?esc(this.date(fire.end)):esc(fire.outcome)}</strong></div></div>
      ${fire.partial_start?'<p>Partial firing: its start was not captured in the recording.</p>':''}
      ${fire.has_gaps?'<p>Recording has gaps; changes during an outage may not be captured.</p>':''}
      <div id="chart"></div><p>Saved in KilnAid’s persistent archive. Includes available cooling readings for up to 48 hours after heating. Lines connect recorded samples.</p></ha-card>`;
    this.shadowRoot.querySelector('select').onchange=async e=>{this.selection=e.target.value;this.loaded=0;await this.load();};
    if(!points.length){this.shadowRoot.querySelector('#chart').textContent='No temperature samples were recorded for this firing.';return;}
    if(!customElements.get('apexcharts-card')){
      this.shadowRoot.querySelector('#chart').textContent='Install ApexCharts Card in HACS and add its dashboard resource to display the graph.';return;
    }
    const graph=document.createElement('apexcharts-card');
    graph.setConfig({type:'custom:apexcharts-card',graph_span:Math.ceil((end-start)/1000)+'s',span:{offset:Math.min(0,Math.round((end-Date.now())/1000))+'s'},
      header:{show:false},apex_config:{chart:{height:265,toolbar:{show:false}},yaxis:{decimalsInFloat:0},xaxis:{labels:{datetimeUTC:false}},legend:{show:false},annotations:{xaxis:fire.end?[{x:fire.end*1000,borderColor:'#22a06b',label:{text:'Heating ended',style:{color:'#fff',background:'#16805a'}}}]:[]}},
      series:[{entity:this.config.entity,name:'Temperature',unit:fire.unit,stroke_width:2,color:'#f97316',curve:'straight',extend_to:false,data_generator:'return '+JSON.stringify(points)+';'}]});
    graph.hass=this._hass;this.graph=graph;this.shadowRoot.querySelector('#chart').replaceChildren(graph);
  }
}
if(!customElements.get('kilnaid-history-card'))customElements.define('kilnaid-history-card',KilnAidHistoryCard);
window.customCards=window.customCards||[];
window.customCards.push({type:'kilnaid-history-card',name:'KilnAid Firing History',description:'Persistent firing and cooling history; configure a KilnAid status entity.'});
