import http

import pytest
from ocp_resources.inference_service import InferenceService
from ocp_resources.namespace import Namespace
from ocp_resources.trustyai_service import TrustyAIService

from trustyai_tests.tests.metrics import Metric, get_metric_endpoint
from trustyai_tests.tests.utils import (
    verify_trustyai_model_metadata,
    send_data_to_inference_service,
    verify_trustyai_metric_prometheus,
    verify_metric_request,
    verify_metric_scheduling,
    upload_data_to_trustyai_service,
    wait_for_modelmesh_pods_registered,
)
from trustyai_tests.tests.constants import (
    MODEL_DATA_PATH,
)


@pytest.mark.openshift
@pytest.mark.pvc
@pytest.mark.modelmesh
class TestDriftMetricsPVC:
    """
    Verifies the different input data drift metrics available in TrustyAI, using PVC storage.
    Drift metrics: Meanshift, FourierMMD, KSTest, and ApproxKSTest.

    1. Send data to the model (gaussian_credit_model).
    2. Upload training data for TrustyAI (used as baseline to calculate the drift metrics).
    3. For each metric:
        3.1. Send a basic request and verify the response.
        3.2. Send a schedule request and verify the response.
        3.3. Verify that the metric has reached Prometheus.
    """

    def test_gaussian_credit_model_metadata_pvc(
        self, model_namespace: Namespace, trustyai_service_pvc: TrustyAIService, gaussian_credit_model: InferenceService
    ) -> None:
        wait_for_modelmesh_pods_registered(namespace=model_namespace)

        path = f"{MODEL_DATA_PATH}/{gaussian_credit_model.name}"

        send_data_to_inference_service(
            inference_service=gaussian_credit_model,
            namespace=model_namespace,
            data_path=f"{path}/data_batches",
        )

        response = upload_data_to_trustyai_service(
            namespace=model_namespace,
            data_path=f"{path}/training_data.json",
        )
        assert response.status_code == http.HTTPStatus.OK

        verify_trustyai_model_metadata(
            namespace=model_namespace,
            model=gaussian_credit_model,
            data_path=path,
        )

    def test_request_meanshift_pvc(
        self, model_namespace: Namespace, trustyai_service_pvc: TrustyAIService, gaussian_credit_model: InferenceService
    ) -> None:
        verify_metric_request(
            namespace=model_namespace,
            endpoint=get_metric_endpoint(metric=Metric.MEANSHIFT),
            expected_metric_name=Metric.MEANSHIFT.value.upper(),
            json_data={"modelId": gaussian_credit_model.name, "referenceTag": "TRAINING"},
        )

    def test_schedule_meanshift_pvc(
        self, model_namespace: Namespace, trustyai_service_pvc: TrustyAIService, gaussian_credit_model: InferenceService
    ) -> None:
        verify_metric_scheduling(
            namespace=model_namespace,
            endpoint=get_metric_endpoint(metric=Metric.MEANSHIFT, schedule=True),
            json_data={"modelId": gaussian_credit_model.name, "referenceTag": "TRAINING"},
        )

    def test_meanshift_prometheus_query_pvc(
        self, model_namespace: Namespace, trustyai_service_pvc: TrustyAIService, gaussian_credit_model: InferenceService
    ) -> None:
        verify_trustyai_metric_prometheus(
            namespace=model_namespace,
            model=gaussian_credit_model,
            prometheus_query=f'trustyai_{Metric.MEANSHIFT.value}{{namespace="{model_namespace.name}"}}',
            metric_name=Metric.MEANSHIFT.value,
        )

    def test_request_fouriermmd_pvc(
        self, model_namespace: Namespace, trustyai_service_pvc: TrustyAIService, gaussian_credit_model: InferenceService
    ) -> None:
        verify_metric_request(
            namespace=model_namespace,
            endpoint=get_metric_endpoint(metric=Metric.FOURIERMMD),
            expected_metric_name=Metric.FOURIERMMD.value.upper(),
            json_data={"modelId": gaussian_credit_model.name, "referenceTag": "TRAINING"},
        )

    def test_schedule_fouriermmd_pvc(
        self, model_namespace: Namespace, trustyai_service_pvc: TrustyAIService, gaussian_credit_model: InferenceService
    ) -> None:
        verify_metric_scheduling(
            namespace=model_namespace,
            endpoint=get_metric_endpoint(metric=Metric.FOURIERMMD, schedule=True),
            json_data={"modelId": gaussian_credit_model.name, "referenceTag": "TRAINING"},
        )

    def test_fouriermmd_prometheus_query_pvc(
        self, model_namespace: Namespace, trustyai_service_pvc: TrustyAIService, gaussian_credit_model: InferenceService
    ) -> None:
        verify_trustyai_metric_prometheus(
            namespace=model_namespace,
            model=gaussian_credit_model,
            prometheus_query=f'trustyai_{Metric.FOURIERMMD.value}{{namespace="{model_namespace.name}"}}',
            metric_name=Metric.FOURIERMMD.value,
        )

    def test_request_kstest_pvc(
        self, model_namespace: Namespace, trustyai_service_pvc: TrustyAIService, gaussian_credit_model: InferenceService
    ) -> None:
        verify_metric_request(
            namespace=model_namespace,
            endpoint=get_metric_endpoint(metric=Metric.KSTEST),
            expected_metric_name=Metric.KSTEST.value.upper(),
            json_data={"modelId": gaussian_credit_model.name, "referenceTag": "TRAINING"},
        )

    def test_schedule_kstest_scheduling_request_pvc(
        self, model_namespace: Namespace, trustyai_service_pvc: TrustyAIService, gaussian_credit_model: InferenceService
    ) -> None:
        verify_metric_scheduling(
            namespace=model_namespace,
            endpoint=get_metric_endpoint(metric=Metric.KSTEST, schedule=True),
            json_data={"modelId": gaussian_credit_model.name, "referenceTag": "TRAINING"},
        )

    def test_kstest_prometheus_query_pvc(
        self, model_namespace: Namespace, trustyai_service_pvc: TrustyAIService, gaussian_credit_model: InferenceService
    ) -> None:
        verify_trustyai_metric_prometheus(
            namespace=model_namespace,
            model=gaussian_credit_model,
            prometheus_query=f'trustyai_{Metric.KSTEST.value}{{namespace="{model_namespace.name}"}}',
            metric_name=Metric.KSTEST.value,
        )

    def test_request_approxkstest_pvc(
        self, model_namespace: Namespace, trustyai_service_pvc: TrustyAIService, gaussian_credit_model: InferenceService
    ) -> None:
        verify_metric_request(
            namespace=model_namespace,
            endpoint=get_metric_endpoint(metric=Metric.APPROXKSTEST),
            expected_metric_name=Metric.APPROXKSTEST.value.upper(),
            json_data={"modelId": gaussian_credit_model.name, "referenceTag": "TRAINING"},
        )

    def test_schedule_approxkstest_pvc(
        self, model_namespace: Namespace, trustyai_service_pvc: TrustyAIService, gaussian_credit_model: InferenceService
    ) -> None:
        verify_metric_scheduling(
            namespace=model_namespace,
            endpoint=get_metric_endpoint(metric=Metric.APPROXKSTEST, schedule=True),
            json_data={"modelId": gaussian_credit_model.name, "referenceTag": "TRAINING"},
        )

    def test_approxkstest_prometheus_query_pvc(
        self, model_namespace: Namespace, trustyai_service_pvc: TrustyAIService, gaussian_credit_model: InferenceService
    ) -> None:
        verify_trustyai_metric_prometheus(
            namespace=model_namespace,
            model=gaussian_credit_model,
            prometheus_query=f"trustyai_{Metric.APPROXKSTEST.value}" f'{{namespace="{model_namespace.name}"}}',
            metric_name=Metric.APPROXKSTEST.value,
        )


