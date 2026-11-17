const $ = s => document.querySelector(s);
let settings = {};
let paygYears = {};
let selectedPaygYear = "";
const names = {dashboard:"Dashboard",shifts:"Time entries",entry:"New time entry",reports:"Timesheet report",settings:"Settings"};
function toast(message){const el=$("#toast");el.textContent=message;el.classList.add("show");setTimeout(()=>el.classList.remove("show"),2600)}
async function api(url,options={}){const r=await fetch(url,{headers:{"Content-Type":"application/json"},...options});if(!r.ok){const t=await r.text();let message=t||r.statusText;try{const body=JSON.parse(t);message=body.detail||body.message||message}catch{}throw new Error(message)}return r.status===204?null:r.json()}
function showPage(page){if(!names[page])page="dashboard";document.querySelectorAll(".page").forEach(x=>x.classList.toggle("active",x.id===page));document.querySelectorAll(".nav").forEach(x=>x.classList.toggle("active",x.dataset.page===page));$("#page-title").textContent=names[page];if(page==="dashboard")loadDashboard();if(page==="shifts")loadShifts();if(page==="reports"){reportWeekStart=null;loadReport();}if(page==="settings")loadSettings();history.replaceState(null,"","#"+page)}
document.querySelectorAll(".nav").forEach(b=>b.addEventListener("click",()=>showPage(b.dataset.page)));
function showSettingsPanel(key){document.querySelectorAll("[data-settings-panel]").forEach(x=>x.classList.toggle("active",x.dataset.settingsPanel===key));document.querySelectorAll(".settings-nav-button").forEach(x=>x.classList.toggle("active",x.dataset.settingsPage===key));}
document.querySelectorAll(".settings-nav-button").forEach(b=>b.addEventListener("click",()=>showSettingsPanel(b.dataset.settingsPage)));
function formObject(form){return Object.fromEntries(new FormData(form).entries())}
function setDefaultDates(){const today=new Date().toISOString().slice(0,10);document.querySelectorAll('input[type="date"]').forEach(x=>{if(!x.value)x.value=today})}
function hours(v){return Number(v||0).toFixed(2)+" h"}
function money(v){return v==null?"Not configured":new Intl.NumberFormat(undefined,{style:"currency",currency:settings.currency||"AUD"}).format(v)}
let dashboardWeekStart=null;
let dashboardWeekStartDay=null;
function dateText(d){return d.getFullYear()+"-"+String(d.getMonth()+1).padStart(2,"0")+"-"+String(d.getDate()).padStart(2,"0")}
function parseLocalDate(value){const [y,m,d]=value.split("-").map(Number);return new Date(y,m-1,d,12)}
function displayDate(d){return d.toLocaleDateString(undefined,{day:"2-digit",month:"short",year:"numeric"})}
function displayLongDate(d){return d.toLocaleDateString(undefined,{weekday:"long",day:"numeric",month:"long",year:"numeric"})}
let reportWeekStart=null,reportWeekStartDay=null;
async function initialiseReportWeek(){settings=await api("api/settings");const day=Number(settings.week_start_day??0);if(!reportWeekStart||reportWeekStartDay!==day){const now=new Date();reportWeekStart=new Date(now.getFullYear(),now.getMonth(),now.getDate(),12);reportWeekStart.setDate(reportWeekStart.getDate()-((reportWeekStart.getDay()+6-day)%7));reportWeekStartDay=day}const end=new Date(reportWeekStart);end.setDate(end.getDate()+6);$("#report-start").value=dateText(reportWeekStart);$("#report-end").value=dateText(end)}
function shiftReportWeek(amount){if(!reportWeekStart)return;reportWeekStart.setDate(reportWeekStart.getDate()+amount*7);const end=new Date(reportWeekStart);end.setDate(end.getDate()+6);$("#report-start").value=dateText(reportWeekStart);$("#report-end").value=dateText(end);loadReport()}
function shiftDashboardWeek(amount){if(!dashboardWeekStart)return;dashboardWeekStart.setDate(dashboardWeekStart.getDate()+amount*7);loadDashboard()}
async function loadDashboard(){try{settings=await api("api/settings");const weekStartDay=Number(settings.week_start_day??0);const now=new Date();if(!dashboardWeekStart||dashboardWeekStartDay!==weekStartDay){dashboardWeekStart=new Date(now.getFullYear(),now.getMonth(),now.getDate(),12);dashboardWeekStart.setDate(dashboardWeekStart.getDate()-((dashboardWeekStart.getDay()+6-weekStartDay)%7));dashboardWeekStartDay=weekStartDay}const weekEnd=new Date(dashboardWeekStart);weekEnd.setDate(weekEnd.getDate()+6);const startText=dateText(dashboardWeekStart),endText=dateText(weekEnd);$("#dashboard-week-label").textContent="Week ending "+displayDate(weekEnd);const [r,shifts]=await Promise.all([api("api/report?start="+startText+"&end="+endText),api("api/shifts")]);const totalHours=Number(r.total_work_hours||0)+Number(r.total_travel_hours||0);$("#week-hours").textContent=hours(totalHours);$("#gross").textContent=money(r.estimated_gross);$("#gross-note").textContent=r.base_rate_configured?"Calculated estimate":"Set your hourly rate in Settings";$("#take-home").textContent=money(r.estimated_net);$("#take-home-note").textContent=r.estimated_net==null?"Configure the PAYG table for this financial year":"After estimated weekly PAYG withholding";await loadYearEarningsChart();await loadSelectedEarningsChart();}catch(e){toast("Could not load dashboard: "+e.message)}}
function earningsChartHtml(report){
 const totals={};
 (report.shifts||[]).forEach(s=>(s.segments||[]).forEach(seg=>{
  const label=seg.pay_code||seg.category||"Other";
  const value=Number(seg.hours||0)*Number(report.base_rate||0)*Number(seg.multiplier||1);
  if(value>0)totals[label]=(totals[label]||0)+value;
 }));
 (report.travel||[]).forEach(t=>{const value=Number(t.estimated_earnings||0);if(value>0){const label=t.pay_code||"Travel";totals[label]=(totals[label]||0)+value}});
 if(Number(report.total_allowances||0)>0)totals.Allowances=(totals.Allowances||0)+Number(report.total_allowances);
 const items=Object.entries(totals).filter(x=>x[1]>0).sort((a,b)=>b[1]-a[1]);
 const total=items.reduce((sum,x)=>sum+x[1],0);
 if(!total)return '<div class="empty">No earnings recorded for this period.</div>';
 const colors=["#2787b8","#56a36c","#d49b32","#a477c5","#d16d6d","#4caaa5","#8b9bb0","#c17b43","#7794d1","#b5a34b"];
 let angle=0;
 const slices=items.map(([name,value],i)=>{const start=angle;angle+=value/total*360;return colors[i%colors.length]+" "+start.toFixed(2)+"deg "+angle.toFixed(2)+"deg"}).join(",");
 const legend=items.map(([name,value],i)=>'<div class="earnings-legend-row"><i style="background:'+colors[i%colors.length]+'"></i><span>'+esc(name)+'</span><b>'+money(value)+'</b><small>'+((value/total)*100).toFixed(1)+'%</small></div>').join("");
 return '<div class="earnings-chart-layout"><div class="earnings-pie" style="background:conic-gradient('+slices+')"><div><strong>'+money(total)+'</strong><small>Total earnings</small></div></div><div class="earnings-legend">'+legend+'</div></div>';
}
function fyRange(){
 const now=new Date(),year=now.getMonth()>=6?now.getFullYear():now.getFullYear()-1;
 return {start:year+"-07-01",end:dateText(now)};
}
async function loadYearEarningsChart(){
 const p=fyRange();
 try{const r=await api("api/report?start="+p.start+"&end="+p.end);$("#year-earnings-chart").innerHTML=earningsChartHtml(r)}
 catch(e){$("#year-earnings-chart").innerHTML='<div class="empty">Could not load earnings.</div>'}
}
async function loadSelectedEarningsChart(){
 const start=$("#dashboard-chart-start").value,end=$("#dashboard-chart-end").value;
 if(!start||!end||start>end){$("#selected-earnings-chart").innerHTML='<div class="empty">Choose a valid date range.</div>';return}
 try{const r=await api("api/report?start="+start+"&end="+end);$("#selected-earnings-chart").innerHTML=earningsChartHtml(r)}
 catch(e){$("#selected-earnings-chart").innerHTML='<div class="empty">Could not load earnings.</div>'}
}
function timeMins(f,s){let [fh,fm]=f.split(":").map(Number),[sh,sm]=s.split(":").map(Number);let n=fh*60+fm-(sh*60+sm);return n<=0?n+1440:n}
function recordHtml(title,sub,note,right){return '<div class="record"><div><b>'+esc(title)+' · '+esc(sub)+'</b><small>'+esc(note)+'</small></div><div class="right"><b>'+right+'</b></div></div>'}
function esc(s){return String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
let entrySubmitting=false;
let entryBaseline="";
function entrySnapshot(){const f=$("#entry-form");return JSON.stringify({data:formObject(f),checks:["is_public_holiday","is_travelling","is_overseas"].map(k=>f.elements[k].checked)})}
function entryIsDirty(){return !!entryBaseline&&entrySnapshot()!==entryBaseline}
function updateEntryDirtyState(){const dirty=entryIsDirty(),status=$("#entry-dirty-status");if(status)status.textContent=dirty?"Unsaved changes":"";const date=$("#entry-form").elements.work_date.value,label=$("#entry-day-label");if(label)label.textContent=date?displayLongDate(parseLocalDate(date)):"Choose a date to edit"}
$("#entry-form").addEventListener("input",updateEntryDirtyState);
$("#entry-form").addEventListener("change",updateEntryDirtyState);
async function saveEntry(){
 if(entrySubmitting)return false;
 entrySubmitting=true;const saveButton=$("#entry-save");if(saveButton)saveButton.disabled=true;
 const f=$("#entry-form"),d=formObject(f),id=d.entry_id;delete d.entry_id;d.break_minutes=Number(d.break_minutes||0);
 for(const k of ["is_public_holiday","is_travelling","is_overseas"])d[k]=f.elements[k].checked;
 d.leave_type=d.leave_type||"work";d.project=d.project||"";
 if(d.leave_type!=="work"){d.start_time="00:00";d.finish_time="10:00";d.break_minutes=0;d.is_travelling=false;d.is_overseas=false;d.is_public_holiday=false;}
 try{
  const result=await api(id?"api/shifts/"+id:"api/shifts",{method:id?"PUT":"POST",body:JSON.stringify(d)});
  if(!id)f.elements.entry_id.value=result.id;
  toast(id?"Time entry updated":"Time entry saved");
  entryBaseline=entrySnapshot();updateEntryDirtyState();
  const saved=await api("api/shifts");shiftCache=saved;
  return true;
 }catch(err){toast("Save failed: "+err.message);return false}
 finally{entrySubmitting=false;if(saveButton)saveButton.disabled=false;}
}
$("#entry-form").addEventListener("submit",async e=>{e.preventDefault();if(await saveEntry())showPage("shifts")});
let shiftCalendarMonthDate=null;
async function loadShifts(){
 const [rows,calendarSettings,holidays]=await Promise.all([api("api/shifts"),api("api/settings"),api("api/holidays")]);
 renderProjectSelects(calendarSettings.projects||[]);
 shiftCache=rows;settings=calendarSettings;
 if(!shiftCalendarMonthDate){const now=new Date();shiftCalendarMonthDate=new Date(now.getFullYear(),now.getMonth(),1,12)}
 renderShiftCalendar(rows,calendarSettings,holidays||[]);
 $("#shift-list").innerHTML=rows.length?'<table><thead><tr><th>Date</th><th>Time in</th><th>Time out</th><th>Break</th><th>Total hours</th><th>Entry type</th><th>Overseas</th><th>Actions</th></tr></thead><tbody>'+rows.map(s=>{const paid=Math.max(0,timeMins(s.finish_time,s.start_time)-Number(s.break_minutes||0));const payable=s.is_travelling?Math.min(paid,600):paid;return '<tr><td>'+esc(s.work_date)+'</td><td>'+(s.leave_type&&s.leave_type!=="work"?"—":esc(s.start_time))+'</td><td>'+(s.leave_type&&s.leave_type!=="work"?"—":esc(s.finish_time))+'</td><td>'+(s.leave_type&&s.leave_type!=="work"?"—":Number(s.break_minutes||0)+' min')+'</td><td>'+hours(payable/60)+'</td><td>'+(s.leave_type==="annual_leave"?'<span class="tag">Annual Leave</span>':s.leave_type==="sick_leave"?'<span class="tag">Sick Leave</span>':s.is_travelling?'<span class="tag">Travel</span>':s.is_overseas?'<span class="tag">Work – Overseas</span>':s.is_public_holiday?'<span class="tag">Public holiday</span>':'Work')+'</td><td>'+(s.is_overseas?'Yes':'—')+'</td><td><button class="small-btn" onclick="editShift('+s.id+')">Edit</button> <button class="danger" onclick="deleteShift('+s.id+')">Delete</button></td></tr>'}).join("")+'</tbody></table>':'<div class="empty">No time entries yet.</div>'}
function shiftCalendarMonth(amount){
 if(!shiftCalendarMonthDate)return;
 shiftCalendarMonthDate=new Date(shiftCalendarMonthDate.getFullYear(),shiftCalendarMonthDate.getMonth()+amount,1,12);
 renderShiftCalendar(shiftCache,settings,window.shiftCalendarHolidays||[]);
}
function openCalendarDate(date){
 const matches=shiftCache.filter(s=>s.work_date===date);
 if(matches.length===1){editShift(matches[0].id);return}
 if(matches.length>1){
  const choice=prompt("Multiple entries on this day. Enter the entry number to edit:\\n"+matches.map((s,i)=>(i+1)+". "+s.start_time+"–"+s.finish_time+" ("+s.id+")").join("\\n"));
  const index=Number(choice)-1;if(Number.isInteger(index)&&index>=0&&index<matches.length)editShift(matches[index].id);
  return;
 }
 newEntry();$("#entry-form").elements.work_date.value=date;
}
function renderShiftCalendar(rows,config,holidays){
 window.shiftCalendarHolidays=holidays||[];
 const root=$("#shift-calendar");if(!root)return;
 const y=shiftCalendarMonthDate.getFullYear(),m=shiftCalendarMonthDate.getMonth();
 $("#shift-calendar-label").textContent=shiftCalendarMonthDate.toLocaleDateString(undefined,{month:"long",year:"numeric"});
 const first=new Date(y,m,1,12),offset=(first.getDay()+6)%7;
 const days=new Date(y,m+1,0).getDate(),today=new Date();today.setHours(12,0,0,0);
 const totals={};(rows||[]).forEach(s=>{
  const mins=Math.max(0,timeMins(s.finish_time,s.start_time)-Number(s.break_minutes||0));
  const paid=s.is_travelling?Math.min(mins,600):mins;
  totals[s.work_date]=(totals[s.work_date]||0)+paid/60;
 });
 const schedule=config.normal_hours_schedule||[];
 const enabledDays=new Set(schedule.filter(x=>x.enabled).map(x=>Number(x.day)));
 const holidayDates=new Set((holidays||[]).map(h=>h.holiday_date));
 const headers=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"];
 let out=headers.map(x=>'<div class="calendar-weekday">'+x+'</div>').join("");
 for(let i=0;i<offset;i++)out+='<div class="calendar-day calendar-empty"></div>';
 for(let day=1;day<=days;day++){
  const d=new Date(y,m,day,12),key=dateText(d),dow=(d.getDay()+6)%7;
  const total=totals[key]||0,has=total>0,scheduled=enabledDays.has(dow)&&!holidayDates.has(key),missed=d<today&&scheduled&&!has;
  const classes=["calendar-day",has?"calendar-has-hours":"",missed?"calendar-missing":"",key===dateText(today)?"calendar-today":""].filter(Boolean).join(" ");
  out+='<button type="button" class="'+classes+' calendar-day-button" data-date="'+key+'" onclick="openCalendarDate(\''+key+'\')" title="'+(missed?"Scheduled workday with no time entry":has?"Hours recorded — click to edit":"No hours recorded — click to add entry")+'"><span class="calendar-date">'+day+'</span><strong>'+(has?hours(total):"—")+'</strong></button>';
 }
 const cells=offset+days;for(let i=cells;i<Math.ceil(cells/7)*7;i++)out+='<div class="calendar-day calendar-empty"></div>';
 root.innerHTML=out;
}
let shiftCache=[];
function toggleLeaveFields(){const leave=$("#leave-type").value!=="work";$("#work-time-fields").hidden=leave;$("#leave-entry-note").hidden=!leave;const f=$("#entry-form");f.elements.start_time.required=!leave;f.elements.finish_time.required=!leave;}
$("#leave-type").addEventListener("change",toggleLeaveFields);
function newEntry(dateValue){const f=$("#entry-form");f.reset();f.elements.entry_id.value="";f.elements.start_time.value="05:30";f.elements.finish_time.value="16:00";f.elements.break_minutes.value=30;f.elements.is_public_holiday.checked=false;f.elements.is_travelling.checked=false;f.elements.is_overseas.checked=false;f.elements.leave_type.value="work";f.elements.project.value="";toggleLeaveFields();$("#entry-heading").textContent="New time entry";$("#entry-save").textContent="Save time entry";if(dateValue)f.elements.work_date.value=dateValue;else setDefaultDates();entryBaseline=entrySnapshot();updateEntryDirtyState();showPage("entry")}
function editShift(id){const s=shiftCache.find(x=>Number(x.id)===Number(id));if(!s)return;const f=$("#entry-form");f.elements.entry_id.value=s.id;f.elements.work_date.value=s.work_date;f.elements.start_time.value=s.start_time;f.elements.finish_time.value=s.finish_time;f.elements.break_minutes.value=s.break_minutes;f.elements.notes.value=s.notes||"";f.elements.is_public_holiday.checked=!!s.is_public_holiday;f.elements.is_travelling.checked=!!s.is_travelling;f.elements.is_overseas.checked=!!s.is_overseas;f.elements.leave_type.value=s.leave_type||"work";f.elements.project.value=s.project||"";toggleLeaveFields();$("#entry-heading").textContent="Edit time entry";$("#entry-save").textContent="Save changes";entryBaseline=entrySnapshot();updateEntryDirtyState();showPage("entry")}
async function changeEntryDay(offset){
 const current=$("#entry-form").elements.work_date.value;if(!current)return;
 if(entryIsDirty()){
  const save=confirm("You have unsaved changes. Save them before moving to another day?\n\nChoose OK to save, or Cancel to discard the changes.");
  if(save){if(!(await saveEntry()))return}
  else if(!confirm("Discard your unsaved changes and move to another day?"))return;
 }
 const next=parseLocalDate(current);next.setDate(next.getDate()+offset);const date=dateText(next);
 const rows=await api("api/shifts?start="+date+"&end="+date);shiftCache=shiftCache.filter(s=>s.work_date!==date).concat(rows);
 if(rows.length===1){editShift(rows[0].id);return}
 if(rows.length>1){
  const choice=prompt("There are multiple entries on "+date+". Enter the entry number to edit:\n"+rows.map((s,i)=>(i+1)+". "+s.start_time+"–"+s.finish_time+" ("+s.id+")").join("\n"));
  const index=Number(choice)-1;if(Number.isInteger(index)&&index>=0&&index<rows.length)editShift(rows[index].id);
  return;
 }
 newEntry(date);
}
function cancelEntry(){showPage("shifts")}
async function deleteShift(id){if(!confirm("Delete this time entry?"))return;await api("api/shifts/"+id,{method:"DELETE"});loadShifts();toast("Time entry deleted")}
async function deleteShift(id){if(!confirm("Delete this shift and linked travel?"))return;await api("api/shifts/"+id,{method:"DELETE"});loadShifts();toast("Shift deleted")}
async function loadReport(){try{if(!reportWeekStart)await initialiseReportWeek();const from=$("#report-start").value,to=$("#report-end").value,project=$("#report-project").value;$("#report-week-label").textContent="Week ending "+displayDate(parseLocalDate(to));const params=new URLSearchParams();if(from&&to){params.set("start",from);params.set("end",to)}if(project)params.set("project",project);const q=params.toString()?"?"+params.toString():"";const [report,allRows]=await Promise.all([api("api/report"+q),api("api/shifts"+(from&&to?"?start="+encodeURIComponent(from)+"&end="+encodeURIComponent(to):""))]);const rows=project?allRows.filter(s=>(s.project||"")===project):allRows;const calculated=new Map((report.shifts||[]).map(x=>[Number(x.id),x]));let total=0;const rateTotals={};$("#report-timesheet").innerHTML=rows.length?'<table><thead><tr><th>Date</th><th>Time in</th><th>Time out</th><th>Unpaid break</th><th>Project</th><th>Paid hours</th><th>Hours by rate</th><th>Entry</th><th>Notes</th></tr></thead><tbody>'+rows.map(s=>{const item=calculated.get(Number(s.id))||{};const raw=Math.max(0,timeMins(s.finish_time,s.start_time)-Number(s.break_minutes||0));const h=Number(item.payable_hours??(s.is_travelling?Math.min(raw,600)/60:raw/60));total+=h;const segments=item.segments||[];const breakdown=segments.map(seg=>{const label=seg.pay_code||seg.category||"Rate";const sh=Number(seg.hours||0);const mult=Number(seg.multiplier||1);const key=label;rateTotals[key]=(rateTotals[key]||0)+sh;return '<div class="rate-line">'+esc(label)+': '+hours(sh)+' @ '+mult.toFixed(2)+'×</div>'}).join("")||"—";return '<tr><td>'+esc(s.work_date)+'</td><td>'+(s.leave_type&&s.leave_type!=="work"?"—":esc(s.start_time))+'</td><td>'+(s.leave_type&&s.leave_type!=="work"?"—":esc(s.finish_time))+'</td><td>'+(s.leave_type&&s.leave_type!=="work"?"—":Number(s.break_minutes||0)+' min')+'</td><td>'+esc(s.project||'—')+'</td><td>'+hours(h)+'</td><td>'+breakdown+'</td><td>'+(s.leave_type==="annual_leave"?'Annual Leave':s.leave_type==="sick_leave"?'Sick Leave':s.is_travelling?'Travel':s.is_overseas?'Work – Overseas':s.is_public_holiday?'Public holiday':'Work')+'</td><td>'+esc(s.notes||"")+'</td></tr>'}).join("")+'</tbody></table>':'<div class="empty">No entries in this date range.</div>';(report.travel||[]).forEach(t=>{const key=t.pay_code||"Travel-OTH Ordinary 1.3";rateTotals[key]=(rateTotals[key]||0)+Number(t.hours||0)});const allowances=report.allowances||[];$("#report-allowances").innerHTML=allowances.length?'<table><thead><tr><th>Allowance</th><th>Allowance amount</th><th>Frequency</th><th>Basis</th><th>Amount</th></tr></thead><tbody>'+allowances.map(a=>'<tr><td>'+esc(a.name)+'</td><td>'+money(a.unit_amount??a.amount)+'</td><td>'+esc(a.frequency)+'</td><td>'+esc(a.basis)+'</td><td>'+money(a.amount)+'</td></tr>').join("")+'</tbody></table>':'<div class="empty">No allowances for this period.</div>';const codeOrder=["Ordinary 1.0","Ordinary 1.5","Overtime 1.5","Overtime 2.0","Public Holiday","Travel-OTH Ordinary 1.3","Travel-OTH Ordinary 1.8","Travel-OTH OT 1.8","Travel-OTH OT 2.3"];
const rateSummary=Object.entries(rateTotals).sort((a,b)=>{const ai=codeOrder.indexOf(a[0]),bi=codeOrder.indexOf(b[0]);return (ai<0?99:ai)-(bi<0?99:bi)||a[0].localeCompare(b[0])}).map(([k,v])=>'<tr><td>'+esc(k)+'</td><td class="summary-value">'+hours(v)+'</td></tr>').join("");

const amountRows=(items)=>items.map(([label,value,emphasis])=>'<tr class="'+(emphasis||'')+'"><td>'+label+'</td><td class="summary-value">'+money(value)+'</td></tr>').join("");
const summaryTable=(heading,headers,rows)=>'<div class="summary-group"><h3>'+heading+'</h3><table class="summary-table"><thead><tr><th>'+headers[0]+'</th><th>'+headers[1]+'</th></tr></thead><tbody>'+rows+'</tbody></table></div>';
const earningsRows=amountRows([["Total allowances",report.total_allowances||0],["Estimated gross",report.estimated_gross,"summary-emphasis"]]);
const taxRows=amountRows([["PAYG withholding",report.estimated_payg],["Additional withholding",report.payg_extra_withholding],["Total withheld",report.total_withheld,"summary-emphasis"],["Estimated take-home pay",report.estimated_net,"summary-net"]]);
$("#report-totals").innerHTML='<h3>Period totals</h3>'+summaryTable("Paid hours ("+hours(total)+")",["Payroll code","Hours"],rateSummary)+summaryTable("Allowances & earnings",["Description","Amount"],earningsRows)+summaryTable("Tax & take-home",["Description","Amount"],taxRows);}catch(e){toast("Could not load timesheet: "+e.message)}}
function downloadExport(type){const a=document.createElement("a");const start=$("#report-start").value,end=$("#report-end").value;const q=start&&end?"?start="+start+"&end="+end:"";a.href="api/export."+type+q;a.download="timesheet."+type;a.click()}
function clonePaygYears(value){return JSON.parse(JSON.stringify(value||{}))}
function renderPaygEditor(years,preferred){
 paygYears=clonePaygYears(years);const select=$("#payg-financial-year");
 if(!Object.keys(paygYears).length)paygYears["2026-27"]={resident_brackets:[{lower:0,upper:18200,base_tax:0,rate:0},{lower:18200,upper:45000,base_tax:0,rate:0.15},{lower:45000,upper:135000,base_tax:4020,rate:0.30},{lower:135000,upper:190000,base_tax:31020,rate:0.37},{lower:190000,upper:null,base_tax:51370,rate:0.45}]};
 const keys=Object.keys(paygYears).sort();selectedPaygYear=keys.includes(preferred)?preferred:(keys.includes("2026-27")?"2026-27":keys[keys.length-1]);
 select.innerHTML=keys.map(y=>'<option value="'+esc(y)+'">'+esc(y)+'</option>').join("");select.value=selectedPaygYear;renderResidentBrackets();
}
function snapshotPaygYear(){
 if(!selectedPaygYear)return;const rows=[...document.querySelectorAll("#payg-resident-brackets .resident-bracket-row")];
 paygYears[selectedPaygYear]={resident_brackets:rows.map((row,i)=>({lower:Number(row.querySelector('[data-key="lower"]').value||0),upper:i===rows.length-1?null:Number(row.querySelector('[data-key="upper"]').value),base_tax:Number(row.querySelector('[data-key="base_tax"]').value||0),rate:Number(row.querySelector('[data-key="rate"]').value||0)/100}))};
}
function renderResidentBrackets(){
 const rows=(paygYears[selectedPaygYear]||{}).resident_brackets||[];
 $("#payg-resident-brackets").innerHTML=rows.map((r,i)=>'<div class="resident-bracket-row"><input data-key="lower" type="number" min="0" aria-label="Income from" value="'+esc(r.lower??0)+'"><input data-key="upper" type="number" min="0" aria-label="Income to" placeholder="'+(i===rows.length-1?"No limit":"Upper limit")+'" value="'+(r.upper==null?"":esc(r.upper))+'" '+(i===rows.length-1?"disabled":"")+'><input data-key="base_tax" type="number" min="0" aria-label="Base tax" value="'+esc(r.base_tax??0)+'"><input data-key="rate" type="number" min="0" max="100" step="0.01" aria-label="Rate percent" value="'+(Number(r.rate||0)*100)+'"><button type="button" class="danger" onclick="removeResidentBracket('+i+')">Remove</button></div>').join("")||'<div class="empty">No tax brackets configured.</div>';
}
$("#payg-financial-year").addEventListener("change",e=>{snapshotPaygYear();selectedPaygYear=e.target.value;renderResidentBrackets()});
function addResidentBracket(){snapshotPaygYear();const rows=paygYears[selectedPaygYear].resident_brackets;const last=rows[rows.length-1],lower=last?Number(last.lower)+10000:0;if(last)last.upper=lower;rows.push({lower,upper:null,base_tax:last?Number(last.base_tax||0):0,rate:last?Number(last.rate||0):0});renderResidentBrackets()}
function removeResidentBracket(i){snapshotPaygYear();paygYears[selectedPaygYear].resident_brackets.splice(i,1);renderResidentBrackets()}
function addPaygYear(){const input=$("#payg-new-year"),year=input.value.trim();if(!/^[0-9]{4}-[0-9]{2}$/.test(year)){toast("Enter a financial year like 2027-28");return}snapshotPaygYear();if(paygYears[year]){selectedPaygYear=year;$("#payg-financial-year").value=year;renderResidentBrackets();return}paygYears[year]=clonePaygYears({[year]:paygYears[selectedPaygYear]})[year];selectedPaygYear=year;const select=$("#payg-financial-year");select.add(new Option(year,year));select.value=year;input.value="";renderResidentBrackets();toast("Year added — verify brackets against the ATO")}
function collectPaygYears(){snapshotPaygYear();for(const [year,entry] of Object.entries(paygYears)){const rows=entry.resident_brackets||[];if(!rows.length)throw new Error(year+" needs at least one bracket");rows.sort((a,b)=>a.lower-b.lower);if(Number(rows[0].lower)!==0)throw new Error(year+": first bracket must start at $0");for(let i=0;i<rows.length;i++){if(!Number.isFinite(rows[i].lower)||!Number.isFinite(rows[i].base_tax)||!Number.isFinite(rows[i].rate)||rows[i].base_tax<0||rows[i].rate<0||rows[i].rate>1)throw new Error(year+": check bracket values");if(i<rows.length-1&&(rows[i].upper==null||rows[i].upper<=rows[i].lower||rows[i].upper!==rows[i+1].lower))throw new Error(year+": bracket ranges must be continuous")}rows[rows.length-1].upper=null}return paygYears}
const DEFAULT_PAYROLL_CODES={public_holiday:"Public Holiday",annual_leave:"Annual Leave",sick_leave:"Sick Leave"};
const WEEKDAY_NAMES=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"];
function defaultTierCostCode(kind,r){const codes={ordinary_1_0:"Ordinary 1.0",ordinary_1_5:"Ordinary 1.5",overtime_1_5:"Overtime 1.5",overtime_2_0:"Overtime 2.0",travel_ordinary:"Travel-OTH Ordinary",travel_overtime:"Travel-OTH OT"};const after=Number(r.after_hours||0),mult=Number(r.multiplier||1);if(kind==="travel")return after===0?codes.travel_ordinary:codes.travel_overtime;if(after===0)return codes.ordinary_1_0;if(mult>=1.99)return codes.overtime_2_0;if(mult>=1.49)return after<=38?codes.ordinary_1_5:codes.overtime_1_5;return r.label||"Pay tier";}
function renderPayrollCodes(values){const codes={...DEFAULT_PAYROLL_CODES,...values};const keys=Object.keys(DEFAULT_PAYROLL_CODES);$("#payroll-code-rules").innerHTML=keys.map(key=>'<div class="rule-row payroll-code-row"><label>'+esc(key.replaceAll("_"," ").replace(/\\b\\w/g,c=>c.toUpperCase()))+'<input data-code-key="'+esc(key)+'" value="'+esc(codes[key])+'"></label></div>').join("");}
function collectPayrollCodes(){const result={};document.querySelectorAll("#payroll-code-rules [data-code-key]").forEach(el=>{result[el.dataset.codeKey]=el.value.trim()});return result}
function renderRules(kind,items){const target=$("#"+kind+"-rules");target.innerHTML=(items||[]).map((r,i)=>ruleRow(kind,r,i)).join("")||'<div class="empty">No rules configured.</div>'}
function ruleRow(kind,r,i){
 const input=(label,key,val,type="text")=>'<label>'+label+'<input data-key="'+key+'" type="'+type+'"'+(type==="number"?' step="0.01"':'')+' value="'+esc(val??"")+'"></label>';
 const select=(label,key,val,opts)=>'<label>'+label+'<select data-key="'+key+'">'+opts.map(o=>'<option value="'+o[0]+'" '+(String(val)===String(o[0])?"selected":"")+'>'+o[1]+'</option>').join("")+'</select></label>';
 let fields="";
 if(kind==="schedule"){const day=Number(r.day??i);fields='<div class="schedule-day-name">'+WEEKDAY_NAMES[day]+'</div><label class="check">Working day<input data-key="enabled" type="checkbox" '+(r.enabled?"checked":"")+'></label>'+input("Start","start_time",r.start_time,"time")+input("Finish","finish_time",r.finish_time,"time");}
 if(kind==="overtime"||kind==="travel"){fields=input("Tier description","label",r.label)+input("Cost code name","cost_code",r.cost_code||defaultTierCostCode(kind,r))+input("After hours","after_hours",r.after_hours,"number")+input("Multiplier","multiplier",r.multiplier,"number");}
 if(kind==="penalty")fields=input("Name","name",r.name)+select("Condition","condition",r.condition,[["day_of_week","Day of week"],["public_holiday","Public holiday"]])+select("Scope","scope",r.scope,[["work","Work"],["travel","Travel"],["both","Both"]])+input("Multiplier","multiplier",r.multiplier,"number")+select("Day","day",r.day??6,[[0,"Monday"],[1,"Tuesday"],[2,"Wednesday"],[3,"Thursday"],[4,"Friday"],[5,"Saturday"],[6,"Sunday"]])+select("Mode","mode",r.mode,[["replace","Replace rate"],["add","Additional"]]);
 if(kind==="allowance")fields=input("Name","name",r.name)+input("Amount ($)","amount",r.amount,"number")+select("Frequency","frequency",r.frequency,[["hourly","Per work hour"],["weekly","Fixed per week"],["fixed","Per work shift"]]);
 const rowIndex=kind==="schedule"?Number(r.day??i):i;
 return `<div class="rule-row" data-kind="${kind}" data-index="${rowIndex}">${fields}${kind==="schedule"?"":`<button type="button" onclick="removeRule('${kind}',${i})">Remove</button>`}</div>`;
}
function collectRules(kind){return [...document.querySelectorAll('#'+kind+'-rules .rule-row')].map(row=>{const o={};row.querySelectorAll("[data-key]").forEach(el=>{o[el.dataset.key]=el.type==="number"?Number(el.value):el.type==="checkbox"?el.checked:el.value});if(kind==="schedule"){o.day=Number(row.dataset.index);o.label=WEEKDAY_NAMES[o.day]}if(kind==="penalty"){o.enabled=true;o.day=Number(o.day??6)}return o})}
function addRule(kind){const defaults={overtime:{label:"New overtime",cost_code:"New overtime",after_hours:0,multiplier:1.5},travel:{label:"New travel tier",cost_code:"New travel",after_hours:0,multiplier:1.3},penalty:{name:"New penalty",condition:"day_of_week",scope:"work",multiplier:2,mode:"replace",enabled:true,day:6},allowance:{name:"New allowance",amount:0,frequency:"weekly"}};const id=kind==="overtime"?"overtime":kind==="travel"?"travel":kind==="penalty"?"penalty":"allowance";const current=collectRules(id);current.push(defaults[id]);renderRules(id,current)}
function removeRule(kind,index){const current=collectRules(kind);current.splice(index,1);renderRules(kind,current)}
function renderProjectSelects(projects){
 const options='<option value="">No project</option>'+(projects||[]).map(p=>'<option value="'+esc(p)+'">'+esc(p)+'</option>').join("");
 const entry=$("#entry-project");if(entry){const v=entry.value;entry.innerHTML=options;entry.value=v}
 const report=$("#report-project");if(report){const v=report.value;report.innerHTML='<option value="">All projects</option>'+(projects||[]).map(p=>'<option value="'+esc(p)+'">'+esc(p)+'</option>').join("");report.value=v}
}
function renderProjectManager(projects){
 const root=$("#project-list");if(!root)return;
 root.innerHTML=(projects||[]).map((p,i)=>'<div class="rule-row"><label>Project<input data-project-index="'+i+'" value="'+esc(p)+'" onchange="renameProject('+i+',this.value)"></label><button type="button" class="danger" onclick="removeProject('+i+')">Remove</button></div>').join("")||'<div class="empty">No projects created.</div>';
}
async function saveProjects(projects){
 settings.projects=projects;await api("api/settings",{method:"PUT",body:JSON.stringify({projects})});renderProjectManager(projects);renderProjectSelects(projects);
}
async function addProject(){
 const input=$("#new-project-name"),name=input.value.trim();if(!name)return;
 const projects=[...(settings.projects||[])];if(projects.some(p=>p.toLowerCase()===name.toLowerCase())){toast("Project already exists");return}
 projects.push(name);await saveProjects(projects);input.value="";
}
async function renameProject(index,value){
 const name=value.trim(),projects=[...(settings.projects||[])];if(!name)return renderProjectManager(projects);
 if(projects.some((p,i)=>i!==index&&p.toLowerCase()===name.toLowerCase())){toast("Project already exists");return renderProjectManager(projects)}
 const old=projects[index];projects[index]=name;
 try{await saveProjects(projects);await api("api/projects/rename",{method:"POST",body:JSON.stringify({old_name:old,new_name:name})});await loadShifts()}catch(e){toast("Could not rename project: "+e.message)}
}
async function removeProject(index){
 const name=(settings.projects||[])[index];if(!confirm("Remove project '"+name+"'? Existing time entries will be kept but unassigned."))return;
 const projects=[...(settings.projects||[])];projects.splice(index,1);
 await api("api/settings",{method:"PUT",body:JSON.stringify({projects})});
 await api("api/projects/remove",{method:"POST",body:JSON.stringify({name})});
 settings.projects=projects;renderProjectManager(projects);renderProjectSelects(projects);await loadShifts();
}
async function loadSettings(){settings=await api("api/settings");renderProjectManager(settings.projects||[]);renderProjectSelects(settings.projects||[]);const presenceLoaded=await loadPresenceEntities();const f=$("#settings-form");for(const [k,v] of Object.entries(settings)){if(f.elements[k])f.elements[k].value=v??""}renderPaygEditor(settings.payg_annual_years||settings.payg_years||{});renderRules("overtime",settings.overtime_tiers||[]);const savedSchedule=settings.normal_hours_schedule||[];const schedule=Array.from({length:7},(_,day)=>{const existing=savedSchedule.find(x=>Number(x.day)===day);return existing?{...existing,day}:{day,enabled:false,start_time:"05:30",finish_time:"16:00"}});renderRules("schedule",schedule);renderRules("travel",settings.travel_rules||[]);renderRules("penalty",settings.penalty_rules);renderRules("allowance",settings.allowances);renderPayrollCodes(settings.payroll_codes||{});showSettingsPanel("general");loadHolidays();if(presenceLoaded)$("#presence-status").textContent=settings.presence_entity&&(settings.work_zone_entities||[]).length?"Presence monitoring configured":"Choose a tracker and at least one work zone"}
$("#settings-form").addEventListener("submit",async e=>{e.preventDefault();const f=e.currentTarget;const d=formObject(f);d.presence_entity=d.presence_entity||"";d.work_zone_entities=[...$("#work-zone-entities").selectedOptions].map(o=>o.value);d.presence_grace_minutes=Number(d.presence_grace_minutes||30);d.presence_rounding_minutes=Number(d.presence_rounding_minutes||15);d.presence_start_time=d.presence_start_time||"05:30";d.base_rate=d.base_rate===""?null:Number(d.base_rate);d.custom_cycle_days=Number(d.custom_cycle_days);d.week_start_day=Number(d.week_start_day);d.ordinary_hours=Number(d.ordinary_hours);d.public_holiday_credit_hours=Number(d.public_holiday_credit_hours||0);d.public_holiday_credit_counts_toward_overtime=d.public_holiday_credit_counts_toward_overtime===""?null:d.public_holiday_credit_counts_toward_overtime==="true";d.payg_tax_free_threshold=d.payg_tax_free_threshold!=="false";d.payg_extra_withholding=Number(d.payg_extra_withholding||0);try{d.payg_annual_years=collectPaygYears()}catch(err){toast(err.message);return}delete d.payg_years;delete d.payg_tax_free_threshold;d.payroll_codes=collectPayrollCodes();d.normal_hours_schedule=collectRules("schedule");d.overtime_tiers=collectRules("overtime");d.travel_rules=collectRules("travel");d.penalty_rules=collectRules("penalty");d.allowances=collectRules("allowance");try{settings=await api("api/settings",{method:"PUT",body:JSON.stringify(d)});document.querySelectorAll(".settings-status").forEach(el=>el.textContent="Saved");toast("Settings saved")}catch(err){toast("Settings failed: "+err.message)}});
$("#holiday-form").addEventListener("submit",async e=>{e.preventDefault();await api("api/holidays",{method:"POST",body:JSON.stringify(formObject(e.currentTarget))});e.currentTarget.reset();setDefaultDates();loadHolidays();toast("Holiday saved")});
async function loadHolidays(){const rows=await api("api/holidays");$("#holiday-list").innerHTML=rows.map(h=>recordHtml(h.holiday_date,h.name,"Public holiday",'<button class="danger" onclick="deleteHoliday('+h.id+')">×</button>')).join("")||'<div class="empty">No public holidays added.</div>'}
async function deleteHoliday(id){await api("api/holidays/"+id,{method:"DELETE"});loadHolidays()}
$("#today").textContent=new Intl.DateTimeFormat(undefined,{dateStyle:"full"}).format(new Date());setDefaultDates();showPage(location.hash.slice(1)||"dashboard");
async function loadPresenceEntities(){
 const tracker=$("#presence-entity"),zones=$("#work-zone-entities");
 try{const data=await api("api/ha/entities");const people=data.filter(x=>x.domain==="person"||x.domain==="device_tracker"),work=data.filter(x=>x.domain==="zone");
 tracker.innerHTML='<option value="">Disabled</option>'+people.map(x=>'<option value="'+esc(x.entity_id)+'">'+esc(x.name)+' ('+esc(x.entity_id)+')</option>').join("");
 zones.innerHTML=work.map(x=>'<option value="'+esc(x.entity_id)+'">'+esc(x.name)+' ('+esc(x.entity_id)+')</option>').join("");
 tracker.value=settings.presence_entity||"";[...zones.options].forEach(o=>o.selected=(settings.work_zone_entities||[]).includes(o.value));
 $("#presence-status").textContent="Loaded "+people.length+" tracker entities and "+work.length+" zones from Home Assistant";return true;
 }catch(e){tracker.innerHTML='<option value="">Home Assistant unavailable</option>';zones.innerHTML="";$("#presence-status").textContent="Could not load entities: "+e.message;return false}
}
