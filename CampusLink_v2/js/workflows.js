/* Creation and discovery extend the existing v2 UI and shared API helper. */
let editor={type:null,id:null,tags:{},busy:false,trigger:null};
let discovery={mode:null,id:null,version:0,controller:null};
function refreshSuggestions(){
  const skills=[...state.students.flatMap(s=>[...s.skills,...s.extracted_skills]),...state.jobs.flatMap(j=>[...j.required_skills,...j.preferred_skills])];
  const unique=a=>[...new Map(a.filter(Boolean).map(x=>[x.toLowerCase(),x])).values()].sort((a,b)=>a.localeCompare(b));
  $("skillSuggestions").innerHTML=unique(skills).map(x=>'<option value="'+esc(x)+'"></option>').join("");
  $("roleSuggestions").innerHTML=unique([...state.jobs.map(j=>j.title),...state.students.map(s=>s.preferred_role)]).map(x=>'<option value="'+esc(x)+'"></option>').join("");
}
function field(name,label,value="",extra=""){
  return '<label>'+esc(label)+'<input name="'+name+'" value="'+esc(value)+'" '+extra+'></label>';
}
function area(name,label,values=[]){
  return '<label>'+esc(label)+'<textarea name="'+name+'" rows="3" placeholder="One entry per line">'+esc(values.join("\n"))+"</textarea></label>";
}
function skillInput(name,label,values=[]){
  editor.tags[name]=[];
  values.forEach(v=>{if(!editor.tags[name].some(x=>x.toLowerCase()===v.toLowerCase()))editor.tags[name].push(v);});
  return '<div class="skill-editor"><label for="tagInput-'+name+'">'+esc(label)+'</label><div id="tagList-'+name+'" class="skill-tags"></div><div class="tag-entry"><input id="tagInput-'+name+'" data-tag-input="'+name+'" list="skillSuggestions" placeholder="Search or type any skill" autocomplete="off"><button type="button" class="small-btn" data-add-tag="'+name+'">Add skill</button></div><small class="muted">Type a skill and press Enter or comma. Custom skills are welcome.</small></div>';
}
function renderTags(name){
  $("tagList-"+name).innerHTML=editor.tags[name].map((v,i)=>'<span>'+esc(v)+' <button type="button" data-remove-tag="'+name+'" data-index="'+i+'" aria-label="Remove '+esc(v)+'">&times;</button></span>').join("");
}
function addTags(name){
  const input=$("tagInput-"+name);
  for(let v of input.value.split(/[,\n]+/)){
    v=v.trim().replace(/\s+/g," ");
    const known=[...$("skillSuggestions").options].find(o=>o.value.toLowerCase()===v.toLowerCase());
    v=known?.value||v;
    if(v&&!editor.tags[name].some(x=>x.toLowerCase()===v.toLowerCase()))editor.tags[name].push(v);
  }
  input.value="";renderTags(name);
}
function closeEditor(){
  if(editor.busy)return;
  $("editorDialog").close();editor.trigger?.focus();
}
async function openEditor(type,id=null){
  editor={type,id,tags:{},busy:false,trigger:document.activeElement};
  $("editorTitle").textContent=type==="student"?(id?"Edit My Profile":"Create My Profile"):type==="job"?"Add opportunity":"Add Company";
  $("editorBody").innerHTML="";$("editorFields").disabled=true;$("editorDialog").showModal();
  notice("editorState","Loading form...","loading");
  try{
    let data={};
    if(type==="student"&&id)data=await api("/students/"+id);
    if(type==="job"){
      state.companies=await getAll("/companies");state.ready.companies=true;renderCompanies();
    }
    // The user may close while the request is pending.
    if(!$("editorDialog").open||editor.type!==type||editor.id!==id)return;
    refreshSuggestions();
    let html="";
    if(type==="student"){
      html='<p class="muted">Your own profile. Branch maps to the existing department field. Career preference is descriptive and does not override job eligibility.</p><div class="form-grid">'+
        field("name","Name",data.name||"",'required maxlength="150"')+
        field("email","Email",data.email||"",'type="email" required')+
        field("phone","Phone",data.phone||"",'maxlength="25"')+
        field("degree","Degree",data.degree||"",'maxlength="150" placeholder="B.Tech, B.Sc, MCA..."')+
        field("department","Branch / department",data.department||"",'required maxlength="150"')+
        field("graduation_year","Graduation year",data.graduation_year||new Date().getFullYear(),'type="number" min="2000" max="2100" step="1" required')+
        field("cgpa","CGPA (0-10)",data.cgpa??"",'type="number" min="0" max="10" step="any" required')+
        field("professional_experience_years","Professional experience in years (blank = unknown)",data.professional_experience_years??"",'type="number" min="0" max="80" step="any" placeholder="0 for no professional experience"')+
        field("preferred_role","Preferred Career Role",data.preferred_role||"",'list="roleSuggestions" maxlength="150" placeholder="Type any career role"')+
        ["coding","aptitude","communication"].map(k=>field(k+"_score",k[0].toUpperCase()+k.slice(1)+" score (0-100)",data[k+"_score"]??"",'type="number" min="0" max="100" step="any" placeholder="Not assessed"')).join("")+"</div>"+
        skillInput("skills","Skills (add at least one)",data.skills||[])+
        (id?skillInput("extracted_skills","Review / correct resume-extracted skills",data.extracted_skills||[]):"")+
        '<div class="form-grid">'+area("projects","Projects / portfolio (one per line)",data.projects||[])+area("certifications","Certifications (one per line)",data.certifications||[])+"</div>"+
        '<label>Resume (optional, PDF/DOCX/TXT, up to 5 MiB)<input name="resume" type="file" accept=".pdf,.docx,.txt"></label><p class="muted">Uploading a new resume replaces extracted skills. Review them using Edit profile after upload. Manual skills remain unchanged.</p>';
    }else if(type==="job"){
      html='<div class="form-grid">'+field("title","Job title / role","","required maxlength=\"150\" list=\"roleSuggestions\"")+
        '<label>Company<select name="company_id" required><option value="">Choose a company</option>'+state.companies.map(c=>'<option value="'+c.id+'">'+esc(c.name)+"</option>").join("")+
        '<option value="new">+ Create a new company</option></select></label>'+
        field("vacancy_count","Number of openings (blank = unknown)","",'type="number" min="1" step="1"')+field("source_reference","Source reference (optional)")+field("source_url","Source URL (optional)","",'type="url"')+field("location","Location")+field("minimum_cgpa","Minimum CGPA",0,'type="number" min="0" max="10" step="any" required')+
        field("graduation_year","Required graduation year (blank = any)","",'type="number" min="2000" max="2100" step="1"')+
        field("salary_stipend","Salary / stipend","","placeholder=\"6 LPA or INR 25000/month\"")+
        '<label>Job type<select name="job_type"><option>full-time</option><option>internship</option><option>part-time</option><option>contract</option></select></label></div>'+
        '<div id="inlineCompany" hidden class="panel">'+field("company_name","New company name","","maxlength=\"150\"")+field("company_industry","Industry")+"</div>"+
        area("description","Job description")+
        skillInput("required_skills","Required skills (add at least one)")+
        skillInput("preferred_skills","Preferred skills (optional)")+
        '<p class="muted">Manual opportunity eligibility uses configured CGPA, graduation year and required skills. Extracted external requirements also check experience, degree and branch.</p>';
    }else{
      html='<div class="form-grid">'+field("name","Company name","","required maxlength=\"150\"")+field("industry","Industry")+field("location","Location")+field("website","Website")+"</div>"+area("description","Description");
    }
    $("editorBody").innerHTML=html;Object.keys(editor.tags).forEach(renderTags);
    $("editorFields").disabled=false;notice("editorState","");$("editorBody").querySelector("input").focus();
  }catch(e){notice("editorState",e.message,"error");}
}
function invalidateDiscovery(message="Data changed. Refresh these results."){
  discovery.version++;discovery.controller?.abort();$("discoveryResults").innerHTML="";
  if(discovery.mode)notice("discoveryState",message);
}
async function saveRecord(form){
  if(editor.busy)return;
  Object.keys(editor.tags).forEach(addTags);
  if(!form.reportValidity())return;
  const f=new FormData(form),value=k=>String(f.get(k)||"").trim();
  const lines=k=>value(k).split(/\r?\n/).map(x=>x.trim()).filter(Boolean);
  const type=editor.type,id=editor.id;
  let body,path,method=id?"PATCH":"POST";
  if(type==="student"){
    if(!editor.tags.skills.length){notice("editorState","Add at least one skill.","error");return;}
    body={name:value("name"),email:value("email"),phone:value("phone"),degree:value("degree"),department:value("department"),
      professional_experience_years:value("professional_experience_years")===""?null:Number(value("professional_experience_years")),preferred_role:value("preferred_role"),graduation_year:Number(value("graduation_year")),cgpa:Number(value("cgpa")),
      skills:editor.tags.skills,projects:lines("projects"),certifications:lines("certifications"),
      ...Object.fromEntries(["coding_score","aptitude_score","communication_score"].filter(k=>value(k)!=="").map(k=>[k,Number(value(k))]))};
    if(id)body.extracted_skills=editor.tags.extracted_skills;
    path="/students"+(id?"/"+id:"");
  }else if(type==="job"){
    if(!editor.tags.required_skills.length){notice("editorState","Add at least one required skill.","error");return;}
    body={vacancy_count:value("vacancy_count")?Number(value("vacancy_count")):null,source_reference:value("source_reference")||null,source_url:value("source_url")||null,title:value("title"),company_id:Number(value("company_id")),description:value("description"),location:value("location"),
      minimum_cgpa:Number(value("minimum_cgpa")),graduation_year:value("graduation_year")?Number(value("graduation_year")):null,
      required_skills:editor.tags.required_skills,preferred_skills:editor.tags.preferred_skills,salary_stipend:value("salary_stipend"),job_type:value("job_type")};
    path="/opportunities";
  }else{
    body={name:value("name"),industry:value("industry"),location:value("location"),website:value("website"),description:value("description")};path="/companies";
  }
  const file=f.get("resume");
  if(file?.size>5*1024*1024){notice("editorState","Resume exceeds the 5 MiB limit.","error");return;}
  editor.busy=true;$("editorFields").disabled=true;$("closeEditor").disabled=true;
  notice("editorState","Saving...","loading");
  let saved=null,warning="";
  try{
    if(type==="job"&&value("company_id")==="new"){
      if(!value("company_name"))throw new Error("Enter the new company's name.");
      const company=await api("/companies",{method:"POST",json:{name:value("company_name"),industry:value("company_industry")}});
      body.company_id=company.id;
      // Retain the newly created company if the subsequent job request fails.
      state.companies.push(company);renderCompanies();
      const select=form.elements.company_id;select.add(new Option(company.name,String(company.id)));select.value=String(company.id);
      $("inlineCompany").hidden=true;form.elements.company_name.required=false;
    }
    saved=await api(path,{method,json:body});
    invalidateDiscovery();invalidateOpportunity();
    if(type==="student"&&file?.size){
      try{
        const upload=new FormData();upload.append("file",file);
        const result=await api("/students/"+saved.id+"/resume",{method:"POST",body:upload});
        warning=result.warning||"";
      }catch(e){warning="Profile saved, but resume upload failed: "+e.message+" Upload it from your profile.";}
    }
    await loadResource(type==="student"?"students":type==="job"?"jobs":"companies");
    await loadDashboard();
    if(type==="student"){selectStudent(saved.id);go("students");}
    if(type==="job"){selectJob(saved.id);go("jobs");}
    if(type==="company")go("companies");
    $("editorDialog").close();
    const resource=type==="student"?"students":type==="job"?"jobs":"companies";
    if(!state.ready[resource])warning+=" Record saved, but the list could not refresh. Retry loading the list.";
    const message=(type==="student"?"Profile":type==="job"?"Job":"Company")+" saved. "+warning;
    toast(message);
    notice(type==="student"?"studentsState":type==="job"?"jobsState":"companiesState",message,warning?"warning":"success",!state.ready[resource]?resource:"");
  }catch(e){
    notice("editorState",(saved?"Record saved, but refresh failed. Close and reload the page. ":"")+e.message,"error");
    if(saved){editor.id=saved.id;editor.type=type;}
  }finally{editor.busy=false;$("editorFields").disabled=false;$("closeEditor").disabled=false;}
}

