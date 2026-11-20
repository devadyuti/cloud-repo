"""
Serverless event-driven architecture (eu-west-1).

Flow:
  Client -> CloudFront -> API Gateway -> API Lambda
  API Lambda -> DynamoDB            (synchronous read/write)
  API Lambda -> SNS -> SQS -> Worker Lambda -> DynamoDB   (async fan-out)

Renders a PNG using the `diagrams` package (Graphviz backend).
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.network import CloudFront, APIGateway
from diagrams.aws.compute import Lambda
from diagrams.aws.database import Dynamodb
from diagrams.aws.integration import SNS, SQS
from diagrams.aws.general import Users

graph_attr = {
    "fontsize": "20",
    "labelloc": "t",
    "pad": "0.6",
    "splines": "spline",
    "nodesep": "0.8",
    "ranksep": "1.1",
}

with Diagram(
    "Serverless Event-Driven Architecture (eu-west-1)",
    filename="generated-diagrams/serverless_eventdriven_eu_west_1",
    outformat="png",
    show=False,
    direction="LR",
    graph_attr=graph_attr,
):
    users = Users("Clients")
    cdn = CloudFront("CloudFront\n(CDN / edge)")

    with Cluster("Region: eu-west-1"):
        api = APIGateway("API Gateway\n(REST API)")

        with Cluster("Synchronous API tier"):
            api_fn = Lambda("API Lambda\n(request handler)")
            table = Dynamodb("DynamoDB\n(app table)")

        with Cluster("Async processing tier"):
            topic = SNS("SNS\n(event topic)")
            queue = SQS("SQS\n(work queue)")
            worker = Lambda("Worker Lambda\n(async consumer)")

    # Synchronous request path
    users >> Edge(label="1. HTTPS") >> cdn
    cdn >> Edge(label="2. /api/*") >> api
    api >> Edge(label="3. invoke") >> api_fn
    api_fn >> Edge(label="4. read/write") >> table

    # Asynchronous fan-out path
    api_fn >> Edge(label="5. publish event") >> topic
    topic >> Edge(label="6. fan-out") >> queue
    queue >> Edge(label="7. poll") >> worker
    worker >> Edge(label="8. persist") >> table
