import json
import os
import discord
from rootmeClient import RootMeClient
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


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
        with open(self.users_file, "w") as f:
            users_json = {"users": self.users_list}
            f.write(json.dumps(users_json))
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
