import requests
import json


def get_header(token, accept=False, content=False):
    header = {
        "Authorization": "Bearer {}".format(token),
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    fields = (
        ["Authorization"]
        + (["Accept"] if accept else [])
        + (["Content-Type"] if content else [])
    )
    return {k: v for k, v in header.items() if k in fields}


def handle_error(status_code):
    error_message = {
        400: "Bad Request",
        401: "Unauthorized",
        402: "Payment Required",
        403: "Forbidden",
        404: "Not Found",
        429: "Too Many Requests",
        451: "Unavailable For Legal Reasons",
        500: "Internal Server Error",
    }

    if status_code in error_message:
        raise RuntimeError(error_message[status_code])
    elif status_code not in [200, 201]:
        raise RuntimeError("Unown Error")


def asana_request(
    path,
    token,
    requests_type="get",
    accept=False,
    content=False,
    params=None,
    data=None,
):
    base_url = "https://app.asana.com/api/1.0"

    kwargs = {}
    if params:
        kwargs.update({"params": params})
    if data:
        kwargs.update({"data": json.dumps({"data": data})})

    response = {
        "get": requests.get,
        "post": requests.post,
        "put": requests.put
    }[requests_type](
        base_url + path,
        headers=get_header(token, accept=accept, content=content),
        **kwargs
    )

    handle_error(response.status_code)
    return response


def get_user_data(token, user_gid):
    path = "/users/{}".format(user_gid)
    response = asana_request(path=path, token=token)
    return response.json()["data"]


def get_workspaces(token):
    path = "/workspaces"
    response = asana_request(path=path, token=token, accept=True)
    return response.json()["data"]


def get_user_task_list_gid(token, user_gid, workspace_gid):
    path = "/users/{}/user_task_list".format(user_gid)
    params = {"workspace": workspace_gid}
    response = asana_request(path=path, token=token, accept=True, params=params)
    return response.json()["data"]["gid"]


def get_user_task_list(token, user_gid, workspace_gid):
    user_task_list_gid = get_user_task_list_gid(token, user_gid, workspace_gid)
    path = "/user_task_lists/{}/tasks".format(user_task_list_gid)
    params = {"completed_since": "now"}
    response = asana_request(path=path, token=token, accept=True, params=params)
    return response.json()["data"]


def get_projects(token, archived=False):
    path = "/projects"
    params = {"archived": archived}
    response = asana_request(path=path, token=token, accept=True, params=params)
    return response.json()["data"]


def create_task(token, data):
    """
    Example of data (one between workspace and projects must be specified)
    {"name": 'a name', 'projects': ['1198159140753433'], 'assignee': 'me'}
    """
    path = "/tasks"
    response = asana_request(
        path=path,
        token=token,
        requests_type="post",
        accept=True,
        content=True,
        data=data,
    )


def get_task(token, task_gid):
    path = "/tasks/{}".format(task_gid)
    response = asana_request(path=path, token=token, accept=True)
    return response.json()["data"]


def get_fields(task):
    return task["custom_fields"]


def get_field_value(task, field_gid):
    default_values = {
        "number": 0,
    }

    fields = get_fields(task)

    for field in fields:
        if field_gid == field["gid"]:
            field_type = field["type"]
            value_name = field_type + "_value"
            if value_name in field:
                res = field[value_name]
                return res or (default_values[field_type] if field_type in default_values else None)
            else:
                return ValueError("Field without value.")
    else:
        return ValueError("Field not found.")


def set_field_value(token, task_gid, field_gid, value):
    path = "/tasks/{}".format(task_gid)
    data = {"custom_fields": {field_gid: value}}
    response = asana_request(
        path=path,
        token=token,
        requests_type="put",
        accept=True,
        content=True,
        data=data,
    )


def complete_task(token, task_gid):
    path = "/tasks/{}".format(task_gid)
    data = {"completed": True}
    response = asana_request(
        path=path,
        token=token,
        requests_type="put",
        accept=True,
        content=True,
        data=data,
    )
