"""Store the v28 deployment lesson via the canonical Store.append path."""
import sys
from datetime import datetime

sys.path.insert(0, r"D:\dsh\repos\memory-palace\src")
from eventmem.paths import MemoryPaths
from eventmem.schema import Anchors, make_event, new_id
from eventmem.store import Store

PROJECT = r"D:\dsh workspace\dsh test project"
paths = MemoryPaths.for_project(PROJECT)
store = Store(paths)
eid = new_id(datetime.now(), set(store.all_ids()))
e = make_event(
    event_id=eid,
    kind="decision",
    status="done",
    intent="Redo gorilla composite on the user's new headless body and deploy v28.",
    anchors=Anchors(
        commits=["b06519b"],
        files=["bombjack.html", "assets/final_small/gorilla/", "assets/final_small/roach/"],
        dialog=["redo the gorilla", "roach should be 50% bigger"],
    ),
    outcome=(
        "v28 deployed as b06519b. New headless gorilla body (user-drawn white "
        "ellipse at center 388.5,235.5 rx=81.5 ry=103.5 in 980x980); face crop "
        "centered on actual eye_mid (not old baseline center), masked to a "
        "full-crop ellipse, scaled to fill the body ellipse, body cropped to "
        "820x880. Roach head 50% bigger (head_target_h 230->345). Draw sizes "
        "roach 36x74, gorilla 40x43. Push succeeded in one shot: credential "
        "manager + seeded username horaboral = no interactive account screen."
    ),
    lesson=(
        "For face-into-body composites, crop centered on the detected face's "
        "eye_mid, not on a stale baseline center. Mask with a full-crop ellipse. "
        "GitHub push needs no screen: credential.helper=manager plus "
        "credential.https://github.com.username=horaboral is enough."
    ),
    body="v28 deploy: new gorilla body, roach 50% bigger, comparable sizes.",
    salience_prior="high",
    salience_reason="Reusable composite + deploy recipe.",
)
store.append(e)
print("stored", eid)
