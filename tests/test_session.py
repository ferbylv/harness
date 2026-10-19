from harness.session import Session
from harness.store import SessionStore
from harness.types import Message, Role, Usage
from harness.workspace import Workspace


def test_save_load_roundtrip(tmp_path):
    ws = Workspace(tmp_path)
    session = Session.start(ws, model="demo")
    session.add(Message(role=Role.USER, content="hi"))
    session.record_usage(Usage(prompt_tokens=10, completion_tokens=4, cost_usd=0.01))
    store = SessionStore(ws)
    store.save(session)
    loaded = store.load(session.id)
    assert loaded.messages[0].content == "hi"
    assert loaded.prompt_tokens == 10
    assert loaded.cost_usd == 0.01
    assert store.latest_id() == session.id
    assert store.latest().id == session.id


def test_load_drops_legacy_system_message(tmp_path):
    path = tmp_path / "old.json"
    path.write_text(
        '{"id":"abc","messages":[{"role":"system","content":"old"},{"role":"user","content":"hi"}]}',
        encoding="utf-8",
    )
    loaded = Session.load(path)
    assert [m.role for m in loaded.messages] == [Role.USER]


def test_reset_gets_new_id(tmp_path):
    ws = Workspace(tmp_path)
    session = Session.start(ws, model="a")
    old = session.id
    session.add(Message(role=Role.USER, content="x"))
    session.reset(ws, model="b")
    assert session.id != old
    assert session.messages == []
    assert session.model == "b"
