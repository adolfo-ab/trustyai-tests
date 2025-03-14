import time
from io import StringIO

import argparse
import json
import logging
import os
import pathlib
import sys
from time import sleep
import yaml
import multiprocessing
from multiprocessing import Process

from ocp_resources.catalog_source import CatalogSource
from ocp_resources.data_science_cluster import DataScienceCluster
from ocp_resources.dsc_initialization import DSCInitialization
from ocp_resources.mariadb_operator import MariadbOperator
from ocp_resources.namespace import Namespace
from ocp_resources.package_manifest import PackageManifest
from ocp_resources.pod import Pod
from ocp_resources.resource import get_client

from ocp_utilities.operators import install_operator

from timeout_sampler import TimeoutSampler, TimeoutExpiredError

from trustyai_tests.tests.utils import (
    log_namespace_events,
    get_num_running_containers,
    log_namespace_pods,
    log_namespace_logs,
)

logger: logging.Logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

DEFAULT_REPO = "https://github.com/trustyai-explainability/trustyai-service-operator/tarball/main"
RECHECK_INTERVAL = 5


# === UTILITIES ====================================================================================
def header(text):
    logger.info("")
    logger.info(f"============== {text} ==============")


def check_sampler(sampler, success_msg, fail_msg):
    """Run a timeout sampler, logging success_msg or fail_msg as applicable"""
    try:
        for check in sampler:
            if check:
                logger.info(success_msg)
                break
    except TimeoutExpiredError as e:
        logger.error(fail_msg)
        raise e


# === OPERATOR INSTALL PRECHECKS ===================================================================
def wait_for_catalog_sources(client, operator_data):
    """Make sure all requested catalog sources are available"""
    header("Waiting for Catalog Sources")

    for catalog_source in {o["catalogSource"] for o in operator_data}:
        sampler = TimeoutSampler(
            wait_timeout=300,
            sleep=RECHECK_INTERVAL,
            func=lambda: any(catalog_source == s.name for s in CatalogSource.get(dyn_client=client)),
            print_func_log=False,
        )

        check_sampler(sampler, f"{catalog_source} catalog found", f"Timeout: {catalog_source} catalog not found")


def wait_for_package_manifests(client, operator_data):
    """Make sure the package manifest for each requested operator is available"""
    header("Waiting for Package Manifests")

    for operator in operator_data:
        sampler = TimeoutSampler(
            wait_timeout=900,
            sleep=RECHECK_INTERVAL,
            func=lambda target_name: any(
                package_manifest.name == target_name for package_manifest in PackageManifest.get(dyn_client=client)
            ),
            print_func_log=False,
            target_name=operator["name"],
        )

        check_sampler(
            sampler,
            f"{operator['name']} package manifest found",
            f"Timeout: {operator['name']} package manifest not found",
        )


# === OPERATOR INSTALL =============================================================================
def install_operators(client, operator_data):
    """Install the specified operator"""
    header("Installing Operators")

    processes = []
    multiprocessing.set_start_method("fork")
    for operator in operator_data:
        p = Process(
            target=install_operator,
            kwargs={
                "admin_client": client,
                "target_namespaces": [],
                "name": operator["name"],
                "channel": operator["channel"],
                "source": operator["catalogSource"],
                "operator_namespace": operator["namespace"],
                "timeout": 900,
                "install_plan_approval": "Manual",
                "starting_csv": f"{operator['name']}.v{operator['version']}",
            },
        )
        p.start()
        time.sleep(1)

        processes.append(p)
    [p.join() for p in processes]


def verify_operator_running(client, operator_data):
    """Make sure all operator pods are running"""
    header("Verifying Operator Pods")

    for operator in operator_data:
        for target_pod_name in operator["correspondingPods"]:
            sampler = TimeoutSampler(
                wait_timeout=300,
                sleep=RECHECK_INTERVAL,
                func=lambda target_name: any(
                    target_pod_name in pod.name and get_num_running_containers(pod) == 1
                    for pod in Pod.get(dyn_client=client, namespace=operator["namespace"])
                ),
                print_func_log=False,
                target_name=target_pod_name,
            )

            check_sampler(
                sampler, f"{operator['name']} pod running", f"Timeout waiting for {operator['name']} pod to start"
            )


