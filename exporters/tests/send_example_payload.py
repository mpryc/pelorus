import subprocess
import requests
import json
from datetime import datetime
import time
import hashlib
import secrets

PELORUS_NAMESPACE = "test-pelorus-operator"

TIME_IN_S_BETWEEN_EVENTS = 60

def get_webhook_route(exporter_name="webhook-exporter", namespace=None):
    command = ["oc", "get", "route", exporter_name]
    if namespace:
        command += ["-n", namespace]
    command += ["--template='{{ .spec.host }}'"]

    webhook_route = subprocess.check_output(command).decode("utf-8").strip("\n\r")
    return webhook_route


def generate_sha256_hash_signature(payload_json, secret_value):
    command = [
        "echo", "-n", payload_json, "|", "openssl", "dgst", "-sha256", "-hmac", secret_value, "|", "cut", "-d", " ", "-f", "2"
    ]
    sha256_hash_signature = subprocess.check_output(command).decode("utf-8").strip("\n\r")
    return sha256_hash_signature


def send_request(webhook_route, payload_data, header_pelorus_event, secret_value=""):
    header_user_agent = "Pelorus-Webhook/e2e"
    header_content = "application/json"
    headers = {
        "User-Agent": header_user_agent,
        "X-Pelorus-Event": header_pelorus_event,
        "Content-Type": header_content
    }

    if secret_value:
        payload_json = json.dumps(payload_data)
        sha256_hash_signature = generate_sha256_hash_signature(payload_json, secret_value)
        headers["X-Hub-Signature-256"] = f"X-Hub-Signature-256: sha256={sha256_hash_signature}"

    payload_json = json.dumps(payload_data)
    webhook_route_url = "http://" + webhook_route.strip("'") + "/pelorus/webhook"

    print(f"Webhook: {webhook_route_url}, Headers: {headers}, Payload: {payload_json}")
    response = requests.post(
        webhook_route_url,
        headers=headers,
        data=payload_json,
    )
    print(response.text)
    return response

def send_payload(webhook_route, payload_data=None, header_pelorus_event=None, secret_value="", namespace=None):
    if payload_data is None or header_pelorus_event is None:
        return
    response = send_request(webhook_route, payload_data, header_pelorus_event, secret_value)
    return response

def get_commit_hash_value(length: int):
    num_bytes = length // 2
    random_string = secrets.token_hex(num_bytes)
    sha256_hash = hashlib.sha256()
    sha256_hash.update(random_string.encode('utf-8'))
    return sha256_hash.hexdigest()[:length]

def send_events(x: int, y: int, z: int):
    """
    x, y and z represents every N-th time to sent
         commit, deployment and failure payload
    """

    webhook_route=get_webhook_route()

    counter = 1

    while True:
        image_hash=get_commit_hash_value(64)
        commit_hash=get_commit_hash_value(40)
        failure_no = (failure_no + 1) if 'failure_no' in locals() else 1
        
        payload_data_commit = {
            "app": "mongo-todolist",
            "commit_hash": commit_hash,
            "image_sha": f"sha256:{image_hash}",
            "namespace": "mongo-persistent",
            "timestamp": int(datetime.now().timestamp()),
        }

        if counter % x == 0:
            send_payload(webhook_route, payload_data_commit, header_pelorus_event="committime", namespace="test-pelorus-operator")
        time.sleep(TIME_IN_S_BETWEEN_EVENTS)

        payload_data_deploy = {
            "app": "mongo-todolist",
            "image_sha": f"sha256:{image_hash}",
            "namespace": "mongo-persistent",
            "timestamp": int(datetime.now().timestamp()),
        }
        
        if counter % y == 0:
            send_payload(webhook_route, payload_data_deploy, header_pelorus_event="deploytime", namespace="test-pelorus-operator")
        time.sleep(TIME_IN_S_BETWEEN_EVENTS)

        payload_failure_create = {
          "app": "mongo-todolist",
          "failure_id": f"MONGO-{failure_no}",
          "failure_event": "created",
          "timestamp": int(datetime.now().timestamp()),
        }

        if counter % z == 0:
            send_payload(webhook_route, payload_failure_create, header_pelorus_event="failure", namespace="test-pelorus-operator")
        time.sleep(TIME_IN_S_BETWEEN_EVENTS)

        payload_failure_resolve = {
          "app": "mongo-todolist",
          "failure_id": f"MONGO-{failure_no}",
          "failure_event": "resolved",
          "timestamp": int(datetime.now().timestamp()),
        }

        if counter % z == 0:
            send_payload(webhook_route, payload_failure_resolve, header_pelorus_event="failure", namespace="test-pelorus-operator")
            time.sleep(TIME_IN_S_BETWEEN_EVENTS)
        counter += 1

send_events(1, 1, 2)
