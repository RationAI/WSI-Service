import os
import subprocess
from socket import socket

import docker as docker_py
import pytest
import requests
from requests.exceptions import ConnectionError

from wsi_service.tests.test_helper import fetch_test_data


def is_responsive(url):
    try:
        response = requests.get(url)
        print(response)
        if response.status_code == 200:
            return True
    except ConnectionError:
        return False


def free_port():
    """
    port 0 requests a random free port from the OS
    this is a work around, because setting port 0 in docker run does not work as expected
    in very rare cases this work around could result in a race condition
    """
    with socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def get_service_ports():
    port1 = free_port()
    port2 = free_port()
    while port1 == port2:
        port2 = free_port()
    return port1, port2


def add_absolute_test_dir_to_env():
    path = os.path.dirname(os.path.realpath(__file__))
    test_path = path.replace("/integration", "")
    port_wsi_service, port_isyntax = get_service_ports()

    with open(f"{path}/env_tests", "r") as f:
        content = f.readlines()

    new_content = ""
    for line in content:
        sline = line.split("=")
        if line.startswith("WS_DATA_PATH"):
            line = f"{sline[0]}={test_path}{sline[1]}"
        elif line.startswith("WS_PORT"):
            line = f"{sline[0]}={port_wsi_service}\n"
        elif line.startswith("WS_ISYNTAX_PORT"):
            line = f"{sline[0]}={port_isyntax}\n"
        new_content += line

    env_temp_file = f"{path}/env_tests_temp"
    with open(env_temp_file, "w") as f:
        f.writelines(new_content)
    return env_temp_file


@pytest.fixture(scope="session", autouse=True)
def copy_env():
    env_file = add_absolute_test_dir_to_env()
    subprocess.call(f"mv {env_file} .env", shell=True)


@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig, copy_env):
    return os.path.join(str(pytestconfig.rootdir), "docker-compose.yml")


@pytest.fixture(scope="session")
def wsi_service(docker_ip, docker_services, docker_compose_file, fetch_test_data):
    port = docker_services.port_for("wsi_service", 8080)
    url = f"http://{docker_ip}:{port}"
    docker_services.wait_until_responsive(timeout=30.0, pause=0.1, check=lambda: is_responsive(url))
    return url