@pytest.mark.openshift
@pytest.mark.db
@pytest.mark.modelmesh
class TestDriftMetricsDB:
    """
    Verifies the different input data drift metrics available in TrustyAI, using DB storage.
    Drift metrics: Meanshift, FourierMMD, KSTest, and ApproxKSTest.

    1. Send data to the model (gaussian_credit_model).
    2. Upload training data for TrustyAI (used as baseline to calculate the drift metrics).
    3. For each metric:
        3.1. Send a basic request and verify the response.
        3.2. Send a schedule request and verify the response.
        3.3. Verify that the metric has reached Prometheus.
    """

    def test_gaussian_credit_model_metadata_db(
        self, model_namespace: Namespace, trustyai_service_db: TrustyAIService, gaussian_credit_model: InferenceService
    ) -> None:
        wait_for_modelmesh_pods_registered(namespace=model_namespace)

        path = f"{MODEL_DATA_PATH}/{gaussian_credit_model.name}"

        send_data_to_inference_service(
            inference_service=gaussian_credit_model,
            namespace=model_namespace,
            data_path=f"{path}/data_batches",
        )

        response = upload_data_to_trustyai_service(
            namespace=model_namespace,
            data_path=f"{path}/training_data.json",
        )
        assert response.status_code == http.HTTPStatus.OK

        verify_trustyai_model_metadata(
            namespace=model_namespace,
            model=gaussian_credit_model,
            data_path=path,
        )

    def test_request_meanshift_db(
        self, model_namespace: Namespace, trustyai_service_db: TrustyAIService, gaussian_credit_model: InferenceService
    ) -> None:
        verify_metric_request(
            namespace=model_namespace,
            endpoint=get_metric_endpoint(metric=Metric.MEANSHIFT),
            expected_metric_name=Metric.MEANSHIFT.value.upper(),
            json_data={"modelId": gaussian_credit_model.name, "referenceTag": "TRAINING"},
        )

    def test_schedule_meanshift_db(
        self, model_namespace: Namespace, trustyai_service_db: TrustyAIService, gaussian_credit_model: InferenceService
    ) -> None:
        verify_metric_scheduling(
            namespace=model_namespace,
            endpoint=get_metric_endpoint(metric=Metric.MEANSHIFT, schedule=True),
            json_data={"modelId": gaussian_credit_model.name, "referenceTag": "TRAINING"},
        )

    def test_meanshift_prometheus_query_db(
        self, model_namespace: Namespace, trustyai_service_db: TrustyAIService, gaussian_credit_model: InferenceService
    ) -> None:
        verify_trustyai_metric_prometheus(
            namespace=model_namespace,
            model=gaussian_credit_model,
            prometheus_query=f'trustyai_{Metric.MEANSHIFT.value}{{namespace="{model_namespace.name}"}}',
            metric_name=Metric.MEANSHIFT.value,
        )

    def test_request_fouriermmd_db(
        self, model_namespace: Namespace, trustyai_service_db: TrustyAIService, gaussian_credit_model: InferenceService
    ) -> None:
        verify_metric_request(
            namespace=model_namespace,
            endpoint=get_metric_endpoint(metric=Metric.FOURIERMMD),
            expected_metric_name=Metric.FOURIERMMD.value.upper(),
            json_data={"modelId": gaussian_credit_model.name, "referenceTag": "TRAINING"},
        )

    def test_schedule_fouriermmd_db(
        self, model_namespace: Namespace, trustyai_service_db: TrustyAIService, gaussian_credit_model: InferenceService
    ) -> None:
        verify_metric_scheduling(
            namespace=model_namespace,
            endpoint=get_metric_endpoint(metric=Metric.FOURIERMMD, schedule=True),
            json_data={"modelId": gaussian_credit_model.name, "referenceTag": "TRAINING"},
        )

    def test_fouriermmd_prometheus_query_db(
        self, model_namespace: Namespace, trustyai_service_db: TrustyAIService, gaussian_credit_model: InferenceService
    ) -> None:
        verify_trustyai_metric_prometheus(
            namespace=model_namespace,
            model=gaussian_credit_model,
            prometheus_query=f'trustyai_{Metric.FOURIERMMD.value}{{namespace="{model_namespace.name}"}}',
            metric_name=Metric.FOURIERMMD.value,
        )

    def test_request_kstest_db(
        self, model_namespace: Namespace, trustyai_service_db: TrustyAIService, gaussian_credit_model: InferenceService
    ) -> None:
        verify_metric_request(
            namespace=model_namespace,
            endpoint=get_metric_endpoint(metric=Metric.KSTEST),
            expected_metric_name=Metric.KSTEST.value.upper(),
            json_data={"modelId": gaussian_credit_model.name, "referenceTag": "TRAINING"},
        )

    def test_schedule_kstest_scheduling_request_db(
        self, model_namespace: Namespace, trustyai_service_db: TrustyAIService, gaussian_credit_model: InferenceService
    ) -> None:
        verify_metric_scheduling(
            namespace=model_namespace,
            endpoint=get_metric_endpoint(metric=Metric.KSTEST, schedule=True),
            json_data={"modelId": gaussian_credit_model.name, "referenceTag": "TRAINING"},
        )

    def test_kstest_prometheus_query_db(
        self, model_namespace: Namespace, trustyai_service_db: TrustyAIService, gaussian_credit_model: InferenceService
    ) -> None:
        verify_trustyai_metric_prometheus(
            namespace=model_namespace,
            model=gaussian_credit_model,
            prometheus_query=f'trustyai_{Metric.KSTEST.value}{{namespace="{model_namespace.name}"}}',
            metric_name=Metric.KSTEST.value,
        )

    def test_request_approxkstest_db(
        self, model_namespace: Namespace, trustyai_service_db: TrustyAIService, gaussian_credit_model: InferenceService
    ) -> None:
        verify_metric_request(
            namespace=model_namespace,
            endpoint=get_metric_endpoint(metric=Metric.APPROXKSTEST),
            expected_metric_name=Metric.APPROXKSTEST.value.upper(),
            json_data={"modelId": gaussian_credit_model.name, "referenceTag": "TRAINING"},
        )

    def test_schedule_approxkstest_db(
        self, model_namespace: Namespace, trustyai_service_db: TrustyAIService, gaussian_credit_model: InferenceService
    ) -> None:
        verify_metric_scheduling(
            namespace=model_namespace,
            endpoint=get_metric_endpoint(metric=Metric.APPROXKSTEST, schedule=True),
            json_data={"modelId": gaussian_credit_model.name, "referenceTag": "TRAINING"},
        )

    def test_approxkstest_prometheus_query_db(
        self, model_namespace: Namespace, trustyai_service_db: TrustyAIService, gaussian_credit_model: InferenceService
    ) -> None:
        verify_trustyai_metric_prometheus(
            namespace=model_namespace,
            model=gaussian_credit_model,
            prometheus_query=f"trustyai_{Metric.APPROXKSTEST.value}" f'{{namespace="{model_namespace.name}"}}',
            metric_name=Metric.APPROXKSTEST.value,
        )
