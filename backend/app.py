import os
import threading
import time
from typing import Optional

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from prompts import PROMPTS

app = FastAPI(title="Crypto Autochat Test Harness")

state = {
    "running": False,
    "delay_seconds": 5,
    "sent_count": 0,
    "max_messages": 0,
    "target_url": "",
    "last_message": None,
    "thread": None,
}

lock = threading.Lock()


class StartRequest(BaseModel):
    target_url: str = Field(..., description="Endpoint test milik lo sendiri")
    delay_seconds: int = Field(default=5, ge=1, le=3600)
    max_messages: int = Field(default=100, ge=1, le=100000)


def worker():
    index = 0

    while True:
        with lock:
            if not state["running"]:
                break

            delay_seconds = state["delay_seconds"]
            max_messages = state["max_messages"]
            target_url = state["target_url"]
            sent_count = state["sent_count"]

            if sent_count >= max_messages:
                state["running"] = False
                break

            message = PROMPTS[index % len(PROMPTS)]
            index += 1

        try:
            resp = requests.post(
                target_url,
                json={"message": message},
                timeout=20,
            )
            resp.raise_for_status()

            with lock:
                state["sent_count"] += 1
                state["last_message"] = message

        except Exception as e:
            with lock:
                state["running"] = False
                state["last_message"] = f"ERROR: {str(e)}"
            break

        time.sleep(delay_seconds)


@app.get("/")
def root():
    return {"ok": True, "service": "crypto-autochat-test-harness"}


@app.get("/status")
def status():
    with lock:
        return {
            "running": state["running"],
            "delay_seconds": state["delay_seconds"],
            "sent_count": state["sent_count"],
            "max_messages": state["max_messages"],
            "target_url": state["target_url"],
            "last_message": state["last_message"],
        }


@app.post("/start")
def start(req: StartRequest):
    with lock:
        if state["running"]:
            raise HTTPException(status_code=400, detail="Worker already running")

        state["running"] = True
        state["delay_seconds"] = req.delay_seconds
        state["max_messages"] = req.max_messages
        state["target_url"] = req.target_url
        state["sent_count"] = 0
        state["last_message"] = None

        t = threading.Thread(target=worker, daemon=True)
        state["thread"] = t
        t.start()

    return {"ok": True, "message": "Worker started"}


@app.post("/stop")
def stop():
    with lock:
        state["running"] = False
    return {"ok": True, "message": "Worker stopped"}


@app.post("/mock-receiver")
def mock_receiver(payload: dict):
    # Endpoint test lokal supaya lo bisa cek flow dulu
    return {
        "ok": True,
        "received": payload.get("message"),
    }
