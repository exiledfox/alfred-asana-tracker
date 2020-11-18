import getpass
import os
import time

from asana.api import get_field_value, get_task, set_field_value
from workflow import PasswordNotFound

EPSILON = 0.00001


def get_default_workspace_gid(wf):
    if "workspace_gid" not in wf.settings:
        wf.add_item("Select default Workspace", valid=True, arg="%set_workspace")
        wf.send_feedback()
        return 0
    else:
        return wf.settings["workspace_gid"]


def get_default_project_gid(wf):
    if "project_gid" not in wf.settings:
        wf.add_item("Select default Project", valid=True, arg="%set_project")
        wf.send_feedback()
        return 0
    else:
        return wf.settings["project_gid"]


def get_token(wf):
    try:
        return wf.get_password("asana_personal_access_token")
    except PasswordNotFound:
        wf.add_item(
            "Not authenticated",
            "Click to set your Personal Access Token",
            valid=True,
            arg="%set_token",
        )
        wf.send_feedback()
        return 0


def stop_task(wf, task_gid):
    """Update spent hours on Asana, update Alfred history (for the report)
    and return elapsed hours.
    """
    token = get_token(wf)
    task_info = wf.stored_data("task_info")
    task = task_info[task_gid]
    field_gid = task["spent_hours_field_gid"]
    spent_hours = task["spent_hours"]

    # align alfred with asana
    asn_spent_hours = get_field_value(get_task(token, task_gid), field_gid)
    if round(spent_hours) != round(asn_spent_hours):
        spent_hours = asn_spent_hours

    start_timestamp = task["start_timestamp"]
    end_timestamp = time.time()
    elapsed_hours = (end_timestamp - start_timestamp) / 3600
    spent_hours = spent_hours + elapsed_hours
    set_field_value(token, task_gid, field_gid, spent_hours)

    # update task_history
    task_history = wf.stored_data("task_history")
    task = get_task(token, task_gid)
    task_history.append(
        {
            "task": {
                k: v for k, v in task.items() if k in ["name", "gid", "projects", "permalink_url"]
            },
            "start_timestamp": start_timestamp,
            "end_timestamp": end_timestamp,
        }
    )
    wf.store_data("task_history", task_history)

    # update task_info
    task_info[task_gid]["start_timestamp"] = None
    task_info[task_gid]["spent_hours"] = spent_hours
    wf.store_data("task_info", task_info)

    return elapsed_hours


def string_to_seconds(string):
    sub = string.split(" ")
    if len(sub) not in [1, 2]:
        return False
    if len(sub) == 2:
        try:
            n = float(sub[0])
        except:
            return False
    else:
        n = 1

    suff = "s" if n != 1 else ""
    units = {
        "second" + suff: 1,
        "minute" + suff: 60,
        "hour" + suff: 60 * 60,
        "day" + suff: 24 * 60 * 60,
        "week" + suff: 7 * 24 * 60 * 60,
        "month" + suff: 30 * 24 * 60 * 60,
        "year" + suff: 365 * 24 * 60 * 60,
    }

    if sub[-1] not in units:
        return False

    return n * units[sub[-1]]


def generate_report(wf, query):
    seconds = string_to_seconds(query)
    assert seconds

    user = getpass.getuser()
    dir = wf.cachedir
    file_name = "asana-report.md"

    path = os.path.join(dir, file_name)

    title = "Asana {} report".format(query)
    headers = ["Task", "Projects", "Hours", "Percentage"]
    style = [":-", ":-:", "-:", "-:"]
    format = ["{}", "{}", "{:.1f}", "{:.0f}%"]

    min_timestamp = time.time() - seconds
    rows = {}
    task_history = wf.stored_data("task_history")
    for i in range(len(task_history)):
        item = task_history[-(i + 1)]
        task = item["task"]
        if item["end_timestamp"] < min_timestamp:
            break
        if task["gid"] not in rows:
            rows[task["gid"]] = {
                "Task": task["name"],
                "Projects": "<br>".join([e["name"] for e in task["projects"]]),
                "Hours": 0,
            }
        rows[task["gid"]]["Hours"] += (
            item["end_timestamp"] - max(item["start_timestamp"], min_timestamp)
        ) / 3600
    tot_hours = sum([value["Hours"] for value in rows.values()]) if rows else 0
    for key in rows:
        rows[key]["Percentage"] = rows[key]["Hours"] / tot_hours * 100

    content = "#{}\n".format(title)
    content += "|{}|\n".format("|".join(headers))
    content += "|{}|\n".format("|".join(style))
    content += "".join(
        [
            (u"|{}|\n".format("|".join(format))).format(*[row[header] for header in headers])
            for row in rows.values()
        ]
    )
    content += "|" + (len(headers) * "|") + "\n"
    content += ("|{}|".format("|".join(format))).format("**Total**", "", tot_hours, 100)

    file = open(path, "w")
    file.write(content.encode("utf-8"))
    file.close()

    command = (
        "qlmanage -p "
        + path.replace(" ", "\ ")
        + " -c .md -g "
        + "/Users/"
        + user.replace(" ", "\ ")
        + "/Library/QuickLook/QLMarkdown.qlgenerator"
        + " >/dev/null 2>&1 &"
    )
    os.system(command)
