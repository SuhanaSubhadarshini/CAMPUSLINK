const eligibilityLabel=e=>e.status==="UNVERIFIED"?"Eligibility unverified":e.eligible?"Eligible":"Not eligible";
const eligibilityClass=e=>e.status==="UNVERIFIED"?"unverified":e.eligible?"ready":"not-ready";
const coverageText=v=>v===null||v===undefined?"Skill coverage unavailable":fmt(v)+"%";
const componentText=v=>v===null||v===undefined?"Unavailable":fmt(v);
// All fit scores and eligibility decisions come from the backend.
const API_BASE_URL = "https://campuslink-rj40.onrender.com/api/v1";
const $ = id => document.getElementById(id);
const esc = v => String(v ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const fmt = (v, n=1) => Number(v).toFixed(n);
const assessmentText=v=>v===null||v===undefined||v===""?"Not assessed":String(v)+" / 100";
function readProfileSelection(){try{return Number(localStorage.getItem("campuslink.profile"))||null;}catch{return null;}}
function rememberProfile(id){try{if(id)localStorage.setItem("campuslink.profile",String(id));else localStorage.removeItem("campuslink.profile");}catch{}}
const state = {jobCatalog:{},students:[],jobs:[],companies:[],placements:[],ready:{},errors:{},studentId:readProfileSelection(),jobId:null,dashboard:null,fit:null,gap:null,eligibility:null,version:0,busy:false,placing:false};
const student = () => state.students.find(s => s.id === state.studentId);
const job = () => state.jobs.find(j => j.id === state.jobId);
const statuses = ["offered","accepted","joined","rejected","withdrawn"];
let matchController, toastTimer, modalTrigger;

async function api(path, options={}) {
  const {json,binary=false,root=false,signal,...rest}=options;
  const controller=new AbortController(), timer=setTimeout(()=>controller.abort(),20000);
  const abort=()=>controller.abort(); signal?.addEventListener("abort",abort,{once:true});
  if(signal?.aborted) controller.abort();
  try {
    const headers=new Headers(rest.headers||{});
    if(json!==undefined) headers.set("Content-Type","application/json");
    const response=await fetch((root?"http://127.0.0.1:8000":API_BASE_URL)+path,{
      ...rest,headers,signal:controller.signal,...(json!==undefined?{body:JSON.stringify(json)}:{})
    });
    if(!response.ok) {
      let detail; try {detail=(await response.json()).detail;} catch {}
      throw new Error(Array.isArray(detail)?detail.map(d=>(d.loc||[]).join(".")+": "+d.msg).join("; "):
        typeof detail==="string"?detail:"Backend request failed (HTTP "+response.status+").");
    }
    if(response.status===204) return null;
    return binary?await response.blob():await response.json();
  } catch(e) {
    if(signal?.aborted) throw e;
    if(e.name==="AbortError") throw new Error("Backend request timed out. Please retry.");
    if(e instanceof TypeError) throw new Error("Unable to connect to CAMPUSLINK backend. Start FastAPI at http://127.0.0.1:8000, then open index.html with Live Server (http://127.0.0.1 or http://localhost). If you changed CORS settings, restart the backend.");
    throw e;
  } finally {clearTimeout(timer);signal?.removeEventListener("abort",abort);}
}
async function getAll(path) {
  const all=[];
  for(let skip=0;;skip+=500) {const page=await api(path+(path.includes("?")?"&":"?")+"skip="+skip+"&limit=500");all.push(...page);if(page.length<500)return all;}
}
function toast(text) {$("toast").textContent=text;$("toast").classList.add("show");clearTimeout(toastTimer);toastTimer=setTimeout(()=>$("toast").classList.remove("show"),5000);}
function notice(id,text,kind="",retry="") {
  const e=$(id);e.className="api-state "+kind;e.setAttribute("aria-busy",String(kind==="loading"));
  e.innerHTML=text?"<span>"+esc(text)+"</span>"+(retry?' <button class="small-btn" data-retry="'+retry+'">Retry</button>':""):"";
}
function go(id) {
  if(!document.querySelector(".page-section#"+CSS.escape(id))) id="home";
  document.querySelectorAll(".page-section").forEach(s=>s.classList.toggle("active-section",s.id===id));
  document.querySelectorAll(".nav-item").forEach(n=>{n.classList.toggle("active",n.dataset.section===id);if(n.dataset.section===id)n.setAttribute("aria-current","page");else n.removeAttribute("aria-current");});
  if(id==="roadmap"&&typeof loadGapChoices==="function")loadGapChoices();
  history.replaceState(null,"","#"+id);window.scrollTo({top:0,behavior:"smooth"});
}
const tags=(a,kind="")=>a.length?'<div class="skill-tags">'+a.map(s=>'<span class="'+kind+'">'+esc(s)+"</span>").join("")+"</div>":'<p class="muted">None listed.</p>';
const list=(a,empty="None listed.")=>a.length?"<ul>"+a.map(s=>"<li>"+esc(s)+"</li>").join("")+"</ul>":'<p class="muted">'+esc(empty)+"</p>";
const metric=(label,value,detail="")=>'<div class="insight-card"><span>'+esc(label)+"</span><strong>"+esc(value)+"</strong><small>"+esc(detail)+"</small></div>";
const studentName=id=>state.students.find(s=>s.id===id)?.name||"Student #"+id;
const jobName=id=>state.jobs.find(j=>j.id===id)?.title||state.jobCatalog[id]?.title||"Job #"+id;
const companyName=id=>state.companies.find(c=>c.id===id)?.name||"Company #"+id;
function bars(items,total) {
  return items.length?'<div class="score-bars">'+items.map(x=>'<div><span>'+esc(x.skill)+"</span><b>"+x.count+'</b><i><u style="width:'+Math.min(100,x.count/Math.max(total,1)*100)+'%"></u></i></div>').join("")+"</div>":'<p class="muted">No skill data available.</p>';
}
function renderDashboard() {
  const d=state.dashboard;if(!d)return;
  const cards='<div class="insight-grid">'+metric("Total students",d.total_students)+metric("Companies",d.total_companies)+metric("Jobs",d.total_jobs)+metric("Total placements",d.placement_statistics.total_records)+metric("Placed students",d.placed_students,"Distinct accepted / joined students")+metric("Placement rate",fmt(d.placement_rate)+"%")+metric("Average CGPA",fmt(d.average_cgpa,2))+"</div>";
  const charts='<div class="grid-2"><article class="panel"><span class="eyebrow">STUDENT SKILLS</span><h3>Top skills</h3>'+bars(d.top_skills,d.total_students)+'</article><article class="panel"><span class="eyebrow">JOB REQUIREMENTS</span><h3>Most demanded skills</h3>'+bars(d.most_demanded_skills,d.total_jobs)+"</article></div>"+'<article class="panel space-top"><h3>Common student skill gaps</h3>'+(d.skill_gaps.map(g=>'<div class="risk-row"><span>'+esc(g.skill)+' / '+g.jobs_requiring+' jobs</span><b>'+g.students_without_skill+' students missing</b></div>').join("")||'<p class="muted">No skill gap data yet.</p>')+"</article>";
  const externalCount=d.opportunity_sources?.adzuna||0;
  const openJobs=state.ready.jobs?state.jobs.filter(j=>j.status==="open"):d.latest_opportunities;
  const latest=kind=>openJobs.filter(j=>opportunityKind(j)===kind).sort((a,b)=>b.id-a.id).slice(0,5);
  const latestCards=rows=>rows.map(j=>'<div class="latest-opportunity">'+sourceBadge(j)+'<button class="match-item" data-job="'+j.id+'"><div><b>'+esc(j.title)+'</b><small>'+esc(j.company.name)+' / '+esc(j.location||"Location not specified")+'</small></div></button>'+adzunaAttribution(j)+originalListing(j)+'</div>').join("");
  const externalIds=new Set(openJobs.filter(j=>j.source==="adzuna").map(j=>j.id));
  const externalMatches=d.eligible_students_per_job.filter(j=>externalIds.has(j.job_id));
  const sumMatches=key=>externalMatches.reduce((n,j)=>n+(j[key]||0),0);
  const matching=state.ready.jobs?'<p>Verified eligible: '+sumMatches('eligible_students')+' / Unverified: '+sumMatches('unverified_students')+' / Not eligible: '+sumMatches('not_eligible_students')+'</p><p class="muted">Student / open external opportunity pairs. A fit score does not verify eligibility.</p>':'<p class="muted">Load opportunities to see external matching counts.</p>';
  $("dashboardContent").innerHTML='<div class="insight-grid">'+metric("Real external opportunities",externalCount,"Saved open Adzuna listings; availability may change")+metric("Students",d.total_students,"Stored profiles, including demonstration profiles")+metric("Stored opportunities",d.available_opportunities,"All open sources, including "+(d.opportunity_sources?.demo||0)+" demo opportunities")+metric("Placed students",d.placed_students,"All stored sources, including demo offers; accepted / joined")+'</div><article class="panel matching-insight space-top"><h3>Matching Insight</h3><p>External opportunities</p>'+matching+'<details><summary>All stored matching data (includes demo opportunities)</summary><p>'+esc(d.available_opportunities)+' open opportunities analyzed against '+esc(d.total_students)+' student profiles.</p><p>'+esc(d.eligible_matches)+' verified eligible student / opportunity matches identified.'+esc(" "+(d.unverified_matches??0)+" unverified; "+(d.not_eligible_matches??0)+" not eligible.")+'</p></details></article><div class="grid-2 space-top"><article class="panel latest-external"><h2>Latest Real Opportunities</h2><p class="muted">Recently saved Adzuna listings. View the original job for current availability.</p><div class="stack">'+(latestCards(latest('external'))||'<p>No saved external opportunities yet. Search Adzuna to explore current listings.</p>')+'</div></article><article class="panel"><span class="eyebrow">YOUR NEXT STEP</span><h2>Find a match you can explain.</h2><p>Explore external opportunities and select a profile to see your match, eligibility and skills.</p><button class="primary-btn" id="dashboardJobsForMe">Jobs for Me</button><button class="ghost-btn" data-go="jobs">Explore opportunities</button><p class="muted">Source listings can be incomplete. Unverified eligibility remains distinct from eligible.</p></article></div>'+(latest('placement').length?'<details class="panel space-top"><summary>Placement cell records</summary><p class="muted">Manually entered/imported records; externally unverified availability.</p>'+latestCards(latest('placement'))+'</details>':'')+(latest('demo').length?'<details class="panel demo-section space-top"><summary>Demo Opportunities</summary><p>Fictional examples for matching and skill-gap demonstrations.</p>'+latestCards(latest('demo'))+'</details>':'');

  $("analyticsContent").innerHTML='<p class="dataset-scope">All stored records, including demo opportunities, profiles and offers. These are platform dataset statistics, not verified real-world placements or market statistics.</p>'+cards+charts+'<div class="analytics-grid"><article class="panel chart-panel"><h3>Department overview</h3>'+
    (d.department_statistics.length?'<div class="table-scroll"><table><thead><tr><th>Department</th><th>Students</th><th>Average CGPA</th></tr></thead><tbody>'+d.department_statistics.map(x=>"<tr><td>"+esc(x.department)+"</td><td>"+x.students+"</td><td>"+fmt(x.average_cgpa,2)+"</td></tr>").join("")+"</tbody></table></div>":'<p class="muted">No departments yet.</p>')+
    '</article><article class="panel risk-panel"><h3>Offer statistics</h3>'+metric("Average package (LPA)",fmt(d.placement_statistics.average_package_lpa,2),"Accepted / joined offers")+
    Object.entries(d.placement_statistics.by_status).map(([s,n])=>'<div class="risk-row"><span>'+esc(s)+"</span><b>"+n+"</b></div>").join("")+'</article></div><article class="panel space-top"><h3>Eligible students per job</h3>'+
    (d.eligible_students_per_job.map(j=>'<div class="risk-row"><span>'+esc(j.title)+"</span><b>"+j.eligible_students+"</b></div>").join("")||'<p class="muted">No jobs yet.</p>')+"</article>";
}
function renderStudents() {
  $("studentList").innerHTML=state.students.map(s=>'<button class="match-item '+(s.id===state.studentId?"selected":"")+'" data-student="'+s.id+'"><span class="avatar">'+esc(s.name.split(/\s+/).map(p=>p[0]).slice(0,2).join(""))+"</span><div><b>"+esc(s.name)+"</b><small>"+esc(s.department)+" / "+s.graduation_year+"</small></div><strong>"+s.cgpa+"</strong></button>").join("");
  renderProfile();
}
function renderProfile() {
  const s=student();
  $("currentStudentName").textContent=s?.name||"Select a student";
  $("currentStudentMeta").textContent=s?s.department+" / "+s.cgpa+" CGPA":"Student profile";
  $("studentInitials").textContent=s?s.name.split(/\s+/).map(p=>p[0]).slice(0,2).join(""):"?";
  if(!s){$("studentProfile").innerHTML='<p class="muted">Select an available student to view their profile.</p>';return;}
  $("studentProfile").innerHTML='<span class="eyebrow">SELECTED CANDIDATE</span><h2>'+esc(s.name)+'</h2><div class="hero-actions"><button class="small-btn dark" id="editProfile">Edit profile / review skills</button><button class="small-btn" id="suitableJobs">Find Suitable Jobs</button></div><dl class="profile-details">'+
    [["Email",s.email],["Phone",s.phone||"Not provided"],["Degree",s.degree||"Not provided"],["Branch",s.department],["Preferred career role",s.preferred_role||"Not provided"],["Professional experience",s.professional_experience_years==null?"Not provided":s.professional_experience_years+" years"],["Graduation",s.graduation_year],["CGPA",s.cgpa],["Coding",assessmentText(s.coding_score)],["Aptitude",assessmentText(s.aptitude_score)],["Communication",assessmentText(s.communication_score)]].map(([k,v])=>"<dt>"+k+"</dt><dd>"+esc(v)+"</dd>").join("")+
    "</dl><p class='muted'>Assessment scores are self-reported. The current backend stores omitted scores as 0; a stored zero does not confirm that an assessment was taken.</p><h3>Skills</h3>"+tags(s.skills)+"<h3>Resume-extracted skills</h3>"+tags(s.extracted_skills)+"<h3>Certifications</h3>"+list(s.certifications)+"<h3>Projects</h3>"+list(s.projects)+
    '<div class="hero-actions"><button class="primary-btn" data-go="jobs">Choose a job</button><button class="ghost-btn" data-go="offers">View offers</button></div>'+
    '<div class="modal-section"><h3>Resume</h3><p class="muted">'+esc(s.resume_filename||"No resume uploaded.")+'</p><form id="resumeForm"><label>PDF, DOCX or UTF-8 TXT (up to 5 MiB)<input id="resumeFile" name="file" type="file" accept=".pdf,.docx,.txt" required></label><button class="small-btn dark" type="submit">Upload resume</button></form>'+
    (s.resume_filename?'<button class="small-btn" id="downloadResume">Download resume</button>':"")+'<div id="resumeState" class="api-state" role="status"></div></div>';
}

function renderCompanies() {
  $("companyList").innerHTML=state.companies.map(c=>'<button class="company-tile" data-company="'+c.id+'"><span class="logo">'+esc(c.name[0])+"</span><b>"+esc(c.name)+"</b><small>Company ID: "+c.id+"</small><small>"+esc(c.industry||"Industry not provided")+"</small><small>"+esc(c.location||"Location not provided")+"</small></button>").join("");

}
function openCompany(id,trigger) {
  const c=state.companies.find(c=>c.id===id);if(!c)return;
  modalTrigger=trigger;
  $("companyModalBody").innerHTML='<span class="eyebrow">COMPANY SNAPSHOT</span><div class="modal-company"><span class="logo">'+esc(c.name[0])+'</span><div><h2 id="modalCompany">'+esc(c.name)+"</h2><p>"+esc(c.industry)+"</p></div></div><p>"+esc(c.description||"No description provided.")+'</p><p class="muted">'+esc(c.location)+"</p><p>"+esc(c.website||"No website listed")+'</p><div class="modal-section"><h3>Jobs</h3>'+
    (state.ready.jobs?state.jobs.filter(j=>j.company_id===id).map(j=>'<button class="match-item" data-job="'+j.id+'">'+esc(j.title)+"</button>").join("")||'<p class="muted">No jobs listed.</p>':'<p class="muted">Jobs have not loaded. Retry on the Jobs page.</p>')+"</div>";
  $("companyModal").classList.add("show");$("closeModal").focus();
}
function closeModal() {$("companyModal").classList.remove("show");modalTrigger?.focus();}
function syncSelections() {
  ["matchStudent","placementStudent"].forEach(id=>{
    $(id).innerHTML='<option value="">Select a student</option>'+state.students.map(s=>'<option value="'+s.id+'">'+esc(s.name)+"</option>").join("");
    $(id).value=state.studentId||"";$(id).disabled=!state.ready.students||!state.students.length;
  });
  ["matchJob","placementJob"].forEach(id=>{
    $(id).innerHTML='<option value="">Select a job</option>'+state.jobs.map(j=>'<option value="'+j.id+'">'+esc(j.title+" / "+j.company.name+" / "+sourceLabel(j.source))+"</option>").join("");
    $(id).value=state.jobId||"";$(id).disabled=!state.ready.jobs||!state.jobs.length;
  });
  updateButtons();
}
function updateButtons() {
  const valid=Boolean(student()&&job()&&state.ready.students&&state.ready.jobs);
  $("eligibilityBtn").disabled=$("fitBtn").disabled=!valid||state.busy;
  $("placementFields").disabled=!state.ready.students||!state.ready.jobs||!state.students.length||!state.jobs.length||state.placing;
}
function clearMatch() {
  if(typeof invalidateGapChoices==="function")invalidateGapChoices();
  state.version++;matchController?.abort();state.busy=false;state.fit=state.gap=state.eligibility=null;
  $("matchingResult").innerHTML=$("readinessResult").innerHTML=$("gapResult").innerHTML="";
  const errors=[state.errors.students,state.errors.jobs].filter(Boolean);
  const message=errors.length?errors.join(" "):"Select a student and opportunity, then check eligibility or generate a fit score.";
  notice("matchingState",message,errors.length?"error":"",errors.length?"matching-data":"");
  notice("readinessState",errors.length?message:"No fit score generated for the current selection.",errors.length?"error":"",errors.length?"matching-data":"");
  notice("gapState",errors.length?message:"Generate a fit score to load this candidate's job-specific skill gaps.",errors.length?"error":"",errors.length?"matching-data":"");
  updateButtons();
}
function selectStudent(id) {
  if(typeof invalidateOpportunity==="function")invalidateOpportunity();state.studentId=state.students.some(s=>s.id===id)?id:null;rememberProfile(state.studentId);clearMatch();syncSelections();renderStudents();renderPlacements();renderJobs();if(typeof renderApplications==="function")renderApplications();}
function selectJob(id) {state.jobId=state.jobs.some(j=>j.id===id)?id:null;clearMatch();syncSelections();renderJobs();}
function eligibilityHTML(e) {
  const record=state.jobs.find(j=>j.id===e.job_id)||state.jobCatalog[e.job_id];
  return '<article class="panel space-top">'+sourceBadge(record)+' <span class="status-pill '+eligibilityClass(e)+'">'+eligibilityLabel(e)+"</span><h3>"+esc(studentName(e.student_id))+" / "+esc(jobName(e.job_id))+"</h3><p>"+esc(state.jobs.find(j=>j.id===e.job_id)?.company.name||"")+"</p>"+list(e.reasons)+
    (e.missing_requirements.length?"<h4>Missing requirements</h4>"+list(e.missing_requirements.map(r=>r.requirement==="required_skills"?"Required skills: "+r.missing.join(", "):r.requirement+": expected "+r.expected+"; actual "+r.actual)):"")+"</article>";
}
function skillGroups(g) {
  return (g.skill_match_percentage==null?'<p class="external-notice">No required skills extracted. Skill coverage unavailable.</p>':"")+'<div class="grid-2"><article class="panel"><h3>Matched required skills</h3>'+tags(g.matched_skills,"matched")+"<h3>Matched preferred skills</h3>"+tags(g.matched_preferred_skills,"matched")+'</article><article class="panel"><h3>Missing required skills</h3>'+tags(g.missing_skills,"missing")+"<h3>Missing preferred skills</h3>"+tags(g.missing_preferred_skills,"missing")+"</article></div>";
}
function renderMatch() {
  const f=state.fit,g=state.gap;
  $("matchingResult").innerHTML=eligibilityHTML(state.eligibility)+'<div class="insight-grid space-top">'+metric(f.provisional?"Provisional Fit Score":"Overall Fit Score",fmt(f.overall_fit_score)+" / 100")+metric("Skill Match",coverageText(f.skill_match_percentage))+"</div>"+skillGroups(f)+
    '<div class="grid-2"><article class="panel"><h3>Strengths</h3>'+list(f.strengths)+'</article><article class="panel"><h3>Improvement suggestions</h3>'+list(f.improvement_suggestions,"No suggestions returned.")+'</article></div><div class="hero-actions"><button class="primary-btn" data-go="readiness">See score explanation</button><button class="ghost-btn" data-go="roadmap">Show skill gaps</button></div>';
  const labels={skills:"Skills",cgpa:"CGPA",coding:"Coding",aptitude:"Aptitude",communication:"Communication",portfolio:"Portfolio"};
  $("readinessResult").innerHTML=sourceBadge(job())+'<p class="selection-context">'+esc(studentName(f.student_id)+" / "+jobName(f.job_id)+" / "+job().company.name)+'</p><div class="readiness-layout"><article class="panel big-score"><div class="score-orb" style="--score:'+f.overall_fit_score+'%"><strong>'+fmt(f.overall_fit_score)+'</strong><small>/ 100</small></div><span class="status-pill '+eligibilityClass(f.eligibility)+'">'+eligibilityLabel(f.eligibility)+'</span><h2>'+(f.provisional?"Provisional fit":"Student / opportunity fit")+'</h2><p class="muted">AI-Assisted Explainable Matching: hackathon heuristic</p></article><article class="panel factor-panel"><h3>Score breakdown</h3>'+
    Object.entries(f.explanation.components).map(([key,c])=>'<div class="factor"><div><span>'+esc(labels[key]||key)+"</span><b>"+componentText(c.score)+' / 100</b></div><i><u style="width:'+(c.score??0)+'%"></u></i><p class="muted">Weight: '+c.weight_percent+"% / Contribution: "+fmt(c.contribution,2)+" points</p></div>").join("")+"</article></div>"+
    '<details class="panel space-top" open><summary>How is this score calculated?</summary><p>'+esc(f.explanation.formula)+'</p><p class="muted">'+esc(f.explanation.limitations)+"</p></details>";
  $("gapResult").innerHTML='<article class="panel roadmap-board space-top"><div class="roadmap-head"><div><span class="eyebrow">TARGET JOB</span><h2>'+esc(jobName(g.job_id))+"</h2><p>"+esc(studentName(g.student_id))+'</p></div><span class="demo-badge">'+coverageText(g.skill_match_percentage)+' required skill coverage</span></div><h3>Recommended skills to learn</h3>'+tags(g.recommended_skills_to_learn,"missing")+"</article>"+skillGroups(g)+'<div class="gap-grid space-top">'+
    (g.priorities.map((p,i)=>'<article class="gap-card"><span class="gap-number">'+String(i+1).padStart(2,"0")+"</span><h3>"+esc(p.skill)+'</h3><span class="status-pill '+(p.priority==="high"?"not-ready":"ready")+'">'+esc(p.priority)+" priority</span><p>"+esc(p.reason)+"</p></article>").join("")||'<article class="panel"><h3>No skill gaps found for this job.</h3></article>')+"</div>";
}
async function runMatch(full) {
  if(!student()||!job())return;
  clearMatch();const version=state.version;matchController=new AbortController();const signal=matchController.signal;
  state.busy=true;updateButtons();["matchingState","readinessState","gapState"].forEach(id=>notice(id,"Loading candidate-job results...","loading"));
  const query="?"+new URLSearchParams({student_id:state.studentId,job_id:state.jobId});
  try {
    if(full) {
      const [e,f,g]=await Promise.all([api("/matching/eligibility"+query,{signal}),api("/matching/fit"+query,{signal}),api("/matching/skill-gap"+query,{signal})]);
      if(version!==state.version)return;
      state.eligibility=e;state.fit=f;state.gap=g;renderMatch();["matchingState","readinessState","gapState"].forEach(id=>notice(id,""));
    } else {
      const e=await api("/matching/eligibility"+query,{signal});if(version!==state.version)return;
      state.eligibility=e;$("matchingResult").innerHTML=eligibilityHTML(e);
      notice("matchingState","Eligibility checked. Generate Fit Score for the explanation and skill gaps.","success");
      notice("readinessState","Generate Fit Score to see the breakdown.");notice("gapState","Generate Fit Score to see this job's skill gaps.");
    }
  } catch(e) {
    if(version!==state.version)return;matchController.abort();
    ["matchingState","readinessState","gapState"].forEach(id=>notice(id,e.message,"error",full?"fit":"eligibility"));
  } finally {if(version===state.version){state.busy=false;updateButtons();}}
}

function renderPlacements() {
  if(!state.ready.placements){$("placementList").innerHTML="";return;}
  const records=(!isOfficer()||$("placementFilter").value==="selected")?state.placements.filter(p=>p.student_id===state.studentId):state.placements;
  $("placementList").innerHTML=records.length?records.map(p=>'<article class="offer-card panel">'+sourceBadge(state.jobCatalog[p.job_id]||state.jobs.find(j=>j.id===p.job_id))+'<div class="offer-top"><div><span class="logo">'+esc(companyName(p.company_id)[0])+'</span><div><span class="eyebrow">'+esc(p.status)+"</span><h2>"+esc(studentName(p.student_id))+'</h2><p class="muted">'+esc(companyName(p.company_id)+" / "+jobName(p.job_id))+'</p></div></div><span class="offer-amount">'+fmt(p.package,2)+' LPA</span></div><p class="muted">Offer: '+esc(p.offer_date||"Not provided")+" / Joining: "+esc(p.joining_date||"Not provided")+'</p><form data-placement-status="'+p.id+'"><label>Status<select name="status" aria-label="Status for placement '+p.id+'">'+statuses.map(s=>'<option'+(s===p.status?" selected":"")+">"+s+"</option>").join("")+'</select></label><button class="small-btn dark" type="submit">Save status</button><div class="api-state" role="status" id="statusMessage'+p.id+'"></div></form></article>').join(""):'<article class="panel"><p class="muted">No placement records for this selection.</p></article>';
}
const resources={students:["studentsState","studentList"],jobs:["jobsState","jobList"],companies:["companiesState","companyList"],placements:["placementState","placementList"]};
const loads={};
async function loadResource(name) {
  if(loads[name])return loads[name];
  loads[name]=(async()=>{
    const [messageId,contentId]=resources[name];
    state.ready[name]=false;state[name]=[];delete state.errors[name];$(contentId).innerHTML="";
    if(name==="students")renderProfile();
    syncSelections();notice(messageId,"Loading "+name+"...","loading");
    try {
      state[name]=await getAll(name==="jobs"?"/opportunities":"/"+name);state.ready[name]=true;
      if(name==="jobs")state.jobs.forEach(j=>state.jobCatalog[j.id]=j);
      if(name==="placements"){
        const ids=[...new Set(state.placements.map(p=>p.job_id))];
        await Promise.all(ids.map(async id=>{state.jobCatalog[id]=await api("/opportunities/"+id);}));
      }
      if(name==="students"&&!student())state.studentId=null;
      if(name==="jobs"&&!job())state.jobId=null;
      notice(messageId,state[name].length?"":"No "+name+" records available.");
      if(name==="students")renderStudents();
      if(name==="jobs")renderJobs();
      if(name==="companies")renderCompanies();
    } catch(e) {state.errors[name]=e.message;notice(messageId,e.message,"error",name);}
    finally {
      syncSelections();renderPlacements();renderDashboard();
      if(typeof refreshSuggestions==="function")refreshSuggestions();
      if(name==="students"||name==="jobs"){clearMatch();renderJobs();}
    }
  })();
  try {await loads[name];} finally {delete loads[name];}
}
async function loadDashboard() {
  notice("dashboardState","Loading dashboard...","loading");notice("analyticsState","Loading analytics...","loading");
  $("dashboardContent").innerHTML=$("analyticsContent").innerHTML="";state.dashboard=null;
  try {
    state.dashboard=await api("/analytics/dashboard");renderDashboard();
    const empty=!state.dashboard.total_students&&!state.dashboard.total_jobs&&!state.dashboard.total_companies;
    notice("dashboardState",empty?"No placement data yet.":"");notice("analyticsState",empty?"No placement data yet.":"");
  } catch(e) {notice("dashboardState",e.message,"error","dashboard");notice("analyticsState",e.message,"error","dashboard");}
}
async function health() {
  try {await api("/health",{root:true});$("connectionStatus").textContent="Backend online";}
  catch {$("connectionStatus").textContent="Backend unavailable";}
}
async function uploadResume(form) {
  const s=student(),file=form.elements.file.files[0];if(!s||!file)return;
  if(file.size>5*1024*1024){notice("resumeState","Resume exceeds the 5 MiB limit.","error");return;}
  const button=form.querySelector("button");button.disabled=true;notice("resumeState","Uploading and extracting skills...","loading");
  const data=new FormData();data.append("file",file);let uploaded=false;
  try {
    const result=await api("/students/"+s.id+"/resume",{method:"POST",body:data});uploaded=true;
    if(state.studentId===s.id)clearMatch();
    if(typeof invalidateDiscovery==="function")invalidateDiscovery("Profile skills changed. Refresh recommendations.");
    invalidateOpportunity();
    const updated=await api("/students/"+s.id);state.students=state.students.map(x=>x.id===updated.id?updated:x);
    const text="Resume uploaded for "+s.name+". Extracted skills: "+(result.extracted_skills.join(", ")||"None detected.")+(result.warning?" "+result.warning:"");
    if(state.studentId===s.id){renderProfile();clearMatch();renderJobs();notice("resumeState",text+" Generate a fresh fit score.",result.warning?"warning":"success");}
    toast(text);await loadDashboard();
  } catch(e) {
    const text=(uploaded?"Resume saved, but profile refresh failed. Retry the student list. ":"")+e.message;
    if(state.studentId===s.id)notice("resumeState",text,"error");toast(text);
  } finally {button.disabled=false;}
}
async function downloadResume(button) {
  const s=student();if(!s)return;button.disabled=true;
  try {
    const blob=await api("/students/"+s.id+"/resume/download",{binary:true}),url=URL.createObjectURL(blob),a=document.createElement("a");
    a.href=url;a.download=s.resume_filename;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
    if(state.studentId===s.id)notice("resumeState","Resume downloaded.","success");
  } catch(e) {if(state.studentId===s.id)notice("resumeState",e.message,"error");}
  finally {button.disabled=false;}
}
async function createPlacement(form) {
  const studentId=Number($("placementStudent").value),jobId=Number($("placementJob").value),j=state.jobs.find(j=>j.id===jobId);
  if(!studentId||!j)return;
  const f=new FormData(form),body={student_id:studentId,job_id:jobId,company_id:j.company_id,status:f.get("status"),package:Number(f.get("package")),offer_date:f.get("offer_date")||null,joining_date:f.get("joining_date")||null};
  state.placing=true;updateButtons();notice("placementFormState","Saving offer...","loading");
  try {
    const result=await api("/placements",{method:"POST",json:body});notice("placementFormState","Placement #"+result.id+" created.","success");
    await Promise.all([loadResource("placements"),loadDashboard(),loadApplications()]);
  } catch(e) {notice("placementFormState",e.message,"error");}
  finally {state.placing=false;updateButtons();}
}
async function updateStatus(form) {
  const id=Number(form.dataset.placementStatus),status=form.elements.status.value;form.querySelector("button").disabled=true;
  notice("statusMessage"+id,"Saving status...","loading");
  try {
    const updated=await api("/placements/"+id+"/status",{method:"PATCH",json:{status}});
    state.placements=state.placements.map(p=>p.id===id?updated:p);renderPlacements();loadApplications();notice("statusMessage"+id,"Status saved.","success");await loadDashboard();
  } catch(e) {notice("statusMessage"+id,e.message,"error");}
  finally {form.querySelector("button").disabled=false;}
}
async function retry(name) {
  if(name==="dashboard")await loadDashboard();
  else if(name==="fit"||name==="eligibility")await runMatch(name==="fit");
  else if(name==="matching-data")await Promise.all([loadResource("students"),loadResource("jobs")]);
  else await loadResource(name);
  health();
}
document.addEventListener("click",e=>{
  const b=e.target.closest("button, a");if(!b)return;
  if(b.dataset.go||b.dataset.section){e.preventDefault();go(b.dataset.go||b.dataset.section);}
  if(b.dataset.student)selectStudent(Number(b.dataset.student));
  if(b.dataset.job){closeModal();openOpportunity(Number(b.dataset.job));}
  if(b.dataset.company)openCompany(Number(b.dataset.company),b);
  if(b.dataset.retry)retry(b.dataset.retry);
  if(b.id==="eligibilityBtn")runMatch(false);
  if(b.id==="fitBtn")runMatch(true);
  if(b.id==="studentBtn")go("students");
  if(b.id==="helpBtn")toast("Select your profile, explore opportunities, review your fit, then express interest.");
  if(b.id==="closeModal")closeModal();
  if(b.id==="downloadResume")downloadResume(b);
});
document.addEventListener("change",e=>{
  if(e.target.id==="matchStudent")selectStudent(Number(e.target.value));
  if(e.target.id==="matchJob")selectJob(Number(e.target.value));
  if(e.target.id==="placementFilter")renderPlacements();
});
document.addEventListener("submit",e=>{
  e.preventDefault();
  if(e.target.id==="resumeForm")uploadResume(e.target);
  if(e.target.id==="placementForm")createPlacement(e.target);
  if(e.target.dataset.placementStatus)updateStatus(e.target);
});
$("companyModal").addEventListener("click",e=>{if(e.target===$("companyModal"))closeModal();});
document.addEventListener("keydown",e=>{
  if(!$("companyModal").classList.contains("show"))return;
  if(e.key==="Escape")closeModal();
  if(e.key==="Tab"){
    const a=[...$("companyModal").querySelectorAll("button,a[href]")];
    if(e.shiftKey&&document.activeElement===a[0]){e.preventDefault();a.at(-1).focus();}
    else if(!e.shiftKey&&document.activeElement===a.at(-1)){e.preventDefault();a[0].focus();}
  }
});
window.addEventListener("hashchange",()=>go(location.hash.slice(1)));
window.addEventListener("DOMContentLoaded",()=>{clearMatch();go(location.hash.slice(1)||"home");health();loadDashboard();Object.keys(resources).forEach(loadResource);});
