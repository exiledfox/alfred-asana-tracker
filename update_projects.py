import os
import sys

from asana.api import get_projects
from utils import EPSILON
from workflow import Workflow3


def main(wf):
    token = wf.get_password("asana_personal_access_token")
    wf.cached_data("get_projects", lambda: get_projects(token), max_age=EPSILON)
    return 0


if __name__ == "__main__":
    wf = Workflow3()
    sys.exit(wf.run(main))
