#!/usr/bin/env python3
"""Demo Amazon SQS pe LocalStack: pozitii GPS ale unei flote auto.

Operatii: creare coada, inserare mesaje, numarare, citire fara stergere,
consumare (citire + procesare + stergere), golire, stergerea cozii.

Exemple:
    python sqs_demo.py create
    python sqs_demo.py send --plate BH-01-FLT --lat 47.05 --lng 21.92
    python sqs_demo.py send-sample
    python sqs_demo.py count
    python sqs_demo.py peek
    python sqs_demo.py consume
    python sqs_demo.py purge
    python sqs_demo.py delete-queue
"""
import argparse
import json
import os
import sys

import boto3
from botocore.exceptions import BotoCoreError, ClientError

QUEUE_NAME = "gps-positions"
ENDPOINT = os.environ.get("LOCALSTACK_ENDPOINT", "http://localhost.localstack.cloud:4566")

# LocalStack accepta orice credentiale; prin conventie se foloseste test / test
sqs = boto3.client(
    "sqs",
    endpoint_url=ENDPOINT,
    region_name="us-east-1",
    aws_access_key_id="test",
    aws_secret_access_key="test",
)

SAMPLE = [
    {"plate": "BH-01-FLT", "lat": 47.05, "lng": 21.92},   # Oradea
    {"plate": "CJ-07-ABC", "lat": 46.77, "lng": 23.59},   # Cluj-Napoca
    {"plate": "B-123-FLT", "lat": 44.43, "lng": 26.10},   # Bucuresti
]


def queue_url():
    """Adresa cozii; daca nu exista, explica ce trebuie facut."""
    try:
        return sqs.get_queue_url(QueueName=QUEUE_NAME)["QueueUrl"]
    except ClientError as err:
        if "NonExistentQueue" in str(err):
            sys.exit(f"Coada '{QUEUE_NAME}' nu exista. Rulati intai: python sqs_demo.py create")
        raise


def cmd_create(_args):
    url = sqs.create_queue(QueueName=QUEUE_NAME)["QueueUrl"]
    print(f"Coada creata: {url}")


def cmd_send(args):
    body = {"plate": args.plate, "lat": args.lat, "lng": args.lng}
    resp = sqs.send_message(QueueUrl=queue_url(), MessageBody=json.dumps(body))
    print(f"Trimis {body}  (MessageId={resp['MessageId']})")


def cmd_send_sample(_args):
    url = queue_url()
    for body in SAMPLE:
        sqs.send_message(QueueUrl=url, MessageBody=json.dumps(body))
        print(f"Trimis {body}")


def cmd_count(_args):
    attrs = sqs.get_queue_attributes(
        QueueUrl=queue_url(),
        AttributeNames=["ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible"],
    )["Attributes"]
    print(f"Mesaje in coada:        {attrs['ApproximateNumberOfMessages']}")
    print(f"Mesaje in procesare:    {attrs['ApproximateNumberOfMessagesNotVisible']}")


def cmd_peek(_args):
    """Citeste mesajele fara sa le ascunda (VisibilityTimeout=0), deci raman in coada."""
    resp = sqs.receive_message(
        QueueUrl=queue_url(), MaxNumberOfMessages=10, VisibilityTimeout=0
    )
    messages = resp.get("Messages", [])
    if not messages:
        print("Coada este goala.")
    for m in messages:
        print(m["Body"])


def cmd_consume(args):
    """Un consumator real: citeste, proceseaza, sterge (cu receipt handle)."""
    url = queue_url()
    processed = 0
    while True:
        resp = sqs.receive_message(
            QueueUrl=url, MaxNumberOfMessages=10, WaitTimeSeconds=1
        )
        messages = resp.get("Messages", [])
        if not messages:
            break
        for m in messages:
            data = json.loads(m["Body"])
            print(f"Procesez: masina {data['plate']} la ({data['lat']}, {data['lng']})")
            sqs.delete_message(QueueUrl=url, ReceiptHandle=m["ReceiptHandle"])
            processed += 1
            if args.limit and processed >= args.limit:
                print(f"Gata: {processed} mesaje consumate si sterse.")
                return
    print(f"Gata: {processed} mesaje consumate si sterse.")


def cmd_purge(_args):
    sqs.purge_queue(QueueUrl=queue_url())
    print("Toate mesajele au fost sterse.")


def cmd_delete_queue(_args):
    sqs.delete_queue(QueueUrl=queue_url())
    print(f"Coada '{QUEUE_NAME}' a fost stearsa.")


def main():
    parser = argparse.ArgumentParser(description="Demo SQS pe LocalStack (pozitii GPS)")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("create", help="creeaza coada").set_defaults(func=cmd_create)

    p_send = sub.add_parser("send", help="trimite un mesaj (o pozitie GPS)")
    p_send.add_argument("--plate", required=True, help="numar de inmatriculare, ex. BH-01-FLT")
    p_send.add_argument("--lat", type=float, required=True)
    p_send.add_argument("--lng", type=float, required=True)
    p_send.set_defaults(func=cmd_send)

    sub.add_parser("send-sample", help="trimite 3 mesaje de exemplu").set_defaults(func=cmd_send_sample)
    sub.add_parser("count", help="numara mesajele din coada").set_defaults(func=cmd_count)
    sub.add_parser("peek", help="citeste mesajele fara sa le stearga").set_defaults(func=cmd_peek)

    p_consume = sub.add_parser("consume", help="citeste, proceseaza si sterge mesajele")
    p_consume.add_argument("--limit", type=int, default=0, help="se opreste dupa N mesaje (0 = toate)")
    p_consume.set_defaults(func=cmd_consume)

    sub.add_parser("purge", help="sterge toate mesajele").set_defaults(func=cmd_purge)
    sub.add_parser("delete-queue", help="sterge coada").set_defaults(func=cmd_delete_queue)

    args = parser.parse_args()
    try:
        args.func(args)
    except BotoCoreError as err:
        sys.exit(
            f"Nu ma pot conecta la LocalStack ({ENDPOINT}).\n"
            "Verificati ca LocalStack ruleaza: docker compose ps\n"
            f"Detalii: {err}"
        )


if __name__ == "__main__":
    main()
