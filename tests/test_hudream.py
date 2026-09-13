import pytest

from hudream import Room, SiteBackoff, SiteChanged, parse_search_response


def test_parse_search_response_requires_both_counts_for_caller():
    rooms = parse_search_response({
        "list": [
            {"qrtrs_type": "스탠다드더블", "rcnt": "2", "cnt": "1"},
            {"qrtrs_type": "한강뷰", "rcnt": 3, "cnt": 0},
        ]
    })
    assert rooms == [Room("스탠다드더블", 2, 1), Room("한강뷰", 3, 0)]
    assert [room.room_type for room in rooms if room.rcnt > 0 and room.cnt > 0] == ["스탠다드더블"]


def test_parse_search_response_detects_overload():
    with pytest.raises(SiteBackoff):
        parse_search_response({"msg": 1, "list": []})


@pytest.mark.parametrize("payload", [None, {}, {"list": None}, {"list": [{"qrtrs_type": "A", "rcnt": "bad", "cnt": 1}]}])
def test_parse_search_response_rejects_changed_schema(payload):
    with pytest.raises(SiteChanged):
        parse_search_response(payload)
