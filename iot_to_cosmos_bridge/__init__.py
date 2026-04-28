"""
Bridge telemetry from IoT Hub/Event Hub to Cosmos DB (Mongo API).

This function consumes messages from the IoT Hub built-in Event Hub endpoint
and writes them into the same Mongo collection consumed by alarm_monitor_function.
"""

import json
import logging
import os
from datetime import datetime

import azure.functions as func
from pymongo import MongoClient


MONGODB_CONNECTION_STRING = os.environ.get("MongoDBConnectionString")
COSMOS_DATABASE = os.environ.get("COSMOS_DATABASE", "IoTDatabase")
COSMOS_COLLECTION = os.environ.get("COSMOS_COLLECTION", "iotmessages")


def _to_dict(ev: func.EventHubEvent) -> dict:
    """Convert EventHubEvent body to a dictionary safely."""
    try:
        body = ev.get_body().decode("utf-8")
        parsed = json.loads(body)
        if isinstance(parsed, dict):
            return parsed
        return {"payload": parsed}
    except Exception:
        return {"raw": ev.get_body().decode("utf-8", errors="replace")}


def _windows_filetime_now() -> int:
    """Return current UTC time as Windows FILETIME (100ns since 1601)."""
    now = datetime.utcnow()
    windows_epoch = datetime(1601, 1, 1)
    return int((now - windows_epoch).total_seconds() * 10_000_000)


def main(events: func.EventHubEvent):
    """Ingest IoT Hub batch and write into Cosmos Mongo collection."""
    if not MONGODB_CONNECTION_STRING:
        logging.error("MongoDBConnectionString not configured")
        return

    if not events:
        logging.info("No events received in this batch")
        return

    client = None
    try:
        client = MongoClient(MONGODB_CONNECTION_STRING)
        collection = client[COSMOS_DATABASE][COSMOS_COLLECTION]

        docs = []
        for ev in events:
            doc = _to_dict(ev)

            # Ensure downstream alarm monitor can sort/parse recency reliably.
            if "_timestamp" not in doc:
                doc["_timestamp"] = _windows_filetime_now()

            # Helpful traceability tag for debugging pipeline origin.
            doc.setdefault("ingest_source", "iot_hub_bridge")
            docs.append(doc)

        if docs:
            collection.insert_many(docs, ordered=False)
            logging.info(
                "Inserted %s telemetry document(s) into %s.%s",
                len(docs),
                COSMOS_DATABASE,
                COSMOS_COLLECTION,
            )
    except Exception as e:
        logging.error(f"Bridge write failed: {e}")
    finally:
        if client is not None:
            client.close()

