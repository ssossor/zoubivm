import json
import os
import discord
from clients import RootMeClient
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


def write_json_file(path: str, data) -> None:
    """
    Write data as JSON to path, through a temporary file and an atomic rename.

    Args:
        path: Destination file
        data: JSON-serializable data
    """
    tmp_path = path + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(data, f)
    os.replace(tmp_path, path)


class ZoubiClient:
    users_file = None
    users_list = []

    def __init__(self, users_file: str):
        self.users_file = users_file

        if not os.path.exists(users_file):
            with open(users_file, "a") as f:
                f.write('{"users":[]}')
            logger.info(f"File {users_file} created!")
        else:
            logger.info(f"Fetching data from {users_file}...")
            with open(users_file, "r") as f:
                d = json.load(f)
                self.users_list = d["users"]
            logger.info(f"File {users_file} loaded!")
        logger.info("Zoubi Client initialized!")

    def save_users_list_to_file(self):
        """
        Save self.users_list to the file at self.users_file
        """
        write_json_file(self.users_file, {"users": self.users_list})
        logger.info(f"File {self.users_file} saved!")

    def list_users(self) -> str:
        """
        Basic listing for registered users
        """
        return "\n".join([key["nom"] + " | " + key["score"] + " | " + key["id_auteur"] for key in self.users_list])

    def get_user_from_username(self, username: str) -> dict:
        """
        Return user data from its username
        """
        for user in self.users_list:
            if user["nom"] == username:
                return user
        return None

    def get_user_from_id(self, user_id: str) -> dict:
        """
        Return user data from its ID
        """
        for user in self.users_list:
            if user["id_auteur"] == user_id:
                return user
        return None

    def get_all_users(self):
        """
        Return all registered users data
        """
        return self.users_list

    def set_all_users(self, users: list):
        """
        Setter for all registered users
        """
        self.users_list = users

    def register_user(self, user_data: dict):
        """
        Add user data to self.users_list and save it to self.users_file file
        """
        try:
            self.users_list.append(user_data)
            self.save_users_list_to_file()
        except Exception as err:
            raise err

    def remove_user(self, user_id: str) -> dict | None:
        """
        Remove a user from registered users from its ID
        """
        deleted_user_data = None
        try:
            for i in range(len(self.users_list)):
                if self.users_list[i]["id_auteur"] == user_id:
                    deleted_user_data = self.users_list[i]
                    del self.users_list[i]
                    break
            if deleted_user_data is not None:
                self.save_users_list_to_file()
            return deleted_user_data
        except Exception as err:
            raise err


class ChallengesCache:
    """
    Challenges already fetched from Root-Me, persisted in a JSON file.
    """

    def __init__(self, cache_file: str):
        self.cache_file = cache_file
        self.challenges = {}

        if os.path.exists(cache_file):
            with open(cache_file, "r") as f:
                self.challenges = json.load(f)
        logger.info(f"{len(self.challenges)} challenges loaded from {cache_file}")

    def get(self, challenge_id: str) -> dict | None:
        """
        Return cached challenge data, or None if unknown.

        Args:
            challenge_id: Challenge ID

        Returns:
            Challenge data or None
        """
        return self.challenges.get(challenge_id)

    def add(self, challenge_id: str, chall_data: dict) -> None:
        """
        Add a challenge to the cache and save it to self.cache_file.

        Args:
            challenge_id: Challenge ID
            chall_data: Challenge data from the API
        """
        self.challenges[challenge_id] = {
            "titre": chall_data["titre"],
            "score": chall_data["score"],
            "url_challenge": chall_data["url_challenge"],
        }
        write_json_file(self.cache_file, self.challenges)
