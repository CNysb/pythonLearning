import unittest
from pathlib import Path
import sys
from unittest import TestCase
from unittest.mock import Mock, patch
from gitlab import Gitlab
from gitlab.v4.objects import Project, Group

sys.path.append(str(Path(__file__).parent))
import git_action
from git_action import git_util


class test_git_action(TestCase):
    @patch("git_action.Gitlab")
    @patch("git_action.git_util")
    def test_init(self, mock_git_util, mock_Gitlab):
        g1 = git_util()
        g2 = git_util()
        self.assertEqual(g1, g2)


    # @patch("gitlab.Gitlab")
    # def setUp(self, mock_gitlab):
    #     top_group = Mock(spec=Group)
    #     common_group = Mock(spec=Group)
    #     domain_group = Mock(spec=Group)
    #     self.git_util = git_util(job_token="mock_job_token", personal_token="mock_personal_token")
    #     self.git_util.personal_git = mock_gitlab
    #     mock_gitlab.groups.get.return_value = top_group
    #     top_group.subgroups.list.return_value = [common_group, domain_group]


if __name__ == "__main__":
    pass
