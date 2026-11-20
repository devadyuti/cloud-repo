"""
Parallel Multi-Language Transcribe Architecture

S3 -> Lambda -> Step Functions -> parallel Amazon Transcribe (one language per job) -> S3

The Step Functions Map state fans out one StartTranscriptionJob per target
language (20 in the sample). The diagram shows 3 concrete language jobs plus a
node representing the remaining jobs; concurrency and quota limits are called
out separately in the accompanying notes.

Render:
    python3 parallel_transcribe_architecture.py
Produces: parallel_transcribe_architecture.png
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.storage import SimpleStorageServiceS3 as S3
from diagrams.aws.compute import Lambda
from diagrams.aws.integration import StepFunctions, Eventbridge
from diagrams.aws.ml import Transcribe
from diagrams.aws.general import User

graph_attr = {
    "fontsize": "20",
    "labelloc": "t",
    "pad": "0.6",
    "splines": "spline",
    "nodesep": "0.6",
    "ranksep": "1.1",
    "bgcolor": "white",
}

node_attr = {"fontsize": "13"}

with Diagram(
    "Parallel Multi-Language Transcribe Pipeline",
    filename="parallel_transcribe_architecture",
    show=False,
    direction="LR",
    graph_attr=graph_attr,
    node_attr=node_attr,
):
    user = User("User / Upstream\nSystem")

    with Cluster("Ingestion"):
        s3_in = S3("S3 Input Bucket\n(audio / video media)")

    with Cluster("Trigger & Orchestration"):
        trigger = Lambda("Lambda\nTrigger / Job Preparer")
        sfn = StepFunctions("Step Functions\nState Machine")

    with Cluster("Map State - one language per job (20 total, 3 shown)"):
        job_en = Transcribe("StartTranscriptionJob\nen-US")
        job_es = Transcribe("StartTranscriptionJob\nes-ES")
        job_fr = Transcribe("StartTranscriptionJob\nfr-FR")
        job_rest = Transcribe("... 17 more jobs\n(de-DE, ja-JP, hi-IN, ...)")

    with Cluster("Completion & Results"):
        events = Eventbridge("EventBridge\nJob State Change")
        s3_out = S3("S3 Output Bucket\ntranscripts/{lang}/...json")

    # Ingestion -> trigger -> orchestration
    user >> Edge(label="1. Upload media") >> s3_in
    s3_in >> Edge(label="2. ObjectCreated event") >> trigger
    trigger >> Edge(label="3. StartExecution\n(media + 20-language list)") >> sfn

    # Fan-out: Step Functions Map state -> one Transcribe job per language
    sfn >> Edge(label="4. Map fan-out") >> job_en
    sfn >> job_es
    sfn >> job_fr
    sfn >> Edge(style="dashed") >> job_rest

    # Each job writes its own transcript to S3
    job_en >> Edge(label="5. transcript per language") >> s3_out
    job_es >> s3_out
    job_fr >> s3_out
    job_rest >> Edge(style="dashed") >> s3_out

    # Completion signalling back to Step Functions
    job_en >> Edge(label="6. job COMPLETE", style="dashed") >> events
    job_rest >> Edge(style="dashed") >> events
    events >> Edge(label="7. resume / aggregate") >> sfn
