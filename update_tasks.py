import os, sys
from workflow import Workflow3
from asana.api import get_user_task_list

EPSILON = float(os.getenv('EPSILON'))


def main(wf):
	token = wf.get_password('asana_personal_access_token')
	workspace_gid = wf.settings["workspace_gid"]
	wf.cached_data(
		"get_user_task_list",
		lambda: get_user_task_list(token, "me", workspace_gid),
		max_age=EPSILON
	)
	return 0

if __name__ == "__main__":
	wf = Workflow3()
	sys.exit(wf.run(main))
