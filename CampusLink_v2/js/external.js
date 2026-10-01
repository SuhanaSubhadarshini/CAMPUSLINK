function originalListing(j){
  return j.source==="adzuna"&&/^https?:\/\//i.test(j.source_url||"")?'<a class="ghost-btn" href="'+esc(j.source_url)+'" target="_blank" rel="noopener noreferrer">View Original Listing</a>':"";
}
/* Adzuna is called only by the backend. Search never writes; import is explicit. */
function adzunaAttribution(j){
  return j.source==="adzuna"?'<div class="adzuna-attribution"><a href="https://www.adzuna.in" target="_blank" rel="noopener noreferrer">Jobs</a> by <a href="https://www.adzuna.in" target="_blank" rel="noopener noreferrer"><img src="assets/adzuna-logo.png" alt="Adzuna" width="90" height="30"></a></div>':"";
}
function externalNotice(j){
  return j.source==="adzuna"?'<p class="external-notice">Extracted requirements are automated interpretations of an Adzuna description snippet. Please review the original listing before making an application decision.</p>':"";
}
function externalFacts(j){
  if(j.source!=="adzuna")return "";
  const m=j.external_metadata||{},a=m.requirement_analysis||{};
  const experience=a.experience_detected?((a.minimum_experience??"No minimum extracted")+" to "+(a.maximum_experience??"no maximum extracted")+" years"):"Not verified";
  const rows=[["Extraction status",a.status||"INSUFFICIENT_DATA"],["Required skills",a.required_skills?.join(", ")||"No requirements extracted"],["Experience requirement",experience],["Education requirement",a.education_requirements?.join(" / ")||"Not verified"],["Branch restrictions",a.branch_restrictions?.join(" / ")||"Not extracted"],["Graduation / batch",a.graduation_years?.join(", ")||"Not extracted"],["Job category",a.job_category||"Unknown"],["Source employer",m.source_company_name||j.company_name||j.company?.name||"Not provided"],["Source posted date",m.posted_at||"Not provided"],["Source", "Adzuna"]];
  return '<details class="extracted-requirements"><summary>Job requirements and analysis</summary><dl class="profile-details">'+rows.map(([k,v])=>'<dt>'+esc(k)+'</dt><dd>'+esc(v)+'</dd>').join("")+'</dl><h4>Extracted technical skills</h4>'+tags(a.technical_skills||m.detected_skills||[])+list(a.warnings||[])+ '<details><summary>Extraction evidence</summary>'+list((a.evidence||[]).filter(e=>e.skills?.length||e.mandatory).map(e=>e.method+": "+e.text))+'</details><details><summary>Original available description</summary><p class="original-description">'+esc(m.original_description??j.description??"Not provided")+'</p></details></details>';
}
let externalSearch=null, externalBusy=false;
async function searchExternal(){
  if(externalBusy)return;
  externalBusy=true;const button=$("externalSearchForm").querySelector("button");button.disabled=true;
  externalSearch=null;$("externalResults").innerHTML="";notice("externalState","Searching Adzuna...","loading");
  try{
    const params=new URLSearchParams(new FormData($("externalSearchForm")));
    externalSearch=await api("/opportunities/external/adzuna?"+params);
    $("externalResults").innerHTML=externalSearch.results.map((j,i)=>'<article class="panel external-card"><span class="status-pill external-source">Source: Adzuna / External listing</span><h3>'+esc(j.title)+'</h3><p>'+esc(j.company_name)+' / '+esc(j.location||"Location not provided")+'</p>'+externalFacts(j)+'<p>'+esc(j.description)+'</p>'+externalNotice(j)+adzunaAttribution(j)+'<div class="hero-actions"><button class="primary-btn" data-external-import="'+i+'">Import &amp; View Match</button><a class="ghost-btn" href="'+esc(j.source_url)+'" target="_blank" rel="noopener noreferrer">View Original Listing</a></div><div class="api-state" role="status" id="externalImportState'+i+'"></div></article>').join("");
    notice("externalState",(externalSearch.results.length?externalSearch.results.length+" search results; nothing stored until you import.":"No usable listings returned. Try another keyword or location.")+(externalSearch.cached?" Reused cached search.":"")+(externalSearch.skipped?" "+externalSearch.skipped+" malformed or duplicate records skipped.":""),externalSearch.results.length?"success":"");
  }catch(e){notice("externalState",e.message,"error");}
  finally{externalBusy=false;button.disabled=false;}
}
async function importExternal(button){
  const index=Number(button.dataset.externalImport),search=externalSearch,j=search?.results[index];if(!j)return;
  button.disabled=true;notice("externalImportState"+index,"Importing selected listing...","loading");
  try{
    const result=await api("/opportunities/import/adzuna",{method:"POST",json:{search_token:search.search_token,references:[j.source_reference]}});
    invalidateDiscovery();invalidateOpportunity();
    await Promise.all([loadResource("companies"),loadResource("jobs"),loadDashboard()]);
    // A new search may have replaced these cards while import was pending.
    if(search===externalSearch){notice("externalImportState"+index,result.created?"Opportunity imported.":"Existing opportunity refreshed; its ID and applications were preserved.","success");button.textContent="Refresh stored listing & Analyze";}
    await openOpportunity(result.opportunities[0].id);
  }catch(e){if(search===externalSearch)notice("externalImportState"+index,e.message,"error");else toast(e.message);}
  finally{button.disabled=false;}
}
$("externalSearchForm").addEventListener("submit",e=>{e.preventDefault();searchExternal();});
document.addEventListener("click",e=>{const b=e.target.closest("button");if(b?.dataset.externalImport!==undefined)importExternal(b);});
