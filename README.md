# COSC 3657 – Unit 2: Declarative Infrastructure & Mini-K8s Reconciliation

## 1. Project Overview

This project demonstrates declarative infrastructure and automated reconciliation using Kubernetes and Python.

The main objective is to create a custom Kubernetes resource called `ResilientDeployment` and develop a Python controller that monitors the cluster and maintains the desired number of application pods.

The controller compares the desired state defined in the custom resource with the actual state of the Kubernetes cluster. If a difference is detected, it automatically takes action to correct it.

For example, if the desired number of replicas is three but one pod is deleted, the controller detects the change and creates a replacement.

## 2. Technologies Used

- Python 3.13
- Kubernetes
- kind (Kubernetes in Docker)
- Docker Desktop
- Kubernetes Python Client
- YAML

## 3. Project Structure

The project contains the following main files:

```text
Assignment 2/
│
├── crd_definition.yaml
├── sample_cr.yaml
├── reconciler.py
└── README.md
```

**File descriptions:**

- `crd_definition.yaml`: Defines the custom Kubernetes resource called ResilientDeployment.
- `sample_cr.yaml`: Defines the desired application configuration, including the number of replicas and container image.
- `reconciler.py`: Contains the Python controller responsible for monitoring Kubernetes events and correcting differences between the desired and actual states.
- `README.md`: Provides project documentation.

## 4. Kubernetes Cluster Setup

A local Kubernetes cluster was created using kind.

The cluster contains three nodes:

- One control-plane node
- Two worker nodes

The cluster was created using:

```bash
kind create cluster --name cosc3657-unit2 --config kind-config.yaml
```

To verify the cluster nodes:

```bash
kubectl get nodes
```

All three nodes should report a Ready status.

## 5. Installing Dependencies

The project uses a Python virtual environment to manage its dependencies.

Activate the environment:

```bash
source venv/bin/activate
```

Install the required packages:

```bash
pip install kubernetes rich pyyaml
```

## 6. Creating the Custom Resource

The Custom Resource Definition (CRD) is defined in `crd_definition.yaml`.

It creates a new Kubernetes resource type called `ResilientDeployment`.

The resource allows the user to specify:

- The desired number of replicas.
- The container image used by the application.

Apply the CRD:

```bash
kubectl apply -f crd_definition.yaml
```

Apply the sample custom resource:

```bash
kubectl apply -f sample_cr.yaml
```

The sample resource requests three application pods using the `hashicorp/http-echo:1.0.0` image.

## 7. Running the Python Reconciler

The Python controller connects to the Kubernetes cluster using the Kubernetes Python Client.

Start the controller with:

```bash
python reconciler.py
```

The controller performs an initial reconciliation and then starts two Kubernetes event watches:

1. **Pod Event Watch:** Monitors pod events, including additions, modifications, and deletions.
2. **Resource Event Watch:** Monitors changes to the ResilientDeployment custom resource.

When an event occurs, the controller runs the reconciliation process.

It compares the desired replica count with the current number of active pods and calculates the difference, also known as drift.

If the number of pods is too low, new pods are created.

If the number of pods is too high, extra pods are deleted.

If both values match, the controller reports that the system is in equilibrium.

## 8. Reconciliation and Self-Healing

The reconciliation process is designed to maintain the desired state automatically.

For example, if the desired replica count is three and only two active pods remain, the controller detects the difference:

```text
[RECONCILE] Desired: 3 | Current: 2 | Drift: 1
Creating 1 missing pod(s)...
Created a new pod.
```

After creating the replacement, the controller checks the cluster again.

When the desired and actual states match, it reports:

```text
[RECONCILE] Desired: 3 | Current: 3 | Drift: 0
EQUILIBRIUM: System is in the desired state.
```

This process allows the application to recover automatically when pods are deleted.

## 9. Testing

Several tests were performed to verify the controller.

### Test 1: Initial Deployment

The custom resource was configured to request three replicas.

The controller detected the initial difference and created the required pods.

### Test 2: Forced Pod Deletion

One application pod was manually deleted using:

```bash
kubectl delete pod POD_NAME --grace-period=0 --force
```

The controller detected the pod event, identified that one replica was missing, and automatically created a replacement.

The cluster returned to three running pods.

### Test 3: Scaling Up

The desired replica count was changed from three to five:

```bash
kubectl patch resilientdeployment echo-cluster --type='json' -p='[{"op": "replace", "path": "/spec/replicas", "value": 5}]'
```

The controller detected the custom resource modification and created two additional pods.

### Test 4: Scaling Down

The desired replica count was changed from five back to three:

```bash
kubectl patch resilientdeployment echo-cluster --type='json' -p='[{"op": "replace", "path": "/spec/replicas", "value": 3}]'
```

The controller detected the change and removed two extra pods.

### Test Results

All tests were successful:

- Three replicas were created during initial deployment.
- A deleted pod was automatically replaced.
- The application successfully scaled from three to five replicas.
- The application successfully scaled from five back to three replicas.
- The controller repeatedly confirmed equilibrium when the desired and actual states matched.

## 10. Challenges and Learning

One of the main challenges was configuring the local Kubernetes environment and making sure the Python controller could communicate with the cluster.

Another challenge was implementing the reconciliation process so that it could detect changes and correct the cluster without creating unnecessary pods.

The project also helped demonstrate the importance of event-driven programming. Instead of relying only on a repeating polling loop, the final controller uses Kubernetes Watch events to respond to changes in the cluster.

Through this assignment, I gained practical experience with Kubernetes, custom resources, Python multithreading, event monitoring, and automated reconciliation.

## 11. Use of AI

ChatGPT was used as a supporting tool during the development of this project. It helped with troubleshooting the development environment, understanding Kubernetes concepts, reviewing the reconciliation logic, and resolving implementation issues.

The project was tested locally using kind and Kubernetes commands to verify that the controller behaved as expected.

## 12. Conclusion

This project demonstrates how declarative infrastructure can be used to maintain an application's desired state.

By creating a custom Kubernetes resource and a Python-based event-driven controller, the system can detect changes, calculate drift, and automatically correct differences.

The final implementation successfully demonstrated automatic pod replacement, scaling up, scaling down, and maintaining equilibrium within the Kubernetes cluster.
