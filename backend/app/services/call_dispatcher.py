import uuid

class CallDispatcher:
    def dispatch(self, queue_item_id: uuid.UUID) -> None:
        """
        Mock interface for handing off a CLAIMED job to the voice layer.
        In a real scenario, this might push a message to Celery, AWS SQS, 
        or directly invoke a Twilio/AI voice agent endpoint.
        """
        print(f"Handoff to Worker: Queue Item {queue_item_id} dispatched.")

call_dispatcher = CallDispatcher()
