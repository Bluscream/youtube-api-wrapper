import asyncio

async def run_in_background(func, *args, **kwargs):
    task = asyncio.create_task(func(*args, **kwargs))
    return task

def main():
    # Start a background task
    bg_task = run_in_background(example_function, "Hello", "World")

    print("Background task started. Doing other stuff...")

    # Do other stuff in the meantime
    import time
    time.sleep(2)  # Simulate doing other things

    # Now we wait for the result
    result = asyncio.run(bg_task)
    print(f"Result: {result}")

async def example_function(message: str) -> str:
    await asyncio.sleep(3)  # Simulate a long-running operation
    return f"{message} from background"

if __name__ == "__main__":
    main()
