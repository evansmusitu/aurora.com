'use strict';
/* MUSITU Studio: no browser-stored bearer tokens, third-party scripts or eval. */
let csrf = null, projects = [], jobs = [], audit = [], currentProject = null;
const $ = id => document.getElementById(id);
const templateDemo = {
  schema:'musitu.blender.job.v1', frame_end:48,
  objects:[
    {name:'STAGE_floor',type:'cube',location:[0,0,-.16],dimensions:[9,5,.25],material:'graphite'},
    {name:'ARCH_foundation',type:'cube',location:[-2,0,.1],dimensions:[2.4,2.1,.2],material:'ivory'},
    {name:'ARCH_wall',type:'cube',location:[-2,.94,1.3],dimensions:[2.4,.15,2.5],material:'ivory'},
    {name:'ARCH_roof',type:'cube',location:[-2,0,2.65],dimensions:[2.8,2.4,.18],material:'copper'},
    {name:'PRODUCT_chassis',type:'cube',location:[1.6,0,.7],dimensions:[2,.85,.36],material:'teal'},
    {name:'PRODUCT_cabin',type:'cube',location:[1.5,0,1.1],dimensions:[.98,.8,.52],material:'blueglass'},
    {name:'PRODUCT_wheelL',type:'cylinder',location:[1,-.46,.33],dimensions:[.56,.56,.21],material:'rubber'},
    {name:'PRODUCT_wheelR',type:'cylinder',location:[2.24,-.46,.33],dimensions:[.56,.56,.21],material:'rubber'},
    {name:'CHAR_body',type:'cube',location:[3.65,0,1.06],dimensions:[.5,.4,.95],material:'copper'},
    {name:'CHAR_head',type:'sphere',location:[3.65,0,1.76],dimensions:[.55,.55,.55],material:'ivory'},
    {name:'CHAR_arm',type:'cube',location:[4.04,0,1.05],dimensions:[.19,.19,.75],material:'wood'},
    {name:'STUDIO_orb',type:'sphere',location:[0,-1.3,1.08],dimensions:[1.05,1.05,1.05],material:'teal'}
  ],
  animations:[
    {object:'PRODUCT_wheelL',axis:'Z',degrees:360,start:1,end:48},
    {object:'PRODUCT_wheelR',axis:'Z',degrees:360,start:1,end:48},
    {object:'CHAR_arm',axis:'X',degrees:45,start:1,end:48}
  ]
};
const templateProduct = {schema:'musitu.blender.job.v1',frame_end:24,objects:[
  {name:'STAGE_floor',type:'cube',location:[0,0,-.17],dimensions:[8,5,.26],material:'graphite'},
  {name:'PRODUCT_pedestal',type:'cylinder',location:[0,0,.22],dimensions:[2,2,.45],material:'ivory'},
  {name:'PRODUCT_body',type:'cube',location:[0,0,1.2],dimensions:[2,1,1.3],material:'teal'},
  {name:'PRODUCT_detail',type:'sphere',location:[0,-.54,1.35],dimensions:[.7,.3,.7],material:'copper'}
],animations:[{object:'PRODUCT_detail',axis:'Z',degrees:90,start:1,end:24}]};
function textNode(tag,txt,klass){const n=document.createElement(tag);n.textContent=String(txt??'');if(klass)n.className=klass;return n;}
function button(label,handler,klass='tiny'){const n=textNode('button',label,klass);n.type='button';n.addEventListener('click',handler);return n;}
function closeModal(id){$(id).classList.add('hidden');}
function openModal(id){$(id).classList.remove('hidden');}
let toastTimer;
function toast(msg){$('toast').textContent=msg;$('toast').classList.remove('hidden');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').classList.add('hidden'),5500);}
async function api(path,{method='GET',body=null}={}){
  const headers={};
  if(method!=='GET'){headers['Content-Type']='application/json';if(csrf)headers['X-CSRF-Token']=csrf;}
  const resp=await fetch(path,{method,headers,credentials:'same-origin',body:body===null?undefined:JSON.stringify(body)});
  const data=await resp.json().catch(()=>({error:resp.statusText}));
  if(resp.status===401 && path!=='/api/login'){csrf=null;openModal('login-modal');}
  if(!resp.ok)throw new Error(data.error||data.detail||`HTTP ${resp.status}`);
  return data;
}
const when=t=>t?new Date(t*1000).toLocaleString(undefined,{year:'numeric',month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}):'—';
const projectName=id=>projects.find(x=>x.id===id)?.name||id;
function stateTag(state){const n=textNode('span',state,state.toLowerCase()+' pill');return n;}
async function refresh(){
  if(!csrf)return;
  try{
    const [p,j,a]=await Promise.all([api('/api/projects'),api('/api/jobs'),api('/api/audit')]);
    projects=p.projects;jobs=j.jobs;audit=a.events;
    $('conn-status').textContent='Control active';
    render();
  }catch(e){$('conn-status').textContent='Connection lost';toast(e.message);}
}
function render(){
  $('metric-projects').textContent=projects.length;
  $('metric-jobs').textContent=jobs.length;
  $('metric-verified').textContent=jobs.filter(x=>x.state==='VERIFIED').length;
  $('metric-drafts').textContent=jobs.filter(x=>x.state==='DRAFT').length;
  const cards=$('project-cards');cards.replaceChildren();
  if(!projects.length)cards.append(textNode('div','No projects yet. Create one to start.','empty'));
  for(const p of projects){
    const c=document.createElement('div');c.className='projectcard';
    c.append(textNode('small','◈  WORKSPACE'),textNode('strong',p.name),textNode('small',p.id),
      textNode('small',jobs.filter(j=>j.project_id===p.id).length+' render jobs'),
      button('+ Add render job',()=>showNewJob(p.id),'outline'));cards.append(c);
  }
  const recent=$('recent-jobs');recent.replaceChildren();
  if(!jobs.length)recent.append(textNode('div','No jobs recorded. Create a project to begin.','empty'));
  for(const j of jobs.slice(0,5)){
    const c=document.createElement('div');c.className='recentline';const left=document.createElement('div');left.append(textNode('strong',projectName(j.project_id)),textNode('small',j.id));
    c.append(left,stateTag(j.state));recent.append(c);
  }
  const tbody=$('jobs-table');tbody.replaceChildren();
  if(!jobs.length){const tr=document.createElement('tr'),td=textNode('td','No jobs recorded.');td.colSpan=5;tr.append(td);tbody.append(tr);}
  for(const j of jobs){
    const tr=document.createElement('tr');tr.append(textNode('td',j.id),textNode('td',projectName(j.project_id)));
    const state=document.createElement('td');state.append(stateTag(j.state));tr.append(state,textNode('td',when(j.created)));
    const actions=document.createElement('td'),box=document.createElement('div');box.className='row-actions';
    if(j.state==='DRAFT'){box.append(button('Approve',async()=>{if(!confirm('Approve this validated job for execution?'))return;await mutate('/api/jobs/'+j.id+'/approve');}));box.append(button('Cancel',async()=>{await mutate('/api/jobs/'+j.id+'/cancel');}));}
    if(j.state==='QUEUED')box.append(button('Cancel',async()=>{await mutate('/api/jobs/'+j.id+'/cancel');}));
    if(j.state==='VERIFIED'){for(const [name,label] of [['preview.png','Preview'],['scene.blend','Blender'],['scene.glb','GLB']]){box.append(button(label,()=>window.open('/api/jobs/'+encodeURIComponent(j.id)+'/files/'+name,'_blank','noopener,noreferrer')));}}
    if(j.state==='FAILED')box.append(textNode('small',(j.failure||'Worker failed').slice(0,90)));
    actions.append(box);tr.append(actions);tbody.append(tr);
  }
  const log=$('audit-log');log.replaceChildren();
  if(!audit.length)log.append(textNode('div','No activity recorded','empty'));
  for(const x of audit.slice(0,50)){
    const l=document.createElement('div');l.className='auditline';
    const d=document.createElement('div');d.append(textNode('strong',x.event),textNode('small',x.subject+' · '+x.detail));
    l.append(d,textNode('time',when(x.ts)));log.append(l);
  }
  const sel=$('job-project');sel.replaceChildren();
  for(const p of projects){const o=document.createElement('option');o.value=p.id;o.textContent=p.name;sel.append(o);}
  if(currentProject && projects.some(p=>p.id===currentProject))sel.value=currentProject;
}
async function mutate(path){try{await api(path,{method:'POST',body:{}});toast('Operation recorded.');await refresh();}catch(e){toast(e.message);}}
function showNewJob(pid){if(!projects.length){toast('Create a project first.');openModal('project-modal');return;}currentProject=pid||projects[0].id;$('job-json').value=JSON.stringify(templateDemo,null,2);$('job-template').value='demo';render();openModal('job-modal');}
function initEvents(){
  document.querySelectorAll('[data-close]').forEach(b=>b.addEventListener('click',()=>closeModal(b.dataset.close)));
  document.querySelectorAll('.navbtn').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('.navbtn').forEach(x=>x.classList.remove('active'));b.classList.add('active');const s=b.dataset.nav;if(s==='overview')window.scrollTo({top:0,behavior:'smooth'});else $(s+'-section').scrollIntoView({behavior:'smooth',block:'start'});}));
  $('refresh-btn').addEventListener('click',refresh);$('new-project').addEventListener('click',()=>openModal('project-modal'));
  $('new-job').addEventListener('click',()=>showNewJob());$('quick-create').addEventListener('click',()=>showNewJob());
  $('view-all-jobs').addEventListener('click',()=>$('jobs-section').scrollIntoView({behavior:'smooth'}));
  $('job-template').addEventListener('change',e=>$('job-json').value=JSON.stringify(e.target.value==='product'?templateProduct:templateDemo,null,2));
  $('login-form').addEventListener('submit',async e=>{e.preventDefault();$('login-error').textContent='';try{const d=await api('/api/login',{method:'POST',body:{token:$('login-token').value}});csrf=d.csrf;$('login-token').value='';closeModal('login-modal');toast('Studio unlocked.');await refresh();}catch(err){$('login-error').textContent=err.message;}});
  $('project-form').addEventListener('submit',async e=>{e.preventDefault();$('project-error').textContent='';try{const p=await api('/api/projects',{method:'POST',body:{name:$('project-name').value}});$('project-name').value='';closeModal('project-modal');currentProject=p.id;await refresh();toast('Project created.');}catch(err){$('project-error').textContent=err.message;}});
  $('job-form').addEventListener('submit',async e=>{e.preventDefault();$('job-error').textContent='';try{let job=JSON.parse($('job-json').value);const p=$('job-project').value;const d=await api('/api/projects/'+encodeURIComponent(p)+'/jobs',{method:'POST',body:job});closeModal('job-modal');await refresh();toast('Draft '+d.id+' created. Approve it from the queue.');}catch(err){$('job-error').textContent=err.message;}});
  $('logout-btn').addEventListener('click',async()=>{try{await api('/api/logout',{method:'POST',body:{}});}catch(_){}csrf=null;projects=[];jobs=[];audit=[];render();openModal('login-modal');});
}
(async()=>{initEvents();try{const r=await api('/api/me');csrf=r.csrf;await refresh();}catch(_){openModal('login-modal');$('conn-status').textContent='Authentication required';}})();
