from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException
import threading

# CONFIGURATION
GROUP = "cosc3657.local"
VERSION = "v1alpha1"
PLURAL = "resilientdeployments"
NAMESPACE = "default"
RESOURCE_NAME = "echo-cluster"

LABEL_SELECTOR = "app.kubernetes.io/managed-by=echo-cluster"

# Prevent two watch threads from reconciling at the same time.
reconcile_lock = threading.Lock()


def connect_to_kubernetes():
    """Connect to the Kubernetes cluster."""
    config.load_kube_config()

    global core_api, custom_api

    core_api = client.CoreV1Api()
    custom_api = client.CustomObjectsApi()

    print("Connected to Kubernetes!")


def get_desired_replicas():
    """Read the desired replica count from the custom resource."""
    resource = custom_api.get_namespaced_custom_object(
        group=GROUP,
        version=VERSION,
        namespace=NAMESPACE,
        plural=PLURAL,
        name=RESOURCE_NAME
    )

    replicas = resource["spec"]["replicas"]
    image = resource["spec"]["image"]

    return replicas, image


def get_current_pods():
    """Find active pods managed by this controller."""
    pods = core_api.list_namespaced_pod(
        namespace=NAMESPACE,
        label_selector=LABEL_SELECTOR
    )

    # Ignore terminating, completed, and failed pods.
    active_pods = []

    for pod in pods.items:
        if pod.metadata.deletion_timestamp is not None:
            continue

        if pod.status.phase in ["Succeeded", "Failed"]:
            continue

        active_pods.append(pod)

    return active_pods


def create_pod(image):
    """Create one new pod."""
    pod = client.V1Pod(
        metadata=client.V1ObjectMeta(
            generate_name="echo-cluster-",
            labels={
                "app.kubernetes.io/managed-by": "echo-cluster"
            }
        ),
        spec=client.V1PodSpec(
            containers=[
                client.V1Container(
                    name="echo",
                    image=image,
                    args=["-text=Hello from echo-cluster"],
                    ports=[
                        client.V1ContainerPort(container_port=5678)
                    ]
                )
            ]
        )
    )

    core_api.create_namespaced_pod(
        namespace=NAMESPACE,
        body=pod
    )

    print("Created a new pod.")


def delete_pod(pod):
    """Delete an extra pod."""
    core_api.delete_namespaced_pod(
        name=pod.metadata.name,
        namespace=NAMESPACE
    )

    print(f"Deleted extra pod: {pod.metadata.name}")


def reconcile():
    """Compare desired and actual state, then correct differences."""

    # Only allow one reconciliation at a time.
    with reconcile_lock:

        desired, image = get_desired_replicas()
        pods = get_current_pods()

        current = len(pods)
        difference = desired - current

        print(
            f"[RECONCILE] Desired: {desired} | "
            f"Current: {current} | Drift: {difference}"
        )

        if difference > 0:
            print(f"Creating {difference} missing pod(s)...")

            for _ in range(difference):
                create_pod(image)

        elif difference < 0:
            print(f"Removing {-difference} extra pod(s)...")

            for pod in pods[:abs(difference)]:
                delete_pod(pod)

        else:
            print("EQUILIBRIUM: System is in the desired state.")


def watch_pod_events():
    """Watch for pod changes and trigger reconciliation."""

    while True:
        event_watcher = watch.Watch()

        try:
            print("Watching for pod events...")

            for event in event_watcher.stream(
                core_api.list_namespaced_pod,
                namespace=NAMESPACE,
                label_selector=LABEL_SELECTOR,
                timeout_seconds=30
            ):
                event_type = event["type"]

                if event_type in ["ADDED", "MODIFIED", "DELETED"]:
                    print(f"[POD EVENT] {event_type}")
                    reconcile()

        except ApiException as error:
            print(f"Pod watch API error: {error.reason}")

        except Exception as error:
            print(f"Pod watch error: {error}")

        finally:
            event_watcher.stop()


def watch_resource_events():
    """Watch for changes to the ResilientDeployment resource."""

    while True:
        event_watcher = watch.Watch()

        try:
            print("Watching for ResilientDeployment changes...")

            for event in event_watcher.stream(
                custom_api.list_namespaced_custom_object,
                group=GROUP,
                version=VERSION,
                namespace=NAMESPACE,
                plural=PLURAL,
                timeout_seconds=30
            ):
                event_type = event["type"]
                resource = event["object"]

                if resource.get("metadata", {}).get("name") != RESOURCE_NAME:
                    continue

                if event_type in ["ADDED", "MODIFIED", "DELETED"]:
                    print(f"[RESOURCE EVENT] {event_type}")
                    reconcile()

        except ApiException as error:
            print(f"Resource watch API error: {error.reason}")

        except Exception as error:
            print(f"Resource watch error: {error}")

        finally:
            event_watcher.stop()


def main():
    connect_to_kubernetes()

    print("\n=== COSC 3657 Kubernetes Reconciler Started ===")

    # Perform an initial reconciliation.
    try:
        reconcile()

    except ApiException as error:
        print(f"Initial reconciliation API error: {error.reason}")

    except Exception as error:
        print(f"Initial reconciliation error: {error}")

    # Start the two watch threads.
    pod_thread = threading.Thread(
        target=watch_pod_events,
        daemon=True
    )

    resource_thread = threading.Thread(
        target=watch_resource_events,
        daemon=True
    )

    pod_thread.start()
    resource_thread.start()

    print("Controller is running and listening for Kubernetes events.")

    # Keep the main program alive.
    try:
        while True:
            pod_thread.join(timeout=1)
            resource_thread.join(timeout=1)

    except KeyboardInterrupt:
        print("\nController stopped.")


if __name__ == "__main__":
    main()
