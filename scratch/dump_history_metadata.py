import asyncio
import logging
from temporalio.client import Client

logging.basicConfig(level=logging.INFO)

async def main():
    client = await Client.connect("localhost:7233")
    
    # Get handle for the completed workflow execution
    handle = client.get_workflow_handle("http-test-01", run_id="019e906b-b52f-7bcf-8034-8c6223511083")
    
    print("\n--- Parsing Event History for http-test-01 ---")
    async for event in handle.fetch_history_events():
        event_type = event.event_type
        print(f"\n[Event ID: {event.event_id}] Type: {event_type}")
        
        # 1. Activity Scheduled (Type 11)
        if event.HasField("activity_task_scheduled_event_attributes"):
            attrs = event.activity_task_scheduled_event_attributes
            print(f"  ActivityType: {attrs.activity_type.name}")
            print(f"  ActivityId:   {attrs.activity_id}")
            # Decode input payloads
            if attrs.input and attrs.input.payloads:
                for idx, payload in enumerate(attrs.input.payloads):
                    metadata = {k: v.decode() for k, v in payload.metadata.items()}
                    try:
                        data = payload.data.decode()
                    except UnicodeDecodeError:
                        data = repr(payload.data)
                    print(f"  Activity Input Payload {idx}: metadata={metadata}, data={data}")
                    
        # 2. Activity Completed (Type 13)
        elif event.HasField("activity_task_completed_event_attributes"):
            attrs = event.activity_task_completed_event_attributes
            print(f"  Scheduled Event ID: {attrs.scheduled_event_id}")
            # Decode result payloads
            if attrs.result and attrs.result.payloads:
                for idx, payload in enumerate(attrs.result.payloads):
                    metadata = {k: v.decode() for k, v in payload.metadata.items()}
                    data = payload.data.decode()
                    print(f"  Activity Result Payload {idx}: metadata={metadata}, data={data}")

if __name__ == "__main__":
    asyncio.run(main())
