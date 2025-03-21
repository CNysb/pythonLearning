import sys
import gitlab
from collections import namedtuple
import unittest
from unittest.mock import Mock, MagicMock, patch, call
import os
from pathlib import Path
import json

from gitlab import Gitlab
from gitlab.v4.objects import Project
from html5tagger.util import attributes

sys.path.append(str(Path(__file__).parent))

# Import the class we're testing
from git_action import git_util


class TestGitUtil(unittest.TestCase):
    def setUp(self):
        self.mock_gitlab = MagicMock()
        self.mock_project = MagicMock()
        self.mock_file = MagicMock()
        self.mock_group = MagicMock()
        self.mock_tags = MagicMock()
        self.mock_files = MagicMock()
        self.mock_commits = MagicMock()

        self.gitlab_patcher = patch("git_action.Gitlab", return_value=self.mock_gitlab)
        self.mock_gitlab_class = self.gitlab_patcher.start()

        git_util._instance = None

        self.git_util = git_util(
            job_token="mock_job_token", personal_token="mock_personal_token"
        )

        self.git_util._fetch_project_id = MagicMock()

    def tearDown(self):
        self.gitlab_patcher.stop()

    def test_init(self):
       self.assertEqual(self.git_util.job_token, "mock_job_token")
       self.assertEqual(self.git_util.personal_token, "mock_personal_token")
       self.assertEqual(self.git_util.personal_git, self.mock_gitlab)
       self.mock_gitlab_class.assert_called_once_with(
           self.git_util.git_hostname, "mock_personal_token"
       )

    def test_singleton_pattern(self):
        another_instance = git_util(
            job_token="another_token", personal_token="another_token"
        )
        self.assertIs(self.git_util, another_instance)

    @patch("git_action.git_util")
    def test_get_next_int_tag(self, mock_project_class):
        mock_project = mock_project_class.return_value
        mock_tag1 = MagicMock()
        mock_tag1.attributes = {"name": "1"}
        mock_tag2 = MagicMock()
        mock_tag2.attributes = {"name": "2"}
        mock_tag3 = MagicMock()
        mock_tag3.attributes = {"name": "not_a_number"}
        mock_project.tags.list.return_value = [mock_tag1, mock_tag2, mock_tag3]
        result = self.git_util.get_next_int_tag(mock_project)
        self.assertEqual(result, 3)
        mock_project.tags.list.assert_called_once_with(ref_name="main")

    @patch("git_action.git_util")
    def test_get_next_int_tag_empty_list(self, mock_project_class):
        mock_project = mock_project_class.return_value
        mock_project.tags.list.return_value = []
        result = self.git_util.get_next_int_tag(mock_project)
        self.assertEqual(result, 1)

    @patch("git_action.git_util")
    def test_check_user_commit_tag_no_tag(self, mock_project_class):
        mock_project = mock_project_class.return_value
        mock_commit = MagicMock()
        mock_commit.get.return_value = None
        mock_project.commits.list.return_value = [mock_commit]
        self.git_util.add_tag = MagicMock()
        self.git_util.check_user_commit_tag(mock_project)
        mock_project.commits.list.assert_called_once_with(ref_name="main")
        mock_commit.get.assert_called_once_with("tag")
        self.git_util.add_tag.assert_called_once_with(project=mock_project)

    @patch("git_action.git_util")
    def test_check_user_commit_tag_with_tag(self, mock_project_class):
        mock_project = mock_project_class.return_value
        mock_commit = MagicMock()
        mock_commit.get.return_value = "some_tag"
        mock_project.commits.list.return_value = [mock_commit]
        self.git_util.add_tag = MagicMock()
        self.git_util.check_user_commit_tag(mock_project)
        mock_project.commits.list.assert_called_once_with(ref_name="main")
        mock_commit.get.assert_called_once_with("tag")
        self.git_util.add_tag.assert_not_called()

    def test_add_tag_with_project_id(self):
        mock_project = MagicMock()
        self.mock_gitlab.projects.get.return_value = mock_project
        self.git_util.add_tag = MagicMock()
        self.git_util.project_id_map = {"test_project": MagicMock(id=123)}
        self.git_util.add_tag_with_project_id(123)
        self.mock_gitlab.projects.get.assert_called_once_with(123)
        self.git_util.add_tag.assert_called_once_with(mock_project)

    @patch("git_action.git_util")
    def test_add_tag(self, mock_project_class):
        mock_project = mock_project_class.return_value
        self.git_util.get_next_int_tag = MagicMock(return_value=3)
        self.git_util.add_tag(mock_project)
        self.git_util.get_next_int_tag.assert_called_once_with(mock_project)
        mock_project.tags.create.assert_called_once_with({"tag_name": 3, "ref": "main"})
        mock_project.save.assert_called_once()

    @patch("git_action.gitlab.exceptions.GitlabGetError")
    @patch("git_action.git_util")
    def test_check_file_exist_true(self, mock_project_class, mock_gitlab_error):
        mock_project = mock_project_class.return_value
        result = self.git_util.check_file_exist(mock_project, "test/path")
        self.assertTrue(result)
        mock_project.files.get.assert_called_once_with(
            file_path="test/path", ref="main"
        )

    @patch("git_action.git_util")
    def test_check_file_exist_false(self, mock_project_class):
        self.mock_project.files.get.side_effect = gitlab.exceptions.GitlabGetError
        result = self.git_util.check_file_exist(self.mock_project, "test/path")
        self.assertFalse(result)

    def test_git_push(self):
        mock_project = MagicMock()
        mock_file = MagicMock()
        self.mock_gitlab.projects.get.return_value = mock_project
        mock_project.files.get.return_value = mock_file
        self.git_util.project_id_map = {"test_project": MagicMock(id=123)}
        self.git_util.add_tag = MagicMock()
        self.git_util.git_push("test/path", "test_project", "test content")
        self.mock_gitlab.projects.get.assert_called_once_with(123)
        mock_project.files.get.assert_called_once_with(
            file_path="test/path", ref="main"
        )
        self.assertEqual(mock_file.content, "test content")
        mock_file.save.assert_called_once_with(
            branch="main", commit_message="auto generate consolidate file"
        )
        self.git_util.add_tag.assert_called_once_with(project=mock_project)

    def test_git_push_create_file(self):
        self.mock_gitlab.projects.get.return_value = self.mock_project
        self.mock_project.files.get.side_effect = gitlab.exceptions.GitlabGetError
        self.git_util.project_id_map = {"test_project": MagicMock(id=123)}
        self.git_util.add_tag = MagicMock()
        self.git_util.git_push("test/path", "test_project", "test content")
        self.mock_project.files.create.assert_called_once()

    def test_git_push_multi_file(self):
        mock_project = MagicMock()
        self.mock_gitlab.projects.get.return_value = mock_project
        self.git_util.project_id_map = {"test_project": MagicMock(id=123)}
        self.git_util.check_file_exist = MagicMock(side_effect=[True, False])
        self.git_util.add_tag = MagicMock()
        mock_file1 = MagicMock()
        mock_file1.project_file_path = "test/path1"
        mock_file1.content = "test content 1"

        mock_file2 = MagicMock()
        mock_file2.project_file_path = "test/path2"
        mock_file2.content = "test content 2"
        self.git_util.git_push_multi_file("test_project", [mock_file1, mock_file2])
        self.mock_gitlab.projects.get.assert_called_once_with(123)
        self.git_util.check_file_exist.assert_has_calls(
            [call(mock_project, "test/path1"), call(mock_project, "test/path2")]
        )

        mock_project.commits.create.assert_called_once_with(
            {
                "branch": "main",
                "commit_message": "auto generate consolidate file",
                "actions": [
                    {
                        "file_path": "test/path1",
                        "content": "test content 1",
                        "action": "update",
                    },
                    {
                        "file_path": "test/path2",
                        "content": "test content 2",
                        "action": "create",
                    },
                ],
            }
        )
        self.git_util.add_tag.assert_called_once_with(project=mock_project)

    @patch("git_action.subprocess.run")
    @patch("git_action.os.path.join")
    @patch("git_action.os.mkdir")
    @patch("git_action.Path")
    def test_clone_repo(self, mock_path, mock_mkdir, mock_join, mock_run):
        mock_path_instance = MagicMock()
        mock_path.return_value = mock_path_instance
        mock_path_instance.parent.parent.parent = "/base/path"
        mock_path_instance.exists.return_value = True
        self.git_util._pre_setup = MagicMock()
        self.git_util._existing_project_update = MagicMock()
        self.git_util._clone = MagicMock()
        self.git_util.clone_repo()
        self.git_util._pre_setup.assert_called_once()
        self.git_util._existing_project_update.assert_called_once()
        self.git_util._clone.assert_called_once()

    @patch("git_action.subprocess.run")
    def test_update_project_action(self, mock_run):
        self.git_util._update_project_action("/test/path")
        mock_run.assert_called_once()

    @patch("git_action.Path")
    @patch("git_action.os.path.join")
    @patch("git_action.os.mkdir")
    def test_pre_setup_paths_exist(self, mock_mkdir, mock_join, mock_path):
        mock_common_path = MagicMock()
        mock_domain_path = MagicMock()
        mock_path.side_effect = [mock_common_path, mock_domain_path]
        mock_common_path.exists.return_value = True
        mock_domain_path.exists.return_value = True
        mock_join.side_effect = ["/base/common", "/base/domain"]
        self.git_util._pre_check = MagicMock()
        self.git_util.base_location = "/base"
        self.git_util._pre_setup()
        mock_join.assert_has_calls(
            [call("/base", "common_rule"), call("/base", "data_domain")]
        )
        self.git_util._pre_check.assert_has_calls(
            [call(mock_common_path), call(mock_domain_path)]
        )
        mock_mkdir.assert_not_called()

    @patch("git_action.Path")
    @patch("git_action.os.path.join")
    @patch("git_action.os.mkdir")
    def test_pre_setup_paths_dont_exist(self, mock_mkdir, mock_join, mock_path):
        mock_common_path = MagicMock()
        mock_domain_path = MagicMock()
        mock_path.side_effect = [mock_common_path, mock_domain_path]
        mock_common_path.exists.return_value = False
        mock_domain_path.exists.return_value = False
        mock_join.side_effect = ["/base/common", "/base/domain"]
        self.git_util.base_location = "/base"
        self.git_util._pre_setup()
        mock_mkdir.assert_has_calls([call(mock_common_path), call(mock_domain_path)])

    @patch("git_action.git_util")
    def test_get_project_file_with_tag(self, mock_project_class):
        mock_project = mock_project_class.return_value
        mock_tag = MagicMock()
        mock_tag.commit = {"id": "commit_id"}
        mock_project.tags.get.return_value = mock_tag
        mock_file = MagicMock()
        mock_file.decode.return_value = '{"key": "value"}'
        mock_project.files.get.return_value = mock_file
        result = self.git_util.get_project_file_with_tag(
            mock_project, "tag_name", "file_path"
        )
        mock_project.tags.get.assert_called_once_with("tag_name")
        mock_project.files.get.assert_called_once_with("file_path", ref="commit_id")
        mock_file.decode.assert_called_once()
        self.assertEqual(result, {"key": "value"})

    def test_project(self):
        mock_project = MagicMock()
        self.mock_gitlab.projects.get.return_value = mock_project
        self.git_util.project_id_map = {"test_project": MagicMock(id=123)}
        result = self.git_util.project("TEST_PROJECT")
        self.mock_gitlab.projects.get.assert_called_once_with(123)
        self.assertEqual(result, mock_project)

    def test_figure_detail(self):
        detail = namedtuple(
            "detail", ["is_common", "id", "name", "git_url", "http_url"]
        )
        mock_project = MagicMock(attributes={
            "id": 1,
            "name": "mock",
            "path_with_namespace": "mock",
            "http_url_to_repo": "mock"
        })
        self.git_util._figure_detail(mock_project,True, detail)
        self.assertEqual(self.git_util.project_id_map["mock"].id, 1)

    @patch("git_action.subprocess.run")
    def test_clone(self, mock_run):
        detail = namedtuple(
            "detail", ["is_common", "git_url"]
        )
        self.git_util.project_id_map["mock"] = detail(is_common=True, git_url="mock")
        self.git_util._clone()
        mock_run.assert_called_once()

    def test_existing_project_update_failed(self):
        self.git_util.existing_project_list = list()
        self.git_util._existing_project_update()


    @patch("git_action.subprocess.run")
    @patch("git_action.os.path.join")
    def test_existing_project_update(self, mock_join, mock_run):
        detail = namedtuple("detail", ["is_common", "name"])
        self.git_util.existing_project_list = [detail(is_common=True, name="mock")]
        mock_join.return_value = "mock"
        self.git_util._existing_project_update()
        mock_run.assert_called_once()

    def test_pre_check_fail(self):
        folder_path = Mock()
        folder_path.iterdir.return_value = []
        self.git_util._pre_check(folder_path)

    def test_pre_check(self):
        folder_path = Mock()
        folder_path.iterdir.return_value = ["mock/common"]
        self.git_util.project_id_map['common'] = "mock"
        self.git_util._pre_check(folder_path)
        self.assertIn("mock", self.git_util.existing_project_list)

if __name__ == "__main__":
    unittest.main()
