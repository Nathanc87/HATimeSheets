"""Home Assistant zone presence integration for automatic work shifts."""
import asyncio, json, os, urllib.request
from datetime import datetime, timedelta
from .db import connect, get_settings, save_settings, now_iso
HA_URL=os.environ.get("HASS_URL","http://supervisor/core/api")
HA_TOKEN=os.environ.get("SUPERVISOR_TOKEN","")
def _ha_get(path):
    if not HA_TOKEN: raise RuntimeError("Supervisor API token is not available")
    req=urllib.request.Request(HA_URL.rstrip("/") + path,headers={"Authorization":"Bearer "+HA_TOKEN,"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=8) as response: return json.loads(response.read().decode())
def get_ha_entities():
    states=_ha_get("/states"); result=[]
    for item in states:
        eid=item.get("entity_id",""); domain=eid.split(".",1)[0]
        if domain in ("person","device_tracker","zone"):
            result.append({"entity_id":eid,"name":item.get("attributes",{}).get("friendly_name",eid),"domain":domain,"state":item.get("state","")})
    return sorted(result,key=lambda x:(x["domain"],x["name"].lower()))
def _now(): return datetime.now().astimezone()
def _clock(dt): return dt.strftime("%H:%M")
def _round(dt,interval):
    interval=max(1,int(interval or 15)); mins=dt.hour*60+dt.minute
    rounded=int((mins+interval/2)//interval)*interval; rounded%=1440
    return f"{rounded//60:02d}:{rounded%60:02d}"
def _zone(state,names):
    if not state or state in ("unknown","unavailable","not_home","home"): return None
    val=str(state).strip().casefold()
    return next((eid for eid,name in names.items() if val in (eid.casefold(),name.casefold())),None)
def _save(db,settings,session):
    settings["presence_session"]=session; save_settings(db,settings)
def _start(db,settings,now):
    start=settings.get("presence_start_time") or "05:30"
    cur=db.execute("""INSERT INTO shifts(work_date,start_time,finish_time,break_minutes,notes,is_public_holiday,is_travelling,is_overseas,created_at,updated_at)
    VALUES(?,?,?,?,?,?,?,?,?,?)""",(now.date().isoformat(),start,_clock(now),30,"Automatically recorded from Home Assistant work-zone presence",0,0,0,now_iso(),now_iso()))
    return cur.lastrowid
def _process(state,zones,now):
    with connect() as db:
        settings=get_settings(db); selected=settings.get("work_zone_entities") or []
        if not settings.get("presence_entity") or not selected: return
        names={z["entity_id"]:z["name"] for z in zones if z["entity_id"] in selected}
        current=_zone(state,names); session=settings.get("presence_session")
        grace=max(0,int(settings.get("presence_grace_minutes",30))); rounding=int(settings.get("presence_rounding_minutes",15))
        if session:
            pending=datetime.fromisoformat(session["pending_until"]) if session.get("pending_until") else None
            if current:
                if pending and now<=pending:
                    session.update({"pending_until":None,"departure_at":None,"current_zone":current})
                    db.execute("UPDATE shifts SET finish_time=?,updated_at=? WHERE id=?",(_clock(now),now_iso(),session["shift_id"]))
                    _save(db,settings,session); return
                if not pending and session.get("current_zone"):
                    session["current_zone"]=current
                    db.execute("UPDATE shifts SET finish_time=?,updated_at=? WHERE id=?",(_clock(now),now_iso(),session["shift_id"]))
                    _save(db,settings,session); return
            elif session.get("current_zone") and not pending:
                session["departure_at"]=now.isoformat()
                session["pending_until"]=(now+timedelta(minutes=grace)).isoformat()
                db.execute("UPDATE shifts SET finish_time=?,updated_at=? WHERE id=?",(_round(now,rounding),now_iso(),session["shift_id"]))
                session["current_zone"]=None; _save(db,settings,session); return
            if pending and now>pending:
                _save(db,settings,None); session=None
        if current and session is None:
            shift_id=_start(db,settings,now)
            _save(db,settings,{"shift_id":shift_id,"current_zone":current,"started_at":now.isoformat(),"departure_at":None,"pending_until":None})
async def presence_poll():
    while True:
        try:
            with connect() as db: settings=get_settings(db)
            tracker=settings.get("presence_entity"); selected=settings.get("work_zone_entities") or []
            if tracker and selected and HA_TOKEN:
                states=await asyncio.to_thread(_ha_get,"/states"); byid={x.get("entity_id"):x for x in states}
                state=byid.get(tracker,{}).get("state"); zones=[]
                for eid in selected:
                    item=byid.get(eid)
                    if item: zones.append({"entity_id":eid,"name":item.get("attributes",{}).get("friendly_name",eid)})
                await asyncio.to_thread(_process,state,zones,_now())
        except asyncio.CancelledError: raise
        except Exception as exc: print(f"Presence monitor warning: {exc}",flush=True)
        await asyncio.sleep(10)
