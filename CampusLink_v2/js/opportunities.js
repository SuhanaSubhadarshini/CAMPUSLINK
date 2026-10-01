/* Opportunity discovery and the minimal interest-to-offer workflow. */
const sourceLabel=s=>({adzuna:"Adzuna",demo:"Demo Opportunity",manual:"Manual entry",json_import:"JSON import",legacy:"Placement database record"}[s]||s);
const isOfficer=()=>$("roleSelect").value==="officer";
// Source is assigned by the backend. Never infer provenance from a title/company.
const opportunityKind=j=>j.source==="adzuna"?"external":j.source==="demo"?"demo":"placement";
function sourceBadge(j){
  if(!j)return "";
  const kind=opportunityKind(j);
  return '<span class="status-pill source-badge source-'+kind+'">'+esc(kind==="demo"?"DEMO":kind==="external"?"REAL / EXTERNAL - Adzuna":sourceLabel(j.source))+'</span>';
}
function opportunitySections(rows,render,getJob=x=>x,options={}){
  const groups={external:[],placement:[],demo:[]};rows.forEach(r=>groups[opportunityKind(getJob(r))].push(r));
  const body=kind=>'<div class="'+(options.layout||"gap-grid")+'">'+groups[kind].map(render).join("")+'</div>';
  let html='<section class="source-section" data-source-group="external"><h2>Real Opportunities</h2><p>Current opportunities from connected job sources</p><p class="muted">Saved Adzuna listings. Check the original job for current availability.</p>'+(groups.external.length?body('external'):'<p class="source-empty">No saved external opportunities match this view. Search Adzuna by keyword and location, then import a listing to analyze it.</p>')+'</section>';
  if(groups.placement.length)html+='<section class="source-section placement-section" data-source-group="placement"><h2>Placement Cell Opportunities</h2><p class="muted">Records entered or imported by the placement cell; availability has not been verified by an external source.</p>'+body('placement')+'</section>';
  if(groups.demo.length)html+='<details class="source-section demo-section" data-source-group="demo"'+((options.demoOpen??isOfficer())?' open':'')+'><summary>Demo Opportunities <span class="demo-count">'+groups.demo.reduce((n,r)=>n+(options.count?options.count(r):1),0)+' samples</span></summary><p>Sample opportunities used to demonstrate CAMPUSLINK&#39;s matching and skill-gap analysis</p><p class="muted">Fictional examples, not live vacancies.</p>'+body('demo')+'</details>';
  return html;
}
let opportunityMatchesVersion=0,opportunityMatchesController;
function cardMatchHTML(f){
  return '<p class="match-percent">'+(f.provisional?'Provisional match: ':'Match: ')+fmt(f.overall_fit_score)+'%</p><span class="status-pill '+eligibilityClass(f.eligibility)+'">'+eligibilityLabel(f.eligibility)+'</span><p class="muted">Fit score, not a hiring probability or eligibility decision.</p><h4>Matched skills</h4>'+tags([...new Set([...f.matched_skills,...f.matched_preferred_skills])],'matched')+'<h4>Missing required skills</h4>'+(f.skill_match_percentage==null?'<p>Required skills not extracted.</p>':tags(f.missing_skills,'missing'))+'<p>Required skill coverage: '+coverageText(f.skill_match_percentage)+'</p>';
}
async function loadOpportunityCardMatches(rows){
  const version=++opportunityMatchesVersion;opportunityMatchesController?.abort();
  const s=student();if(!s)return;
  opportunityMatchesController=new AbortController();const signal=opportunityMatchesController.signal;
  const external=rows.filter(j=>j.source==="adzuna");let next=0;
  async function worker(){
    while(next<external.length&&version===opportunityMatchesVersion){
      const j=external[next++],target=document.querySelector('#jobList [data-card-match="'+j.id+'"]');
      if(!target)continue;
      target.innerHTML='<p class="muted">Analyzing your match...</p>';
      try{
        const f=await api('/matching/fit?'+new URLSearchParams({student_id:s.id,job_id:j.id}),{signal});
        if(version===opportunityMatchesVersion&&state.studentId===s.id&&target.isConnected)target.innerHTML=cardMatchHTML(f);
      }catch(e){if(version===opportunityMatchesVersion&&target.isConnected)target.innerHTML='<p class="api-state error">'+esc(e.message)+'</p><button class="small-btn" data-refresh-card-matches>Retry match analysis</button>';}
    }
  }
  await Promise.all(Array.from({length:Math.min(3,external.length)},worker));
}
let applications=[], applicationError="", detailVersion=0, detailJobId=null, filterVersion=0;
function applyRole(){
  document.body.dataset.view=$("roleSelect").value;
  document.querySelectorAll("[data-role]").forEach(e=>e.hidden=e.dataset.role!==$("roleSelect").value);
  $("placementForm").closest("article").hidden=!isOfficer();
  $("placementFilter").value=isOfficer()?"all":"selected";
  $("placementFilter").closest("label").hidden=!isOfficer();
  try{localStorage.setItem("campuslink.view",$("roleSelect").value);}catch{}
  const profileLabel=isOfficer()?"Student Profiles":"My Profile";
  document.querySelector('[data-section="students"]').innerHTML='<span class="nav-icon">P</span>'+profileLabel;
  $("students").querySelector("h1").textContent=profileLabel;
  $("students").querySelector(".page-title p").textContent=isOfficer()?"Select a student to analyze their skills, opportunities and placement readiness.":"Review your selected profile, skills and resume, then find suitable opportunities. You can switch profiles below.";
  $("myProfile").textContent=isOfficer()?"Selected profile":"My Profile";
  $("addStudent").textContent=isOfficer()?"Add student":"Create My Profile";
  renderPlacements();renderApplications();renderJobs();renderDashboard();
  document.querySelectorAll('[data-source-group="demo"]').forEach(e=>{if(e.tagName==="DETAILS")e.open=isOfficer();});
  if(!isOfficer()&&["admin","companies","analytics","matches"].includes(location.hash.slice(1)))go("home");
}
function opportunityCard(j){
  const external=j.source==="adzuna";
  return '<article class="gap-card opportunity-card '+(j.source==="demo"?'demo-card':'')+'" data-opportunity-source="'+esc(opportunityKind(j))+'"><span class="eyebrow">'+esc(j.company.name)+'</span><h3>'+esc(j.title)+'</h3>'+sourceBadge(j)+'<p>'+esc(j.location||"Location not specified")+(j.job_type!=="unknown"?' / '+esc(j.job_type):'')+'</p>'+(j.vacancy_count!=null?'<p>'+j.vacancy_count+' reported openings</p>':'')+(external?'<div data-card-match="'+j.id+'"><p>Select a profile to see your match, eligibility and skills.</p></div>':'<h4>Required skills</h4>'+tags(j.required_skills))+(j.source==="demo"?'<p class="muted">Fictional sample for matching demonstrations.</p>':'')+adzunaAttribution(j)+'<div class="hero-actions"><button class="primary-btn" data-job="'+j.id+'">'+(external?'View Match / Details':'View Details')+'</button>'+originalListing(j)+(isOfficer()?'<button class="ghost-btn" data-candidates="'+j.id+'">Find Suitable Candidates</button>':'')+'</div></article>';
}
function showOpportunityRows(rows){
  const requestedDemo=$("opportunityFilters").elements.source.value==="demo";
  $("jobList").innerHTML=(!rows.length&&state.ready.jobs?'<p>No available opportunities match these filters.</p>':'')+opportunitySections(rows,opportunityCard,x=>x,{demoOpen:isOfficer()||requestedDemo});
  loadOpportunityCardMatches(rows);
}
function renderJobs(){
  const f=new FormData($("opportunityFilters")),q=String(f.get("q")||"").toLowerCase(),location=String(f.get("location")||"").toLowerCase();
  const rows=state.jobs.filter(j=>j.status==="open"&&(!q||(j.title+" "+j.company.name).toLowerCase().includes(q))&&(!location||j.location.toLowerCase().includes(location))&&(!f.get("job_type")||j.job_type===f.get("job_type"))&&(!f.get("source")||j.source===f.get("source")));
  showOpportunityRows(rows);
}
async function filterOpportunities(){
  const version=++filterVersion;
  notice("jobsState","Filtering opportunities...","loading");
  const q=new URLSearchParams(new FormData($("opportunityFilters")));
  try{
    const rows=await getAll("/opportunities?"+q);
    if(version!==filterVersion)return;
    showOpportunityRows(rows);
    notice("jobsState",rows.length+" stored opportunities match these filters; sources are shown separately.");
  }catch(e){if(version===filterVersion)notice("jobsState",e.message,"error");}
}
function invalidateOpportunity(){
  detailVersion++;$("opportunityDetail").innerHTML="";
  if(detailJobId)notice("opportunityState","Profile changed. Reopen the opportunity to analyze the current profile.");
}
async function openOpportunity(id){
  const version=++detailVersion;detailJobId=id;go("opportunity");
  $("opportunityDetail").innerHTML="";notice("opportunityState","Loading opportunity and analysis...","loading");
  try{
    const j=await api("/opportunities/"+id);if(version!==detailVersion)return;
    if(!state.jobs.some(x=>x.id===id))state.jobs.push(j);else state.jobs=state.jobs.map(x=>x.id===id?j:x);
    selectJob(id);
    const sourceURL=j.source_url&&/^https?:\/\//i.test(j.source_url)?'<a href="'+esc(j.source_url)+'" target="_blank" rel="noopener noreferrer">View Original Listing</a>':"";
    $("opportunityDetail").innerHTML='<div class="page-title"><span class="eyebrow">'+esc(j.company.name)+'</span><h1>'+esc(j.title)+'</h1><p>'+esc(j.description||"No description provided.")+'</p></div><article class="panel">'+sourceBadge(j)+'<p>'+esc(j.status)+'</p><dl class="profile-details">'+
      [["Location",j.location||"Not provided"],["Type",j.job_type],["Openings",j.vacancy_count??"Not provided"],["Salary / stipend",j.salary_stipend||"Not provided"],["Minimum CGPA",j.source==="adzuna"&&!j.minimum_cgpa?"Not verified":j.minimum_cgpa],["Graduation year",j.graduation_year??(j.source==="adzuna"?"See extracted requirements":"Any year")],["Degree / branch",j.source==="adzuna"?"See extracted requirements":"No restriction configured"]].map(([k,v])=>'<dt>'+k+'</dt><dd>'+esc(v)+'</dd>').join("")+'</dl>'+(isOfficer()?'<details class="source-technical"><summary>Source record details</summary><p>Reference: '+esc(j.source_reference||'Not provided')+'</p><p>Recorded: '+esc(j.created_at||'Unknown')+'</p></details>':'')+sourceURL+externalFacts(j)+externalNotice(j)+adzunaAttribution(j)+'<h3>Required skills</h3>'+(j.source==="adzuna"&&!j.required_skills.length?"<p>No requirements extracted</p>":tags(j.required_skills))+'<h3>Preferred skills</h3>'+tags(j.preferred_skills)+(isOfficer()?'<button class="primary-btn" data-candidates="'+j.id+'">Find Suitable Candidates</button>':'')+'</article><div id="opportunityAnalysis" class="space-top"></div>';
    const s=student();
    if(!s){$("opportunityAnalysis").innerHTML='<article class="panel"><h2>How does this opportunity fit you?</h2><p>Select or create your profile first.</p><button class="primary-btn" data-go="students">Choose my profile</button></article>';notice("opportunityState","");return;}
    const query="?"+new URLSearchParams({student_id:s.id,job_id:id});
    const [e,g]=await Promise.all([api("/matching/eligibility"+query),api("/matching/skill-gap"+query)]);
    const f=await api("/matching/fit"+query);
    if(version!==detailVersion)return;
    state.eligibility=e;state.gap=g;state.fit=f;
    if(f){renderMatch();["matchingState","readinessState","gapState"].forEach(x=>notice(x,""));}
    else{$("gapResult").innerHTML=skillGroups(g);notice("gapState",coverageText(g.skill_match_percentage)+" required skill coverage for "+s.name+" / "+j.title);}
    $("opportunityAnalysis").innerHTML=externalNotice(j)+eligibilityHTML(e)+(f?'<article class="panel space-top"><h2>'+(f.provisional?"Provisional fit score: ":"Fit score: ")+''+fmt(f.overall_fit_score)+' / 100</h2><p>AI-Assisted Explainable Matching</p><div class="table-scroll"><table><thead><tr><th>Component</th><th>Score / 100</th><th>Weight</th><th>Contribution</th></tr></thead><tbody>'+Object.entries(f.explanation.components).map(([k,c])=>'<tr><td>'+esc(k)+'</td><td>'+componentText(c.score)+'</td><td>'+c.weight_percent+'%</td><td>'+fmt(c.contribution,2)+'</td></tr>').join("")+'</tbody></table></div><p>'+esc(f.explanation.formula)+'</p><p class="muted">'+esc(f.explanation.limitations)+'</p></article>':'<p>Eligibility requirements are not met. Review the gaps below.</p>')+skillGroups(g)+'<p>Required skill coverage: '+coverageText(g.skill_match_percentage)+'</p><div class="hero-actions">'+(e.eligible&&j.status==="open"?'<button class="primary-btn" id="expressInterest" data-student-id="'+s.id+'" data-job-id="'+id+'">Express interest</button>':'')+'<button class="ghost-btn" data-go="offers">Applications / Placements</button></div><div id="interestState" class="api-state" role="status"></div>';
    notice("opportunityState","");
  }catch(e){if(version===detailVersion)notice("opportunityState",e.message+" Reopen this opportunity to retry.","error");}
}
async function showJobsForMe(){if(student())await discover("jobs",state.studentId);else{go("students");notice("studentsState","Select or create your profile to find suitable opportunities.");}}
async function loadApplications(){
  notice("applicationState","Loading applications...","loading");
  try{applications=await getAll("/applications");applicationError="";renderApplications();}
  catch(e){applications=[];applicationError=e.message;renderApplications();}
}
function renderApplications(){
  const rows=isOfficer()?applications:applications.filter(a=>a.student_id===state.studentId);
  notice("applicationState",applicationError||(!isOfficer()&&!student()?"Select a profile to see its applications.":""),applicationError?"error":"");
  $("applicationList").innerHTML=rows.map(a=>'<article class="application-card">'+sourceBadge(state.jobs.find(j=>j.id===a.job_id)||state.jobCatalog[a.job_id])+'<h3>'+esc(a.job_title)+' / '+esc(a.company_name)+'</h3><p>'+esc(a.student_name)+' / '+'<span class="status-pill stage-'+esc(a.status)+'">'+esc(a.status)+'</span>'+(a.placement_status?' / <span class="status-pill stage-'+esc(a.placement_status)+'">Offer: '+esc(a.placement_status)+'</span>':'')+'</p><small>Interest recorded: '+esc(a.created_at)+'</small>'+(isOfficer()?'<form data-application-status="'+a.id+'"><label>Application stage<select name="status">'+["interested","shortlisted","interview","selected","rejected","withdrawn"].map(s=>'<option'+(s===a.status?' selected':'')+'>'+s+'</option>').join("")+'</select></label><button class="small-btn dark" type="submit">Save stage</button></form>'+(a.status==="selected"&&!a.placement_id?'<button class="ghost-btn" data-offer-student="'+a.student_id+'" data-offer-job="'+a.job_id+'">Record offer</button>':''):'')+'</article>').join("")||(!applicationError?'<p class="muted">No interest recorded for this view yet.</p>':"");
}
async function expressInterest(button){
  button.disabled=true;
  try{await api("/applications",{method:"POST",json:{student_id:Number(button.dataset.studentId),job_id:Number(button.dataset.jobId)}});notice("interestState","Interest recorded. Your placement cell can now shortlist this application.","success");await Promise.all([loadApplications(),loadDashboard()]);}
  catch(e){notice("interestState",e.message,"error");button.disabled=false;}
}
async function loadAdmin(){
  notice("adminState","Loading availability...","loading");
  try{const rows=await getAll("/opportunities?status=all");$("adminOpportunities").innerHTML=rows.map(j=>'<div class="risk-row"><span>'+esc(j.title)+' / '+esc(j.company.name)+' / '+esc(sourceLabel(j.source))+' / '+esc(j.status)+'</span><button class="small-btn" data-availability="'+j.id+'" data-status="'+(j.status==="open"?'closed':'open')+'">'+(j.status==="open"?'Close':'Reopen')+'</button></div>').join("")||'<p>No opportunities yet.</p>';notice("adminState","");}
  catch(e){notice("adminState",e.message,"error");}
}
async function importOpportunities(){
  const b=$("importForm").querySelector("button");b.disabled=true;notice("importState","Importing...","loading");
  try{const payload=JSON.parse($("importJSON").value),rows=await api("/opportunities/import",{method:"POST",json:payload});notice("importState",rows.length+" opportunities imported. Source: JSON import.","success");invalidateDiscovery();invalidateOpportunity();await Promise.all([loadResource("jobs"),loadDashboard(),loadAdmin()]);}
  catch(e){notice("importState",e.message,"error");}finally{b.disabled=false;}
}
document.addEventListener("click",async e=>{
  const b=e.target.closest("button,a");if(!b)return;
  if(["jobsForMe","opportunityJobsForMe","dashboardJobsForMe"].includes(b.id)||(b.dataset.section==="discovery"))showJobsForMe();
  if(b.id==="refreshApplications"||b.dataset.section==="offers")loadApplications();
  if(b.id==="expressInterest")expressInterest(b);
  if(b.id==="refreshAdmin"||b.dataset.section==="admin")loadAdmin();
  if(b.dataset.availability){
    b.disabled=true;
    try{await api("/jobs/"+b.dataset.availability,{method:"PATCH",json:{status:b.dataset.status}});invalidateDiscovery();invalidateOpportunity();await Promise.all([loadResource("jobs"),loadDashboard(),loadAdmin()]);}
    catch(err){notice("adminState",err.message,"error");b.disabled=false;}
  }
  if(b.dataset.offerStudent){
    const id=Number(b.dataset.offerJob);
    try{if(!state.jobs.some(j=>j.id===id))state.jobs.push(await api("/opportunities/"+id));selectStudent(Number(b.dataset.offerStudent));selectJob(id);$("placementForm").scrollIntoView({behavior:"smooth"});}
    catch(err){notice("applicationState",err.message,"error");}
  }
});
document.addEventListener("submit",async e=>{
  if(e.target.id==="opportunityFilters")filterOpportunities();
  if(e.target.id==="importForm")importOpportunities();
  if(e.target.dataset.applicationStatus){
    const b=e.target.querySelector("button");b.disabled=true;
    try{await api("/applications/"+e.target.dataset.applicationStatus+"/status",{method:"PATCH",json:{status:e.target.elements.status.value}});await Promise.all([loadApplications(),loadDashboard()]);}
    catch(err){notice("applicationState",err.message,"error");b.disabled=false;}
  }
});
$("roleSelect").addEventListener("change",applyRole);
$("importFile").addEventListener("change",async e=>{
  const file=e.target.files[0];if(!file)return;
  if(file.size>1024*1024){notice("importState","Use a JSON file up to 1 MiB.","error");return;}
  $("importJSON").value=await file.text();
});
window.addEventListener("DOMContentLoaded",()=>{
  try{$("roleSelect").value=localStorage.getItem("campuslink.view")==="officer"?"officer":"student";}catch{}
  applyRole();loadApplications();
});


