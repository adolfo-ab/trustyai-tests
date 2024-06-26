import pytest
import yaml
from ocp_resources.configmap import ConfigMap
from ocp_resources.namespace import Namespace
from ocp_resources.resource import get_client
from ocp_resources.service_account import ServiceAccount

from trustyai_tests.resources.storage.minio_pod import MinioPod
from trustyai_tests.resources.storage.minio_secret import MinioSecret
from trustyai_tests.resources.storage.minio_service import MinioService
from trustyai_tests.resources.trustyai_service import TrustyAIService
from trustyai_tests.constants import (
    TRUSTYAI_SERVICE,
)


@pytest.fixture(scope="session")
def client():
    yield get_client()


@pytest.fixture(scope="class")
def model_namespace(client):
    with Namespace(
        client=client,
        name="test-namespace",
        label={"modelmesh-enabled": "true"},
        delete_timeout=600,
    ) as ns:
        ns.wait_for_status(status=Namespace.Status.ACTIVE, timeout=120)
        yield ns


@pytest.fixture(scope="class")
def modelmesh_serviceaccount(client, model_namespace):
    with ServiceAccount(client=client, name="modelmesh-serving-sa", namespace=model_namespace.name):
        yield


@pytest.fixture(scope="session")
def cluster_monitoring_config(client):
    config_yaml = yaml.dump({"enableUserWorkload": "true"})
    with ConfigMap(
        name="cluster-monitoring-config",
        namespace="openshift-monitoring",
        data={"config.yaml": config_yaml},
    ) as cm:
        yield cm


@pytest.fixture(scope="session")
def user_workload_monitoring_config(client):
    config_yaml = yaml.dump({"prometheus": {"logLevel": "debug", "retention": "15d"}})
    with ConfigMap(
        name="user-workload-monitoring-config",
        namespace="openshift-user-workload-monitoring",
        data={"config.yaml": config_yaml},
    ) as cm:
        yield cm


@pytest.fixture(scope="class")
def trustyai_service(
    client,
    model_namespace,
    modelmesh_serviceaccount,
):
    with TrustyAIService(
        name=TRUSTYAI_SERVICE,
        namespace=model_namespace.name,
        storage_format="PVC",
        storage_folder="/inputs",
        storage_size="1Gi",
        data_filename="data.csv",
        data_format="CSV",
        metrics_schedule_interval="5s",
        client=client,
    ) as trusty:
        yield trusty


@pytest.fixture(scope="class")
def minio_service(client, model_namespace):
    with MinioService(
        name="minio",
        port=9000,
        target_port=9000,
        namespace=model_namespace.name,
        client=client,
    ) as ms:
        yield ms


@pytest.fixture(scope="class")
def minio_pod(client, model_namespace):
    with MinioPod(
        client=client,
        name="minio",
        namespace=model_namespace.name,
        image="quay.io/trustyai/modelmesh-minio-examples:gauss",
    ) as mp:
        yield mp


@pytest.fixture(scope="class")
def minio_secret(client, model_namespace):
    with MinioSecret(
        client=client,
        name="aws-connection-minio-data-connection",
        namespace=model_namespace.name,
        # Dummy AWS values
        aws_access_key_id="VEhFQUNDRVNTS0VZ",
        aws_default_region="dXMtc291dGg=",
        aws_s3_bucket="bW9kZWxtZXNoLWV4YW1wbGUtbW9kZWxz",
        aws_s3_endpoint="aHR0cDovL21pbmlvOjkwMDA=",
        aws_secret_access_key="VEhFU0VDUkVUS0VZ",
    ) as ms:
        yield ms


@pytest.fixture(scope="class")
def minio_data_connection(minio_service, minio_pod, minio_secret):
    yield minio_secret
