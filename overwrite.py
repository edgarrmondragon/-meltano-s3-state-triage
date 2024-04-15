#!/usr/bin/env python

"""Simple Singer tap."""

# flake8: noqa

from __future__ import annotations

import argparse
import datetime
import json
import sys

DEFAULT_STATE = {
    "bookmarks": {},
}

def _gen_catalog(streams):
    return {
        "streams": [
            {
                "tap_stream_id": stream_id,
                "schema": {
                    "properties": {
                        "id": {"type": "integer"},
                        "created_at": {"type": "string", "format": "date-time"},
                    },
                },
                "metadata": [
                    {
                        "breadcrumb": [],
                        "metadata": {
                            "selected": True,
                        },
                    },
                ],
            }
            for stream_id in streams
        ],
    }


def sync_stream(stream_id: str, timestamp: str):
    """Sync a stream."""
    sys.stdout.write(
        json.dumps(
            {
                "type": "SCHEMA",
                "stream": stream_id,
                "schema": {
                    "properties": {
                        "id": {"type": "integer"},
                        "created_at": {"type": "string", "format": "date-time"},
                    },
                },
                "key_properties": ["id"],
            },
        )
        + "\n",
    )
    sys.stdout.write(
        json.dumps(
            {
                "type": "RECORD",
                "stream": stream_id,
                "record": {
                    "id": 1,
                    "created_at": timestamp,
                },
            },
        )
        + "\n",
    )


def is_selected(stream_id: str, catalog: dict):
    """Check if a stream is selected."""
    for stream in catalog["streams"]:
        if stream["tap_stream_id"] != stream_id:
            continue
        metadata = stream.get("metadata", [])
        stream_metadata = next(
            filter(lambda m: m.get("breadcrumb") == [], metadata),
            {},
        )
        print(f"stream_metadata: {stream_metadata}", file=sys.stderr)
        return stream_metadata.get("metadata", {}).get("selected", False)

    return False


def sync(config: dict, catalog: dict, state: dict):
    """Sync data."""
    print(f"catalog: {catalog}", file=sys.stderr)
    timestamp = config.get(
        "ts",
        datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
    )
    if config.get("overwrite_state", True):
        state = DEFAULT_STATE

    state = state or DEFAULT_STATE

    print(f"state: {state}", file=sys.stderr)

    for stream_id in config.get("streams", []):
        if not is_selected(stream_id, catalog):
            print(f"stream {stream_id} is not selected", file=sys.stderr)
            continue
        sync_stream(stream_id, timestamp)
        state["bookmarks"][stream_id] = {"created_at": timestamp}

    sys.stdout.write(json.dumps({"type": "STATE", "value": state}))


def discover(config):
    """Discover catalog."""
    catalog = _gen_catalog(config.get("streams", [1, 2, 3]))
    sys.stdout.write(json.dumps(catalog))


def main():
    """Main entrypoint."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=argparse.FileType("r"))
    parser.add_argument("--catalog", type=argparse.FileType("r"))
    parser.add_argument("--state", type=argparse.FileType("r"))
    parser.add_argument("--discover", action="store_true")
    args = parser.parse_args()

    config = json.load(args.config) if args.config else {}
    print(f"config: {config}", file=sys.stderr)

    if args.discover:
        discover(config)
        return
    
    catalog = json.load(args.catalog) if args.catalog else {}
    state = json.load(args.state) if args.state else {}

    sync(config, catalog, state)


if __name__ == "__main__":
    main()
