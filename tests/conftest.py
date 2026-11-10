import asyncio
import copy
import json
from types import SimpleNamespace

import discord
import httpx
import pytest

import clients.rootme as rootme_module
import cogs.zoubi_cog as cog_module
from clients import RootMeClient
from cogs.zoubi_cog import ZoubiCog
from zoubiClient import ChallengesCache, ZoubiClient


def make_validation(challenge_id: str, date: str) -> dict:
    return {"id_challenge": challenge_id, "titre": f"Challenge {challenge_id}",
            "id_rubrique": "1", "date": date}


def make_author(author_id: str, nom: str, challenge_ids: list) -> dict:
    validations = [make_validation(cid, f"2026-11-0{i + 1} 10:00:00")
                   for i, cid in enumerate(challenge_ids)]
    validations.reverse()
    return {"id_auteur": author_id, "nom": nom, "score": str(20 * len(challenge_ids)),
            "logo_url": "IMG/logo/auton0.png", "validations": validations}


def stored_user(author: dict, missing: int = 0) -> dict:
    """Author as saved in users.json, missing its `missing` most recent validations."""
    user = copy.deepcopy(author)
    user["validations"] = user["validations"][missing:]
    user["score"] = str(20 * len(user["validations"]))
    user["profile_id"] = user["nom"]
    return user


class FakeRootMe:
    def __init__(self, authors: list):
        self.authors = {a["id_auteur"]: a for a in authors}
        self.faults = []
        self.calls = []

    def inject(self, prefix: str, *outcomes) -> None:
        """Next calls whose path starts with prefix get these outcomes.

        An outcome is a status code, a (status code, headers) tuple or an exception.
        """
        self.faults.extend((prefix, o) for o in outcomes)

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        self.calls.append((path, request.headers.get("cookie", "")))
        for i, (prefix, outcome) in enumerate(self.faults):
            if path.startswith(prefix):
                del self.faults[i]
                if isinstance(outcome, Exception):
                    raise outcome
                status, headers = outcome if isinstance(outcome, tuple) else (outcome, {})
                return httpx.Response(status, headers=headers, json={"error": status})

        if path == "/auteurs":
            name = request.url.params.get("nom", "").lower()
            found = [a for a in self.authors.values() if name in a["nom"].lower()]
            if not found:
                return httpx.Response(404, json=[{"error": "not found"}])
            return httpx.Response(200, json=[{str(i): {"id_auteur": a["id_auteur"], "nom": a["nom"]}
                                              for i, a in enumerate(found)}])
        if path.startswith("/auteurs/"):
            author = self.authors.get(path.rsplit("/", 1)[1])
            if author is None:
                return httpx.Response(404, json=[{"error": "not found"}])
            return httpx.Response(200, json=author)
        if path.startswith("/challenges/"):
            cid = path.rsplit("/", 1)[1]
            return httpx.Response(200, json=[{"titre": f"Challenge {cid}", "score": "20",
                                              "url_challenge": f"fr/Challenges/{cid}"}])
        return httpx.Response(404, json=[{"error": "not found"}])

    def paths(self, prefix: str) -> list:
        return [p for p, _ in self.calls if p.startswith(prefix)]


class FakeChannel:
    def __init__(self):
        self.sent = []
        self.texts = []
        self.fail_next = 0

    async def send(self, content=None, *, embed=None, **_):
        if self.fail_next:
            self.fail_next -= 1
            raise discord.HTTPException(SimpleNamespace(status=503, reason="test"), "fake outage")
        if embed is not None:
            self.sent.append(embed)
        if content is not None:
            self.texts.append(content)


class FakeInteraction:
    def __init__(self):
        self.messages = []
        self.response = SimpleNamespace(defer=self._defer, send_message=self._send)
        self.followup = SimpleNamespace(send=self._send)

    async def _defer(self, **_):
        pass

    async def _send(self, content=None, *, embed=None, **_):
        self.messages.append((content, embed))

    def texts(self) -> list:
        return [content for content, _ in self.messages if content]


@pytest.fixture
def authors() -> list:
    return [
        make_author("643003", "Aube", ["1", "2", "3", "4"]),
        make_author("822479", "Ssor", ["1", "5", "6"]),
        make_author("700001", "Kiwi", ["7"]),
    ]


@pytest.fixture
def fake_rootme(authors, monkeypatch) -> FakeRootMe:
    fake = FakeRootMe(authors + [make_author("123456", "NewPlayer", ["8"])])
    original = httpx.AsyncClient

    class MockClient(original):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(fake.handler)
            kwargs.pop("proxy", None)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", MockClient)
    return fake


@pytest.fixture
def sleeps(monkeypatch) -> list:
    recorded = []

    async def fake_sleep(seconds):
        recorded.append(seconds)

    monkeypatch.setattr(rootme_module, "asyncio", SimpleNamespace(sleep=fake_sleep, Lock=asyncio.Lock))
    monkeypatch.setattr(cog_module, "asyncio", SimpleNamespace(sleep=fake_sleep))
    return recorded


@pytest.fixture
async def rm_client(fake_rootme, sleeps) -> RootMeClient:
    client = await RootMeClient.create(api_keys=["key1", "key2"])
    yield client
    await client.close()


@pytest.fixture
def users_file(tmp_path) -> str:
    return str(tmp_path / "users.json")


@pytest.fixture
def channel() -> FakeChannel:
    return FakeChannel()


@pytest.fixture
def log_channel() -> FakeChannel:
    return FakeChannel()


@pytest.fixture
def make_cog(rm_client, users_file, tmp_path, channel, log_channel):
    def factory(users: list) -> ZoubiCog:
        with open(users_file, "w") as f:
            json.dump({"users": users}, f)
        bot = SimpleNamespace(get_channel=lambda id_: log_channel if id_ == 43 else channel,
                              tree=SimpleNamespace(sync=None))
        cache = ChallengesCache(str(tmp_path / "challenges.json"))
        return ZoubiCog(bot, rm_client, ZoubiClient(users_file), cache, 42, 43)

    return factory


def load_users(path: str) -> list:
    with open(path) as f:
        return json.load(f)["users"]