async function discover(mode,id){
  invalidateDiscovery();discovery.mode=mode;discovery.id=id;
  const version=discovery.version;discovery.controller=new AbortController();const signal=discovery.controller.signal;
  go("discovery");$("discoveryTitle").textContent=mode==="candidates"?"Find Suitable Candidates":"Jobs for Me";
  $("discoveryContext").textContent="Loading current records...";
  notice("discoveryState","Loading all records from the backend...","loading");
  try{
    let records,subject;
    $("discoverySource").innerHTML="";
    if(mode==="candidates"){
      [subject,records]=await Promise.all([api("/opportunities/"+id,{signal}),getAll("/students")]);
      if(version!==discovery.version)return;
      if(subject.status!=="open")throw new Error("This opportunity is closed. Choose an available opportunity.");
      $("discoverySource").innerHTML=sourceBadge(subject)+adzunaAttribution(subject)+originalListing(subject);
      state.students=records;state.ready.students=true;
      state.jobs=state.jobs.map(j=>j.id===id?subject:j);
      $("discoveryContext").textContent=subject.title+" / "+subject.company.name+" - eligible students ranked by backend fit score."+(subject.source==="adzuna"?" Only verified eligible students are ranked. Unknown requirements require review.":"");
    }else{
      [subject,records]=await Promise.all([api("/students/"+id,{signal}),getAll("/opportunities")]);
      if(version!==discovery.version)return;
      state.jobs=records;state.ready.jobs=true;
      state.students=state.students.map(s=>s.id===id?subject:s);
      $("discoveryContext").textContent=subject.name+(subject.preferred_role?" / Preferred role: "+subject.preferred_role:"")+" - all jobs are evaluated; career preference is not an eligibility filter.";
    }
    renderStudents();renderJobs();syncSelections();refreshSuggestions();
    if(!records.length){notice("discoveryState",mode==="candidates"?"No students available. Create a profile first.":"No open opportunities available. Ask your placement cell to import opportunities.");return;}
    const results=[],failures=[];let next=0,done=0;
    async function worker(){
      while(next<records.length&&version===discovery.version){
        const record=records[next++],sid=mode==="candidates"?record.id:id,jid=mode==="candidates"?id:record.id;
        const query="?"+new URLSearchParams({student_id:sid,job_id:jid});
        try{
          const eligibility=await api("/matching/eligibility"+query,{signal});
          if(mode==="jobs"||eligibility.eligible){
            const fit=await api("/matching/fit"+query,{signal});
            const gap=mode==="jobs"?await api("/matching/skill-gap"+query,{signal}):fit;
            results.push({record,sid,jid,eligibility,fit,gap});
          }
        }catch(e){if(version!==discovery.version)return;failures.push((record.name||record.title)+": "+e.message);}
        done++;
        if(version===discovery.version)notice("discoveryState","Evaluated "+done+" of "+records.length+" records...","loading");
      }
    }
    // Bounded concurrency keeps the MVP server responsive as lists grow.
    await Promise.all(Array.from({length:Math.min(3,records.length)},worker));
    if(version!==discovery.version)return;
    results.sort((a,b)=>(mode==="jobs"?Number(b.eligibility.eligible)-Number(a.eligibility.eligible):0)||(b.fit?.overall_fit_score??-1)-(a.fit?.overall_fit_score??-1)||a.record.id-b.record.id);
    const resultCard=(r,i)=>'<article class="panel discovery-card '+(mode==="jobs"&&r.record.source==="demo"?'demo-card':'')+'"><div class="panel-head"><div><span class="eyebrow">'+
      (mode==="candidates"?"RANK "+(i+1):esc(r.record.company.name))+"</span><h3>"+esc(r.record.name||r.record.title)+
      '</h3></div><span class="fit-score">'+(r.fit?(r.fit.provisional?'Provisional match: ':'Match: ')+fmt(r.fit.overall_fit_score)+'% ('+fmt(r.fit.overall_fit_score)+' / 100)':'Eligibility not met')+'</span></div><p><span class="status-pill '+eligibilityClass(r.eligibility)+'">'+
      eligibilityLabel(r.eligibility)+"</span></p>"+
      (r.eligibility.eligible?"":list(r.eligibility.reasons))+"<h4>Matched required skills</h4>"+tags(r.gap.matched_skills,"matched")+
      "<h4>Missing required skills</h4>"+tags(r.gap.missing_skills,"missing")+
      "<h4>Matched preferred skills</h4>"+tags(r.gap.matched_preferred_skills,"matched")+"<h4>Missing preferred skills</h4>"+tags(r.gap.missing_preferred_skills,"missing")+
      (mode==="jobs"?sourceBadge(r.record)+externalNotice(r.record)+adzunaAttribution(r.record)+originalListing(r.record):'')+'<p class="muted">Required skill match: '+coverageText(r.gap.skill_match_percentage)+'</p><button class="primary-btn" data-explain-student="'+r.sid+'" data-explain-job="'+r.jid+'">View Explanation</button>'+(mode==="jobs"?' <button class="ghost-btn" data-job="'+r.jid+'">View Opportunity</button>':'')+'</article>';
    if(mode==="jobs"){
      function matchGroups(rows){
        const groups=[['Eligible Matches','Known mandatory requirements are satisfied.',rows.filter(r=>r.eligibility.eligible)],['Eligibility Unverified','Requirements or profile information need verification. Provisional match scores do not confirm eligibility.',rows.filter(r=>r.eligibility.status==="UNVERIFIED")],['Opportunities With Skill Gaps','Required skills are the only known unmet requirements.',rows.filter(r=>r.eligibility.status==="NOT_ELIGIBLE"&&r.eligibility.missing_requirements.length&&r.eligibility.missing_requirements.every(m=>m.requirement==="required_skills"))],['Currently Not Eligible','One or more known eligibility requirements are not met; fit scores do not override them.',rows.filter(r=>r.eligibility.status==="NOT_ELIGIBLE"&&(!r.eligibility.missing_requirements.length||r.eligibility.missing_requirements.some(m=>m.requirement!=="required_skills")))]];
        return groups.map(([title,description,items])=>'<section class="match-group" data-match-group="'+title+'"><h3>'+title+'</h3><p class="muted">'+description+'</p>'+(items.length?items.map(resultCard).join(''):'<p class="muted">No opportunities in this group.</p>')+'</section>').join('');
      }
      // Partition by provenance before eligibility so even an unverified real listing
      // precedes every fictional match. Scores are always returned by the backend.
      const partitioned=['external','placement','demo'].map(kind=>({kind,items:results.filter(r=>opportunityKind(r.record)===kind)})).filter(g=>g.items.length);
      $("discoveryResults").innerHTML=opportunitySections(partitioned,g=>matchGroups(g.items),g=>g.items[0].record,{layout:'match-groups',count:g=>g.items.length});

    }else $("discoveryResults").innerHTML=results.map(resultCard).join("");
    if(!results.length)$("discoveryResults").innerHTML='<article class="panel"><h3>'+ (mode==="candidates"?"No eligible candidates found.":"No job results available.")+'</h3><p class="muted">Update your records or try again after adding profiles/jobs.</p></article>';
    notice("discoveryState",failures.length?"Partial results: "+failures.length+" records could not be evaluated. "+failures.join(" ")+" Refresh to retry.":
      "Checked "+records.length+" records. "+results.length+(mode==="candidates"?" eligible candidates.":" jobs evaluated. Real external opportunities appear first; demo examples are separate. Eligibility groups remain distinct."),failures.length?"error":"success");
  }catch(e){if(version===discovery.version)notice("discoveryState",e.message,"error");}
}
document.addEventListener("click",async e=>{
  const b=e.target.closest("button");if(!b)return;
  if(["addStudent","createMyProfile"].includes(b.id))openEditor("student");
  if(b.id==="editProfile"&&student())openEditor("student",state.studentId);
  if(b.id==="myProfile"){if(student()){go("students");$("studentProfile").scrollIntoView({behavior:"smooth",block:"start"});}else openEditor("student");}
  if(b.id==="addJob")openEditor("job");
  if(b.id==="addCompany")openEditor("company");
  if(["closeEditor","cancelEditor"].includes(b.id))closeEditor();
  if(b.dataset.addTag){addTags(b.dataset.addTag);$("tagInput-"+b.dataset.addTag).focus();}
  if(b.dataset.removeTag){const name=b.dataset.removeTag;editor.tags[name].splice(Number(b.dataset.index),1);renderTags(name);}
  if(b.dataset.candidates)discover("candidates",Number(b.dataset.candidates));
  if(b.id==="suitableJobs"&&student())discover("jobs",state.studentId);
  if(b.id==="refreshDiscovery"&&discovery.mode)discover(discovery.mode,discovery.id);
  if(b.dataset.explainStudent){
    selectStudent(Number(b.dataset.explainStudent));selectJob(Number(b.dataset.explainJob));go("matches");
    await openOpportunity(Number(b.dataset.explainJob));
  }
});
$("recordForm").addEventListener("submit",e=>{e.preventDefault();saveRecord(e.target);});
$("editorDialog").addEventListener("cancel",e=>{if(editor.busy)e.preventDefault();});
$("editorDialog").addEventListener("keydown",e=>{
  if(e.target.dataset.tagInput&&(e.key==="Enter"||e.key===",")){e.preventDefault();addTags(e.target.dataset.tagInput);}
});
$("editorDialog").addEventListener("change",e=>{
  if(e.target.name==="company_id"){
    const show=e.target.value==="new";$("inlineCompany").hidden=!show;
    $("recordForm").elements.company_name.required=show;
  }
});
$("editorDialog").addEventListener("focusout",e=>{
  if(e.target.dataset.tagInput&&e.target.value.trim())addTags(e.target.dataset.tagInput);
});
refreshSuggestions();
