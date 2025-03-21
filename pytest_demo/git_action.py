from collections import namedtuple
from typing import Dict, List
import json
import subprocess
import os
import logging
from pathlib import Path

import gitlab
from gitlab import Gitlab
from gitlab.v4.objects import Project

LOGGER = logging.getLogger(__name__)


class git_util:
    branch_name = "main"
    _instance = None
    git_hostname = "https://gitlab.dx1.lseg.com/"
    COMMON_GROUP_ID = 181187
    DOMAIN_GROUP_ID = 181188
    COMMON_DIRNAME = "common_rule"
    DOMAIN_DIRNAME = "data_domain"
    top_group_id = 181186

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(git_util, cls).__new__(cls)
        return cls._instance

    def __init__(self, job_token=None, personal_token=None):
        self.job_token = job_token
        self.personal_token = personal_token
        self.personal_git: Gitlab = None
        self.project_id_map = dict()
        self._init_git(job_token=job_token, personal_token=personal_token)
        self._fetch_project_id()
        self.base_location = Path(__file__).parent.parent.parent
        self.existing_project_list: List = list()

    def _init_git(self, job_token, personal_token):
        LOGGER.info("INIT GIT UTIL ...")
        self.personal_git = Gitlab(self.git_hostname, personal_token)

    def get_next_int_tag(self, project: Project):
        tag_list = project.tags.list(ref_name=self.branch_name)
        int_tag_list = list()
        for tag in tag_list:
            t = tag.attributes["name"]
            if str(t).isdigit():
                int_tag_list.append(int(t))
        int_tag_list.sort(reverse=True)
        print(int_tag_list)
        if len(int_tag_list) != 0:
            next_tag = int_tag_list[0] + 1
        else:
            next_tag = 1
        return next_tag

    def check_user_commit_tag(self, user_project: Project):
        commit_list = user_project.commits.list(ref_name=self.branch_name)
        last_commit = commit_list[0]
        if last_commit.get("tag") is None:
            self.add_tag(project=user_project)

    def add_tag_with_project_id(self, project_id):
        LOGGER.info("ADD TAG...")
        user_project = self.personal_git.projects.get(project_id)
        self.add_tag(user_project)

    def add_tag(self, project: Project):
        LOGGER.info("ADD TAG...")
        next_tag = self.get_next_int_tag(project)
        project.tags.create({"tag_name": next_tag, "ref": self.branch_name})
        project.save()

    def git_push_multi_file(self, project_name, file_list):
        LOGGER.info("GIT PUSH MULTI FILE...")
        project_id = self.project_id_map.get(project_name).id
        project = self.personal_git.projects.get(project_id)
        files = list()
        for file in file_list:
            file_desc = dict()
            file_desc["file_path"] = str(file.project_file_path)
            file_desc["content"] = file.content
            if self.check_file_exist(project, str(file.project_file_path)):
                file_desc["action"] = "update"
            else:
                file_desc["action"] = "create"
            files.append(file_desc)
        LOGGER.info(f"files are {files}")
        project.commits.create(
            {
                "branch": self.branch_name,
                "commit_message": "auto generate consolidate file",
                "actions": files,
            }
        )
        self.add_tag(project=project)

    def check_file_exist(self, project: Project, file_path):
        try:
            project.files.get(file_path=file_path, ref=self.branch_name)
            return True
        except gitlab.exceptions.GitlabGetError:
            return False

    def git_push(self, project_file_path, project_name, content):
        LOGGER.info("GIT PUSH ...")
        project_id = self.project_id_map.get(project_name).id
        project = self.personal_git.projects.get(project_id)
        logging.info(f"PROJECT NAME: {project_name}, PROJECT_ID: {project_id}...")

        try:
            file = project.files.get(
                file_path=str(project_file_path), ref=self.branch_name
            )
            file.content = content
            file.save(
                branch=self.branch_name, commit_message="auto generate consolidate file"
            )
        except gitlab.exceptions.GitlabGetError:
            project.files.create(
                {
                    "file_path": str(project_file_path),
                    "branch": self.branch_name,
                    "content": content,
                    "commit_message": "CI/CD: Auto-generated consolidated expectation suite",
                }
            )

        self.add_tag(project=project)

    def _fetch_project_id(self):
        LOGGER.info("FETCH GIT REPO INFO")
        detail = namedtuple(
            "detail", ["is_common", "id", "name", "git_url", "http_url"]
        )
        sub_group_list = self.personal_git.groups.get(self.top_group_id).subgroups.list(
            all=True
        )
        for group in sub_group_list:
            group_id = group.attributes["id"]

            project_list = self.personal_git.groups.get(group_id).projects.list()
            is_common = True if group_id == self.COMMON_GROUP_ID else False
            list(
                map(
                    lambda project: self._figure_detail(project, is_common, detail),
                    project_list,
                )
            )

    def _figure_detail(self, project: Project, is_common: bool, detail):
        proj_map = project.attributes
        proj_detail = detail(
            is_common,
            proj_map["id"],
            str(proj_map["name"]).lower(),
            proj_map["path_with_namespace"],
            proj_map["http_url_to_repo"],
        )
        self.project_id_map[str(project.attributes["name"]).lower()] = proj_detail

    def clone_repo(self):
        self._pre_setup()
        self._existing_project_update()
        self._clone()

    def _existing_project_update(self):
        if len(self.existing_project_list) == 0:
            return
        for proj in self.existing_project_list:
            proj_parent_name = (
                self.COMMON_DIRNAME if proj.is_common else self.DOMAIN_DIRNAME
            )
            project_path = os.path.join(self.base_location, proj_parent_name, proj.name)
            self._update_project_action(project_path)

    def _update_project_action(self, project_path):
        subprocess.run(
            f"""
            cd {str(project_path)} && git pull
            """,
            shell=True,
        )

    def _pre_setup(self):
        common_path = Path(os.path.join(self.base_location, self.COMMON_DIRNAME))
        domain_path = Path(os.path.join(self.base_location, self.DOMAIN_DIRNAME))
        if common_path.exists():
            self._pre_check(common_path)
        else:
            os.mkdir(common_path)
        if domain_path.exists():
            self._pre_check(domain_path)
        else:
            os.mkdir(domain_path)

    def _pre_check(self, folder_path: Path):
        sub_proj_list = list(folder_path.iterdir())
        if sub_proj_list is None or len(sub_proj_list) == 0:
            return
        sub_proj_name_list = list(
            map(lambda proj_path: str(proj_path).split("/")[-1], sub_proj_list)
        )
        for proj_name in sub_proj_name_list:
            if proj_name in self.project_id_map:
                self.existing_project_list.append(self.project_id_map.pop(proj_name))

    def _clone(self):
        GITLAB_URL = f"https://gitlab-ci-token:{self.job_token}@gitlab.dx1.lseg.com"
        for proj_detail in self.project_id_map.values():
            proj_location = os.path.join(
                self.base_location,
                self.COMMON_DIRNAME if proj_detail.is_common else self.DOMAIN_DIRNAME,
            )

            subprocess.run(
                f"""
                cd {str(proj_location)} && git clone {GITLAB_URL}/{str(proj_detail.git_url)}.git
                """,
                shell=True,
            )

    def project(self, project_name):
        project_id = self.project_id_map.get(str(project_name).lower()).id
        return self.personal_git.projects.get(project_id)

    def get_project_file_with_tag(self, project: Project, tag_name, file_path) -> Dict:
        tag = project.tags.get(tag_name)
        file = project.files.get(file_path, ref=tag.commit["id"]).decode()
        return json.loads(file)


if __name__ == "__main__":
    pass