# === ODH INSTALL ==================================================================================
def create_odh_namespace(client):
    if not any("opendatahub" == ns.name for ns in Namespace.get()):
        ns = Namespace(
            client=client,
            name="opendatahub",
            delete_timeout=600,
        ).deploy()
        ns.wait_for_status(status=Namespace.Status.ACTIVE, timeout=120)


def install_dsci(client):
    """Install a default DSCI"""
    header("Installing DSCI")

    dsci = DSCInitialization(client=client, yaml_file="trustyai_tests/manifests/dsci.yaml")
    dsci.deploy()


def install_datascience_cluster(client, trustyai_manifests_url):
    """Install a DSC that uses the specified manifests url"""
    header("Installing Datascience Cluster")

    logger.info(f"Using manifests from {trustyai_manifests_url}")
    with open("trustyai_tests/manifests/dsc_template.yaml", "r") as f:
        template = f.read()
    config = template.replace("TRUSTYAI_REPO_PLACEHOLDER", trustyai_manifests_url)

    dsc = DataScienceCluster(client=client, yaml_file=StringIO(config))
    dsc.deploy()
    dsc.wait_for_status(status=DataScienceCluster.Status.READY, timeout=900)


def install_mariadb_operator_cr(client, namespace):
    """Install a mariadboperator instance"""
    header("Installing MariaDBOperator CR")
    mdb_op = MariadbOperator(
        client=client,
        yaml_file="trustyai_tests/manifests/mariadb-operator.yaml",
        namespace=namespace,
    )
    mdb_op.deploy()
    mdb_op.wait_for_condition(condition="Deployed", status=mdb_op.Condition.Status.TRUE, timeout=10 * 60)


# === MAIN =========================================================================================
def setup_cluster(args):
    # load config info
    try:
        operator_config_yaml = os.path.join(pathlib.Path(__file__).parent.resolve(), "operators_config.yaml")
        with open(operator_config_yaml, "r") as fr:
            operator_data = yaml.load(fr, yaml.Loader)
            fr.seek(0)
            with open(os.path.join(args.artifact_dir, "operators_config.yaml"), "w") as fw:
                fw.write(fr.read())
    except FileNotFoundError as e:
        logger.error(f"Operator config yaml {operator_config_yaml} not found:")
        logger.error(e)
        raise e

    namespaces = {od["name"]: od["namespace"] for od in operator_data}

    client = get_client()

    # make sure cluster is ready for operator installation
    if not args.skip_operators_installation:
        logger.info("Installing the following operator configurations: " + json.dumps(operator_data, indent=4))
        wait_for_catalog_sources(client, operator_data)
        wait_for_package_manifests(client, operator_data)

        # install prereq operators
        install_operators(client, operator_data)
        verify_operator_running(client, operator_data)

        install_mariadb_operator_cr(client, namespaces["mariadb-operator"])

    if not args.skip_dsc_installation:
        # create odh namespace
        create_odh_namespace(client)

        # install and setup ODH
        install_dsci(client)
        install_datascience_cluster(client, args.trustyai_manifests_url)

    for namespace in ["opendatahub"] + list(set(namespaces.values())):
        log_namespace_pods(args.artifact_dir, namespace=namespace, directory="cluster-setup")
        log_namespace_events(args.artifact_dir, client=client, namespace=namespace, directory="cluster-setup")
        log_namespace_logs(args.artifact_dir, namespace=namespace, directory="cluster-setup")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="TrustyAI CI Cluster Setup",
        description="Configure a fresh Openshift cluster in preparation " "for the TrustyAI CI test suite",
    )
    parser.add_argument(
        "--trustyai_manifests_url",
        help="URL of the TrustyAI manifests tarball. Defaults to `main` if not specified.",
        default=DEFAULT_REPO,
    )
    parser.add_argument(
        "--skip_operators_installation",
        help="Whether to skip the installation the prerequisite operators. Use this flag if they are already "
        "installed on your cluster.",
        action="store_true",
    )
    parser.add_argument(
        "--skip_dsc_installation",
        help="Whether to skip the installation of the ODH DataScienceCluster. Use this flag if you already have a "
        "DataScienceCluster running.",
        action="store_true",
    )
    parser.add_argument("--artifact_dir", help="Directory where test artifacts are stored.", default="/tmp/")
    args = parser.parse_args()

    setup_cluster(args)
