from pathlib import Path
from tempfile import TemporaryDirectory

from storage import Storage


def test_add_enable_delete():
    with TemporaryDirectory() as d:
        s = Storage(Path(d) / "w.db")
        watch_id = s.add(10, "2026-10-01", 2, "스탠다드더블")
        row = s.list(10)[0]
        assert row.id == watch_id
        assert row.checkout == "2026-10-03"
        assert s.set_enabled(10, watch_id, False)
        assert not s.list(10)[0].enabled
        assert s.delete(10, watch_id)
        assert s.list(10) == []