// Direct skill-gap entry uses existing gap responses, with no relevance scoring.
let gapChoicesVersion=0,gapDetailVersion=0,gapChoiceTimer;
function invalidateGapChoices(){
  gapChoicesVersion++;$("gapChoices").innerHTML="";
  clearTimeout(gapChoiceTimer);
  if(location.hash==="#roadmap")gapChoiceTimer=setTimeout(loadGapChoices,100);
}
async function loadGapChoices(){
  const version=++gapChoicesVersion,s=student();
  $("gapChoices").innerHTML="";
  if(!s){notice("gapChoicesState","Select or create your profile to compare opportunity requirements.");return;}
  notice("gapChoicesState","Loading skill gaps for "+s.name+"...","loading");
  try{
    const jobs=await getAll("/opportunities"),results=[],failures=[];let next=0;
    async function worker(){
      while(next<jobs.length&&version===gapChoicesVersion){
        const j=jobs[next++];
        try{const gap=await api("/matching/skill-gap?"+new URLSearchParams({student_id:s.id,job_id:j.id}));results.push({j,gap});}
        catch(e){failures.push(j.title+": "+e.message);}
      }
    }
    await Promise.all(Array.from({length:Math.min(3,jobs.length)},worker));
    if(version!==gapChoicesVersion)return;
    // Preserve opportunity order, rather than inventing a new recommendation rank.
    results.sort((a,b)=>jobs.indexOf(a.j)-jobs.indexOf(b.j));
    $("gapChoices").innerHTML=opportunitySections(results,({j,gap})=>'<article class="panel">'+sourceBadge(j)+'<h3>'+esc(j.title)+'</h3><p>'+esc(j.company.name)+'</p>'+externalNotice(j)+adzunaAttribution(j)+'<p class="status-pill '+eligibilityClass(gap.eligibility)+'">'+eligibilityLabel(gap.eligibility)+'</p><p>Required skill match: '+coverageText(gap.skill_match_percentage)+'</p><p>'+esc(gap.missing_skills.length?'Missing: '+gap.missing_skills.join(', '):gap.coverage_available?'All required skills present':'No required skills extracted')+'</p><button class="small-btn dark" data-gap-job="'+j.id+'">Analyze skill gaps</button></article>',r=>r.j);
    notice("gapChoicesState",failures.length?"Some opportunities could not be analyzed. Refresh to retry. "+failures.join(" "):jobs.length?"Open opportunities for "+s.name+". Skill coverage alone does not establish eligibility.":"No open opportunities yet. Check again after your placement cell adds opportunities.",failures.length?"error":"");
  }catch(e){if(version===gapChoicesVersion)notice("gapChoicesState",e.message+" Use Refresh opportunities to retry.","error");}
}
async function loadSelectedGap(id){
  const s=student();if(!s)return;
  const version=state.version,request=++gapDetailVersion;$("gapResult").innerHTML="";notice("gapState","Loading detailed skill gaps...","loading");
  try{
    const [j,g]=await Promise.all([api("/opportunities/"+id),api("/matching/skill-gap?"+new URLSearchParams({student_id:s.id,job_id:id}))]);
    if(version!==state.version||request!==gapDetailVersion||state.studentId!==s.id)return;
    state.gap=g;
    $("gapResult").innerHTML='<article class="panel space-top">'+sourceBadge(j)+'<h2>'+esc(j.title)+'</h2><p>'+esc(s.name)+' / '+esc(j.company.name)+'</p>'+externalNotice(j)+adzunaAttribution(j)+eligibilityHTML(g.eligibility)+'<p>Required skill match: '+coverageText(g.skill_match_percentage)+'</p></article>'+skillGroups(g)+'<article class="panel space-top"><h3>Skills to focus on</h3>'+list(g.priorities.map(p=>p.skill+' ? '+p.priority+' priority: '+p.reason),'No skill gaps returned for this opportunity.')+'</article>';
    notice("gapState","");
  }catch(e){if(version===state.version&&request===gapDetailVersion)notice("gapState",e.message+" Select the opportunity again to retry.","error");}
}
document.addEventListener("click",e=>{
  const b=e.target.closest("button");if(!b)return;
  if(b.hasAttribute("data-refresh-card-matches"))renderJobs();
  if(b.id==="refreshGapChoices")loadGapChoices();
  if(b.dataset.gapJob)loadSelectedGap(Number(b.dataset.gapJob));
});
