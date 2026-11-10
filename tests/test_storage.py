import json

import pytest

import zoubiClient
from zoubiClient import ChallengesCache, ZoubiClient


def test_crash_during_save_keeps_previous_file(users_file, monkeypatch):
    with open(users_file, "w") as f:
        json.dump({"users": [{"nom": "Aube", "score": "80", "id_auteur": "643003"}]}, f)
    client = ZoubiClient(users_file)
    client.users_list.append({"nom": "Ssor", "score": "60", "id_auteur": "822479"})

    def crash(data, f):
        f.write('{"users": [')
        raise OSError("disk full")

    monkeypatch.setattr(zoubiClient.json, "dump", crash)
    with pytest.raises(OSError):
        client.save_users_list_to_file()
    monkeypatch.undo()

    with open(users_file) as f:
        assert [u["nom"] for u in json.load(f)["users"]] == ["Aube"]


def test_save_users_list(users_file):
    with open(users_file, "w") as f:
        json.dump({"users": []}, f)
    client = ZoubiClient(users_file)

    client.register_user({"nom": "Aube", "score": "80", "id_auteur": "643003"})

    assert [u["nom"] for u in ZoubiClient(users_file).get_all_users()] == ["Aube"]


def test_challenges_cache_is_persisted(tmp_path):
    cache_file = str(tmp_path / "challenges.json")
    cache = ChallengesCache(cache_file)
    assert cache.get("85") is None

    cache.add("85", {"titre": "Challenge 85", "score": "20",
                     "url_challenge": "fr/Challenges/85", "id_challenge": "85"})

    assert ChallengesCache(cache_file).get("85") == {
        "titre": "Challenge 85", "score": "20", "url_challenge": "fr/Challenges/85"}
